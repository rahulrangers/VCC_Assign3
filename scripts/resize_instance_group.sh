#!/bin/bash
# This script resizes the managed instance group to a specified size.
INSTANCE_GROUP_NAME="todo-app-group"
ZONE="us-central1-a"
NEW_SIZE=3

echo "Resizing instance group $INSTANCE_GROUP_NAME to $NEW_SIZE instances."
gcloud compute instance-groups managed resize "$INSTANCE_GROUP_NAME" --size="$NEW_SIZE" --zone="$ZONE"
echo "Resize command executed."
