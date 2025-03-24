#!/usr/bin/env python3
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)
todos = []

# Simple HTML template with a small frontend
html_template = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Todo App</title>
</head>
<body>
    <h1>Todo List</h1>
    <form action="{{ url_for('add_todo') }}" method="POST">
        <input type="text" name="todo" placeholder="Enter new todo" required>
        <input type="submit" value="Add">
    </form>
    <ul>
    {% for todo in todos %}
        <li>{{ todo }}</li>
    {% endfor %}
    </ul>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    return render_template_string(html_template, todos=todos)

@app.route('/add', methods=['POST'])
def add_todo():
    todo = request.form.get('todo')
    if todo:
        todos.append(todo)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Run on port 8080 so that the app is accessible from external instances
    app.run(host='0.0.0.0', port=8080)

