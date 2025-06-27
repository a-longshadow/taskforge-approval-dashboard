# Copy-Paste Configurations

## 🔧 HTTP Request Node (POST - Store Tasks)

### Settings to Configure:
- **Method**: `POST`
- **URL**: `https://web-production-c8f1d.up.railway.app/store-tasks`
- **Send Body**: `Yes` ✅
- **Body Content Type**: `JSON`
- **Specify Body**: `JSON`

### JSON Body (Copy-Paste This Exactly):
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

---

## 🔧 HTTP Request1 Node (GET - Retrieve Approved)

### Settings to Configure:
- **Method**: `GET`
- **URL**: (Copy-paste this exactly)
```
https://web-production-c8f1d.up.railway.app/get-approved/{{ $json.execution_id }}
```
- **Send Body**: `No` ❌
- **Authentication**: `None`

### ⚠️ CRITICAL FIX:
Use `{{ $json.execution_id }}` NOT `{{ $('HTTP Request').first().json.execution_id }}`
The execution_id comes from the HITL node, not the HTTP Request response.

---

## 🧪 Test the Configuration

### 1. Run the workflow and check HTTP Request output:
Should see:
```json
{
  "success": true,
  "execution_id": "exec_123456789",
  "stored_tasks": 24
}
```

### 2. Click the approval link in Telegram/Email
- Should load the Railway UI
- Approve some tasks
- Submit

### 3. Check HTTP Request1 output:
Should see:
```json
{
  "approved_tasks": [...],
  "approved_count": 5,
  "total_tasks": 24
}
```

## 🚨 Critical Points

1. **HTTP Request JSON**: `tasks` and `total_tasks` have NO QUOTES
2. **HTTP Request1 URL**: Must reference the first HTTP Request's execution_id
3. **Flow**: POST → User Approval → GET → Build Payload

## 🐛 If Something Breaks

### HTTP Request fails?
- Check Railway app is running
- Verify JSON syntax (no extra quotes)

### HTTP Request1 returns 404?
- Normal if user hasn't approved yet
- Check execution_id matches

### No approved tasks?
- User might not have approved any
- Check Railway app UI works 