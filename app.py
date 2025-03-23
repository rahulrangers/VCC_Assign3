from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Simple in-memory storage for TODOs
todos = []

# HTML template for the TODO app
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Simple TODO App</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .todo-item { margin: 10px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px; }
        .todo-form { margin: 20px 0; }
        input[type="text"] { padding: 8px; width: 80%; }
        button { padding: 8px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #45a049; }
    </style>
</head>
<body>
    <h1>Simple TODO Application</h1>
    
    <div class="todo-form">
        <input type="text" id="newTodo" placeholder="Enter a new task...">
        <button onclick="addTodo()">Add TODO</button>
    </div>
    
    <h2>Current TODOs:</h2>
    <div id="todoList">
        {% for todo in todos %}
            <div class="todo-item">
                <p>{{ todo.task }}</p>
                <button onclick="deleteTodo({{ todo.id }})">Delete</button>
            </div>
        {% endfor %}
    </div>

    <script>
        function addTodo() {
            const task = document.getElementById('newTodo').value;
            if (task) {
                fetch('/api/todos', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ task: task }),
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('newTodo').value = '';
                    window.location.reload();
                });
            }
        }
        
        function deleteTodo(id) {
            fetch(`/api/todos/${id}`, {
                method: 'DELETE',
            })
            .then(() => {
                window.location.reload();
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, todos=todos)

@app.route('/api/todos', methods=['GET'])
def get_todos():
    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data = request.json
    todo_id = len(todos) + 1
    new_todo = {
        'id': todo_id,
        'task': data.get('task', '')
    }
    todos.append(new_todo)
    return jsonify(new_todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    global todos
    todos = [todo for todo in todos if todo['id'] != todo_id]
    return '', 204

if __name__ == '__main__':
    # Create some sample TODOs
    todos = [
        {'id': 1, 'task': 'Learn about VM auto-scaling'},
        {'id': 2, 'task': 'Set up monitoring with Prometheus'},
        {'id': 3, 'task': 'Deploy application to GCP'}
    ]
    
    app.run(host='0.0.0.0', port=5000)