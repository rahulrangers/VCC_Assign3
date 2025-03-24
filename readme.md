# VM Auto-Scaling Monitoring System

This project implements an automated system that monitors a local VM and triggers auto-scaling to Google Cloud Platform (GCP) when resource usage exceeds 75%.

## Overview

The system continuously monitors CPU, memory, and disk usage on a local VM. When resource utilization crosses the 75% threshold, it automatically provisions new instances on GCP using instance groups to handle the increased load.

## Architecture

```
Local VM ─────┐
  │           │
  ▼           │
Monitoring    │ Resource Usage > 75%
(Prometheus)  │
  │           │
  ▼           ▼
Visualization ───> GCP Auto-Scaling
(Grafana)          (Instance Groups)
  │
  ▼
Sample Flask App
(Load Generator)
```

## File Structure

```
├── flask_app/
│   └── app.py                # Sample Flask application to demonstrate load
├── scripts/
│   ├── create_instance_group.sh   # Script to create instance group on GCP
│   ├── resize_instance_group.sh   # Script to resize instance group based on load
│   └── startup_script.sh     # Initialization script for new VM instances
├── monitor_start.py          # Main monitoring script that tracks resource usage
└── readme.md                 # This documentation file
```

## Setup Instructions

### Prerequisites

- Python 3.7+
- VirtualBox or VMware for local VM
- Google Cloud SDK
- Prometheus
- Grafana
- Flask and required Python packages

### Local VM Setup

1. Create a local VM using VirtualBox or VMware with Ubuntu 20.04
2. Install required dependencies:

```bash
sudo apt update
sudo apt install -y python3-pip prometheus-node-exporter
pip3 install prometheus-client flask psutil requests google-api-python-client
```

3. Clone this repository to your local VM

### Prometheus Setup

1. Install Prometheus:

```bash
wget https://github.com/prometheus/prometheus/releases/download/v2.37.0/prometheus-2.37.0.linux-amd64.tar.gz
tar xvfz prometheus-2.37.0.linux-amd64.tar.gz
```

2. Configure Prometheus using the following config to scrape metrics from the local VM:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'flask-app'
    static_configs:
      - targets: ['localhost:5000']
```

### Grafana Setup

1. Install Grafana:

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana
sudo systemctl start grafana-server
```

2. Access Grafana at http://localhost:3000 (default credentials: admin/admin)
3. Add Prometheus as a data source
4. Import the dashboard template provided in the repository

### GCP Configuration

1. Set up a Google Cloud Platform account and create a project
2. Install and configure Google Cloud SDK
3. Authenticate with GCP:

```bash
gcloud auth login
gcloud config set project [YOUR_PROJECT_ID]
```

4. Enable required APIs:
   - Compute Engine API
   - Cloud Monitoring API
   - Cloud Resource Manager API

## Running the System

1. Start the Flask application:

```bash
cd flask_app
python3 app.py
```

2. Start the monitoring script:

```bash
python3 monitor_start.py
```

3. Access Grafana dashboard at http://localhost:3000 to view resource metrics

## Auto-Scaling Process

1. The monitoring script (`monitor_start.py`) continuously checks resource usage 
2. When any resource (CPU, memory, disk) exceeds 75% utilization, it calls the `create_instance_group.sh` script
3. The script provisions a new instance group on GCP with the required configurations
4. As resource usage fluctuates, the `resize_instance_group.sh` script adjusts the number of instances accordingly
5. Each new instance uses `startup_script.sh` for initialization and configuration

## Testing

To test the auto-scaling functionality:

1. Run a stress test on the Flask application to increase CPU usage:

```bash
# Install stress-ng if not already installed
sudo apt-get install stress-ng
# Run stress test
stress-ng --cpu 4 --timeout 300s
```

2. Observe the Grafana dashboard to see resource usage exceed 75%
3. Verify that new instances are created in the GCP console

## Troubleshooting

- If monitoring fails, check Prometheus endpoint at http://localhost:9090
- Verify GCP credentials and permissions
- Check logs for the monitoring script: `journalctl -u monitor.service`
- Ensure all required GCP APIs are enabled

## Contributors

- Purmani Rahul Reddy (B22CS041)

## License

This project is licensed under the MIT License - see the LICENSE file for details