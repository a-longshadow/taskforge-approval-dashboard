# 🚀 TaskForge Webhook App - Complete Documentation

## 📋 Table of Contents
- [Overview](#overview)
- [TaskForge Workflow Architecture](#taskforge-workflow-architecture)
- [n8n Integration Details](#n8n-integration-details)
- [Flask App Components](#flask-app-components)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## 🎯 Overview

**TaskForge** is a complete workflow automation system that processes Fireflies.ai meeting transcripts, extracts action items using AI, implements Human-in-the-Loop (HITL) approval via a Flask web app, and pushes approved tasks to Monday.com.

### Key Features
- ✅ **7-day session timeout** (bulletproof against expiry)
- ✅ **Auto-deploy from GitHub** (zero-downtime updates)
- ✅ **Meeting-grouped dashboard** (chronological organization)
- ✅ **Individual & bulk approvals** (flexible task management)
- ✅ **Comprehensive error handling** (production-ready)
- ✅ **Real-time progress tracking** (user-friendly interface)

---

## 🏗️ TaskForge Workflow Architecture

### Complete Data Flow
```
Daily Cron (7 AM EST)
    ↓
Fireflies.ai API (Header Request)
    ↓
Filter Today's Meetings
    ↓
Fireflies.ai API (Detailed Request)
    ↓
AI Agent (Extract Action Items)
    ↓
Transform → Monday.com Schema
    ↓
HITL Generate Approval Payload ← YOU ARE HERE
    ↓
Flask App (Approval Dashboard)
    ↓
Webhook1 (Approval Response) ← YOU ARE HERE
    ↓
Build Payload for GDrive + Monday.com ← YOU ARE HERE
    ↓
Google Drive (ACTION_ITEMS.json) + Monday.com (Individual Tasks)
```

### Critical n8n Nodes

#### 1. **HITL · Generate Approval Payload + Send Notifications**
- **Purpose**: Processes extracted tasks and sends to Flask app
- **Input**: Tasks from "Transform · Parse tasks → Monday schema"
- **Output**: Approval payload sent to Flask app
- **Notifications**: Telegram + Email with approval links

#### 2. **Webhook1**
- **URL**: `https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9`
- **Purpose**: Receives approval responses from Flask app
- **Trigger**: User submits approval decisions in Flask dashboard

#### 3. **Build Payload for GDrive and Monday.com**
- **Purpose**: Processes approved tasks for final destinations
- **Outputs**: 
  - 1 ACTION_ITEMS.json file for Google Drive
  - Individual Monday.com tasks for each approved item

---

## 🔗 n8n Integration Details

### Webhook Configuration
```javascript
// n8n Webhook Node Settings
URL: https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9
Method: POST
Authentication: None
Response: Immediately
```

### Data Flow Between Systems

#### Flask → n8n Webhook Payload
```json
{
  "execution_id": "exec_20250627_143022_abc123",
  "session_id": "session_20250627_143022_def456",
  "approval_status": "completed",
  "approved_tasks": [
    {
      "task_id": "task_1_abc123",
      "task_item": "Follow up with client about project timeline",
      "assignee_emails": ["john@company.com"],
      "assignee_full_names": ["John Smith"],
      "priority": "High",
      "brief_description": "Client expressed concerns about delivery date",
      "date_expected": "2025-06-30",
      "approved_at": "2025-06-27T14:32:15Z",
      "meeting_context": {
        "title": "Weekly Client Check-in",
        "organizer": "Project Manager"
      }
    }
  ],
  "rejected_tasks": [],
  "summary": {
    "total_tasks": 3,
    "approved_count": 2,
    "rejected_count": 1,
    "approval_rate": 66.67
  }
}
```

### Google Drive Integration
- **RAW_TRANSCRIPTS Folder**: `1WYaF58QGAnDIMIXLmhuRKqw0Qjof8iSe`
- **ACTION_ITEMS Folder**: `1PboVBKot2VbmK3z4D-wuT14b84zoEeXZ`
- **File Format**: `YYYY-MM-DD_ACTION_ITEMS_approved_N_sessionID.json`

---

## 🧩 Flask App Components

### Core Files Structure
```
APP/
├── app.py                 # Main Flask application
├── utils/
│   ├── session_manager.py # 7-day session management
│   └── webhook_client.py  # n8n webhook communication
├── templates/
│   ├── base.html         # Base template with modern UI
│   ├── dashboard.html    # Meeting-grouped approval interface
│   ├── success.html      # Confirmation page
│   └── error.html        # Error handling page
├── static/
│   ├── css/style.css     # Google/Apple-inspired design
│   └── js/script.js      # Interactive approval logic
├── requirements.txt      # Python dependencies
├── Procfile             # Railway deployment config
├── runtime.txt          # Python version
└── railway.json         # Auto-deploy configuration
```

### Key Features

#### Session Management (7-Day Timeout)
```python
# utils/session_manager.py
- Default timeout: 168 hours (7 days)
- Grace period: 24 hours
- Auto-extension capability
- Thread-safe operations
- Emergency recovery system
```

#### Webhook Client (Retry Logic)
```python
# utils/webhook_client.py
- 3 retry attempts with exponential backoff
- Comprehensive error logging
- Timeout handling (30 seconds)
- Status code validation
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Railway account
- GitHub repository
- n8n workflow (TaskForge_2_1)

### Local Development
```bash
# Clone repository
git clone https://github.com/a-longshadow/TaskForge_Webhook_App.git
cd TaskForge_Webhook_App

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY="your-secret-key"
export N8N_WEBHOOK_URL="https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9"
export FLASK_ENV="development"

# Run application
python app.py
```

### Testing the Integration
```bash
# Test approval request
curl -X POST http://localhost:5000/receive-approval-request \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "test_exec_123",
    "session_id": "test_session_456",
    "tasks": [...],
    "webhook_return_url": "https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9"
  }'
```

---

## 🌐 Deployment

### Railway Auto-Deploy Setup

#### 1. **GitHub Integration** (Already Configured)
- Repository: `https://github.com/a-longshadow/TaskForge_Webhook_App`
- Branch: `main`
- Auto-deploy: ✅ **ENABLED**

#### 2. **Environment Variables**
```bash
SECRET_KEY=your-production-secret-key
N8N_WEBHOOK_URL=https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9
FLASK_ENV=production
```

#### 3. **Production URL**
```
https://taskforgewebhookapp-production.up.railway.app
```

#### 4. **Health Check**
```
GET /health
Response: {"status": "healthy", "version": "1.0.0", "active_sessions": 0, "session_timeout_hours": 168}
```

### Deployment Commands
```bash
# Manual deploy (if needed)
railway up

# Check deployment status
railway status

# View logs
railway logs

# Set environment variable
railway variables set SECRET_KEY=your-key
```

---

## ⚙️ Configuration

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | - | Flask session encryption key |
| `N8N_WEBHOOK_URL` | ✅ | - | n8n webhook endpoint |
| `FLASK_ENV` | ✅ | development | Flask environment |
| `SESSION_TIMEOUT_HOURS` | ❌ | 168 | Session timeout in hours |
| `SESSION_BACKUP_DIR` | ❌ | /tmp/taskforge_sessions | Session backup directory |

### Flask App Settings
```python
# app.py configuration
SESSION_TIMEOUT = 168 hours (7 days)
GRACE_PERIOD = 24 hours
MAX_RETRIES = 3
WEBHOOK_TIMEOUT = 30 seconds
```

---

## 📡 API Documentation

### Endpoints

#### `POST /receive-approval-request`
**Purpose**: Receive approval requests from n8n HITL node

**Request Body**:
```json
{
  "execution_id": "exec_20250627_143022_abc123",
  "session_id": "session_20250627_143022_def456",
  "tasks": [
    {
      "task_id": "task_1_abc123",
      "task_item": "Follow up with client",
      "assignee_emails": ["john@company.com"],
      "assignee_full_names": ["John Smith"],
      "priority": "High",
      "brief_description": "Client follow-up required",
      "date_expected": "2025-06-30",
      "meeting_context": {
        "title": "Weekly Client Check-in",
        "date": "2025-06-27",
        "organizer": "Project Manager"
      }
    }
  ],
  "webhook_return_url": "https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9"
}
```

**Response**:
```json
{
  "status": "success",
  "session_id": "session_20250627_143022_def456",
  "approval_url": "https://taskforgewebhookapp-production.up.railway.app/approve/session_20250627_143022_def456",
  "tasks_count": 3,
  "expires_at": "2025-07-04T14:30:22Z"
}
```

#### `GET /approve/{session_id}`
**Purpose**: Display approval dashboard for session

**Response**: HTML approval interface with meeting-grouped tasks

#### `POST /approve/{session_id}`
**Purpose**: Process approval decisions and send to n8n

**Request Body**:
```json
{
  "decisions": {
    "task_1_abc123": "approved",
    "task_2_def456": "rejected",
    "task_3_ghi789": "approved"
  }
}
```

**Response**: Redirect to success page + webhook sent to n8n

#### `GET /health`
**Purpose**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "active_sessions": 2,
  "session_timeout_hours": 168
}
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Session Expired Error**
```
Error: "Session not found or expired"
Solution: Sessions now last 7 days with 24-hour grace period
Check: GET /health to verify session timeout settings
```

#### 2. **Webhook Delivery Failed**
```
Error: "Failed to send webhook to n8n"
Solution: Check N8N_WEBHOOK_URL environment variable
Debug: Check Railway logs for webhook retry attempts
```

#### 3. **n8n Node Errors**
```
Error: "Referenced node doesn't exist"
Solution: Verify node names in n8n workflow match exactly
Check: Use $('node_name').first().json syntax
```

#### 4. **Auto-Deploy Not Working**
```
Error: Changes not deploying automatically
Solution: Verify GitHub integration in Railway dashboard
Check: Push to main branch triggers deployment
```

### Debug Commands
```bash
# Check Railway logs
railway logs --tail

# Test webhook endpoint
curl -X POST https://taskforgewebhookapp-production.up.railway.app/health

# Verify environment variables
railway variables

# Check deployment status
railway status
```

### n8n Debugging
```javascript
// Add to any n8n Code node for debugging
console.log('Node input:', JSON.stringify($input.all(), null, 2));
console.log('Available nodes:', Object.keys($));
return $input.all();
```

---

## 🛠️ Development

### Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set development environment
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key
export N8N_WEBHOOK_URL=http://localhost:5678/webhook/test

# Run with hot reload
python app.py
```

### Testing
```bash
# Run tests (if implemented)
python -m pytest tests/

# Test webhook integration
python test_webhook.py

# Load test sessions
python test_sessions.py
```

### Code Structure
```python
# app.py - Main Flask application
# utils/session_manager.py - Session handling
# utils/webhook_client.py - n8n communication
# templates/ - Jinja2 templates
# static/ - CSS/JS assets
```

---

## 📞 Support

### Key Information for Support
- **n8n Workflow**: TaskForge_2_1 (version 2.1)
- **Webhook ID**: `3142af19-c362-47fc-b046-5e1d2b3882b9`
- **Production URL**: `https://taskforgewebhookapp-production.up.railway.app`
- **GitHub Repo**: `https://github.com/a-longshadow/TaskForge_Webhook_App`
- **Session Timeout**: 168 hours (7 days)

### Architecture Summary
1. **n8n processes** Fireflies.ai transcripts daily
2. **AI extracts** action items from meetings
3. **HITL node sends** tasks to Flask app
4. **User approves/rejects** via web dashboard
5. **Flask sends** decisions back to n8n webhook
6. **n8n creates** Google Drive files + Monday.com tasks

### Contact
- Repository: https://github.com/a-longshadow/TaskForge_Webhook_App
- Issues: Create GitHub issue with detailed description
- Documentation: This README.md (comprehensive)

---

**🎉 TaskForge is now fully documented and production-ready!**

*Any developer or LLM can pick up this documentation and continue development seamlessly.* 