# Data folder

The original dataset is too large to be stored in Github, so it needs to be downloaded from the following link: [Zenodo](https://doi.org/10.5281/zenodo.14338912). Once you have the dataset downloaded, you can extract it in this folder.

If you don't want to use the original dataset, you can collect your own dataset using the `application_capture.py` script. The script will collect the data and store it in the same format as the original dataset. The data will appear in this folder.

# Format

The data is stored in the following format and hierarchy:

- Root folder

  - There are multiple csv files that contain aggregated statistical information about the data, applications and results.

  - There are subfolders for each recorded application. The folders are named `<application_name>-<timestamp>`.

    - Each subfolder contains all the recorded data for each application version deployment in PCAP format. Each recording is named `<application_name>_<version>_<deployment_number>.pcap`.

    - Each subfolder also contains a config file that can be used to recapture the recorded data.

    - Each subfolder also has a pod metadata file and an output csv file that contains a summary of the recorded PCAP files.

    - Each subfolder also contains a subfolder named `fingerprint_comparison` that contains the fingerprint comparison results and the final classification results.

      - The comparison results are stored in a csv and PCAP format. PCAP is more used for debugging and the csv file is used to generate the final `aggregated_results.csv` file which is fed to the machine learning model.

      - The final classification results are stored in the `prediction_results.csv` file.
