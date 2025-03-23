# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Node Exporter for Prometheus
wget https://github.com/prometheus/node_exporter/releases/download/v1.5.0/node_exporter-1.5.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.5.0.linux-amd64.tar.gz
sudo mv node_exporter-1.5.0.linux-amd64/node_exporter /usr/local/bin/
sudo useradd -rs /bin/false node_exporter

# Create systemd service for Node Exporter
sudo tee /etc/systemd/system/node_exporter.service > /dev/null << EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

# Start and enable Node Exporter
sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter

# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.43.0/prometheus-2.43.0.linux-amd64.tar.gz
tar xvfz prometheus-2.43.0.linux-amd64.tar.gz
sudo mv prometheus-2.43.0.linux-amd64 /opt/prometheus

# Create Prometheus config file
sudo tee /opt/prometheus/prometheus.yml > /dev/null << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
EOF

# Create systemd service for Prometheus
sudo tee /etc/systemd/system/prometheus.service > /dev/null << EOF
[Unit]
Description=Prometheus
After=network.target

[Service]
User=root
Group=root
Type=simple
ExecStart=/opt/prometheus/prometheus --config.file=/opt/prometheus/prometheus.yml

[Install]
WantedBy=multi-user.target
EOF

# Start and enable Prometheus
sudo systemctl daemon-reload
sudo systemctl start prometheus
sudo systemctl enable prometheus

# Install Google Cloud SDK
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-425.0.0-linux-x86_64.tar.gz
tar -xf google-cloud-sdk-425.0.0-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh

# Initialize gcloud
./google-cloud-sdk/bin/gcloud init

mkdir -p ~/todo-app
cd ~/todo-app
python3 -m venv venv
source venv/bin/activate
pip install flask prometheus_client gunicorn
sudo tee /etc/systemd/system/todo-app.service > /dev/null << EOF
[Unit]
Description=Todo Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/todo-app
ExecStart=/home/ubuntu/todo-app/venv/bin/gunicorn --bind 0.0.0.0:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start todo-app
sudo systemctl enable todo-app

cat > ~/todo-app/wsgi.py << EOF
from app import app

if __name__ == "__main__":
    app.run()
EOF

# Save the auto-scaling script to ~/todo-app/autoscale.py
# Save the GCP startup script to ~/todo-app/gcp_startup.sh
chmod +x ~/todo-app/autoscale.py
chmod +x ~/todo-app/gcp_startup.sh

sudo tee /etc/systemd/system/autoscale.service > /dev/null << EOF
[Unit]
Description=Auto-Scaling Service
After=network.target todo-app.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/todo-app
ExecStart=/home/ubuntu/todo-app/venv/bin/python /home/ubuntu/todo-app/autoscale.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start autoscale
sudo systemctl enable autoscale

gcloud auth login
