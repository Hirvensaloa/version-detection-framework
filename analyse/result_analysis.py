import os
import pandas as pd
import semver

def summarize_csv_folders(folders, output_file):
    summary_data = []

    for folder in folders:
        folder_name = os.path.normpath(folder).split("/")[-2]
        csv_files = [f for f in os.listdir(folder) if f.endswith('prediction_results.csv')]

        for csv_file in csv_files:
            file_path = os.path.join(folder, csv_file)
          
            # Read the CSV file
            df = pd.read_csv(file_path)

            # Version range
            df['version'] = df['version'].apply(lambda x: semver.VersionInfo.parse(x))
            version_range = f"{df['version'].min()} - {df['version'].max()}"

            # Number of versions
            number_of_versions = df['version'].nunique()

            # Accuracy
            accuracy = df['accuracy'].mean()
            min_accuracy = df['accuracy'].min()
            max_accuracy = df['accuracy'].max()

            # True precision
            true_precision = df['true precision'].mean()
            min_true_precision = df['true precision'].min()
            max_true_precision = df['true precision'].max()

            # False precision
            false_precision = df['false precision'].mean()
            min_false_precision = df['false precision'].min()
            max_false_precision = df['false precision'].max()

            # True recall
            true_recall = df['true recall'].mean()
            min_true_recall = df['true recall'].min()
            max_true_recall = df['true recall'].max()

            # False recall
            false_recall = df['false recall'].mean()
            min_false_recall = df['false recall'].min()
            max_false_recall = df['false recall'].max()

            # True f1-score
            true_f1_score = df['true f1-score'].mean()
            min_true_f1_score = df['true f1-score'].min()
            max_true_f1_score = df['true f1-score'].max()

            # False f1-score
            false_f1_score = df['false f1-score'].mean()
            min_false_f1_score = df['false f1-score'].min()
            max_false_f1_score = df['false f1-score'].max()

            # True support
            true_support = df['true support'].mean()
            min_true_support = df['true support'].min()
            max_true_support = df['true support'].max()

            # False support
            false_support = df['false support'].mean()
            min_false_support = df['false support'].min()
            max_false_support = df['false support'].max()

            # Total support
            total_support = df['total_support'].mean()
            min_total_support = df['total_support'].min()
            max_total_support = df['total_support'].max()

            # Confusion matrix values
            tp = df['true positive'].sum()
            fp = df['false positive'].sum()
            tn = df['true negative'].sum()
            fn = df['false negative'].sum()

            # Extract feature importances
            feature_importances = df.drop(columns=['version', 'accuracy', 'true precision', 'false precision', 'true recall', 'false recall', 'true f1-score', 'false f1-score', 'true support', 'false support', 'total_support'])
            feature_importances = feature_importances.mean()

            # Summarize the data
            summary_data.append({
                'folder': folder_name,
                'version_range': version_range,
                'number_of_versions': number_of_versions,
                'accuracy': accuracy,
                'true_precision': true_precision,
                'false_precision': false_precision,
                'true_recall': true_recall,
                'false_recall': false_recall,
                'true_f1_score': true_f1_score,
                'false_f1_score': false_f1_score,
                'true_support': true_support,
                'false_support': false_support,
                'total_support': total_support,
                'true_positive': tp,
                'false_positive': fp,
                'true_negative': tn,
                'false_negative': fn,
                'min_accuracy': min_accuracy,
                'min_true_precision': min_true_precision,
                'min_false_precision': min_false_precision,
                'min_true_recall': min_true_recall,
                'min_false_recall': min_false_recall,
                'min_true_f1_score': min_true_f1_score,
                'min_false_f1_score': min_false_f1_score,
                'min_true_support': min_true_support,
                'min_false_support': min_false_support,
                'min_total_support': min_total_support,
                'max_accuracy': max_accuracy,
                'max_true_precision': max_true_precision,
                'max_false_precision': max_false_precision,
                'max_true_recall': max_true_recall,
                'max_false_recall': max_false_recall,
                'max_true_f1_score': max_true_f1_score,
                'max_false_f1_score': max_false_f1_score,
                'max_true_support': max_true_support,
                'max_false_support': max_false_support,
                'max_total_support': max_total_support,
                **feature_importances.to_dict()
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
# Find sub folders named 'fingerprint_comparison'
folders = [os.path.join(f, 'fingerprint_comparison') for f in folders if os.path.exists(os.path.join(f, 'fingerprint_comparison'))]

output_file = "../data/result_summary.csv" 
summarize_csv_folders(folders, output_file)