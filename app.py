from flask import Flask, render_template_string, request, jsonify
import requests
import json
import uuid
from datetime import datetime

app = Flask(__name__)

# Store sessions in memory
sessions = {}

# Simple HTML template
TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>TaskForge Approval</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { background: #4CAF50; color: white; padding: 20px; border-radius: 5px; text-align: center; }
        .meeting { background: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .task { border-left: 4px solid #2196F3; padding: 15px; margin: 10px 0; background: #f9f9f9; }
        .task.approved { border-left-color: #4CAF50; background: #e8f5e9; }
        .task.rejected { border-left-color: #f44336; background: #ffebee; }
        .task-title { font-weight: bold; margin-bottom: 10px; }
        .task-details { font-size: 0.9em; color: #666; margin-bottom: 10px; }
        .task-actions { text-align: right; }
        button { padding: 8px 16px; margin: 0 5px; border: none; border-radius: 3px; cursor: pointer; }
        .approve { background: #4CAF50; color: white; }
        .reject { background: #f44336; color: white; }
        .submit { background: #2196F3; color: white; padding: 15px 30px; font-size: 16px; margin: 20px 0; }
        .counter { position: fixed; top: 20px; right: 20px; background: #2196F3; color: white; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="counter">Approved: <span id="count">0</span>/{{ tasks|length }}</div>
    
    <div class="container">
        <div class="header">
            <h1>🚀 TaskForge Approval</h1>
            <p>Meeting: {{ meeting_title }}</p>
            <p>{{ tasks|length }} tasks found</p>
        </div>
        
        <form id="approvalForm">
            {% for task in tasks %}
            <div class="task" data-task-id="{{ task.task_id }}">
                <div class="task-title">{{ task.task_item }}</div>
                <div class="task-details">
                    👤 {{ task.assignee_full_names }} ({{ task.assignee_emails }})<br>
                    📅 Due: {{ task.date_expected }} | 🔥 Priority: {{ task.priority }}
                </div>
                <div>{{ task.brief_description }}</div>
                <div class="task-actions">
                    <button type="button" class="reject" onclick="setAction('{{ task.task_id }}', 'reject')">❌ Reject</button>
                    <button type="button" class="approve" onclick="setAction('{{ task.task_id }}', 'approve')">✅ Approve</button>
                </div>
                <input type="hidden" name="action_{{ task.task_id }}" value="reject">
            </div>
            {% endfor %}
            
            <div style="text-align: center;">
                <button type="button" class="submit" onclick="submitApproval()">💾 Save & Send to TaskForge</button>
            </div>
        </form>
    </div>
    
    <script>
        let approvedCount = 0;
        const sessionId = '{{ session_id }}';
        const webhookUrl = '{{ webhook_url }}';
        
        function setAction(taskId, action) {
            const task = document.querySelector(`[data-task-id="${taskId}"]`);
            const input = document.querySelector(`input[name="action_${taskId}"]`);
            
            task.className = 'task ' + action + 'd';
            input.value = action;
            
            updateCounter();
        }
        
        function updateCounter() {
            approvedCount = document.querySelectorAll('input[value="approve"]').length;
            document.getElementById('count').textContent = approvedCount;
        }
        
        function submitApproval() {
            const formData = new FormData(document.getElementById('approvalForm'));
            const approved = [];
            
            {% for task in tasks %}
            if (formData.get('action_{{ task.task_id }}') === 'approve') {
                approved.push({{ task|tojson }});
            }
            {% endfor %}
            
            fetch(webhookUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    approved_tasks: approved,
                    approved_count: approved.length,
                    total_tasks: {{ tasks|length }},
                    timestamp: new Date().toISOString()
                })
            }).then(() => {
                document.body.innerHTML = '<div class="container"><div class="header"><h1>✅ Approved!</h1><p>' + approved.length + ' tasks sent to TaskForge</p><p>This page will now close.</p></div></div>';
                setTimeout(() => window.close(), 2000);
            });
        }
        
        // Initialize all as rejected
        {% for task in tasks %}
        setAction('{{ task.task_id }}', 'reject');
        {% endfor %}
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return '<h1>TaskForge Approval System</h1><p>Ready!</p>'

@app.route('/approve/<session_id>')
def approve(session_id):
    if session_id not in sessions:
        return '<h1>Session Expired</h1>', 404
    
    data = sessions[session_id]
    return render_template_string(TEMPLATE, 
        session_id=session_id,
        tasks=data['tasks'],
        meeting_title=data['meeting_title'],
        webhook_url=data['webhook_url']
    )

@app.route('/create-session', methods=['POST'])
def create_session():
    data = request.json
    session_id = str(uuid.uuid4())
    
    sessions[session_id] = {
        'tasks': data.get('tasks', []),
        'meeting_title': data.get('meeting_title', 'Unknown Meeting'), 
        'webhook_url': data.get('webhook_url', ''),
        'created': datetime.now().isoformat()
    }
    
    approval_url = f"{request.host_url}approve/{session_id}"
    
    return jsonify({
        'session_id': session_id,
        'approval_url': approval_url,
        'tasks_count': len(data.get('tasks', []))
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 