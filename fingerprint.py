import argparse
import os
from scapy.all import *
import pyshark
import binascii
from collections import OrderedDict
from datetime import datetime
import pandas as pd
import json
from typing import List
from utils.aggregate_diffs import aggregate_diffs
from concurrent.futures import ThreadPoolExecutor

def create_diff_string(diff_indices, payload, invisible=False):
    diff_string = ''
    strike_through = '\u0336' if not invisible else ''
    for i in range(len(payload)):
        if i in diff_indices:
            diff_string += payload[i] + strike_through
        else:
            diff_string += payload[i] if not invisible else '\u2800'
    return diff_string

# Filter the packets in the input pcap file based on the packet numbers and write the filtered packets to the output pcap file
def filter_pcap(input_file, output_file, packet_numbers):
    packets = rdpcap(input_file)
    filtered_packets = [packet for i, packet in enumerate(packets, start=1) if i in packet_numbers]
    wrpcap(output_file, filtered_packets)

def compare_strings(s1, s2):
    return [i for i in range(min(len(s1), len(s2))) if s1[i] == s2[i]]

# Compares two strings and given set of indices. Return a list of indices where the indices are different.
def compare_strings_with_indices(s1, s2, indices):
    return [i for i in indices if s1[i] != s2[i]]
    

def compare_string_to_all_strings(string, strings):
    mutual_indices = set()
    for i in range(len(strings)):
      s = strings[i]
      if i == 0:
         mutual_indices = set(compare_strings(string, s))
      else: 
         different_indices = compare_strings_with_indices(string, s, mutual_indices)
         mutual_indices = mutual_indices.difference(different_indices)

    return mutual_indices

def find_diffs(new_string, common_indices, common_string):
    not_matching_indices = []
    for m in common_indices:
        if common_string[m] != new_string[m]:
            not_matching_indices.append(m)
            
    return not_matching_indices

def escape_csv_delimiter(s):
    s = s.replace('"', '""')
    return f"""\"{s}\""""
        
def extract_packet(packet):
    data = OrderedDict()

    highest_layer = packet.highest_layer
    data['proto'] = highest_layer # Highest layer name is the protocol. Note that this is up to the highest layer that pyshark (tshark) dissect to.
    data['length'] = 0 # Init to 0 as some packets might not have a payload that thsark can extract
    data['payload'] = ''
    data['packet_number'] = packet.number

    try:
        if hasattr(packet, 'tcp') and hasattr(packet.tcp, 'payload'):
            data['payload'] = binascii.unhexlify(packet.tcp.payload.replace(':', '')).decode('latin-1', errors='ignore')
            data['length'] = len(data['payload']) # If application layer has some payload use that length as otherwise an edge case can happen where two different application layer payloads are matched because the transport layer frame was of the different size and the total length happens to match
        if hasattr(packet, 'udp') and hasattr(packet.udp, 'payload'):
            data['payload'] = binascii.unhexlify(packet.udp.payload.replace(':', '')).decode('latin-1', errors='ignore')
            data['length'] = len(data['payload'])
    except Exception as e:
        print(f"Error when handling packet #{packet.number}: {data}")
        print(f"Error: {e}")
        exit(1)

    return data

# Cache parsed packets
parsed_packets_map = {}

def extract_pcap(pcap_file, time=None):
    # if pcap_file in parsed_packets_map:
    #     return parsed_packets_map[pcap_file]
    # else:
        display_filter = f"frame.time_relative < {time}" if time else None
        packets = pyshark.FileCapture(pcap_file, include_raw=False, use_json=True, display_filter=display_filter) # There are some bugs with the include_raw parameter in pyshark (and poor documentation, false types etc.). So set it to false. 
        extracted_packets = [extract_packet(packet) for packet in packets]
        parsed_packets = [(p['proto'], p['length'], p['payload'], p['packet_number']) for p in extracted_packets]

        # parsed_packets_map[pcap_file] = parsed_packets

        packets.close()

        return parsed_packets

# Creates a version fingerprint from the given pcap files list. 
def create_version_fingerprint(pcap_files, limit=None, time=None):
  pcap_files.sort()
  common_packets = set()
  fingerprint = {}

  limit = len(pcap_files)
  print('Extracting packets from old pcap files...')
  for i in range(limit):
    packets = set()
    pcap_file = pcap_files[i]
    print(f'Extracting packets from {pcap_file}... Progress: {i+1}/{limit}')
    parsed_packets = extract_pcap(pcap_file=pcap_file, time=time)
    for packet in parsed_packets:
      proto, length, payload, number = packet
      packets.add((proto, length))
      if (proto, length) not in fingerprint:
        fingerprint[(proto, length)] = {
          'payloads': set([payload])
        }
      else: 
        fingerprint[(proto, length)]['payloads'].add(payload)

      if i == 0:
        common_packets.add((proto, length))

    common_packets = common_packets.intersection(packets)

  print('Finished extracting packets from old pcap files.')

  print('Determining the common values between the old packets. I.e. fingerprinting the version...')

  def process_key(key):
    if key not in common_packets:
      return key, None
    
    payloads = list(fingerprint[key]['payloads'])
    common_indices = compare_string_to_all_strings(payloads[0], payloads)
    return key, common_indices

  with ThreadPoolExecutor() as executor:
    results = list(executor.map(process_key, fingerprint.keys()))

  for key, common_indices in results:
    if common_indices is not None:
      fingerprint[key]['common_payload_indices'] = common_indices

  fingerprint['common_packets'] = common_packets
  print('Version fingerprinting completed.')
  return fingerprint

def add_diff_packet_to_df(df, packet_number, total_packets, proto, length, payload, new_packet, missing_packet, diff_indices, fingerprint_indices):
  payload_diff = escape_csv_delimiter(create_diff_string(diff_indices, payload)) if not new_packet and not missing_packet else ''
  payload_diff_invisible = escape_csv_delimiter(create_diff_string(diff_indices, payload, invisible=True)) if not new_packet and not missing_packet else ''
  payload = escape_csv_delimiter(payload) 

  return pd.concat([df, pd.DataFrame({
    'packet_number': [packet_number],
    'total_packets': [total_packets],
    'proto': [proto],
    'length': [length],
    'new_packet': [new_packet],
    'missing_packet': [missing_packet],
    'payload': [payload],
    'payload_diff': [payload_diff],
    'payload_diff_invisible': [payload_diff_invisible],
    'diff_indices': [diff_indices if not new_packet and not missing_packet else ''],
    'fingerprint_indices': [fingerprint_indices if not new_packet else '']
  })], ignore_index=True)

# Compare a pcap file to a fingerprint. Save the differences to a new pcap file and a CSV file.
def compare_pcap_to_fingerprint(fingerprint, pcap_file, result_dir, fingerprint_version, time=None):
  common_packets = fingerprint['common_packets'].copy()

  print(f'\tExtracting packets from the pcap file...')

  new_version_packets = extract_pcap(pcap_file, time=time)

  print(f'\tFinished extracting packets from the pcap file.')

  different_packets_df = pd.DataFrame(columns=['packet_number', 'total_packets', 'proto', 'length', 'new_packet', 'missing_packet', 'payload', 'payload_diff', 'payload_diff_invisible', 'diff_indices', 'fingerprint_indices'])

  print(f'\tComparing packets with the fingerprint...')
  total_packets = len(new_version_packets)
  for packet in new_version_packets:
    proto, length, payload, number = packet
    common_packets.discard((proto, length))

    if (proto, length) in fingerprint:
      packet_is_different = False

      if (proto, length) in fingerprint['common_packets']:
        fingerprint_packets = fingerprint[(proto, length)]

        # Find the different indices in strings between the new payload and the fingerprint payload
        diffs = find_diffs(new_string=payload, common_indices=fingerprint_packets['common_payload_indices'], common_string=list(fingerprint_packets['payloads'])[0])

        # Packet is different if diffs is not empty
        packet_is_different = len(diffs) > 0

      if packet_is_different:
        different_packets_df = add_diff_packet_to_df(df=different_packets_df, packet_number=number, total_packets=total_packets, proto=proto, length=length, payload=payload, new_packet=False, missing_packet=False, diff_indices=diffs, fingerprint_indices=fingerprint_packets['common_payload_indices'])
    else: 
      different_packets_df = add_diff_packet_to_df(df=different_packets_df, packet_number=number, total_packets=total_packets, proto=proto, length=length, payload=payload, new_packet=True, missing_packet=False, diff_indices='', fingerprint_indices='')

  # Add all the missing packets
  for proto, length in list(common_packets):
    different_packets_df = add_diff_packet_to_df(df=different_packets_df, packet_number=0, total_packets=total_packets, proto=proto, length=length, payload=list(fingerprint[(proto, length)]['payloads'])[0], new_packet=False, missing_packet=True, diff_indices='', fingerprint_indices='')


  file_end = pcap_file.split('/')[-1].split('_')
  new_version = file_end[1] + '_' + file_end[2].split('.')[0]
  filename = f"{fingerprint_version}_to_{new_version}"

  # Write the different packets to a new pcap file
  different_packet_numbers = different_packets_df['packet_number'].tolist()
  output_pcap_file = os.path.join(result_dir, f'{filename}.pcap')
  filter_pcap(input_file=pcap_file, output_file=output_pcap_file, packet_numbers=different_packet_numbers)

  # Write the different packets to a CSV file
  output_csv_file = os.path.join(result_dir, f'{filename}.csv')
  different_packets_df.to_csv(output_csv_file, index=False, escapechar='\\')

# Choose the files to be used for fingerprinting and testing
# 
# For each version a set of test files need to be chosen (The files that are compared against the fingerprint)
# This also includes the version that is used for the fingerprint. We also want to compare the fingerprint version against its own version. 
def choose_files(pcap_dir: str, fingerprint_version: str, test_versions: List[str]):
  application_name = pcap_dir.split('/')[-1].split('-')[0]

  # Fetch all of the pcap files in the directory that start with the application name
  pcap_files = [f for f in os.listdir(pcap_dir) if f.startswith(application_name) and f.endswith('.pcap')]

  # Fetch all the files that qualify for fingerprinting, i.e. version matches. 
  fingerprint_pcap_files = [f for f in pcap_files if fingerprint_version in f]
  test_pcap_files: List[str] = []

  # The percentage of files that should be used for fingerprinting. Rest are left for testing/comparison against the fingerprint. 
  fingerprint_file_percentage = 0.5
  test_file_percentage = 1 - fingerprint_file_percentage
  test_file_amount = int(len(fingerprint_pcap_files) * test_file_percentage)
  for test_version in test_versions:
    version_pcap_files = [f for f in pcap_files if test_version in f]
    files = version_pcap_files[:test_file_amount]
    test_pcap_files.extend(files)

    # Make sure to remove the test file from the fingerprint files if the version is the same. If we test a file against the fingerprint that was also used to create the fingerprint, the result is misleading. 
    if test_version == fingerprint_version:
      print(test_file_amount, len(version_pcap_files), len(fingerprint_pcap_files))
      for i in range(test_file_amount):
        fingerprint_pcap_files.remove(version_pcap_files[i])

  fingerprint_pcap_files = [os.path.join(pcap_dir, f) for f in fingerprint_pcap_files]

  # Create a directory to store the results
  result_dir = os.path.join(pcap_dir, 'fingerprint_comparison')
  os.makedirs(result_dir, exist_ok=True)

  return fingerprint_pcap_files, test_pcap_files, result_dir
   
def compare_pcap_files_to_fingerprint(fingerprint, fingerprint_version, pcap_files, result_dir, pcap_dir, time=None):
  for pcap_file in pcap_files:
    pcap_file = os.path.join(pcap_dir, pcap_file)
    print(f"Comparing {pcap_file} to fingerprint version {fingerprint_version}")
    compare_pcap_to_fingerprint(fingerprint=fingerprint, pcap_file=pcap_file, result_dir=result_dir, fingerprint_version=fingerprint_version, time=time)
    print(f"Finished comparing {pcap_file} to fingerprint version {fingerprint_version}\n")

def load_configuration(config_file, pcap_dir):
  # Load configuration from JSON file. If config file is not provided, use the default config.json in the pcap directory
  if not config_file:
    config_file = os.path.join(pcap_dir, 'config.json') 

  with open(config_file, 'r') as f:
      config = json.load(f)

  name = config.get('name')
  reruns = config.get('reruns_default')
  timeout = config.get('timeout')
  url = config.get('url')
  jobs = config.get('jobs')
  label = config.get('label')

  # Check if JSON fields are correctly parsed
  if not name or not isinstance(reruns, int) or not timeout or not url:
      raise ValueError("Error: Missing or invalid fields in the JSON configuration file.")

  print(f"Configuration loaded:")
  print(f"Name: {name}")
  print(f"Default reruns: {reruns}")
  print(f"Timeout: {timeout}")
  print(f"URL: {url}")
  print(f"Label: {label}")
  print(f"Jobs: {jobs}")
  print("--------------------------------\n")

  versions = [job.get('version') for job in jobs]

  return jobs, versions

def main(pcap_dir, config_file = None, time=None):
  now = datetime.now()

  jobs, versions = load_configuration(config_file=config_file, pcap_dir=pcap_dir)

  for job in jobs:
    fingerprint_version = job.get('version')
    print(f"Comparing fingerprint version {fingerprint_version} to the following versions: {versions}")
    fingerprint_pcap_files, test_pcap_files, result_dir = choose_files(pcap_dir=pcap_dir, fingerprint_version=fingerprint_version, test_versions=versions)
    fingerprint = create_version_fingerprint(pcap_files=fingerprint_pcap_files, time=time)
    compare_pcap_files_to_fingerprint(fingerprint=fingerprint, fingerprint_version=fingerprint_version, pcap_files=test_pcap_files, result_dir=result_dir, pcap_dir=pcap_dir, time=time)

  # Aggregate the differences
  result_dir = os.path.join(pcap_dir, 'fingerprint_comparison')
  aggregate_diffs(result_dir)

  print('---------------------------------')
  print(f"Completed. Time taken: {datetime.now() - now}")

if __name__ == "__main__":
  # Take in three arguments: The directory of the pcap files, the old version, and the new version 
  parser = argparse.ArgumentParser(description='Detect Helm chart version change.')
  parser.add_argument('pcap_dir', type=str, help='Directory containing the PCAP files')
  parser.add_argument('-c', '--config_file_path', required=False, type=str, help='Path to the JSON configuration file')

  args = parser.parse_args()
  pcap_dir = args.pcap_dir
  config_file = args.config_file_path

  main(config_file=config_file, pcap_dir=pcap_dir)