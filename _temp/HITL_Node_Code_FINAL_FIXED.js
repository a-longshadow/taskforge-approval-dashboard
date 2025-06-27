// HITL APPROVAL - FINAL FIXED VERSION (NO MORE BUGS!)
// This node serves 3 outputs: Telegram, Gmail, and HTTP POST to Railway
// FIXES: 
// 1. Proper Telegram formatting (no double escaping)
// 2. Professional email HTML formatting  
// 3. Consistent URL usage across all nodes
// 4. Fixed HTTP Request JSON payload structure
// 5. REAL meeting data extraction (no more "Unknown Meeting")

try {
  const tasks = [];
  
  // FIXED: Extract real meeting data from input
  const firstTask = items[0]?.json || {};
  const realMeetingTitle = firstTask.meeting_title || 
                          firstTask.title || 
                          firstTask.meeting_name ||
                          firstTask.name || 
                          'TaskForge Meeting';
  const realMeetingOrganizer = firstTask.meeting_organizer || 
                              firstTask.organizer || 
                              firstTask.organizer_email ||
                              firstTask.creator ||
                              'TaskForge System';
  const realMeetingDate = firstTask.meeting_date || 
                         firstTask.date || 
                         firstTask.created_at ||
                         new Date().toISOString();
  
  console.log(`📋 Processing meeting: "${realMeetingTitle}" by ${realMeetingOrganizer}`);
  
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
        meeting_title: realMeetingTitle,
        meeting_organizer: realMeetingOrganizer,
        meeting_date: realMeetingDate,
        meeting_id: `meeting_${Date.now()}`
      });
    }
  });

  if (tasks.length === 0) {
    return [{ json: { error: 'No tasks found', status: 'no_tasks' } }];
  }

  // Generate unique execution ID for this approval session
  const executionId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  const meetingTitle = realMeetingTitle; // Use real meeting title
  
  // CONSISTENT URL - Use same short URL for ALL nodes (Railway will load tasks from server)
  const approvalUrl = `https://web-production-c8f1d.up.railway.app?exec_id=${executionId}`;

  console.log(`📋 Generated ${tasks.length} tasks for approval`);
  console.log(`🆔 Execution ID: ${executionId}`);
  console.log(`🔗 Approval URL: ${approvalUrl}`);
  console.log(`📅 Meeting: ${meetingTitle} (${realMeetingOrganizer})`);

  // FIXED: Proper Telegram message formatting (no double escaping)
  const telegramMessage = [
    '🔥 *TaskForge Approval Required*',
    '',
    `📋 *Meeting:* ${meetingTitle}`,
    `👤 *Organizer:* ${realMeetingOrganizer}`,
    `📊 *Tasks:* ${tasks.length}`,
    '',
    `👆 [*APPROVE TASKS*](${approvalUrl})`,
    '',
    `🆔 Execution: ${executionId}`
  ].join('\n');

  // FIXED: Professional email HTML formatting
  const emailHtml = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskForge Approval Required</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
        <h1 style="color: white; margin: 0; font-size: 28px;">🔥 TaskForge Approval Required</h1>
    </div>
    
    <div style="background: #f8f9fa; padding: 25px; border-radius: 8px; margin-bottom: 25px;">
        <h2 style="color: #495057; margin-top: 0; font-size: 20px;">📋 Meeting Details</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; font-weight: bold; color: #6c757d;">Meeting:</td>
                <td style="padding: 8px 0;">${meetingTitle}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; font-weight: bold; color: #6c757d;">Organizer:</td>
                <td style="padding: 8px 0;">${realMeetingOrganizer}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; font-weight: bold; color: #6c757d;">Date:</td>
                <td style="padding: 8px 0;">${new Date(realMeetingDate).toLocaleDateString()}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; font-weight: bold; color: #6c757d;">Tasks:</td>
                <td style="padding: 8px 0;">${tasks.length} action items</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; font-weight: bold; color: #6c757d;">Execution ID:</td>
                <td style="padding: 8px 0; font-family: monospace; font-size: 12px;">${executionId}</td>
            </tr>
        </table>
    </div>
    
    <div style="text-align: center; margin: 40px 0;">
        <a href="${approvalUrl}" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-size: 18px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3); transition: all 0.3s ease;">
            ✅ APPROVE TASKS
        </a>
    </div>
    
    <div style="background: #e9ecef; padding: 20px; border-radius: 8px; margin-top: 30px;">
        <h3 style="color: #495057; margin-top: 0; font-size: 16px;">📝 Task Preview</h3>
        <ul style="margin: 0; padding-left: 20px;">
            ${tasks.slice(0, 3).map(task => 
              `<li style="margin-bottom: 8px; color: #6c757d;">
                <strong>${task.task_item}</strong> 
                <span style="color: #adb5bd;">→ ${task.assignee_full_names}</span>
              </li>`
            ).join('')}
            ${tasks.length > 3 ? `<li style="color: #adb5bd; font-style: italic;">... and ${tasks.length - 3} more tasks</li>` : ''}
        </ul>
    </div>
    
    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px;">
        <p style="margin: 0;">This email was sent automatically by TaskForge</p>
        <p style="margin: 5px 0 0 0;">Click the button above to review and approve tasks</p>
    </div>
</body>
</html>`;

  // Return single object with all data for all 3 nodes to access
  return [{
    json: {
      // For Telegram1 node - FIXED: Proper formatting
      telegram_message: telegramMessage,
      
      // For Gmail node - FIXED: Professional HTML
      email_subject: `🔥 TaskForge: ${tasks.length} Action Items from "${meetingTitle}"`,
      email_html: emailHtml,
      
      // For HTTP Request node - FIXED: Proper JSON structure (no quotes around values)
      execution_id: executionId,
      tasks: tasks,
      meeting_title: meetingTitle,
      meeting_organizer: realMeetingOrganizer,
      meeting_date: realMeetingDate,
      created_at: new Date().toISOString(),
      total_tasks: tasks.length,
      source: 'TaskForge_HITL_HTTP',
      
      // Common fields for all nodes - CONSISTENT URL
      approval_url: approvalUrl,
      tasks_count: tasks.length,
      
      // Debug info
      debug_info: {
        execution_id: executionId,
        tasks_generated: tasks.length,
        meeting_title: meetingTitle,
        meeting_organizer: realMeetingOrganizer,
        meeting_date: realMeetingDate,
        url_used: approvalUrl,
        timestamp: new Date().toISOString()
      }
    }
  }];

} catch (error) {
  console.error('❌ Error in HITL node:', error.message);
  
  // Return single error output
  return [{ json: { error: error.message, status: 'error', timestamp: new Date().toISOString() } }];
} 