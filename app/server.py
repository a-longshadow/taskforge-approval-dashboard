#!/usr/bin/env python3
from flask import Flask, send_from_directory, request, jsonify
import os
import requests
import json
import graphene
from flask_graphql import GraphQLView

app = Flask(__name__)

# In-memory storage for HTTP request approach
stored_tasks = {}
approved_results = {}

# GraphQL Schema Definitions
class TaskType(graphene.ObjectType):
    task_id = graphene.String()
    name = graphene.String()
    assignee_full_names = graphene.String()
    assignee_emails = graphene.String()
    priority = graphene.String()
    brief_description = graphene.String()
    date_expected = graphene.String()
    approved = graphene.Boolean()

class MeetingType(graphene.ObjectType):
    execution_id = graphene.String()
    meeting_title = graphene.String()
    meeting_organizer = graphene.String()
    total_tasks = graphene.Int()
    stored_at = graphene.String()
    monday_tasks = graphene.List(TaskType)

class ApprovalResultType(graphene.ObjectType):
    execution_id = graphene.String()
    approved_count = graphene.Int()
    total_tasks = graphene.Int()
    timestamp = graphene.String()
    source = graphene.String()
    approved_monday_tasks = graphene.List(TaskType)

# GraphQL Queries
class Query(graphene.ObjectType):
    # Get stored tasks by execution ID
    meeting = graphene.Field(MeetingType, execution_id=graphene.String(required=True))
    
    # Get all stored meetings
    meetings = graphene.List(MeetingType)
    
    # Get approved results
    approved_tasks = graphene.Field(ApprovalResultType, execution_id=graphene.String(required=True))
    
    # Health check
    health = graphene.String()

    def resolve_meeting(self, info, execution_id):
        if execution_id in stored_tasks:
            data = stored_tasks[execution_id]
            # Convert monday_tasks to TaskType objects
            tasks = []
            for task in data.get('monday_tasks', []):
                if isinstance(task, dict) and 'columnValues' in task:
                    # Handle Monday.com format
                    tasks.append(TaskType(
                        task_id=task.get('task_id'),
                        name=task.get('name'),
                        assignee_full_names=task.get('columnValues', {}).get('text_mkr7jgkp'),
                        assignee_emails=task.get('columnValues', {}).get('text_mkr0hqsb'),
                        priority=task.get('columnValues', {}).get('status_1'),
                        brief_description=task.get('columnValues', {}).get('long_text'),
                        date_expected=task.get('columnValues', {}).get('date_mkr7ymmh')
                    ))
                else:
                    # Handle simple format
                    tasks.append(TaskType(
                        task_id=task.get('task_id'),
                        name=task.get('task_item'),
                        assignee_full_names=task.get('assignee(s)_full_names'),
                        assignee_emails=task.get('assignee_emails'),
                        priority=task.get('priority'),
                        brief_description=task.get('brief_description'),
                        date_expected=task.get('date_expected')
                    ))
            
            return MeetingType(
                execution_id=data.get('execution_id'),
                meeting_title=data.get('meeting_title'),
                meeting_organizer=data.get('meeting_organizer'),
                total_tasks=data.get('total_tasks'),
                stored_at=data.get('stored_at'),
                monday_tasks=tasks
            )
        return None

    def resolve_meetings(self, info):
        meetings = []
        for execution_id, data in stored_tasks.items():
            meetings.append(MeetingType(
                execution_id=data.get('execution_id'),
                meeting_title=data.get('meeting_title'),
                meeting_organizer=data.get('meeting_organizer'),
                total_tasks=data.get('total_tasks'),
                stored_at=data.get('stored_at')
            ))
        return meetings

    def resolve_approved_tasks(self, info, execution_id):
        if execution_id in approved_results:
            data = approved_results[execution_id]
            tasks = []
            for task in data.get('approved_monday_tasks', []):
                tasks.append(TaskType(
                    task_id=task.get('task_id'),
                    name=task.get('name'),
                    assignee_full_names=task.get('assignee_full_names'),
                    assignee_emails=task.get('assignee_emails'),
                    priority=task.get('priority'),
                    brief_description=task.get('brief_description'),
                    date_expected=task.get('date_expected'),
                    approved=True
                ))
            
            return ApprovalResultType(
                execution_id=data.get('execution_id'),
                approved_count=data.get('approved_count'),
                total_tasks=data.get('total_tasks'),
                timestamp=data.get('timestamp'),
                source=data.get('source'),
                approved_monday_tasks=tasks
            )
        return None

    def resolve_health(self, info):
        return f"TaskForge GraphQL API is running! Stored meetings: {len(stored_tasks)}, Approved results: {len(approved_results)}"

# GraphQL Mutations
class StoreTasksMutation(graphene.Mutation):
    class Arguments:
        execution_id = graphene.String(required=True)
        meeting_title = graphene.String()
        meeting_organizer = graphene.String()
        monday_tasks = graphene.String(required=True)  # JSON string
        created_at = graphene.String()

    success = graphene.Boolean()
    execution_id = graphene.String()
    stored_tasks_count = graphene.Int()
    message = graphene.String()

    def mutate(self, info, execution_id, monday_tasks, meeting_title=None, meeting_organizer=None, created_at=None):
        try:
            # Parse monday_tasks JSON string
            tasks_data = json.loads(monday_tasks)
            
            stored_tasks[execution_id] = {
                'execution_id': execution_id,
                'monday_tasks': tasks_data,
                'meeting_title': meeting_title or 'TaskForge Meeting',
                'meeting_organizer': meeting_organizer,
                'total_tasks': len(tasks_data),
                'stored_at': created_at
            }
            
            print(f"📦 GraphQL: Stored {len(tasks_data)} tasks for execution: {execution_id}")
            
            return StoreTasksMutation(
                success=True,
                execution_id=execution_id,
                stored_tasks_count=len(tasks_data),
                message=f"Successfully stored {len(tasks_data)} tasks"
            )
        except Exception as e:
            return StoreTasksMutation(
                success=False,
                message=f"Error storing tasks: {str(e)}"
            )

class SubmitApprovalMutation(graphene.Mutation):
    class Arguments:
        execution_id = graphene.String(required=True)
        monday_tasks_with_approval = graphene.String(required=True)  # JSON string
        timestamp = graphene.String()

    success = graphene.Boolean()
    approved_count = graphene.Int()
    total_tasks = graphene.Int()
    message = graphene.String()

    def mutate(self, info, execution_id, monday_tasks_with_approval, timestamp=None):
        try:
            # Parse tasks with approval JSON string
            tasks_data = json.loads(monday_tasks_with_approval)
            
            # Filter approved tasks
            approved_tasks = [task for task in tasks_data if task.get('approved') == True]
            
            approved_results[execution_id] = {
                'execution_id': execution_id,
                'approved_monday_tasks': approved_tasks,
                'approved_count': len(approved_tasks),
                'total_tasks': len(tasks_data),
                'timestamp': timestamp,
                'source': 'TaskForge_HITL_GraphQL'
            }
            
            print(f"✅ GraphQL: Processed {len(tasks_data)} tasks, approved {len(approved_tasks)}")
            
            return SubmitApprovalMutation(
                success=True,
                approved_count=len(approved_tasks),
                total_tasks=len(tasks_data),
                message="Approval submitted successfully"
            )
        except Exception as e:
            return SubmitApprovalMutation(
                success=False,
                message=f"Error submitting approval: {str(e)}"
            )

class Mutation(graphene.ObjectType):
    store_tasks = StoreTasksMutation.Field()
    submit_approval = SubmitApprovalMutation.Field()

# Create GraphQL Schema
schema = graphene.Schema(query=Query, mutation=Mutation)

# REST API Routes (existing)
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# Add GraphQL endpoint
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

@app.route('/store-tasks', methods=['POST'])
def store_tasks():
    """Store Monday.com tasks from n8n for HITL approval"""
    try:
        data = request.get_json()
        execution_id = data.get('execution_id')
        monday_tasks = data.get('monday_tasks', [])
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
            
        if not monday_tasks:
            return jsonify({'error': 'No monday_tasks provided'}), 400
            
        # Store the complete Monday.com payload
        stored_tasks[execution_id] = {
            'execution_id': execution_id,
            'monday_tasks': monday_tasks,
            'meeting_title': data.get('meeting_title', 'TaskForge Meeting'),
            'total_tasks': len(monday_tasks),
            'stored_at': data.get('created_at')
        }
        
        print(f"📦 Stored {len(monday_tasks)} Monday.com tasks for execution: {execution_id}")
        
        return jsonify({
            'success': True, 
            'execution_id': execution_id,
            'stored_tasks': len(monday_tasks)
        })
        
    except Exception as e:
        print(f"❌ Error storing tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-tasks/<execution_id>', methods=['GET'])
def get_tasks(execution_id):
    """Get stored tasks for UI display"""
    if execution_id in stored_tasks:
        data = stored_tasks[execution_id]
        print(f"📤 Serving tasks for execution: {execution_id}")
        return jsonify(data)
    
    print(f"❌ Tasks not found for execution: {execution_id}")
    return jsonify({'error': 'Tasks not found'}), 404

@app.route('/get-approved', methods=['GET', 'POST'])
def get_approved():
    """Get approved tasks for n8n (supports both GET and POST)"""
    if request.method == 'POST':
        data = request.get_json()
        execution_id = data.get('execution_id')
    else:
        execution_id = request.args.get('execution_id')
    
    if not execution_id:
        return jsonify({'error': 'No execution_id provided'}), 400
    
    if execution_id in approved_results:
        result = approved_results.pop(execution_id)  # Remove from approved
        stored_tasks.pop(execution_id, None)  # Remove from stored
        
        print(f"✅ Self-destructed data for execution: {execution_id}")
        print(f"📊 Returned {result.get('approved_count', 0)} approved tasks")
        
        return jsonify(result)
    
    # Check if tasks exist but not yet approved
    if execution_id in stored_tasks:
        print(f"⏳ Tasks exist but not yet approved for: {execution_id}")
        return jsonify({'status': 'pending', 'message': 'Tasks not yet approved'}), 202
    
    print(f"❌ No data found for execution: {execution_id}")
    return jsonify({'error': 'Execution ID not found or already processed'}), 404

@app.route('/submit-approval', methods=['POST'])
def submit_approval():
    """Store Monday.com tasks with approval status from UI"""
    try:
        data = request.get_json()
        execution_id = data.get('execution_id')
        monday_tasks_with_approval = data.get('monday_tasks_with_approval', [])
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
            
        # Filter to get only approved tasks (approved: true)
        approved_monday_tasks = [task for task in monday_tasks_with_approval if task.get('approved') == True]
        
        # Store result for n8n to retrieve
        approved_results[execution_id] = {
            'execution_id': execution_id,
            'approved_monday_tasks': approved_monday_tasks,  # Only TRUE tasks
            'approved_count': len(approved_monday_tasks),
            'total_tasks': len(monday_tasks_with_approval),
            'timestamp': data.get('timestamp'),
            'source': 'TaskForge_HITL_Railway'
        }
        
        print(f"✅ Processed {len(monday_tasks_with_approval)} tasks for execution: {execution_id}")
        print(f"📊 Approved: {len(approved_monday_tasks)} tasks")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌ Error storing approval: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Legacy endpoints for backward compatibility
@app.route('/submit', methods=['POST'])
def submit_to_n8n():
    """Legacy webhook forwarding (kept for compatibility)"""
    try:
        payload = request.get_json()
        
        if not payload:
            return jsonify({'error': 'No payload received'}), 400
            
        webhook_url = payload.pop('webhook_url', None)
        
        if not webhook_url:
            return jsonify({'error': 'No webhook URL provided'}), 400
            
        print(f"🔄 Forwarding to N8N webhook: {webhook_url}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Tasks submitted successfully to TaskForge',
                'approved_count': payload.get('approved_count', 0)
            })
        else:
            return jsonify({
                'error': f'N8N webhook failed with status {response.status_code}',
                'details': response.text
            }), 500
            
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True) 