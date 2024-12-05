import subprocess
import json
import re
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

now = datetime.now()

# Load configuration from JSON file
config_file = 'config.json'

with open(config_file, 'r') as f:
    config = json.load(f)

name = config.get('name')
reruns = config.get('reruns_default')
timeout = config.get('timeout')
url = config.get('url')
jobs = config.get('jobs')
label = config.get('label')
repo_add = config.get('repo_add')
helm_install = config.get('helm_install')
use_oci = config.get('use_oci')

# Check if JSON fields are correctly parsed
if not name or not isinstance(reruns, int) or not timeout or (not url or (not repo_add and not helm_install)):
    raise ValueError("Error: Missing or invalid fields in the JSON configuration file.")

print(f"Configuration loaded:")
print(f"Name: {name}")
print(f"Default reruns: {reruns}")
print(f"Timeout: {timeout}")
print(f"Label: {label}")
print(f"Jobs: {jobs}")
if use_oci:
    print(f"Using OCI registry.")
    print(f"URL: {url}")
else: 
    print(f"Using HTTPS registry.")
    print(f"Repo add: {repo_add}")
    print(f"Helm install: {helm_install}")
print("--------------------------------\n")
    
# HELPERS

def update_json_file(file_path, new_data):
    if not os.path.exists(file_path):
        # If the file doesn't exist, create it with an empty list
        with open(file_path, 'w') as f:
            json.dump([], f)
    
    # Read the existing data
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Append the new data
    data.append(new_data)
    
    # Write the updated data back to the file
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def run_command(command, shell=True, background=False, accept_timeout=False):
    """Executes a shell command and prints the output. Can run in the background."""
    print(f"Running command: {command}")
    if background:
        process = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process
    else:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        timeout_occurred = bool(re.search(r'status 124|exit.*124', result.stderr))
        if result.returncode != 0 and (not timeout_occurred or not accept_timeout):
            print(f"Command failed with error: {result.stderr}")
            raise Exception(f"Command failed with error: {result.stderr}")

        return result

def get_pod_names():
    command = f"kubectl get pods -l 'app.kubernetes.io/instance={label}' -o json"
    result = run_command(command)
    pods_json = json.loads(result.stdout)

    if pods_json.get('items') is None or not pods_json['items']:
        # If no pods are found with the instance label, try to find pods with the release label
        print("No pods found with the instance label. Trying to find pods with the release label.")
        alternate_command = f"kubectl get pods -l 'release={label}' -o json"
        result = run_command(alternate_command)
        pods_json = json.loads(result.stdout)

    return [pod['metadata']['name'] for pod in pods_json['items']]

def wait_for_pod(pod_name):
    command = f"kubectl wait --for=condition=ready pod/{pod_name} --timeout=900s"
    try:
        run_command(command)
        return pod_name, True
    except Exception as e:
        return pod_name, False

def wait_for_first_ready_pod():
    # Fetch pod names dynamically
    pod_names = get_pod_names()
    print(f"Found pods: {pod_names}")

    if not pod_names:
        print("No pods found matching the label.")
        raise Exception("No pods found matching the label.")

    with ThreadPoolExecutor(max_workers=len(pod_names)) as executor:
        futures = {executor.submit(wait_for_pod, pod_name): pod_name for pod_name in pod_names}
        try:
            for future in as_completed(futures):
                result = future.result()
                if result and result[1]:
                    return result
        finally:
            for future in futures:
                future.cancel()

    print("No pods became ready within the timeout period.")
    raise Exception("No pods became ready within the timeout period.")    

def get_pods_ips():
    """Fetches the IPs of the pods."""
    command = "kubectl get pods -o wide | awk 'NR>1 {for(i=1;i<=NF;i++) if($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/) print $i}'" # Fetch only the IPs by pattern matching
    result = run_command(command)
    if result.returncode == 0:
        ips = [ip.strip() for ip in result.stdout.splitlines()]
        return ips
    return []

def get_pods_info(version, run, calibration_run=False):
    # Get pod information in JSON format
    kubectl_cmd = ["kubectl", "get", "pods", "-o", "json"]
    result = subprocess.run(kubectl_cmd, capture_output=True, text=True)
    pods_json = json.loads(result.stdout)

    pod_info = []
    for pod in pods_json['items']:
        pod_name = pod['metadata']['name']
        
        # Find the last ready condition
        ready_condition = next((c for c in reversed(pod['status']['conditions']) if c['type'] == 'Ready' and c['status'] == 'True'), None)
        
        if ready_condition:
            ready_time = datetime.strptime(ready_condition['lastTransitionTime'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            current_time = datetime.now(timezone.utc)
            uptime = current_time - ready_time
            
            pod_info.append({
                "name": pod_name,
                "ready_duration": str(uptime)
            })

    output_data = {
        "version": version,
        "run": run,
        "number_of_pods": len(pod_info),
        "pods": pod_info,
        "calibration_run": calibration_run
    }

    return output_data

def calibrate(label, url, version, helm_install, use_oci):
    """Calibrates the environment by installing the specified version of the service. This is useful when installing the version for the first time as it may take significantly longer to start the pods."""
    print(f"Calibrating the environment for version {version}.")
    run_helm_install(label=label, url=url, use_oci=use_oci, version=version, helm_install=helm_install)
    wait_for_first_ready_pod()
    cleanup(label=label)
    print(f"Calibration completed for version {version}.")
    pod_info = get_pods_info(version=version, run=0, calibration_run=True)
    return pod_info

def run_helm_install(label, url, version, use_oci, helm_install):
    helm_command = f"helm install {label} {url} --version {version} --timeout 2m" if use_oci else f"{helm_install} --version {version} --timeout 2m"
    try:
        run_command(helm_command)
    except Exception as e:
        # Sometimes the helm install command fails due to a timeout but the pods are still created. In that case, we can try to proceed.
        print(f"Error: {e}")
        pods = get_pod_names()
        if not pods:
            raise Exception("No pods found after the helm install command failed.")
        print(f"Pods found after the helm install command failed: {pods}")

def cleanup(label):
    run_command(f"helm uninstall {label} --ignore-not-found")
    run_command("kubectl delete pvc --all") # Helm might not delete all PVCs, need to delete them manually
    run_command("minikube ssh '[ -f /tmp/minikube_traffic.pcap ] && sudo rm -f /tmp/minikube_traffic.pcap || true'") # Delete the pcap file, if exists

timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
output_dir = f'data/{name}-{timestamp}'

# Step 1: Check if all the versions are available
print("Checking if all the versions are available...")
chart_keyword = url
if not use_oci:
    # Add the repository and update the charts. This is required first step so that we can search if the chart is available.
    run_command(repo_add)
    helm_update = "helm repo update"
    run_command(helm_update)
    chart_keyword = helm_install.split()[-1] # The last word in the helm install command is the chart keyword that can be used to search for the chart (If not installing with OCI)

for job in jobs:
    version = job['version']
    check_version_command = f"helm show chart {chart_keyword} --version {version}"
    result = run_command(check_version_command)
print("All versions are available.")

# Step 2: Start minikube
run_command("minikube start")
print("Minikube started.")

# Step 3: Start tcpdump on minikube
tcpdump_install_command = f"minikube ssh 'sudo apt update && sudo apt install -y tcpdump'"
run_command(tcpdump_install_command)

# Check if data/name directory exists. Create if it doesn't.
if not os.path.exists('data'):
    os.mkdir('data')
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

# Save the config file into the output directory. So that we can reproduce the results later.
config_file_output = f"{output_dir}/config.json"
with open(config_file_output, 'w') as f:
    json.dump(config, f, indent=4)

pod_metadata_file = f"{output_dir}/pod_metadata.json"

highest_rerun_value = max([job.get('reruns', reruns) for job in jobs]) # Find the highest rerun value specified in the jobs. If we just use the default rerun value, we run into problems if some version specifies a higher rerun value than the default value. 

# This loop nesting is better than nesting the rerun loop inside jobs loop. If iterate through the versions and wait until all the reruns are completed for that version, we can run into issues where a specific version has too similar timestamps and IPs which can mess up the fingerprint.
# For example, if we run version 1 for 5 times and it takes an hour or less to complete all the runs -> the timestamp values within version 1 are then for that specific hour. Rather if we run version 1, then version 2 and only then loop back to run the next rerun values, we can mix the timestamps.  
for i in range(0, highest_rerun_value + 1):
    for job in jobs:
        version = job['version']
        rerun_value = job.get('reruns', reruns) # Check if reruns are specified for this version, use the default reruns otherwise
        if rerun_value < i: # If rerun_value for the specific version is less than the current run, then skip. This can happen if the rerun_value is specified for this version and it is lower than the default value or vice versa. 
            continue
        # Use the first run to calibrate the environment. This makes it so that the first run is not included in the results. First run is often significantly slower than the rest. 
        if i == 0:
            pod_info = calibrate(label=label, url=url, version=version, helm_install=helm_install, use_oci=use_oci)
            update_json_file(pod_metadata_file, pod_info)
            continue

        print(f"Run {i} of {rerun_value}. Version: {version}")

        try:
            # Step 4: Deploy a service using helm
            run_helm_install(label=label, url=url, version=version, helm_install=helm_install, use_oci=use_oci)

            # Step 5: Wait for any pod to be ready, pod related traffic is not generated before that
            # Then start listening with tcpdump
            pod_name = wait_for_first_ready_pod()
            print(f"Pod {pod_name} is ready. Starting tcpdump...")
            tcpdump_command = f"minikube ssh 'sudo timeout {timeout} tcpdump -i any -w /tmp/minikube_traffic.pcap'"
            run_command(command=tcpdump_command, accept_timeout=True)

            # Step 6: Discover all services and their IPs. Save pods metadata.
            print("Fetching pods and their IPs...")
            pod_ips = get_pods_ips()
            pod_info = get_pods_info(version=version, run=i)
            update_json_file(pod_metadata_file, pod_info)

            # Step 7: Copy captured pcap to the local machine
            pcap_filename = f"traffic_{name}_{version}_{i}.pcap"
            pcap_filepath = f"{output_dir}/{pcap_filename}"
            copy_command = f"minikube cp minikube:/tmp/minikube_traffic.pcap ./{pcap_filepath}"
            run_command(copy_command)

            # Step 8: Filter out traffic that doesn't relate to the pods
            # Adjust IP addresses based on the output of Step 5
            if pod_ips:
                ip_filter = ' or '.join([f'host {ip}' for ip in pod_ips])
                filtered_pcap_filename = f"{name}_{version}_{i}.pcap"
                filtered_pcap_path = f"{output_dir}/{filtered_pcap_filename}"
                filter_command = f"tcpdump -r ./{pcap_filepath} -w ./{filtered_pcap_path} 'not arp and ({ip_filter})'"
                run_command(filter_command)

                # Step 9: Aggregate the pcap to CSV. This creates a single row entry for the pcap file.
                output_csv = f"{output_dir}/output.csv"
                sum_pcap_command = f"python3 ./utils/sum_pcap_to_csv.py {filtered_pcap_path} {output_csv} {version}"
                run_command(sum_pcap_command)

                # Step 10: Remove the unfiltered pcap file
                os.remove(pcap_filepath)
        except Exception as e:
                print(f"Error: {e}")

        print(f"Completed Run {i} / {rerun_value}. Version: {version}")

        # Step 11: Cleanup
        cleanup(label=label)

print("All runs completed.")

# Cleanup: Stop and delete Minikube
print("Stopping and deleting Minikube...")
run_command("minikube stop")
run_command("minikube delete")

print("--------------------------------\n")

end = datetime.now()
print("Finished.")
print(f"Execution time: {end - now}")

