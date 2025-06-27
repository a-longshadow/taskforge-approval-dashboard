# TaskForge 2.1 - HITL Approval System

HTTP request-based Human-in-the-Loop task approval system for n8n workflows.

## 📁 Project Structure

```
TaskForge_2_1/
├── app/                    # 🚀 Railway deployment files
│   ├── server.py          # Flask server with HTTP endpoints
│   ├── index.html         # Task approval UI
│   ├── requirements.txt   # Python dependencies
│   ├── Procfile          # Railway process config
│   ├── railway.toml      # Railway deployment settings
│   └── README.md         # Railway app documentation
│
├── _temp/                 # 📋 Development & documentation files
│   ├── CHANGELOG.md      # Version history
│   ├── HITL_Node_Code.js # n8n node JavaScript code
│   ├── HITL_HTTP_REQUEST_PLAN.md # Implementation guide
│   ├── TaskForge_2_1 (59).json  # n8n workflow export
│   └── README.md         # Development files documentation
│
└── README.md             # This file
```

## 🚀 Quick Start

### Railway App (Live)
- **URL**: https://web-production-c8f1d.up.railway.app
- **Purpose**: Task approval UI for human review
- **Files**: See `app/` directory

### n8n Workflow
- **Code**: Use `_temp/HITL_Node_Code.js` in your n8n node
- **Workflow**: Import `_temp/TaskForge_2_1 (59).json`
- **Guide**: Follow `_temp/HITL_HTTP_REQUEST_PLAN.md`

## 🔄 Architecture

```
n8n Workflow → HTTP POST (store tasks) → Railway UI → User Approval → HTTP GET (retrieve approved) → Continue Workflow
```

### Key Benefits
- ✅ **No webhooks**: n8n controls the flow with HTTP requests
- ✅ **Self-destructing links**: One-time use for security
- ✅ **Short URLs**: Fixes Telegram message length limits
- ✅ **Automatic cleanup**: No persistent data storage

## 🛠️ Development

### Railway App
```bash
cd app/
pip install -r requirements.txt
python server.py
```

### n8n Integration
1. Copy code from `_temp/HITL_Node_Code.js`
2. Configure HTTP Request nodes per the plan
3. Test the complete flow

## 📚 Documentation

- **App Documentation**: `app/README.md`
- **Development Files**: `_temp/README.md`
- **Implementation Plan**: `_temp/HITL_HTTP_REQUEST_PLAN.md`
- **Change History**: `_temp/CHANGELOG.md`

## 🔗 Links

- **Railway Project**: [TaskForge Dashboard](https://railway.com/project/b7380a3c-c370-4006-9ea2-f206ea4b525f)
- **GitHub Repo**: [taskforge-approval-dashboard](https://github.com/a-longshadow/taskforge-approval-dashboard)
- **Live App**: https://web-production-c8f1d.up.railway.app 