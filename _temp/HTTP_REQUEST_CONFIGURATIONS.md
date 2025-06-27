# HTTP Request Configurations - Complete Setup

## Current Issues in Your Workflow

### ❌ HTTP Request Node Problems:
1. **Invalid JSON syntax** in the body
2. **HTTP Request1** calling wrong endpoint
3. **Missing proper JSON structure**

## ✅ FIXED: HTTP Request (POST - Store Tasks)

### Node Settings:
- **Method**: `POST`
- **URL**: `https://web-production-c8f1d.up.railway.app/store-tasks`
- **Send Body**: `Yes`
- **Body Content Type**: `JSON`
- **Specify Body**: `JSON`

### ✅ CORRECT JSON Body:
```json
{
  "execution_id": "{{ $json.execution_id }}",
  "tasks": {{ $json.tasks }},
  "meeting_title": "{{ $json.meeting_title }}",
  "created_at": "{{ $json.created_at }}",
  "total_tasks": {{ $json.total_tasks }},
  "source": "{{ $json.source }}"
}
```

**Key Points:**
- `tasks` and `total_tasks` have **NO QUOTES** (they stay as array/number)
- String fields have quotes: `"execution_id": "{{ $json.execution_id }}"`

## ✅ FIXED: HTTP Request1 (GET - Retrieve Approved Tasks)

### Node Settings:
- **Method**: `GET`
- **URL**: `https://web-production-c8f1d.up.railway.app/get-approved/{{ $('HTTP Request').first().json.execution_id }}`
- **Send Body**: `No`
- **Authentication**: `None`

### Expected Response:
```json
{
  "execution_id": "exec_123456",
  "approved_tasks": [
    {
      "task_id": "task_1",
      "task_item": "Complete integration",
      "assignee_full_names": "Joe Maina",
      "assignee_emails": "joe@example.com",
      "priority": "High",
      "brief_description": "...",
      "date_expected": "2025-01-01",
      "approved_at": "2025-01-01T10:30:00Z"
    }
  ],
  "approved_count": 1,
  "total_tasks": 5,
  "session_id": "session_123",
  "source": "TaskForge_HITL_Railway"
}
```

## Complete Flow Verification

### 1. HITL Node Output Structure:
```javascript
{
  // For Telegram
  telegram_message: "🔥 *TaskForge Approval Required*...",
  
  // For Email  
  email_subject: "🔥 TaskForge: 5 Action Items Need Approval",
  email_html: "<!DOCTYPE html>...",
  
  // For HTTP Request (CRITICAL - these exact field names)
  execution_id: "exec_1751064312554_gx24r5",
  tasks: [
    {
      task_id: "task_1751064312554_0",
      task_item: "Complete integration",
      assignee_full_names: "Joe Maina",
      assignee_emails: "joe@coophive.network",
      priority: "High",
      brief_description: "...",
      date_expected: "2025-01-01",
      meeting_title: "Unknown Meeting",
      meeting_organizer: "Unknown"
    }
  ],
  meeting_title: "Unknown Meeting",
  created_at: "2025-01-01T01:45:00.000Z",
  total_tasks: 24,
  source: "TaskForge_HITL_HTTP",
  
  // Common fields
  approval_url: "https://web-production-c8f1d.up.railway.app?exec_id=exec_1751064312554_gx24r5",
  tasks_count: 24
}
```

### 2. HTTP Request Flow:
```
HITL Node → HTTP Request (POST /store-tasks) → HTTP Request1 (GET /get-approved/{exec_id}) → Build Payload
```

### 3. What Should Happen:
1. **HITL Node** generates tasks and execution_id
2. **HTTP Request** POSTs tasks to Railway `/store-tasks`
3. User clicks approval link and approves tasks
4. **HTTP Request1** GETs approved tasks from `/get-approved/{exec_id}`
5. **Build Payload** processes approved tasks for Monday.com

## Quick Fix Instructions

### For HTTP Request Node:
Replace the current `jsonBody` with:
```json
{
  "execution_id": "{{ $json.execution_id }}",
  "tasks": {{ $json.tasks }},
  "meeting_title": "{{ $json.meeting_title }}",
  "created_at": "{{ $json.created_at }}",
  "total_tasks": {{ $json.total_tasks }},
  "source": "{{ $json.source }}"
}
```

### For HTTP Request1 Node:
Change the URL to:
```
https://web-production-c8f1d.up.railway.app/get-approved/{{ $('HTTP Request').first().json.execution_id }}
```

## Testing the Flow

### 1. Check HTTP Request Response:
Should return:
```json
{
  "success": true,
  "execution_id": "exec_123456",
  "stored_tasks": 24,
  "message": "Tasks stored successfully"
}
```

### 2. Check HTTP Request1 Response:
Should return approved tasks or 404 if not yet approved.

### 3. Check Build Payload Input:
Should receive the approved tasks from HTTP Request1.

## Error Scenarios

### If HTTP Request fails:
- Check Railway app logs
- Verify JSON structure is correct
- Ensure all required fields are present

### If HTTP Request1 returns 404:
- Normal - means user hasn't approved yet
- In production, add retry logic or polling

### If Build Payload gets no data:
- Check if HTTP Request1 received approved tasks
- Verify the execution_id matches between requests 