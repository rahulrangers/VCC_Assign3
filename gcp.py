#!/usr/bin/env python3
import os
import time
import json
import requests
import subprocess
import logging
from google.cloud import compute_v1

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='autoscale.log'
)

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
CPU_THRESHOLD = 75  # percentage
MEMORY_THRESHOLD = 75  # percentage
DISK_THRESHOLD = 75  # percentage
CHECK_INTERVAL = 60  # seconds

# GCP Configuration
PROJECT_ID = "your-gcp-project-id"
ZONE = "us-central1-a"
INSTANCE_NAME = "auto-scaled-vm"
MACHINE_TYPE = "e2-medium"
IMAGE_FAMILY = "ubuntu-2004-lts"
IMAGE_PROJECT = "ubuntu-os-cloud"

# Local application path to migrate
APP_PATH = "/path/to/your/application"

def get_metric_value(query):
    """Get metric value from Prometheus"""
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
    result = response.json()
    
    if result['status'] == 'success' and len(result['data']['result']) > 0:
        return float(result['data']['result'][0]['value'][1])
    return 0

def check_resources():
    """Check if resource usage exceeds thresholds"""
    # CPU usage (100 - idle percentage)
    cpu_usage = get_metric_value('100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
    
    # Memory usage percentage
    memory_usage = get_metric_value('100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)')
    
    # Disk usage percentage
    disk_usage = get_metric_value('100 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100')
    
    logging.info(f"Resource Usage - CPU: {cpu_usage:.2f}%, Memory: {memory_usage:.2f}%, Disk: {disk_usage:.2f}%")
    
    # Check if any resource exceeds threshold
    if cpu_usage > CPU_THRESHOLD or memory_usage > MEMORY_THRESHOLD or disk_usage > DISK_THRESHOLD:
        logging.warning("Resource threshold exceeded, initiating cloud migration")
        return True
    
    return False

def create_gcp_instance():
    """Create a VM instance in GCP"""
    logging.info("Creating GCP instance...")
    
    instance_client = compute_v1.InstancesClient()
    
    # Get the latest image
    image_client = compute_v1.ImagesClient()
    image_response = image_client.get_from_family(
        project=IMAGE_PROJECT,
        family=IMAGE_FAMILY
    )
    source_disk_image = image_response.self_link
    
    # Configure the machine
    machine_type = f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}"
    
    # Network interface
    network_interface = compute_v1.NetworkInterface()
    network_interface.name = "global/networks/default"
    access_config = compute_v1.AccessConfig()
    access_config.name = "External NAT"
    access_config.type_ = "ONE_TO_ONE_NAT"
    access_config.network_tier = "PREMIUM"
    network_interface.access_configs = [access_config]
    
    # Disk configuration
    disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = source_disk_image
    initialize_params.disk_size_gb = 20
    initialize_params.disk_type = f"zones/{ZONE}/diskTypes/pd-standard"
    disk.initialize_params = initialize_params
    disk.auto_delete = True
    disk.boot = True
    
    # Instance configuration
    instance = compute_v1.Instance()
    instance.name = INSTANCE_NAME
    instance.machine_type = machine_type
    instance.disks = [disk]
    instance.network_interfaces = [network_interface]
    
    # Startup script to install required packages
    startup_script = """#!/bin/bash
    apt-get update
    apt-get install -y nginx python3 python3-pip
    pip3 install flask gunicorn
    """
    
    # Metadata
    metadata = compute_v1.Metadata()
    metadata_items = [
        compute_v1.Items(
            key="startup-script",
            value=startup_script
        )
    ]
    metadata.items = metadata_items
    instance.metadata = metadata
    
    # Create the instance
    operation = instance_client.insert(
        project=PROJECT_ID,
        zone=ZONE,
        instance_resource=instance
    )
    
    # Wait for the operation to complete
    while not operation.status == "DONE":
        time.sleep(5)
        operation = instance_client.get_operation(
            project=PROJECT_ID,
            zone=ZONE,
            operation=operation.name
        )
    
    if operation.error:
        logging.error(f"Error creating instance: {operation.error}")
        return None
    
    # Get the instance details
    instance = instance_client.get(
        project=PROJECT_ID,
        zone=ZONE,
        instance=INSTANCE_NAME
    )
    
    external_ip = instance.network_interfaces[0].access_configs[0].nat_ip
    logging.info(f"GCP instance created with IP: {external_ip}")
    
    return external_ip

def deploy_application(ip_address):
    """Deploy the application to the GCP instance"""
    logging.info("Deploying application to GCP instance...")
    
    # Wait for SSH to be available
    time.sleep(60)
    
    # Create a compressed archive of the application
    subprocess.run(["tar", "-czvf", "app.tar.gz", "-C", os.path.dirname(APP_PATH), os.path.basename(APP_PATH)])
    
    # Copy the archive to the GCP instance
    subprocess.run(["gcloud", "compute", "scp", "app.tar.gz", f"ubuntu@{INSTANCE_NAME}:~", "--zone", ZONE])
    
    # Extract and run the application
    subprocess.run([
        "gcloud", "compute", "ssh", f"ubuntu@{INSTANCE_NAME}", "--zone", ZONE, "--command",
        "mkdir -p app && tar -xzvf app.tar.gz -C app && cd app && sudo pip3 install -r requirements.txt && sudo systemctl restart nginx && sudo nohup gunicorn -b 0.0.0.0:8000 app:app &"
    ])
    
    logging.info("Application deployed successfully")

def main():
    """Main function to monitor resources and scale to cloud if needed"""
    logging.info("Starting auto-scaling service")
    
    while True:
        if check_resources():
            # Create GCP instance
            external_ip = create_gcp_instance()
            
            if external_ip:
                # Deploy application
                deploy_application(external_ip)
                
                logging.info(f"Migration complete. Application running at http://{external_ip}")
                break
        
        # Wait for the next check interval
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()