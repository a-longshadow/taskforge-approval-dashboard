# TaskForge HITL HTTP Request Conversion Plan

## Overview
Convert webhook-based HITL approval system to HTTP request-based system for simpler, more controlled workflow execution.

## Current Architecture vs New Architecture

### Current (Webhook-based):
```
n8n HITL Node → Notifications → Webhook Listener → Build Payload
```

### New (HTTP Request-based):
```
n8n HITL Node → HTTP POST (store) → HTTP GET (retrieve) → Build Payload
```

## 1. HITL Node: "HITL · Generate Approval Payload + Send Notifications"

### Current Outputs (3 nodes):
1. **Telegram1** - Send notification
2. **Gmail** - Send email notification  
3. **HTTP Request** - Store tasks for approval

### Required Code Changes:

```javascript
// HITL APPROVAL - HTTP REQUEST APPROACH (No Sessions)
try {
  const tasks = [];
  
  // Process input tasks
  items.forEach((item, index) => {
    if (item.json) {
      tasks.push({
        task_id: `task_${Date.now()}_${index}`,
        task_item: item.json.task_item || 'Untitled Task',
        assignee_full_names: item.json['assignee(s)_full_names'] || 'Unassigned',
        assignee_emails: item.json.assignee_emails || '',
        priority: item.json.priority || 'Medium',
        brief_description: item.json.brief_description || 'No description',
        date_expected: item.json.date_expected || new Date().toISOString().split('T')[0],
        meeting_title: item.json.meeting_title || 'TaskForge Meeting',
        meeting_organizer: item.json.meeting_organizer || 'Unknown'
      });
    }
  });

  if (tasks.length === 0) {
    return [{ json: { error: 'No tasks found', status: 'no_tasks' } }];
  }

  // Generate unique execution ID for this approval session
  const executionId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  const meetingTitle = tasks[0].meeting_title || 'TaskForge Meeting';
  
  // Prepare data for Railway app
  const tasksData = encodeURIComponent(JSON.stringify(tasks));
  const approvalUrl = `https://web-production-c8f1d.up.railway.app?tasks=${tasksData}&title=${encodeURIComponent(meetingTitle)}&exec_id=${executionId}`;

  // Prepare payload for HTTP POST to Railway
  const storePayload = {
    execution_id: executionId,
    tasks: tasks,
    meeting_title: meetingTitle,
    created_at: new Date().toISOString(),
    total_tasks: tasks.length
  };

  return [
    // Output 1: For Telegram notification
    {
      json: {
        telegram_message: `🔥 *TaskForge Approval Required*\\n\\n📋 *Meeting:* ${meetingTitle}\\n📊 *Tasks:* ${tasks.length}\\n\\n👆 [*APPROVE TASKS*](${approvalUrl})`,
        approval_url: approvalUrl,
        tasks_count: tasks.length,
        execution_id: executionId
      }
    },
    // Output 2: For Gmail notification
    {
      json: {
        email_subject: `TaskForge: ${tasks.length} Action Items Need Approval`,
        email_html: `<h2>TaskForge Approval</h2><p>${tasks.length} tasks need approval.</p><p><a href="${approvalUrl}">Click to approve</a></p>`,
        approval_url: approvalUrl,
        tasks_count: tasks.length,
        execution_id: executionId
      }
    },
    // Output 3: For HTTP POST to Railway (store tasks)
    {
      json: {
        ...storePayload,
        url: 'https://web-production-c8f1d.up.railway.app/store-tasks',
        method: 'POST',
        status: 'ready_to_store'
      }
    }
  ];

} catch (error) {
  return [{ json: { error: error.message, status: 'error' } }];
}
```

## 2. HTTP Request Nodes Configuration

### HTTP Request Node 1: "Store Tasks"
- **Method**: POST
- **URL**: `https://web-production-c8f1d.up.railway.app/store-tasks`
- **Body**: JSON from HITL node output 3
- **Headers**: `Content-Type: application/json`

### HTTP Request Node 2: "Retrieve Approved Tasks"
- **Method**: GET  
- **URL**: `https://web-production-c8f1d.up.railway.app/get-approved/{{ $('HITL · Generate Approval Payload + Send Notifications').first().json.execution_id }}`
- **Timeout**: 300 seconds (5 minutes for user approval)
- **Retry**: 3 attempts with 30s delay

## 3. Railway App Modifications

### server.py additions:
```python
# In-memory storage (simple dict)
stored_tasks = {}
approved_results = {}

@app.route('/store-tasks', methods=['POST'])
def store_tasks():
    data = request.get_json()
    execution_id = data.get('execution_id')
    stored_tasks[execution_id] = data
    return jsonify({'success': True, 'execution_id': execution_id})

@app.route('/get-approved/<execution_id>', methods=['GET'])
def get_approved(execution_id):
    if execution_id in approved_results:
        result = approved_results.pop(execution_id)  # Self-destruct
        stored_tasks.pop(execution_id, None)  # Cleanup
        return jsonify(result)
    return jsonify({'status': 'pending'}), 202

@app.route('/submit-approval', methods=['POST'])
def submit_approval():
    data = request.get_json()
    execution_id = data.get('execution_id')
    approved_results[execution_id] = data
    return jsonify({'success': True})
```

### index.html modifications:
```javascript
// Add execution_id handling
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        tasks: params.get('tasks'),
        title: params.get('title'),
        exec_id: params.get('exec_id')
    };
}

// Modified submit function
async function submitApprovals() {
    const params = getUrlParams();
    const payload = {
        execution_id: params.exec_id,
        approved_tasks: approvedTasks,
        // ... rest of payload
    };
    
    // Submit to our own server
    const response = await fetch('/submit-approval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    if (response.ok) {
        // Self-destruct UI
        document.body.innerHTML = '<div style="text-align:center;padding:50px;"><h2>✅ Submitted!</h2><p>This link has expired.</p></div>';
    }
}
```

## 4. Workflow Connection Changes

### Remove:
- Webhook node
- "HTTP Request1" (webhook wait)

### Add:
- "HTTP Request - Store Tasks" (connects to HITL output 3)
- "HTTP Request - Get Approved" (connects after Store Tasks)
- Connect "Get Approved" to "Build Payload for GDrive and Monday.com"

## 5. Benefits of New Approach

✅ **Simpler**: No webhook management  
✅ **Controlled**: n8n drives the flow  
✅ **Self-cleaning**: One-time use links  
✅ **Debuggable**: Clear request/response cycle  
✅ **Minimal**: Leverages existing Railway structure  

## 6. Implementation Steps

1. Update HITL node code
2. Add Railway server endpoints
3. Modify index.html for self-destruct
4. Replace webhook nodes with HTTP requests
5. Test end-to-end flow
6. Deploy Railway changes

## 7. Error Handling

- **Store fails**: Retry HTTP POST
- **User timeout**: Return empty approved tasks after 5 minutes
- **Get fails**: Retry with exponential backoff
- **Railway down**: Fallback to error reporting 