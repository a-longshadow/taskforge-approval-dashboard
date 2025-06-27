// SIMPLE HITL NODE - NO BULLSHIT VERSION
// Sends COMPLETE Monday.com payload to Railway
// Railway adds TRUE/FALSE to each item
// HTTP Request1 gets only approved items

try {
  // Get all tasks from input (already in Monday.com format)
  const mondayTasks = items.map((item, index) => ({
    // ALL Monday.com columns
    task_item: item.json.task_item || 'Untitled Task',
    'assignee(s)_full_names': item.json['assignee(s)_full_names'] || 'Unassigned',
    assignee_emails: item.json.assignee_emails || '',
    priority: item.json.priority || 'Medium',
    brief_description: item.json.brief_description || 'No description',
    date_expected: item.json.date_expected || new Date().toISOString().split('T')[0],
    
    // Meeting data
    meeting_title: item.json.meeting_title || 'TaskForge Meeting',
    meeting_organizer: item.json.meeting_organizer || 'TaskForge System',
    
    // Internal tracking
    task_id: `task_${Date.now()}_${index}`,
    
    // Will be set by Railway app
    approved: null  // Railway will set to true/false
  }));

  if (mondayTasks.length === 0) {
    return [{ json: { error: 'No tasks found', status: 'no_tasks' } }];
  }

  // Simple execution ID
  const executionId = `exec_${Date.now()}`;
  const meetingTitle = mondayTasks[0].meeting_title;
  
  // Simple approval URL
  const approvalUrl = `https://web-production-c8f1d.up.railway.app?exec_id=${executionId}`;

  console.log(`📋 Sending ${mondayTasks.length} tasks to Railway for approval`);
  console.log(`🆔 Execution ID: ${executionId}`);

  // Simple Telegram message
  const telegramMessage = [
    '🔥 *TaskForge Approval Required*',
    '',
    `📋 *Meeting:* ${meetingTitle}`,
    `📊 *Tasks:* ${mondayTasks.length}`,
    '',
    `👆 [*APPROVE TASKS*](${approvalUrl})`
  ].join('\n');

  // Simple email
  const emailHtml = `
<h1>🔥 TaskForge Approval Required</h1>
<p><strong>Meeting:</strong> ${meetingTitle}</p>
<p><strong>Tasks:</strong> ${mondayTasks.length} action items</p>
<p><a href="${approvalUrl}" style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px;">✅ APPROVE TASKS</a></p>
`;

  // Return data for all 3 nodes
  return [{
    json: {
      // For Telegram
      telegram_message: telegramMessage,
      
      // For Gmail  
      email_subject: `🔥 TaskForge: ${mondayTasks.length} Action Items Need Approval`,
      email_html: emailHtml,
      
      // For HTTP Request - SIMPLE PAYLOAD
      execution_id: executionId,
      monday_tasks: mondayTasks,  // Complete Monday.com data
      meeting_title: meetingTitle,
      total_tasks: mondayTasks.length,
      approval_url: approvalUrl
    }
  }];

} catch (error) {
  console.error('❌ HITL Error:', error.message);
  return [{ json: { error: error.message, status: 'error' } }];
} 