#!/usr/bin/env python3
import time
import json
import os
import subprocess
import logging
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/home/ubuntu/autoscale.log'
)

# GCP Configuration
GCP_PROJECT_ID = "YOUR_GCP_PROJECT_ID"  # Replace with your actual project ID
GCP_ZONE = "us-central1-a"              # Choose your preferred zone
GCP_MACHINE_TYPE = "e2-medium"          # Choose your preferred machine type
GCP_IMAGE_FAMILY = "ubuntu-2204-lts"
GCP_IMAGE_PROJECT = "ubuntu-os-cloud"
GCP_NETWORK = "default"

# Application Configuration
APP_PORT = 5000
THRESHOLD_CPU = 75.0     # CPU threshold in percentage
THRESHOLD_MEMORY = 75.0  # Memory threshold in percentage
CHECK_INTERVAL = 30      # Check every 30 seconds
SCALING_COOLDOWN = 300   # 5 minutes cooldown after scaling

# State tracking
is_scaled_to_cloud = False
last_scale_time = 0
instance_name = f"todo-app-vm-{int(time.time())}"

def get_metrics():
    """Get current system metrics from the app's metrics endpoint"""
    try:
        with open('/tmp/app_metrics.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read metrics: {e}")
        return {"cpu": 0, "memory": 0}

def should_scale_to_cloud(metrics):
    """Determine if we should scale to the cloud based on metrics"""
    # Check if we're above thresholds
    cpu_high = metrics.get('cpu', 0) > THRESHOLD_CPU
    memory_high = metrics.get('memory', 0) > THRESHOLD_MEMORY
    
    # Check if we're outside the cooldown period
    outside_cooldown = (time.time() - last_scale_time) > SCALING_COOLDOWN
    
    # Only scale if we're not already scaled, above thresholds, and outside cooldown
    return not is_scaled_to_cloud and (cpu_high or memory_high) and outside_cooldown

def create_gcp_vm():
    """Create a VM instance in GCP"""
    logging.info(f"Creating GCP VM instance: {instance_name}")
    
    try:
        # Create VM instance
        result = subprocess.run([
            "gcloud", "compute", "instances", "create", instance_name,
            "--project", GCP_PROJECT_ID,
            "--zone", GCP_ZONE,
            "--machine-type", GCP_MACHINE_TYPE,
            "--image-family", GCP_IMAGE_FAMILY,
            "--image-project", GCP_IMAGE_PROJECT,
            "--network", GCP_NETWORK,
            "--tags", "http-server,https-server",
            "--metadata-from-file", f"startup-script={os.path.expanduser('~/todo-app/gcp_startup.sh')}"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Failed to create VM: {result.stderr}")
            return False
        
        # Get the external IP of the new instance
        ip_result = subprocess.run([
            "gcloud", "compute", "instances", "describe", instance_name,
            "--project", GCP_PROJECT_ID,
            "--zone", GCP_ZONE,
            "--format", "json(networkInterfaces[0].accessConfigs[0].natIP)"
        ], capture_output=True, text=True)
        
        if ip_result.returncode != 0:
            logging.error(f"Failed to get VM IP: {ip_result.stderr}")
            return False
            
        ip_data = json.loads(ip_result.stdout)
        external_ip = ip_data.get('networkInterfaces', [{}])[0].get('accessConfigs', [{}])[0].get('natIP')
        
        if not external_ip:
            logging.error("Could not determine VM IP address")
            return False
            
        logging.info(f"VM created with IP: {external_ip}")
        
        # Wait for the application to start on the remote VM
        app_ready = False
        max_attempts = 20
        attempts = 0
        
        while not app_ready and attempts < max_attempts:
            try:
                response = requests.get(f"http://{external_ip}:{APP_PORT}/api/metrics", timeout=5)
                if response.status_code == 200:
                    app_ready = True
                    logging.info("Application is now running on GCP VM")
                else:
                    logging.info(f"Waiting for app to start (attempt {attempts+1}/{max_attempts})...")
                    time.sleep(15)
            except requests.RequestException:
                logging.info(f"Waiting for app to start (attempt {attempts+1}/{max_attempts})...")
                time.sleep(15)
            attempts += 1
        
        if not app_ready:
            logging.error("Timed out waiting for application to start")
            return False
            
        # Create firewall rule to allow access to the app
        firewall_result = subprocess.run([
            "gcloud", "compute", "firewall-rules", "create", f"allow-todo-app-{instance_name}",
            "--project", GCP_PROJECT_ID,
            "--allow", f"tcp:{APP_PORT}",
            "--target-tags", "http-server",
            "--description", "Allow access to Todo app"
        ], capture_output=True, text=True)
        
        if firewall_result.returncode != 0:
            logging.error(f"Failed to create firewall rule: {firewall_result.stderr}")
            # Not returning False here since the VM is created and might still work
        
        return True
    
    except Exception as e:
        logging.error(f"Error during VM creation: {e}")
        return False

def terminate_gcp_vm():
    """Terminate the GCP VM instance"""
    logging.info(f"Terminating GCP VM instance: {instance_name}")
    
    try:
        # Delete the VM instance
        result = subprocess.run([
            "gcloud", "compute", "instances", "delete", instance_name,
            "--project", GCP_PROJECT_ID,
            "--zone", GCP_ZONE,
            "--quiet"  # Don't ask for confirmation
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Failed to delete VM: {result.stderr}")
            return False
            
        # Delete the firewall rule
        fw_result = subprocess.run([
            "gcloud", "compute", "firewall-rules", "delete", f"allow-todo-app-{instance_name}",
            "--project", GCP_PROJECT_ID,
            "--quiet"
        ], capture_output=True, text=True)
        
        if fw_result.returncode != 0:
            logging.error(f"Failed to delete firewall rule: {fw_result.stderr}")
            # Not returning False since the VM is deleted
            
        logging.info("VM terminated successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error during VM termination: {e}")
        return False

def main():
    """Main monitoring loop"""
    global is_scaled_to_cloud, last_scale_time
    
    logging.info("Starting auto-scaling monitoring")
    
    while True:
        try:
            metrics = get_metrics()
            logging.info(f"Current metrics - CPU: {metrics.get('cpu', 0):.2f}%, Memory: {metrics.get('memory', 0):.2f}%")
            
            if should_scale_to_cloud(metrics):
                logging.info("Resource threshold exceeded, scaling to cloud")
                if create_gcp_vm():
                    is_scaled_to_cloud = True
                    last_scale_time = time.time()
                    logging.info("Successfully scaled to cloud")
                    
                    # Wait for the cooldown period before checking if we should scale back
                    time.sleep(SCALING_COOLDOWN)
                else:
                    logging.error("Failed to scale to cloud")
            
            # Check if we should scale back (this would be based on VM metrics)
            # This is simplified - in a real scenario, you would check the cloud VM's metrics
            elif is_scaled_to_cloud and time.time() - last_scale_time > SCALING_COOLDOWN:
                # For demo purposes, we'll just scale back after the cooldown period
                logging.info("Cooldown period elapsed, scaling back to local VM")
                if terminate_gcp_vm():
                    is_scaled_to_cloud = False
                    last_scale_time = time.time()
                    logging.info("Successfully scaled back to local VM")
                else:
                    logging.error("Failed to scale back to local VM")
        
        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()