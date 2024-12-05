import os
import pandas as pd
import semver

def summarize_csv_folders(folders, output_file):
    summary_data = []

    for folder in folders:
        folder_name = os.path.basename(folder.rstrip(os.sep))
        csv_files = [f for f in os.listdir(folder) if f.endswith('output.csv')]

        for csv_file in csv_files:
            file_path = os.path.join(folder, csv_file)
          
            # Read the CSV file
            df = pd.read_csv(file_path)

            # Version range
            df['version'] = df['version'].apply(lambda x: semver.VersionInfo.parse(x))
            version_range = f"{df['version'].min()} - {df['version'].max()}"

            # Number of versions
            number_of_versions = df['version'].nunique()

            # Number of different connection
            number_of_different_source_addresses = df['number_of_different_source_addresses'].mean()
            number_of_different_destination_addresses = df['number_of_different_destination_addresses'].mean()
                
            # Extract protocol-specific columns starting after `number_of_different_destination_addresses`
            start_index = df.columns.get_loc('number_of_different_destination_addresses') + 1
            protocol_cols = df.columns[start_index:]

            # Calculate the average total packets and bytes
            avg_packets = df['total_packets_sent'].mean()
            avg_bytes = df['total_bytes_sent'].mean()
            max_packets = df['total_packets_sent'].max()
            min_packets = df['total_packets_sent'].min()
            max_bytes = df['total_bytes_sent'].max()
            min_bytes = df['total_bytes_sent'].min()

            # Separate protocol columns into packets and bytes
            protocol_data = {}
            for col in protocol_cols:
                if '_packets' in col:
                    protocol_name = col.replace('_packets', '')
                    protocol_data.setdefault(protocol_name, {})['packets'] = col
                elif '_bytes' in col:
                    protocol_name = col.replace('_bytes', '')
                    protocol_data.setdefault(protocol_name, {})['bytes'] = col

            # Summarize the data
            summary_data.append({
                'folder': folder_name,
                'version_range': version_range,
                'number_of_versions': number_of_versions,
                'protocols': len(protocol_data),
                'number_of_different_source_addresses': number_of_different_source_addresses,
                'number_of_different_destination_addresses': number_of_different_destination_addresses,
                'avg_packets': avg_packets,
                'avg_bytes': avg_bytes,
                'max_packets': max_packets,
                'min_packets': min_packets,
                'max_bytes': max_bytes,
                'min_bytes': min_bytes,
                **{f'{protocol}_avg_packets': df[protocol_data[protocol]['packets']].mean() for protocol in protocol_data},
                **{f'{protocol}__avg_bytes': df[protocol_data[protocol]['bytes']].mean() for protocol in protocol_data}
            })

            # Create a summary DataFrame
            summary_df = pd.DataFrame(summary_data)
            # Fill NaN values with 0
            summary_df = summary_df.fillna(0)

            # Save to output CSV file
            summary_df.to_csv(output_file, index=False)
            print(f"Summary saved to {output_file}")

    # Summarise the mean of each row to get the average of the entire dataset. Create a new row in the DataFrame
    summary_df = pd.read_csv(output_file)

    summary_df.loc['Average'] = summary_df.mean(numeric_only=True)
    summary_df.loc['Average', 'folder'] = 'Average'
    summary_df.loc['Min'] = summary_df.min(numeric_only=True)
    summary_df.loc['Max'] = summary_df.max(numeric_only=True)
    summary_df.loc['Min', 'folder'] = 'Min'
    summary_df.loc['Max', 'folder'] = 'Max'

    # Add blank row between last - 3 
    summary_df = pd.concat([summary_df.iloc[:-3], pd.DataFrame(index=['', '']), summary_df.iloc[-3:]]).reset_index(drop=True)

    summary_df.to_csv(output_file, index=False)

# Read the data directory to get the list of folders
folders = os.listdir('../data')
folders = [os.path.join('../data', f) for f in folders if os.path.isdir(os.path.join('../data', f))]

output_file = "../data/application_summary.csv" 
summarize_csv_folders(folders, output_file)