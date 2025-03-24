#!/bin/bash
# This startup script runs on each new instance created by the MIG.
sudo apt-get update
sudo apt-get install -y python3 python3-pip wget
sudo apt-get install -y python3-flask

# Download the Flask Todo application from your repository.
# Replace the URL with your actual repository URL.
wget -O /home/$USER/app.py https://raw.githubusercontent.com/yourusername/yourrepo/main/app.py

# Run the Flask Todo application in the background.
nohup python3 /home/$USER/app.py > /home/$USER/todo_app.log 2>&1 &
