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
```n8n → POST /store-tasks → UI loads via /get-tasks → User approves → POST /submit-approval → n8n GET /get-approved
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
# --- Quick Postgres setup (Docker) ---
# pull & run a disposable Postgres 16 container
docker run -d --name hitl-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=hitl -p 5432:5432 postgres:16

# create a .env file (or export) with:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hitl

# then run the server
python server.py
```

Access at: http://localhost:8080

## 📝 Notes

- **No database**: Uses in-memory Python dictionaries
- **Stateless**: Each deployment clears all data
- **Simple**: Pure Flask, no frameworks
- **Fast**: Minimal dependencies for quick startup 

## ♻️ 2024-07 Update – HITL Behaviour

* The dashboard now supports **hand-pick approval**: only tasks marked `approved` are forwarded; un-selected items are dropped.
* The `/approved` endpoint blocks for up to 5 minutes (`APPROVAL_WAIT_SEC`). On timeout it auto-approves everything and replies 200 OK. The previous 202 "pending" response no longer exists.
* For local dev the SQLite connection is opened with `check_same_thread=False` to avoid thread errors when using Flask's debug server. 