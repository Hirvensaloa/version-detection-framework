import os
import pandas as pd
import re

def is_same_version(filename):
    # Regex to extract versions from filename pattern 'xx.yy.zz[-suffix]_to_xx.yy.zz[-suffix]_num.csv'
    match = re.match(r"(\d+\.\d+\.\d+(?:-[\w\.]+)?)_to_(\d+\.\d+\.\d+(?:-[\w\.]+)?)_\d+\.csv", filename)
    if match:
        fingerprint_version = match.group(1)
        compared_version = match.group(2)
        is_same_version = int(fingerprint_version == compared_version)
        return is_same_version
    return False

def extract_means(df):
    # Number of packets
    number_of_packets = df['number_of_packets'].mean()

    # Number of unique packets
    number_of_unique_packets = df['number_of_unique_packets'].mean()

    # Average length
    average_length = df['average_length'].mean()

    # Number of new packets
    number_of_new_packets = df['number_of_new_packets'].mean()

    # Number of unique new packets
    number_of_unique_new_packets = df['number_of_unique_new_packets'].mean()

    # Missing packets
    number_of_missing_packets = df['number_of_missing_packets'].mean()

    # Average change in payload
    avg_change_in_payload = df['avg_change_in_payload_%'].mean()

    # Similar packets
    similar_packets = df['similar_packets_%'].mean()

    return number_of_packets, number_of_unique_packets, average_length, number_of_new_packets, number_of_unique_new_packets, number_of_missing_packets, avg_change_in_payload, similar_packets

def summarize_csv_folders(folders, output_file):
    summary_data = []

    for folder in folders:
        folder_name = os.path.normpath(folder).split("/")[-2]
        csv_files = [f for f in os.listdir(folder) if f.endswith('aggregated_results.csv')]

        for csv_file in csv_files:
            file_path = os.path.join(folder, csv_file)
          
            # Read the CSV file
            df = pd.read_csv(file_path)

            # Create a new column to check if the versions are the same
            df['is_same_version'] = df['filename'].apply(is_same_version)

            # Based on the new column, group the data and calculate the mean
            df_grouped = df.groupby('is_same_version').mean(numeric_only=True)
            # Min 
            df_min = df.groupby('is_same_version').min(numeric_only=True)
            # Max
            df_max = df.groupby('is_same_version').max(numeric_only=True)

            # Take the values from the grouped data and add to a single row
            summary_data.append({ 
                'folder': folder_name,
                'number_of_packets': df_grouped['number_of_packets'][1],
                'number_of_unique_packets': df_grouped['number_of_unique_packets'][1],
                'average_length': df_grouped['average_length'][1],
                'number_of_new_packets': df_grouped['number_of_new_packets'][1],
                'number_of_unique_new_packets': df_grouped['number_of_unique_new_packets'][1],
                'number_of_missing_packets': df_grouped['number_of_missing_packets'][1],
                'avg_change_in_payload_%': df_grouped['avg_change_in_payload_%'][1],
                'benign_packets_%': df_grouped['benign_packets_%'][1],
                'min_number_of_packets': df_min['number_of_packets'][1],
                'min_number_of_unique_packets': df_min['number_of_unique_packets'][1],
                'min_average_length': df_min['average_length'][1],
                'min_number_of_new_packets': df_min['number_of_new_packets'][1],
                'min_number_of_unique_new_packets': df_min['number_of_unique_new_packets'][1],
                'min_number_of_missing_packets': df_min['number_of_missing_packets'][1],
                'min_avg_change_in_payload_%': df_min['avg_change_in_payload_%'][1],
                'min_benign_packets_%': df_min['benign_packets_%'][1],
                'max_number_of_packets': df_max['number_of_packets'][1],
                'max_number_of_unique_packets': df_max['number_of_unique_packets'][1],
                'max_average_length': df_max['average_length'][1],
                'max_number_of_new_packets': df_max['number_of_new_packets'][1],
                'max_number_of_unique_new_packets': df_max['number_of_unique_new_packets'][1],
                'max_number_of_missing_packets': df_max['number_of_missing_packets'][1],
                'max_avg_change_in_payload_%': df_max['avg_change_in_payload_%'][1],
                'max_benign_packets_%': df_max['benign_packets_%'][1],
                'DIFFERENT_VERSION>': '',
                'dif_number_of_packets': df_grouped['number_of_packets'][0],
                'dif_number_of_unique_packets': df_grouped['number_of_unique_packets'][0],
                'dif_average_length': df_grouped['average_length'][0],
                'dif_number_of_new_packets': df_grouped['number_of_new_packets'][0],
                'dif_number_of_unique_new_packets': df_grouped['number_of_unique_new_packets'][0],
                'dif_number_of_missing_packets': df_grouped['number_of_missing_packets'][0],
                'dif_avg_change_in_payload_%': df_grouped['avg_change_in_payload_%'][0],
                'dif_benign_packets_%': df_grouped['benign_packets_%'][0],
                'min_dif_number_of_packets': df_min['number_of_packets'][0],
                'min_dif_number_of_unique_packets': df_min['number_of_unique_packets'][0],
                'min_dif_average_length': df_min['average_length'][0],
                'min_dif_number_of_new_packets': df_min['number_of_new_packets'][0],
                'min_dif_number_of_unique_new_packets': df_min['number_of_unique_new_packets'][0],
                'min_dif_number_of_missing_packets': df_min['number_of_missing_packets'][0],
                'min_dif_avg_change_in_payload_%': df_min['avg_change_in_payload_%'][0],
                'min_dif_benign_packets_%': df_min['benign_packets_%'][0],
                'max_dif_number_of_packets': df_max['number_of_packets'][0],
                'max_dif_number_of_unique_packets': df_max['number_of_unique_packets'][0],
                'max_dif_average_length': df_max['average_length'][0],
                'max_dif_number_of_new_packets': df_max['number_of_new_packets'][0],
                'max_dif_number_of_unique_new_packets': df_max['number_of_unique_new_packets'][0],
                'max_dif_number_of_missing_packets': df_max['number_of_missing_packets'][0],
                'max_dif_avg_change_in_payload_%': df_max['avg_change_in_payload_%'][0],
                'max_dif_benign_packets_%': df_max['benign_packets_%'][0],
                'DIFF>': '',
                '%_number_of_packets': df_grouped['number_of_packets'][0] / df_grouped['number_of_packets'][1] * 100,
                '%_number_of_unique_packets': df_grouped['number_of_unique_packets'][0] / df_grouped['number_of_unique_packets'][1] * 100,
                '%_average_length': df_grouped['average_length'][0] / df_grouped['average_length'][1] * 100,
                '%_number_of_new_packets': df_grouped['number_of_new_packets'][0] / df_grouped['number_of_new_packets'][1] * 100,
                '%_number_of_unique_new_packets': df_grouped['number_of_unique_new_packets'][0] / df_grouped['number_of_unique_new_packets'][1] * 100,
                '%_number_of_missing_packets': df_grouped['number_of_missing_packets'][0] / df_grouped['number_of_missing_packets'][1] * 100,
                '%_avg_change_in_payload_%': df_grouped['avg_change_in_payload_%'][0] / df_grouped['avg_change_in_payload_%'][1] * 100,
                '%_benign_packets_%': df_grouped['benign_packets_%'][0] / df_grouped['benign_packets_%'][1] * 100,
                '%_min_number_of_packets': df_min['number_of_packets'][0] / df_min['number_of_packets'][1] * 100,
                '%_min_number_of_unique_packets': df_min['number_of_unique_packets'][0] / df_min['number_of_unique_packets'][1] * 100,
                '%_min_average_length': df_min['average_length'][0] / df_min['average_length'][1] * 100,
                '%_min_number_of_new_packets': df_min['number_of_new_packets'][0] / df_min['number_of_new_packets'][1] * 100,
                '%_min_number_of_unique_new_packets': df_min['number_of_unique_new_packets'][0] / df_min['number_of_unique_new_packets'][1] * 100,
                '%_min_number_of_missing_packets': df_min['number_of_missing_packets'][0] / df_min['number_of_missing_packets'][1] * 100,
                '%_min_avg_change_in_payload_%': df_min['avg_change_in_payload_%'][0] / df_min['avg_change_in_payload_%'][1] * 100,
                '%_min_benign_packets_%': df_min['benign_packets_%'][0] / df_min['benign_packets_%'][1] * 100,
                '%_max_number_of_packets': df_max['number_of_packets'][0] / df_max['number_of_packets'][1] * 100,
                '%_max_number_of_unique_packets': df_max['number_of_unique_packets'][0] / df_max['number_of_unique_packets'][1] * 100,
                '%_max_average_length': df_max['average_length'][0] / df_max['average_length'][1] * 100,
                '%_max_number_of_new_packets': df_max['number_of_new_packets'][0] / df_max['number_of_new_packets'][1] * 100,
                '%_max_number_of_unique_new_packets': df_max['number_of_unique_new_packets'][0] / df_max['number_of_unique_new_packets'][1] * 100,
                '%_max_number_of_missing_packets': df_max['number_of_missing_packets'][0] / df_max['number_of_missing_packets'][1] * 100,
                '%_max_avg_change_in_payload_%': df_max['avg_change_in_payload_%'][0] / df_max['avg_change_in_payload_%'][1] * 100,
                '%_max_benign_packets_%': df_max['benign_packets_%'][0] / df_max['benign_packets_%'][1] * 100
            })

            final_df = pd.DataFrame(summary_data)

            # Save the summary data
            final_df.to_csv(output_file, index=False)

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
# Find sub folders named 'fingerprint_comparison'
folders = [os.path.join(f, 'fingerprint_comparison') for f in folders if os.path.exists(os.path.join(f, 'fingerprint_comparison'))]

output_file = "../data/fingerprint_comparison_summary.csv" 
summarize_csv_folders(folders, output_file)