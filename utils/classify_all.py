import os

# Read the data directory to get the list of folders
folders = os.listdir('../data')
folders = [os.path.join('../data', f) for f in folders if os.path.isdir(os.path.join('../data', f))]
# Find sub folders named 'fingerprint_comparison'
folders = [os.path.join(f, 'fingerprint_comparison') for f in folders if os.path.exists(os.path.join(f, 'fingerprint_comparison'))]

files = []
# Folders appended with aggregated_results.csv
for folder in folders:
    files.append(os.path.join(folder, 'aggregated_results.csv'))

# Run classify.py on each file (script)
for f in files: 
    os.system(f'python ../classify.py {f}')
