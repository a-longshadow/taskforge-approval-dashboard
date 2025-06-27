# 🚀 TaskForge Deployment Guide

## 🎯 Complete n8n Node Implementation

### **CRITICAL FIX: Transform · Parse tasks → Monday schema**

```javascript
// Transform · Parse tasks → Monday schema
// CRITICAL FIX: Properly preserves meeting context and prevents duplicate meeting IDs

try {
  console.log('🔄 FIXED Transform: Processing AI Agent outputs with proper meeting grouping...');
  
  const allExtractedTasks = [];
  const meetingContextMap = new Map(); // Track unique meeting contexts
  
  for (const currentItem of items) {
    if (!currentItem.json || typeof currentItem.json.output !== 'string') {
      console.warn("⚠️ An input item is not in expected format. Skipping.", currentItem);
      continue;
    }

    // CRITICAL FIX: Extract meeting context from the ORIGINAL meeting data
    // We need to get the meeting ID from the original Parse & Generate Filenames output
    const originalMeetingId = currentItem.json.id || currentItem.json.original_fireflies_id;
    const meetingTitle = currentItem.json.title || 'Unknown Meeting';
    
    // Create consistent meeting ID that won't change between tasks
    const consistentMeetingId = originalMeetingId || `meeting_${meetingTitle.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase()}`;
    
    const meetingContext = {
      title: meetingTitle,
      date: currentItem.json.date || new Date().toISOString(),
      organizer: currentItem.json.organizer_email || currentItem.json.host_email || 'Unknown',
      id: consistentMeetingId,
      original_fireflies_id: originalMeetingId
    };

    console.log(`📋 Processing meeting: ${meetingContext.title} (ID: ${consistentMeetingId})`);

    // Clean the AI output
    const fencedOutput = currentItem.json.output;
    let cleanedJsonText = fencedOutput;

    if (cleanedJsonText.startsWith("```json")) {
      cleanedJsonText = cleanedJsonText.substring(7);
    } else if (cleanedJsonText.startsWith("```")) {
      cleanedJsonText = cleanedJsonText.substring(3);
    }
    if (cleanedJsonText.endsWith("```")) {
      cleanedJsonText = cleanedJsonText.substring(0, cleanedJsonText.length - 3);
    }
    cleanedJsonText = cleanedJsonText.trim();

    let tasksInThisMeeting;
    try {
      tasksInThisMeeting = JSON.parse(cleanedJsonText);
      if (!Array.isArray(tasksInThisMeeting)) {
        if (tasksInThisMeeting && typeof tasksInThisMeeting === 'object') {
          console.warn("⚠️ Parsed AI output was a single object, wrapping in array");
          tasksInThisMeeting = [tasksInThisMeeting];
        } else {
          console.error("❌ Invalid AI output format:", cleanedJsonText);
          continue;
        }
      }
    } catch (error) {
      console.error(`❌ Failed to parse AI output: ${error.message}`);
      continue;
    }

    // Store meeting context ONCE per meeting (not per task)
    if (!meetingContextMap.has(consistentMeetingId)) {
      meetingContextMap.set(consistentMeetingId, meetingContext);
      console.log(`✅ Stored meeting context for: ${meetingContext.title}`);
    }

    // Add meeting context to each task - ALL TASKS FROM SAME MEETING GET SAME ID
    tasksInThisMeeting.forEach((task, taskIndex) => {
      const enrichedTask = {
        ...task,
        // CRITICAL: All tasks from same meeting get the SAME meeting_id
        meeting_id: consistentMeetingId,
        meeting_title: meetingContext.title,
        meeting_date: meetingContext.date,
        meeting_organizer: meetingContext.organizer,
        
        // Task metadata
        task_index: taskIndex,
        total_tasks_in_meeting: tasksInThisMeeting.length,
        
        // Ensure all required fields exist
        task_item: task.task_item || 'Untitled Task',
        'assignee(s)_full_names': task['assignee(s)_full_names'] || task.assignee_full_names || 'Unknown',
        assignee_emails: task.assignee_emails || 'unknown@example.com',
        priority: task.priority || 'Medium',
        brief_description: task.brief_description || task.task_item || 'No description provided',
        date_expected: task.date_expected || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      };
      
      console.log(`   📝 Task ${taskIndex + 1}: ${enrichedTask.task_item} (Meeting ID: ${consistentMeetingId})`);
      allExtractedTasks.push({ json: enrichedTask });
    });
  }

  console.log(`✅ TRANSFORM COMPLETE:`);
  console.log(`   - Total tasks: ${allExtractedTasks.length}`);
  console.log(`   - Unique meetings: ${meetingContextMap.size}`);
  
  // Debug: Show meeting grouping
  const tasksByMeeting = {};
  allExtractedTasks.forEach(task => {
    const meetingId = task.json.meeting_id;
    if (!tasksByMeeting[meetingId]) {
      tasksByMeeting[meetingId] = [];
    }
    tasksByMeeting[meetingId].push(task.json.task_item);
  });
  
  Object.entries(tasksByMeeting).forEach(([meetingId, tasks]) => {
    console.log(`   📋 ${meetingId}: ${tasks.length} tasks`);
  });
  
  return allExtractedTasks;
  
} catch (error) {
  console.error('❌ Error in Transform node:', error.message);
  return [{
    json: {
      error: error.message,
      status: 'error',
      timestamp: new Date().toISOString()
    }
  }];
}
```

### 1. **HITL · Generate Approval Payload + Send Notifications**

```javascript
// HITL · Generate Approval Payload + Send Notifications
// CRITICAL FIX: Enhanced error handling and session creation debugging

try {
  console.log('🚀 HITL NODE STARTED - Enhanced debugging enabled');
  
  // Get tasks from Transform node
  const tasksData = $('Transform · Parse tasks → Monday schema').all();
  console.log(`📊 Received ${tasksData?.length || 0} items from Transform node`);
  
  if (!tasksData || tasksData.length === 0) {
    console.log('⚠️ No tasks received from Transform node');
    return [{
      json: {
        status: 'no_tasks',
        message: 'No tasks to process for approval',
        timestamp: new Date().toISOString(),
        debug: 'Transform node returned empty or null'
      }
    }];
  }
  
  // Generate unique identifiers with extra entropy
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substr(2, 9);
  const executionId = `exec_${timestamp}_${randomSuffix}`;
  const sessionId = `session_${timestamp}_${randomSuffix}`;
  
  console.log(`🆔 Generated IDs: execution=${executionId}, session=${sessionId}`);
  
  // Group tasks by meeting and enrich with full context
  const tasksByMeeting = new Map();
  const enrichedTasks = tasksData.map((taskData, index) => {
    const task = taskData.json;
    console.log(`📋 Processing task ${index + 1}:`, {
      task_item: task.task_item?.substring(0, 50) + '...',
      meeting_id: task.meeting_id,
      meeting_title: task.meeting_title
    });
    
    // Extract meeting context (now preserved from Transform node)
    const meetingId = task.meeting_id || `meeting_${index}`;
    const meetingContext = {
      id: meetingId,
      title: task.meeting_title || 'Unknown Meeting',
      date: task.meeting_date || new Date().toISOString(),
      organizer: task.meeting_organizer || 'Unknown'
    };
    
    // Group tasks by meeting
    if (!tasksByMeeting.has(meetingId)) {
      tasksByMeeting.set(meetingId, {
        context: meetingContext,
        tasks: []
      });
    }
    
    const enrichedTask = {
      task_id: `task_${timestamp}_${index}_${Math.random().toString(36).substr(2, 6)}`,
      task_item: task.task_item || 'Untitled Task',
      assignee_emails: Array.isArray(task.assignee_emails) ? task.assignee_emails : 
                      typeof task.assignee_emails === 'string' ? [task.assignee_emails] : ['unknown@example.com'],
      assignee_full_names: Array.isArray(task['assignee(s)_full_names']) ? task['assignee(s)_full_names'] : 
                          typeof task['assignee(s)_full_names'] === 'string' ? [task['assignee(s)_full_names']] : ['Unknown'],
      priority: task.priority || 'Medium',
      brief_description: task.brief_description || task.task_item || 'No description provided',
      date_expected: task.date_expected || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      meeting_context: meetingContext
    };
    
    tasksByMeeting.get(meetingId).tasks.push(enrichedTask);
    return enrichedTask;
  });
  
  console.log(`✅ Processed ${enrichedTasks.length} tasks from ${tasksByMeeting.size} meetings`);
  
  // Prepare Flask app payload with comprehensive data
  const flaskPayload = {
    execution_id: executionId,
    session_id: sessionId,
    tasks: enrichedTasks,
    meetings: Array.from(tasksByMeeting.entries()).map(([id, data]) => ({
      meeting_id: id,
      meeting_context: data.context,
      task_count: data.tasks.length,
      tasks: data.tasks.map(t => t.task_id)
    })),
    webhook_return_url: 'https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9',
    metadata: {
      created_at: new Date().toISOString(),
      total_tasks: enrichedTasks.length,
      total_meetings: tasksByMeeting.size,
      workflow_version: '2.1',
      source: 'TaskForge_n8n_HITL',
      n8n_execution_id: $execution.id
    }
  };
  
  console.log(`📤 SENDING TO FLASK - Payload summary:`, {
    execution_id: executionId,
    session_id: sessionId,
    tasks_count: enrichedTasks.length,
    meetings_count: tasksByMeeting.size,
    payload_size: JSON.stringify(flaskPayload).length
  });
  
  // Send to Flask app with enhanced error handling
  let response;
  try {
    response = await this.helpers.httpRequest({
      method: 'POST',
      url: 'https://taskforgewebhookapp-production.up.railway.app/receive-approval-request',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'n8n-TaskForge/2.1',
        'X-Execution-ID': executionId,
        'X-Session-ID': sessionId
      },
      body: flaskPayload,
      timeout: 60000, // Increased timeout
      returnFullResponse: true
    });
    
    console.log(`✅ FLASK RESPONSE - Status: ${response.statusCode}`);
    console.log(`📝 FLASK RESPONSE - Headers:`, response.headers);
    console.log(`📄 FLASK RESPONSE - Body:`, response.body);
    
  } catch (httpError) {
    console.error(`❌ HTTP REQUEST FAILED:`, {
      error: httpError.message,
      code: httpError.code,
      response: httpError.response?.body,
      status: httpError.response?.statusCode
    });
    
    // Return detailed error for debugging
    return [{
      json: {
        status: 'http_error',
        error: httpError.message,
        execution_id: executionId,
        session_id: sessionId,
        debug: {
          error_code: httpError.code,
          response_status: httpError.response?.statusCode,
          response_body: httpError.response?.body,
          url: 'https://taskforgewebhookapp-production.up.railway.app/receive-approval-request',
          payload_summary: {
            tasks_count: enrichedTasks.length,
            meetings_count: tasksByMeeting.size
          }
        },
        timestamp: new Date().toISOString()
      }
    }];
  }
  
  if (response.statusCode !== 200) {
    console.error(`❌ FLASK ERROR - Non-200 status: ${response.statusCode}`);
    console.error(`📄 Error body:`, response.body);
    
    return [{
      json: {
        status: 'flask_error',
        error: `Flask app returned status ${response.statusCode}`,
        execution_id: executionId,
        session_id: sessionId,
        flask_response: response.body,
        timestamp: new Date().toISOString()
      }
    }];
  }
  
  const flaskResponse = typeof response.body === 'string' ? JSON.parse(response.body) : response.body;
  console.log('✅ FLASK SUCCESS:', flaskResponse);
  
  // Generate approval URL
  const approvalUrl = flaskResponse.approval_url || 
    `https://taskforgewebhookapp-production.up.railway.app/approve/${sessionId}`;
  
  console.log(`🔗 APPROVAL URL: ${approvalUrl}`);
  
  // Prepare notification messages
  const telegramMessage = `🔔 *TaskForge Approval Required*
  
📊 *${enrichedTasks.length} tasks* from *${tasksByMeeting.size} meetings* need approval
🆔 Session: \`${sessionId}\`
⏰ Expires: ${new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toLocaleString()}

👆 *[APPROVE TASKS](${approvalUrl})*

Meetings summary:
${Array.from(tasksByMeeting.values()).slice(0, 3).map((meeting, i) => 
  `${i + 1}. ${meeting.context.title} (${meeting.tasks.length} tasks)`).join('\n')}
${tasksByMeeting.size > 3 ? `\n... and ${tasksByMeeting.size - 3} more meetings` : ''}`;

  const emailSubject = `TaskForge: ${enrichedTasks.length} tasks from ${tasksByMeeting.size} meetings need approval`;
  const emailBody = `
<h2>🔔 TaskForge Approval Required</h2>
<p><strong>${enrichedTasks.length} tasks</strong> from <strong>${tasksByMeeting.size} meetings</strong> need approval.</p>
<p><strong>Session ID:</strong> ${sessionId}</p>
<p><strong>Expires:</strong> ${new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toLocaleString()}</p>

<div style="margin: 20px 0;">
  <a href="${approvalUrl}" style="background: #4285f4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
    👆 APPROVE TASKS
  </a>
</div>

<h3>Meetings Overview:</h3>
<ul>
${Array.from(tasksByMeeting.values()).slice(0, 5).map(meeting => 
  `<li><strong>${meeting.context.title}</strong> - ${meeting.tasks.length} tasks</li>`).join('')}
${tasksByMeeting.size > 5 ? `<li><em>... and ${tasksByMeeting.size - 5} more meetings</em></li>` : ''}
</ul>

<p><small>This approval link will expire in 7 days.</small></p>
`;

  console.log('🎯 HITL SUCCESS - Returning notification data');

  // Return outputs for Telegram and Email nodes
  return [
    {
      json: {
        // Main execution data
        execution_id: executionId,
        session_id: sessionId,
        tasks_count: enrichedTasks.length,
        meetings_count: tasksByMeeting.size,
        approval_url: approvalUrl,
        flask_response: flaskResponse,
        
        // Telegram notification
        telegram_message: telegramMessage,
        
        // Email notification
        email_subject: emailSubject,
        email_body: emailBody,
        
        // Status
        status: 'approval_request_sent',
        timestamp: new Date().toISOString(),
        
        // Enhanced debug info
        debug: {
          original_tasks_count: tasksData.length,
          processed_tasks_count: enrichedTasks.length,
          meetings_processed: Array.from(tasksByMeeting.keys()),
          flask_status: response.statusCode,
          session_created: true,
          approval_url_generated: true,
          payload_sent_successfully: true
        }
      }
    }
  ];
  
} catch (error) {
  console.error('❌ CRITICAL ERROR in HITL node:', error.message);
  console.error('📚 Stack trace:', error.stack);
  
  return [{
    json: {
      status: 'critical_error',
      error: error.message,
      timestamp: new Date().toISOString(),
      debug_info: {
        error_stack: error.stack,
        error_name: error.name,
        input_data_available: !!$('Transform · Parse tasks → Monday schema').all(),
        execution_id: $execution.id
      }
    }
  }];
}
```

### 2. **Build Payload for GDrive and Monday.com**

```javascript
// Build Payload for GDrive and Monday.com
// Processes Flask webhook response and prepares data for both Google Drive and Monday.com

try {
  console.log('🔄 Processing Flask webhook response...');
  
  // Get the webhook response from Flask
  const webhookData = $input.first().json;
  
  if (!webhookData) {
    throw new Error('No webhook data received from Flask app');
  }
  
  console.log(`📊 Webhook data received:`, {
    execution_id: webhookData.execution_id,
    session_id: webhookData.session_id,
    approval_status: webhookData.approval_status,
    approved_count: webhookData.summary?.approved_count || 0,
    rejected_count: webhookData.summary?.rejected_count || 0
  });
  
  // Extract approved tasks
  const approvedTasks = webhookData.approved_tasks || [];
  const rejectedTasks = webhookData.rejected_tasks || [];
  
  if (approvedTasks.length === 0) {
    console.log('⚠️ No approved tasks to process');
    return [{
      json: {
        status: 'no_approved_tasks',
        message: 'No tasks were approved for processing',
        summary: webhookData.summary,
        timestamp: new Date().toISOString()
      }
    }];
  }
  
  console.log(`✅ Processing ${approvedTasks.length} approved tasks`);
  
  // ============================================
  // 1. PREPARE GOOGLE DRIVE ACTION_ITEMS.json
  // ============================================
  
  const actionItemsPayload = {
    metadata: {
      created_at: new Date().toISOString(),
      execution_id: webhookData.execution_id,
      session_id: webhookData.session_id,
      total_tasks: approvedTasks.length,
      approval_summary: webhookData.summary,
      workflow_version: '2.1',
      source: 'TaskForge_HITL_Approval'
    },
    approved_tasks: approvedTasks.map(task => ({
      task_id: task.task_id,
      task_item: task.task_item,
      assignee_emails: task.assignee_emails,
      assignee_full_names: task.assignee_full_names,
      priority: task.priority,
      brief_description: task.brief_description,
      date_expected: task.date_expected,
      approved_at: task.approved_at,
      meeting_context: task.meeting_context || {}
    })),
    rejected_tasks: rejectedTasks.map(task => ({
      task_id: task.task_id,
      task_item: task.task_item,
      reason: task.reason,
      rejected_at: task.rejected_at
    })),
    processing_notes: {
      original_task_count: webhookData.summary?.total_tasks || 0,
      approval_rate: webhookData.summary?.approval_rate || 0,
      processed_by: 'TaskForge_HITL_System',
      next_steps: 'Tasks will be created in Monday.com board'
    }
  };
  
  // Generate filename for ACTION_ITEMS.json
  const timestamp = new Date().toISOString().split('T')[0];
  const sessionShort = webhookData.session_id.split('_').pop().substring(0, 8);
  const actionItemsFilename = `${timestamp}_ACTION_ITEMS_approved_${approvedTasks.length}_${sessionShort}.json`;
  
  // ============================================
  // 2. PREPARE OUTPUT FOR BOTH SYSTEMS
  // ============================================
  
  const outputs = [];
  
  // First output: Google Drive ACTION_ITEMS.json
  outputs.push({
    json: {
      filename: actionItemsFilename,
      meeting_id: webhookData.session_id,
      total_tasks: approvedTasks.length,
      created_at: new Date().toISOString(),
      ...actionItemsPayload
    }
  });
  
  // Subsequent outputs: Individual Monday.com tasks
  approvedTasks.forEach((task, index) => {
    outputs.push({
      json: {
        // Monday.com task format
        task_item: task.task_item,
        'assignee(s)_full_names': task.assignee_full_names,
        assignee_emails: task.assignee_emails,
        priority: task.priority,
        brief_description: task.brief_description,
        date_expected: task.date_expected,
        
        // Additional metadata
        task_id: task.task_id,
        approved_at: task.approved_at,
        session_id: webhookData.session_id,
        execution_id: webhookData.execution_id,
        task_index: index + 1,
        total_tasks: approvedTasks.length,
        
        // Meeting context if available
        meeting_title: task.meeting_context?.title || 'TaskForge Meeting',
        meeting_organizer: task.meeting_context?.organizer || 'Unknown',
        
        // Processing metadata
        source: 'TaskForge_HITL_Approved',
        workflow_version: '2.1',
        processed_at: new Date().toISOString()
      }
    });
  });
  
  console.log(`📤 Generated outputs:`);
  console.log(`   - 1 ACTION_ITEMS.json file (${actionItemsFilename})`);
  console.log(`   - ${approvedTasks.length} Monday.com tasks`);
  console.log(`   - Total outputs: ${outputs.length}`);
  
  return outputs;
  
} catch (error) {
  console.error('❌ Error in Build Payload node:', error.message);
  
  return [{
    json: {
      error: error.message,
      status: 'error',
      timestamp: new Date().toISOString(),
      debug_info: {
        input_data: $input.first()?.json || 'No input data',
        error_stack: error.stack
      }
    }
  }];
}
```

## 🔧 Railway Auto-Deploy Configuration

### 1. **Environment Variables**
Set these in Railway dashboard:
```bash
SECRET_KEY=your-production-secret-key-here
N8N_WEBHOOK_URL=https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9
FLASK_ENV=production
```

### 2. **GitHub Integration**
- Repository: `https://github.com/a-longshadow/TaskForge_Webhook_App`
- Branch: `main`
- Auto-deploy: **ENABLED** ✅

### 3. **Health Check**
Test deployment:
```bash
curl https://taskforgewebhookapp-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "active_sessions": 0,
  "session_timeout_hours": 168
}
```

## 🚨 Troubleshooting Guide

### Common n8n Errors

#### 1. **"Referenced node doesn't exist"**
```javascript
// ❌ Wrong
const data = $('Non-existent Node').first().json;

// ✅ Correct - Check available nodes
console.log('Available nodes:', Object.keys($));
const data = $('Transform · Parse tasks → Monday schema').first().json;
```

#### 2. **"$http is not defined"**
```javascript
// ❌ Wrong
const response = await $http.post(url, data);

// ✅ Correct
const response = await this.helpers.httpRequest({
  method: 'POST',
  url: url,
  body: data
});
```

#### 3. **"Task data format mismatch"**
```javascript
// ✅ Handle different data formats
const taskItem = task.task_item || task['task item'] || 'Untitled Task';
const assignees = Array.isArray(task.assignee_emails) ? task.assignee_emails : 
                 typeof task.assignee_emails === 'string' ? [task.assignee_emails] : [];
```

### Flask App Debugging

#### 1. **Check Railway Logs**
```bash
railway logs --tail
```

#### 2. **Test Webhook Endpoint**
```bash
curl -X POST https://taskforgewebhookapp-production.up.railway.app/receive-approval-request \
  -H "Content-Type: application/json" \
  -d '{"execution_id": "test", "session_id": "test", "tasks": [], "webhook_return_url": "test"}'
```

#### 3. **Verify Environment Variables**
```bash
railway variables
```

### Session Management

#### 1. **Session Timeout Extended**
- **Default**: 168 hours (7 days)
- **Grace Period**: 24 hours
- **Auto-Extension**: Available

#### 2. **Session Recovery**
```python
# Automatic session recovery in session_manager.py
def _emergency_session_recovery(self, session_id: str) -> Dict[str, Any]:
    # Attempts to recover session from backup
```

## 📋 Pre-Deployment Checklist

### n8n Workflow
- [ ] **HITL node** has correct Flask app URL
- [ ] **Webhook1** path matches Flask webhook URL
- [ ] **Transform node** outputs correct task format
- [ ] **Build Payload node** handles approved/rejected tasks

### Flask App
- [ ] **Environment variables** set in Railway
- [ ] **GitHub integration** enabled for auto-deploy
- [ ] **Health endpoint** responding correctly
- [ ] **Session timeout** set to 7 days

### Integration
- [ ] **Webhook URL** matches in both systems
- [ ] **Data format** consistent between n8n and Flask
- [ ] **Error handling** implemented in all nodes
- [ ] **Logging** enabled for debugging

## 🚀 Deployment Steps

### 1. **Deploy Flask App**
```bash
# Ensure railway.json exists
git add railway.json
git commit -m "Add Railway auto-deploy configuration"
git push origin main
```

### 2. **Update n8n Nodes**
1. Copy **HITL node code** to "HITL · Generate Approval Payload + Send Notifications"
2. Copy **Build Payload code** to "Build Payload for GDrive and Monday.com"
3. Verify **Webhook1** configuration
4. Test workflow with sample data

### 3. **Verify Integration**
1. Check Flask app health: `/health`
2. Test approval flow end-to-end
3. Monitor Railway logs during test
4. Verify Google Drive and Monday.com outputs

## 📞 Support Information

### Key URLs
- **Production App**: `https://taskforgewebhookapp-production.up.railway.app`
- **GitHub Repo**: `https://github.com/a-longshadow/TaskForge_Webhook_App`
- **n8n Webhook**: `https://levirybalov.app.n8n.cloud/webhook/3142af19-c362-47fc-b046-5e1d2b3882b9`

### Critical IDs
- **Webhook ID**: `3142af19-c362-47fc-b046-5e1d2b3882b9`
- **Session Timeout**: 168 hours (7 days)
- **Workflow Version**: 2.1

---

**✅ TaskForge is now fully deployed and documented!** 