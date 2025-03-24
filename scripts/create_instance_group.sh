#!/bin/bash
# This script creates an instance template and a managed instance group (MIG) with autoscaling.

TEMPLATE_NAME="todo-app-template"
GROUP_NAME="todo-app-group"
ZONE="us-central1-a"
MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="debian-11"
IMAGE_PROJECT="debian-cloud"
# Path to your startup script (which will run on each new instance)
STARTUP_SCRIPT_PATH="/home/rahul/assign3/scripts/startup_script.sh"

echo "Creating instance template: $TEMPLATE_NAME"
gcloud compute instance-templates create "$TEMPLATE_NAME" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --metadata-from-file startup-script="$STARTUP_SCRIPT_PATH" \
    --tags=http-server

echo "Creating managed instance group: $GROUP_NAME"
gcloud compute instance-groups managed create "$GROUP_NAME" \
    --base-instance-name=todo-app-instance \
    --size=2 \
    --template="$TEMPLATE_NAME" \
    --zone="$ZONE"

echo "Setting autoscaling for $GROUP_NAME"
gcloud compute instance-groups managed set-autoscaling "$GROUP_NAME" \
    --max-num-replicas=5 \
    --min-num-replicas=2 \
    --target-cpu-utilization=0.75 \
    --cool-down-period=90 \
    --zone="$ZONE"

echo "Managed Instance Group with autoscaling is configured."
