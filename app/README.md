# TaskForge Railway App

This directory contains the Railway deployment for the TaskForge HITL (Human-in-the-Loop) approval dashboard.

## 🚀 Deployment

**Live URL**: https://web-production-c8f1d.up.railway.app

**Railway Project**: [TaskForge Approval Dashboard](https://railway.com/project/b7380a3c-c370-4006-9ea2-f206ea4b525f)

## 📁 Files

- **`server.py`** - Flask server with HTTP request endpoints
- **`index.html`** - Task approval UI (pure HTML/JS)
- **`requirements.txt`** - Python dependencies
- **`Procfile`** - Railway process configuration
- **`railway.toml`** - Railway deployment settings

## 🔄 Architecture

### HTTP Request Flow (New)
```
n8n → POST /store-tasks → UI loads via /get-tasks → User approves → POST /submit-approval → n8n GET /get-approved
```

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Serve main UI |
| `POST` | `/store-tasks` | Store tasks from n8n |
| `GET` | `/get-tasks/<exec_id>` | Load tasks for UI |
| `POST` | `/submit-approval` | Store approved tasks |
| `GET` | `/get-approved/<exec_id>` | Retrieve approved tasks (self-destructs) |

## 🛡️ Security Features

- **Self-destructing links**: URLs expire after use
- **In-memory storage**: No persistent data storage
- **Automatic cleanup**: Data removed after retrieval
- **One-time use**: Prevents replay attacks

## 🔧 Local Development

```bash
cd app/
pip install -r requirements.txt
python server.py
```

Access at: http://localhost:8080

## 📝 Notes

- **No database**: Uses in-memory Python dictionaries
- **Stateless**: Each deployment clears all data
- **Simple**: Pure Flask, no frameworks
- **Fast**: Minimal dependencies for quick startup 