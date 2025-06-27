# TaskForge Development Files

This directory contains development files, documentation, and n8n workflow configurations that are not part of the Railway deployment.

## 📁 Files

### 📋 Documentation
- **`CHANGELOG.md`** - Version history and changes log
- **`HITL_HTTP_REQUEST_PLAN.md`** - Detailed implementation plan for HTTP request approach

### 🔧 n8n Workflow
- **`HITL_Node_Code.js`** - JavaScript code for the "HITL · Generate Approval Payload + Send Notifications" node
- **`TaskForge_2_1 (59).json`** - Complete n8n workflow export (latest version)

## 🔄 Usage

### For n8n Implementation
1. Use `HITL_Node_Code.js` in your n8n workflow node
2. Import `TaskForge_2_1 (59).json` to get the complete workflow
3. Follow `HITL_HTTP_REQUEST_PLAN.md` for step-by-step implementation

### For Development
- `CHANGELOG.md` tracks all changes and versions
- Reference documentation for understanding the architecture

## 🚫 Not for Deployment

These files are **not deployed** to Railway. They are:
- Development documentation
- n8n workflow configurations  
- Implementation guides
- Version tracking

## 📝 Notes

- Keep workflow exports updated in this directory
- Update CHANGELOG.md for any significant changes
- Use HITL_Node_Code.js as the canonical source for n8n node code 