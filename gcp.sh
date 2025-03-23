#!/bin/bash

# Log all output for debugging
exec > >(tee /var/log/startup-script.log) 2>&1

echo "[$(date)] Starting setup script"

# Install required packages
apt-get update
apt-get install -y python3 python3-pip python3-venv git

# Create directory for application
mkdir -p /opt/todo-app
cd /opt/todo-app

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask prometheus_client gunicorn requests

# Create application files
cat > /opt/todo-app/app.py << 'EOF'
from flask import Flask, request, jsonify, render_template_string
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time
import os
import threading
import json

app = Flask(__name__)

# Prometheus metrics
request_count = Counter('app_request_count_total', 'Total app HTTP request count')
request_latency = Histogram('app_request_latency_seconds', 'Request latency in seconds')
cpu_usage = Gauge('app_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('app_memory_usage_percent', 'Memory usage percentage')

# Sample in-memory database
todos = []
next_id = 1

# HTML template for the UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Simple Todo App (GCP VM)</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .todo-item { margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; }
        .completed { text-decoration: line-through; color: #888; }
        form { margin-bottom: 20px; }
        input[type="text"] { padding: 8px; width: 70%; }
        button { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .metrics { margin-top: 30px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
        .cloud-notice { background-color: #ffc107; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="cloud-notice">
        <strong>Notice:</strong> This application is currently running on Google Cloud Platform due to high resource usage on the local VM.
    </div>

    <h1>Todo List</h1>
    <form id="todo-form">
        <input type="text" id="new-todo" placeholder="Add a new task" required>
        <button type="submit">Add</button>
    </form>
    
    <div id="todo-list">
        {% for todo in todos %}
            <div class="todo-item {% if todo.completed %}completed{% endif %}">
                <input type="checkbox" onclick="toggleTodo({{ todo.id }})" {% if todo.completed %}checked{% endif %}>
                {{ todo.title }}
                <button onclick="deleteTodo({{ todo.id }})" style="float: right; background-color: #f44336;">Delete</button>
            </div>
        {% endfor %}
    </div>
    
    <div class="metrics">
        <h3>System Metrics</h3>
        <p>CPU Usage: <span id="cpu-usage">{{ cpu }}%</span></p>
        <p>Memory Usage: <span id="memory-usage">{{ memory }}%</span></p>
    </div>

    <script>
        function toggleTodo(id) {
            fetch(`/api/todos/${id}/toggle`, { method: 'PUT' })
                .then(response => response.json())
                .then(data => window.location.reload());
        }
        
        function deleteTodo(id) {
            fetch(`/api/todos/${id}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(data => window.location.reload());
        }
        
        document.getElementById('todo-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const title = document.getElementById('new-todo').value;
            fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title })
            })
            .then(response => response.json())
            .then(data => window.location.reload());
        });
        
        // Refresh metrics every 5 seconds
        setInterval(() => {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('cpu-usage').textContent = data.cpu + '%';
                    document.getElementById('memory-usage').textContent = data.memory + '%';
                });
        }, 5000);
    </script>
</body>
</html>
'''

def update_system_metrics():
    """Update system metrics periodically"""
    while True:
        try:
            # Read CPU usage
            with open('/proc/stat', 'r') as f:
                cpu_line = f.readline().strip().split()
                user = int(cpu_line[1])
                nice = int(cpu_line[2])
                system = int(cpu_line[3])
                idle = int(cpu_line[4])
                total = user + nice + system + idle
                cpu_percent = 100 * (1 - idle / total)
                cpu_usage.set(cpu_percent)
            
            # Read memory usage
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                total_mem = int(lines[0].split()[1])
                free_mem = int(lines[1].split()[1])
                mem_percent = 100 * (1 - free_mem / total_mem)
                memory_usage.set(mem_percent)
            
            # Save current metrics to file
            with open('/tmp/app_metrics.json', 'w') as f:
                json.dump({
                    'cpu': cpu_percent,
                    'memory': mem_percent
                }, f)
                
        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        time.sleep(5)

@app.route('/')
def index():
    try:
        with open('/tmp/app_metrics.json', 'r') as f:
            metrics = json.load(f)
    except:
        metrics = {'cpu': 0, 'memory': 0}
    
    return render_template_string(HTML_TEMPLATE, todos=todos, cpu=round(metrics['cpu'], 2), memory=round(metrics['memory'], 2))

@app.route('/api/todos', methods=['GET'])
@request_latency.time()
def get_todos():
    request_count.inc()
    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
@request_latency.time()
def create_todo():
    global next_id
    request_count.inc()
    
    data = request.json
    todo = {
        'id': next_id,
        'title': data['title'],
        'completed': False
    }
    next_id += 1
    todos.append(todo)
    return jsonify(todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
@request_latency.time()
def delete_todo(todo_id):
    request_count.inc()
    
    global todos
    todos = [todo for todo in todos if todo['id'] != todo_id]
    return jsonify({'success': True})

@app.route('/api/todos/<int:todo_id>/toggle', methods=['PUT'])
@request_latency.time()
def toggle_todo(todo_id):
    request_count.inc()
    
    for todo in todos:
        if todo['id'] == todo_id:
            todo['completed'] = not todo['completed']
            return jsonify(todo)
    
    return jsonify({'error': 'Todo not found'}), 404

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    try:
        with open('/tmp/app_metrics.json', 'r') as f:
            metrics = json.load(f)
    except:
        metrics = {'cpu': 0, 'memory': 0}
    
    return jsonify({
        'cpu': round(metrics['cpu'], 2),
        'memory': round(metrics['memory'], 2)
    })

if __name__ == '__main__':
    # Start metrics server on port 8000
    start_http_server(8000)
    
    # Start the metrics update thread
    metrics_thread = threading.Thread(target=update_system_metrics, daemon=True)
    metrics_thread.start()
    
    # Add some initial todos
    todos = [
        {'id': 1, 'title': 'Learn Flask', 'completed': True},
        {'id': 2, 'title': 'Build a Todo app', 'completed': False},
        {'id': 3, 'title': 'Implement auto-scaling', 'completed': False}
    ]
    next_id = 4
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
EOF

# Create WSGI file
cat > /opt/todo-app/wsgi.py << EOF
from app import app

if __name__ == "__main__":
    app.run()
EOF

# Create systemd service file
cat > /etc/systemd/system/todo-app.service << EOF
[Unit]
Description=Todo Application
After=network.target

[Service]
User=root
WorkingDirectory=/opt/todo-app
ExecStart=/opt/todo-app/venv/bin/gunicorn --bind 0.0.0.0:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start and enable the service
systemctl daemon-reload
systemctl start todo-app
systemctl enable todo-app

echo "[$(date)] Startup script completed"