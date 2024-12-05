import sys
import os
from collections import OrderedDict
import pandas as pd
import re
import pyshark

# This script processes a pcap file and writes the statistics to a CSV file

def process_pcap(pcap_file, csv_file, version):
    # Read the pcap file using pyshark
    capture = pyshark.FileCapture(pcap_file)
    
    # Initialize statistics
    total_packets = 0
    total_bytes = 0
    protocols = {}
    source_addresses = set()
    destination_addresses = set()
    consecutive_protocols = []
    
    # Analyze packets
    for packet in capture:
        total_packets += 1
        total_bytes += int(packet.length)  # packet.length gives the length of the packet
        
        # Check if the packet has IP layer
        if 'IP' in packet:
            proto = packet.ip.proto
            src = packet.ip.src
            dst = packet.ip.dst
            
            # Convert protocol number to name (if available) and ensure uppercase
            proto_name = packet.highest_layer.upper()
            
            # Update protocol stats
            if proto_name not in protocols:
                protocols[proto_name] = {'packets': 0, 'bytes': 0}
            protocols[proto_name]['packets'] += 1
            protocols[proto_name]['bytes'] += int(packet.length)
            
            # Track unique addresses
            source_addresses.add(src)
            destination_addresses.add(dst)
            
            # Track consecutive protocols
            if len(consecutive_protocols) == 0 or consecutive_protocols[-1]['protocol'] != proto_name:
                consecutive_protocols.append({'protocol': proto_name, 'packets': 0, 'bytes': 0})
            consecutive_protocols[-1]['packets'] += 1
            consecutive_protocols[-1]['bytes'] += int(packet.length)
    
    row_data = OrderedDict()
    # Prepare CSV row data
    row_data['version'] = version
    row_data['total_packets_sent'] = total_packets
    row_data['total_bytes_sent'] = total_bytes
    row_data['number_of_different_protocols'] = len(protocols)
    row_data['number_of_different_source_addresses'] = len(source_addresses)
    row_data['number_of_different_destination_addresses'] = len(destination_addresses)
    
    # Add protocol data to row
    for proto, stats in protocols.items():
        row_data[f'{proto}_total_packets'] = stats['packets']
        row_data[f'{proto}_total_bytes'] = stats['bytes']
    
    # Write to CSV file
    write_to_csv(csv_file, row_data)

column_order = ['version', 
                'total_packets_sent', 
                'total_bytes_sent', 
                'number_of_different_protocols', 
                'number_of_different_source_addresses', 
                'number_of_different_destination_addresses',
                [
                    r'\D+_total_packets', 
                    r'\D+_total_bytes'
                ]
]

def sort_df_columns(df, column_order): 
    current_columns = df.columns.tolist()
    sorted_columns = []
    for col in column_order:
        # Find a match for the column and then add it to the sorted list, remove from the current list
        # If it is a list, then iterate through it so long as the no new matches are found
        if isinstance(col, list):
            while True:
                found = False
                for sub_col in col:
                    for current_col in current_columns:
                        if re.match(sub_col, current_col):
                            sorted_columns.append(current_col)
                            current_columns.remove(current_col)
                            found = True
                            break
                if not found:
                    break
        else: 
            for current_col in current_columns:
                if re.match(col, current_col):
                    sorted_columns.append(current_col)
                    current_columns.remove(current_col)
                    break

    return df[sorted_columns]


def write_to_csv(csv_file, row_data):
    # Check if the CSV file exists
    file_exists = os.path.isfile(csv_file)

    # Write the row data to the CSV file
    df = pd.DataFrame(row_data, index=[0])

    if not file_exists:
        df.to_csv(csv_file, index=False)
    else:
        og_df = pd.read_csv(csv_file)
        new_df = pd.concat([og_df, df], ignore_index=True)
        # Sort the columns
        new_df = sort_df_columns(new_df, column_order)
        # Sort the rows based on the version column
        new_df.sort_values(by='version', inplace=True)

        new_df.to_csv(csv_file, index=False)


if __name__ == "__main__":
    pcap_file = sys.argv[1]
    csv_file = sys.argv[2]
    version = sys.argv[3]
    process_pcap(pcap_file=pcap_file, csv_file=csv_file, version=version)