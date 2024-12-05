import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import argparse
import os
import semver

def classify(file_path):
    # Step 1: Load the CSV file
    df = pd.read_csv(file_path)
    dir_path = os.path.dirname(file_path)

    # Step 2: Define a function to extract version info and is_same_version
    def extract_versions(filename):
        # Regex to extract versions from filename pattern 'xx.yy.zz[-suffix]_to_xx.yy.zz[-suffix]_num.csv'
        match = re.match(r"(\d+\.\d+\.\d+(?:-[\w\.]+)?)_to_(\d+\.\d+\.\d+(?:-[\w\.]+)?)_\d+\.csv", filename)
        if match:
            fingerprint_version = match.group(1)
            compared_version = match.group(2)
            is_same_version = int(fingerprint_version == compared_version)
            
            # Determine if the major versions are the same
            try:
                fingerprint_parsed = semver.VersionInfo.parse(fingerprint_version)
                compared_parsed = semver.VersionInfo.parse(compared_version)
                is_same_major_version = int(fingerprint_parsed.major == compared_parsed.major)
            except ValueError:
                # If version parsing fails, set is_same_major_version to 0
                is_same_major_version = 0
            
            return fingerprint_version, compared_version, is_same_version, is_same_major_version
        return None, None, 0, 0

    # Step 3: Apply the function to extract versions
    df['fingerprint_version'], df['compared_version'], df['is_same_version'], df['is_same_major_version'] = zip(
        *df['filename'].apply(extract_versions)
    )

    # # Step 4: Drop rows where is_same_major_version is True but is_same_version is False. Uncomment this if you want to only classify major versions. 
    # df = df[~((df['is_same_major_version'] == 1) & (df['is_same_version'] == 0))]

    # Step 5: Identify unique fingerprint versions
    unique_fingerprint_versions = df['fingerprint_version'].unique()

    # Step 6: Iterate over each unique fingerprint version
    results = []
    for version in unique_fingerprint_versions:
        print(f"\nTraining classifier for fingerprint version: {version}")
        
        # Step 7: Subset the data for the current fingerprint version
        df_version = df[df['fingerprint_version'] == version]
        
        # Step 8: Drop unnecessary columns (filename, fingerprint_version, compared_version)
        df_cleaned = df_version.drop(columns=['filename', 'fingerprint_version', 'compared_version'])
        
        # Step 9: Split the data into features (X) and labels (y)
        X = df_cleaned.drop(columns=['is_same_version', 'is_same_major_version'])
        y = df_cleaned['is_same_version']  
        
        # Step 10: Split the data into training and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Step 11: Train the RandomForestClassifier
        clf = RandomForestClassifier(random_state=42)
        clf.fit(X_train, y_train)
        
        # Step 12: Make predictions and evaluate the model
        y_pred = clf.predict(X_test)
        
        # Step 13: Calculate accuracy and classification report
        accuracy = accuracy_score(y_test, y_pred)
        classification_rep = classification_report(y_test, y_pred, output_dict=True)
        confusion = confusion_matrix(y_test, y_pred)
        tp = confusion[1][1] if len(confusion) > 1 else 0
        fp = confusion[0][1] if len(confusion) > 1 else 0
        tn = confusion[0][0] if len(confusion) > 1 else 0
        fn = confusion[1][0] if len(confusion) > 1 else 0
        feature_importances = pd.DataFrame({'feature': X.columns.tolist(), 'importance': clf.feature_importances_})
        feature_importances = feature_importances.sort_values('importance', ascending=False).reset_index(drop=True)
        feature_importance_tuples = list(zip(feature_importances['feature'], feature_importances['importance']))

        result = {
            'version': version,
            'accuracy': accuracy,
            'true precision': classification_rep['1']['precision'] if '1' in classification_rep else 0,
            'false precision': classification_rep['0']['precision'] if '0' in classification_rep else 0,
            'true recall': classification_rep['1']['recall'] if '1' in classification_rep else 0,
            'false recall': classification_rep['0']['recall'] if '0' in classification_rep else 0,
            'true f1-score': classification_rep['1']['f1-score'] if '1' in classification_rep else 0,
            'false f1-score': classification_rep['0']['f1-score'] if '0' in classification_rep else 0,
            'true support': classification_rep['1']['support'] if '1' in classification_rep else 0,
            'false support': classification_rep['0']['support'] if '0' in classification_rep else 0,
            'total_support': classification_rep['macro avg']['support'],
            'true positive': tp,
            'false positive': fp,
            'true negative': tn,
            'false negative': fn
        }

        for feature, importance in feature_importance_tuples:
            result[feature] = importance

        # Store results for this version
        results.append(result)

    # Save the results to a CSV file
    results_df = pd.DataFrame(results)
    results_file_path = os.path.join(dir_path, 'prediction_results.csv')
    results_df.to_csv(results_file_path, index=False)

    # Optional: Print a summary of the results
    print("\nSummary of results for all versions:")
    for result in results:
        print(f"Version: {result['version']}, Accuracy: {result['accuracy']}, Total Support: {result['total_support']}")


if __name__ == "__main__":
    # Step 0: Define the parser
    parser = argparse.ArgumentParser(description='Predict changes in versions.')
    parser.add_argument('file_path', type=str, help='Path to the CSV file containing version info')
    args = parser.parse_args()
    file_path = args.file_path
    classify(file_path)
