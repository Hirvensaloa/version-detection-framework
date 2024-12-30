# Index

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Usage](#usage)
   - [1. Data Collection](#1-data-collection)
     - [Prerequisites](#pre1)
     - [Usage](#use1)
   - [2. Fingerprinting](#2-fingerprinting)
     - [Prerequisites](#pre2)
     - [Usage](#use2)
   - [3. Classification](#3-classification)
     - [Prerequisites](#pre3)
     - [Usage](#use3)
5. [Dataset](#dataset)
6. [Other](#other)

# Introduction

This project is part of my master thesis. The repository contains the thesis document and source code for a framework. The framework is used to create unique fingerprints for Helm chart applications. The goal is to be able to classify network traffic traces that belong to a certain Helm chart version or not.

The framework itself is split into three parts: Data collection, Fingerprinting and Classification. The data collection part is responsible for collecting network traffic traces from a Kubernetes cluster. The fingerprinting part is responsible for creating a unique fingerprint for an application version. The classification part is responsible for classifying network traffic traces based on the fingerprints.

More details can be found in the thesis document [here](Version_Sensitive_Network_Traffic_Classification_for_Kubernetes_Applications.pdf).

# Requirements

- Minikube 1.34.0
- Docker 27.3.1
- Helm 3.16.2
- Kubectl 1.31.2
- Python 3.10.12
- Tshark 3.6.2

Most likely works with other versions, but these were the ones used during development. Minikube, Docker, Helm and Kubectl are not needed if you are not going to collect any data.

# Installation

```bash
pip install -r requirements.txt
```

# 1. Data collection

Generates network traffic traces for a specified application and versions. The traces are collected from a Kubernetes cluster. The network traffic traces are stored in PCAP format.
<a id="pre1"></a>

## Prerequisites

Configuration file is needed to specify which application and versions are collected.

Create a `config.json` file in the root directory. The file should contain the following fields:

```js
{
  "name": "hazelcast", // Name of the application. Can be anything.
  "reruns_default": 30, // How many times a job (chart version) is deployed.
  "timeout": "2m", // How long a job is allowed to run. I.e. how long network traffic is collected.
  "jobs": [ // List of helm chart versions.
    {
      "version": "5.10.1"
    },
    {
      "version": "5.9.1"
    },
    {
      "version": "5.8.14"
    }
  ],
  "label": "my-release", // Can be anything. If using HTTPS registry, this should match the label used in helm_install command.

  // If using OCI registry
  "use_oci": false, // Set to true if using OCI registry, false otherwise.
  "url": "oci://registry-1.docker.io/bitnamicharts/moodle", // URL to the OCI helm chart registry. Not needed if using HTTPS registry.

  // If using HTTPS registry. Make sure use_oci is set to false and label matches the helm install [label]",
  "repo_add": "helm repo add hazelcast https://hazelcast-charts.s3.amazonaws.com/", // Add repo command, if using HTTPS registry.
  "helm_install": "helm install my-release hazelcast/hazelcast" // Install command, if using HTTPS registry.
}
```

<a id="use1"></a>

## Usage

```bash
python3 application_capture.py
```

# 2. Fingerprinting

Generates a unique fingerprint for an application version. The fingerprint is generated from the network traffic traces collected in the data collection part. The data collection part is not necessary if you can provide the PCAP files from other sources. Once the fingerprints are created, the PCAP files not used in the fingerprints are compared against the fingerprints to generate a difference csv file (`aggregated_results.csv`). The difference csv file is then used to classify network traffic traces.
<a id="pre2"></a>

## Prerequisites

- Have a dataset collected from the data collection part. The dataset should be stored in the `data` folder.
  <a id="use2"></a>

## Usage

```bash
python3 fingerprint.py ./data/<app_folder_name>
```

For example:

```bash
python3 fingerprint.py ./data/nats-20240919231929
```

# 3. Classification

Classifies network traffic packet differences between a fingerprint and a PCAP file. The classification is implemented with Random Forest.

<a id="pre3"></a>

## Prerequisites

- Have a folder named `fingerprint_comparison` inside the app specific data folder. The folder should contain an `aggregated_results.csv` file which is used as the classifiers input.
  <a id="use3"></a>

## Usage

```bash
python3 classify.py ./data/<app_folder_name>/fingerprint_comparison/aggregated_results.csv
```

For example:

```bash
python3 classify.py ./data/nats-20240919231929/fingerprint_comparison/aggregated_results.csv
```

# Dataset

The dataset is available for download from the following link: [Zenodo](https://doi.org/10.5281/zenodo.14338912).

- [data](./data/README.md) folder contains data collected using the `application_capture.py` script and/or you can download the dataset and extract it there.

# Other

- [analyse](./analyse/README.md) folder contains scripts used to analyse the applications, data and results.
