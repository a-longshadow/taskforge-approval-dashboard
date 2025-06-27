// HITL APPROVAL - HTTP REQUEST APPROACH (No Sessions)
// This node serves 3 outputs: Telegram, Gmail, and HTTP POST to Railway
try {
  const tasks = [];
  
  // Process input tasks from Transform · Parse tasks → Monday schema
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
  
  // Prepare data for Railway app UI (shortened URL for Telegram)
  const approvalUrl = `https://web-production-c8f1d.up.railway.app?exec_id=${executionId}`;
  
  // Full URL with tasks data for email (can be longer)
  const tasksData = encodeURIComponent(JSON.stringify(tasks));
  const fullApprovalUrl = `https://web-production-c8f1d.up.railway.app?tasks=${tasksData}&title=${encodeURIComponent(meetingTitle)}&exec_id=${executionId}`;

  // Prepare payload for HTTP POST to Railway /store-tasks endpoint
  const storePayload = {
    execution_id: executionId,
    tasks: tasks,
    meeting_title: meetingTitle,
    created_at: new Date().toISOString(),
    total_tasks: tasks.length,
    source: 'TaskForge_HITL_HTTP'
  };

  console.log(`📋 Generated ${tasks.length} tasks for approval`);
  console.log(`🆔 Execution ID: ${executionId}`);
  console.log(`🔗 Approval URL: ${approvalUrl}`);

  // Return single object with all data for all 3 nodes to access
  return [{
    json: {
      // For Telegram1 node
      telegram_message: `🔥 *TaskForge Approval Required*\\n\\n📋 *Meeting:* ${meetingTitle}\\n📊 *Tasks:* ${tasks.length}\\n\\n👆 [*APPROVE TASKS*](${approvalUrl})`,
      
      // For Gmail node  
      email_subject: `TaskForge: ${tasks.length} Action Items Need Approval`,
      email_html: `<h2>TaskForge Approval</h2><p><strong>Meeting:</strong> ${meetingTitle}</p><p>${tasks.length} tasks need approval.</p><p><a href="${fullApprovalUrl}" style="background:#4CAF50;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;">Click to Approve Tasks</a></p><p><small>Execution ID: ${executionId}</small></p>`,
      
      // For HTTP Request node (Railway POST payload)
      execution_id: executionId,
      tasks: tasks,
      meeting_title: meetingTitle,
      created_at: new Date().toISOString(),
      total_tasks: tasks.length,
      source: 'TaskForge_HITL_HTTP',
      
      // Common fields for all nodes
      approval_url: approvalUrl,
      tasks_count: tasks.length
    }
  }];

} catch (error) {
  console.error('❌ Error in HITL node:', error.message);
  
  // Return single error output
  return [{ json: { error: error.message, status: 'error' } }];
} 