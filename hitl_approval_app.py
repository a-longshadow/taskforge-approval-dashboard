from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import json
import uuid
from datetime import datetime
import os

app = Flask(__name__)

# Store approval sessions in memory (use Redis in production)
approval_sessions = {}

@app.route('/')
def index():
    return "<h1>TaskForge Approval System</h1><p>Ready to receive approval requests.</p>"

@app.route('/approve/<session_id>')
def approve_tasks(session_id):
    if session_id not in approval_sessions:
        return "<h1>Session Expired</h1><p>This approval link is no longer valid.</p>", 404
    
    session_data = approval_sessions[session_id]
    return render_template('approve.html', 
                         session_id=session_id,
                         tasks=session_data['tasks'],
                         execution_id=session_data['execution_id'],
                         timestamp=session_data['timestamp'])

@app.route('/submit_approval', methods=['POST'])
def submit_approval():
    session_id = request.form.get('session_id')
    
    if session_id not in approval_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = approval_sessions[session_id]
    approved_tasks = []
    
    # Process form data
    for task in session_data['tasks']:
        task_id = task['task_id']
        action = request.form.get(f'action_{task_id}')
        
        if action == 'approve':
            approved_tasks.append(task)
    
    # Send back to N8N webhook
    webhook_url = session_data['webhook_return_url']
    response_data = {
        'execution_id': session_data['execution_id'],
        'session_id': session_id,
        'approved_tasks': approved_tasks,
        'total_tasks': len(session_data['tasks']),
        'approved_count': len(approved_tasks),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        requests.post(webhook_url, json=response_data, timeout=10)
    except Exception as e:
        print(f"Error sending to webhook: {e}")
    
    # Destroy the session
    del approval_sessions[session_id]
    
    return f"<h1>Approval Submitted!</h1><p>{len(approved_tasks)} tasks approved and sent to TaskForge.</p><p>This link is now destroyed.</p>"

@app.route('/receive-approval-request', methods=['POST'])
def receive_approval_request():
    data = request.json
    session_id = str(uuid.uuid4())
    
    # Store the session
    approval_sessions[session_id] = {
        'execution_id': data.get('execution_id'),
        'tasks': data.get('tasks', []),
        'webhook_return_url': data.get('webhook_return_url'),
        'timestamp': data.get('timestamp', datetime.now().isoformat())
    }
    
    approval_url = f"{request.host_url}approve/{session_id}"
    
    return jsonify({
        'session_id': session_id,
        'approval_url': approval_url,
        'tasks_count': len(data.get('tasks', [])),
        'status': 'success'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 