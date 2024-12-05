import argparse
import csv
import os
from statistics import mean
# import sys

# # Increase the field size limit. Uncomment if needed.
# csv.field_size_limit(sys.maxsize)

aggregate_filename = "aggregated_results.csv"
prediction_results_filename = "prediction_results.csv"

fieldnames = [
            'filename', 'number_of_packets', 'number_of_unique_packets', 'average_length',
            'number_of_new_packets', 'number_of_unique_new_packets', 'number_of_missing_packets', 'avg_change_in_payload_%', 'benign_packets_%'
]

def process_directory(directory):
    result = []
    for filename in os.listdir(directory):
        if filename.endswith('.csv') and filename != aggregate_filename and filename != prediction_results_filename: # Skip the aggregated results file and prediction results
            file_path = os.path.join(directory, filename)
            row = process_file(file_path)
            result.append(row)
    
    return result

def calculate_avg_payload_change(rows): 
    change = 0
    total_packets_added = 0
    for row in rows:
        if len(row['fingerprint_indices']) > 0 and row['new_packet'] == 'False':
            change += len(row['diff_indices']) / len(row['fingerprint_indices'])
            total_packets_added += 1

    return change / total_packets_added if total_packets_added > 0 else 0

def process_file(file_path):
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        print(f"Processing {file_path}")
        content = csvfile.read()
        content_without_null = content.replace('\0', '')
        reader = csv.DictReader(content_without_null.splitlines())
        rows = list(reader)
        lengths = [int(row['length']) for row in rows]
        unique_rows = list(set([(row['proto'], row['length'], row['payload'], row['new_packet']) for row in rows]))
        number_of_new_packets = 0
        number_of_missing_packets = 0
        number_of_unique_new_packets = 0

        for row in rows:
            if row['new_packet'] == 'True':
                number_of_new_packets += 1
            if row['missing_packet'] == 'True':
                number_of_missing_packets += 1

        for row in unique_rows:
            if row[3] == 'True':
                number_of_unique_new_packets += 1
        
        return {
            'filename': os.path.basename(file_path),
            'number_of_packets': len(rows),
            'number_of_unique_packets': len(unique_rows),
            'average_length': mean(lengths) if lengths else 0,
            # 'min_length': min(lengths) if lengths else 0,
            # 'max_length': max(lengths) if lengths else 0,
            'number_of_new_packets': number_of_new_packets,
            'number_of_unique_new_packets': number_of_unique_new_packets,
            'number_of_missing_packets': number_of_missing_packets,
            'avg_change_in_payload_%': calculate_avg_payload_change(rows),
            'benign_packets_%': (int(rows[0]['total_packets']) - len(rows)) / int(rows[0]['total_packets']) if rows and int(rows[0]['total_packets']) else 1,
            # 'payload_diff_min_size': min(payload_diffs) if payload_diffs else 0,
            # 'payload_diff_max_size': max(payload_diffs) if payload_diffs else 0
        }

def aggregate_diffs(directory):        
    results = process_directory(directory)
    
    # Sort results by filename
    results.sort(key=lambda x: x['filename'])
    
    output_file = os.path.join(directory, aggregate_filename)
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    
    print(f"Aggregated results have been written to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Aggregate CSV files in a directory.')
    parser.add_argument('directory', type=str, help='Directory containing CSV files')
    args = parser.parse_args()

    aggregate_diffs(args.directory)