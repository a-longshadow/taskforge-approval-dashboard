# TaskForge Railway App Changelog

## [2.0.0] - 2025-01-28

### 🚀 Major Changes - HTTP Request Approach
- **BREAKING**: Converted from webhook-based to HTTP request-based HITL workflow
- **NEW**: Added `/store-tasks` endpoint for n8n to store tasks
- **NEW**: Added `/get-tasks/<exec_id>` endpoint for UI to load tasks by execution ID
- **NEW**: Added `/get-approved/<exec_id>` endpoint for n8n to retrieve approved tasks (self-destructs)
- **NEW**: Added `/submit-approval` endpoint for UI to store approved tasks

### 🔧 Technical Improvements
- **FIXED**: Telegram message length issue by using short URLs with execution IDs
- **NEW**: In-memory storage system (`stored_tasks` and `approved_results` dicts)
- **NEW**: Self-destructing links - UI becomes unusable after submission
- **NEW**: Automatic cleanup of stored data after retrieval
- **ENHANCED**: Better error handling and logging throughout

### 🎨 UI Enhancements
- **NEW**: Support for loading tasks via execution ID (short URLs)
- **NEW**: Self-destruct UI after task submission
- **IMPROVED**: Better error messages and loading states
- **MAINTAINED**: Backward compatibility with original URL-based task loading

### 📡 API Changes
- **NEW**: `POST /store-tasks` - Store tasks from n8n
- **NEW**: `GET /get-tasks/<exec_id>` - Retrieve tasks for UI
- **NEW**: `GET /get-approved/<exec_id>` - Retrieve approved tasks (one-time use)
- **NEW**: `POST /submit-approval` - Store approved tasks from UI
- **MAINTAINED**: Legacy `/submit` endpoint for backward compatibility

### 🔄 Workflow Integration
- **SIMPLIFIED**: n8n workflow now uses 2 HTTP requests instead of webhook waiting
- **CONTROLLED**: n8n drives the entire flow instead of passive webhook listening
- **RELIABLE**: Eliminates webhook timeout and reliability issues
- **DEBUGGABLE**: Clear request/response cycle for easier troubleshooting

### 🛡️ Security & Reliability
- **SECURE**: One-time use links prevent replay attacks
- **CLEAN**: Automatic memory cleanup prevents data leaks
- **ROBUST**: Better error handling for edge cases
- **SIMPLE**: Minimal dependencies, pure Flask implementation

---

## Previous Versions

### [1.0.0] - Previous
- Initial webhook-based implementation
- Basic task approval UI
- Direct n8n webhook integration 