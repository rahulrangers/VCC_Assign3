#!/usr/bin/env python3
import requests
import time
import subprocess
from threading import Thread

# Prometheus API endpoint and query to calculate CPU usage as a percentage.
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
# Query: calculates CPU usage as 100 - idle percentage.
QUERY = '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'

# Configuration parameters
THRESHOLD = 75.0        # CPU usage threshold (%)
CHECK_INTERVAL = 15     # Seconds between queries
TRIGGER_DURATION = 10   # Seconds that usage must be above threshold
# New script to resize the managed instance group.
AUTO_SCALE_SCRIPT = "./scripts/resize_instance_group.sh"

def query_prometheus():
    """Query Prometheus for the current CPU usage percentage."""
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": QUERY})
        data = response.json()
        if data["status"] == "success":
            values = [float(result["value"][1]) for result in data["data"]["result"]]
            if values:
                avg_cpu = sum(values) / len(values)
                return avg_cpu
    except Exception as e:
        print("Error querying Prometheus:", e)
    return None

def start_flask_app():
    """Start the Flask Todo application from flask_app/app.py."""
    subprocess.Popen(["python3", "flask_app/app.py"])
    print("Flask app started.")

def monitor_resources():
    """Monitor CPU usage via Prometheus and trigger MIG resize when above threshold."""
    over_threshold_since = None
    while True:
        cpu_usage = query_prometheus()
        if cpu_usage is not None:
            print(f"Average CPU usage from Prometheus: {cpu_usage:.2f}%")
            if cpu_usage > THRESHOLD:
                if over_threshold_since is None:
                    over_threshold_since = time.time()
                else:
                    elapsed = time.time() - over_threshold_since
                    if elapsed >= TRIGGER_DURATION:
                        print("High CPU usage sustained. Triggering instance group resize.")
                        subprocess.Popen(["bash", AUTO_SCALE_SCRIPT])
                        over_threshold_since = None  # Reset after triggering
            else:
                over_threshold_since = None
        else:
            print("Failed to retrieve CPU usage from Prometheus.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Start the Flask application in a separate thread.
    flask_thread = Thread(target=start_flask_app)
    flask_thread.start()
    # Begin monitoring resources via Prometheus.
    monitor_resources()
