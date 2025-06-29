#!/usr/bin/env python3
from flask import Flask, send_from_directory, request, jsonify
import os
import requests
import json
import sqlite3
from datetime import datetime, timedelta
from flask_cors import CORS
import threading
import time

app = Flask(__name__)
CORS(app)

# ============================================================================
# 🗄️ SQLITE DATABASE SETUP
# ============================================================================

DB_FILE = 'hitl.db'

def init_database():
    """Initialize SQLite database with proper schema"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            execution_id TEXT PRIMARY KEY,
            monday_tasks TEXT NOT NULL,
            meeting_title TEXT,
            meeting_organizer TEXT,
            total_tasks INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            meetings_data TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS approvals (
            execution_id TEXT PRIMARY KEY,
            approved_tasks TEXT NOT NULL,
            approved_count INTEGER,
            total_tasks INTEGER,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            method TEXT DEFAULT 'manual'
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ SQLite database initialized")

def cleanup_expired():
    """Remove expired executions and old approvals"""
    conn = sqlite3.connect(DB_FILE)
    now = datetime.now()
    
    # Remove expired executions
    conn.execute('DELETE FROM executions WHERE expires_at < ?', (now,))
    
    # Remove approvals older than 24 hours
    yesterday = now - timedelta(hours=24)
    conn.execute('DELETE FROM approvals WHERE submitted_at < ?', (yesterday,))
    
    conn.commit()
    conn.close()

def auto_approve_expired():
    """Auto-approve tasks that have exceeded 15 minutes"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Find executions that are expired but not yet approved
    now = datetime.now()
    cursor.execute('''
        SELECT execution_id, monday_tasks, total_tasks 
        FROM executions 
        WHERE expires_at < ? AND status = 'pending'
    ''', (now,))
    
    expired_executions = cursor.fetchall()
    
    for exec_id, tasks_json, total_tasks in expired_executions:
        print(f"⏰ Auto-approving expired execution: {exec_id} ({total_tasks} tasks)")
        
        # Parse tasks and approve all
        tasks = json.loads(tasks_json)
        approved_tasks = []
        for task in tasks:
            task['approved'] = True
            task['auto_approved'] = True
            task['approval_reason'] = '15-minute timeout'
            approved_tasks.append(task)
        
        # Store in approvals table
        cursor.execute('''
            INSERT OR REPLACE INTO approvals 
            (execution_id, approved_tasks, approved_count, total_tasks, method)
            VALUES (?, ?, ?, ?, ?)
        ''', (exec_id, json.dumps(approved_tasks), len(approved_tasks), total_tasks, 'auto_timeout'))
        
        # Update execution status
        cursor.execute('''
            UPDATE executions SET status = 'auto_approved' WHERE execution_id = ?
        ''', (exec_id,))
        
        print(f"✅ Auto-approved {len(approved_tasks)} tasks for {exec_id}")
    
    conn.commit()
    conn.close()
    
    return len(expired_executions)

# ============================================================================
# 🔄 BACKGROUND CLEANUP THREAD
# ============================================================================

def background_cleanup():
    """Background thread for cleanup and auto-approval"""
    while True:
        try:
            cleanup_expired()
            auto_approve_expired()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"❌ Background cleanup error: {e}")
            time.sleep(60)

# Start background thread
cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
cleanup_thread.start()

# ============================================================================
# 📊 API ENDPOINTS
# ============================================================================

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/store-tasks', methods=['POST'])
def store_tasks():
    """Store Monday.com tasks from N8N for HITL approval"""
    try:
        data = request.get_json()
        execution_id = data.get('execution_id')
        monday_tasks = data.get('monday_tasks', [])
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
            
        if not monday_tasks:
            return jsonify({'error': 'No monday_tasks provided'}), 400
        
        # Calculate expiry time (15 minutes from now)
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # Store in SQLite
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''
            INSERT OR REPLACE INTO executions 
            (execution_id, monday_tasks, meeting_title, meeting_organizer, 
             total_tasks, expires_at, meetings_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution_id,
            json.dumps(monday_tasks),
            data.get('meeting_title', 'TaskForge Meeting'),
            data.get('meeting_organizer', ''),
            len(monday_tasks),
            expires_at,
            json.dumps(data.get('meetings', []))
        ))
        conn.commit()
        conn.close()
        
        print(f"📦 Stored {len(monday_tasks)} tasks for {execution_id} (expires: {expires_at})")
        
        return jsonify({
            'success': True, 
            'execution_id': execution_id,
            'stored_tasks': len(monday_tasks),
            'expires_at': expires_at.isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error storing tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-tasks/<execution_id>', methods=['GET'])
def get_tasks(execution_id):
    """Get stored tasks for UI display"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT monday_tasks, meeting_title, meeting_organizer, total_tasks, 
                   created_at, expires_at, meetings_data, status
            FROM executions 
            WHERE execution_id = ?
        ''', (execution_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Tasks not found'}), 404
        
        tasks_json, meeting_title, meeting_organizer, total_tasks, created_at, expires_at, meetings_json, status = result
        
        # Check if expired
        if datetime.fromisoformat(expires_at.replace('Z', '+00:00')) < datetime.now():
            return jsonify({'error': 'Tasks have expired'}), 410
        
        data = {
            'execution_id': execution_id,
            'monday_tasks': json.loads(tasks_json),
            'meeting_title': meeting_title,
            'meeting_organizer': meeting_organizer,
            'total_tasks': total_tasks,
            'created_at': created_at,
            'expires_at': expires_at,
            'status': status,
            'meetings': json.loads(meetings_json) if meetings_json else []
        }
        
        print(f"📤 Serving {total_tasks} tasks for {execution_id}")
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ Error getting tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/submit-approval', methods=['POST'])
def submit_approval():
    """Store approved tasks and trigger N8N continuation"""
    try:
        data = request.get_json()
        execution_id = data.get('execution_id')
        monday_tasks_with_approval = data.get('monday_tasks_with_approval', [])
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
        
        # Filter approved tasks
        approved_tasks = [task for task in monday_tasks_with_approval if task.get('approved') == True]
        
        # Store approval in SQLite
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''
            INSERT OR REPLACE INTO approvals 
            (execution_id, approved_tasks, approved_count, total_tasks, method)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            execution_id,
            json.dumps(approved_tasks),
            len(approved_tasks),
            len(monday_tasks_with_approval),
            'manual'
        ))
        
        # Update execution status
        conn.execute('''
            UPDATE executions SET status = 'approved' WHERE execution_id = ?
        ''', (execution_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Manual approval: {len(approved_tasks)}/{len(monday_tasks_with_approval)} tasks for {execution_id}")
        
        return jsonify({
            'success': True,
            'approved_count': len(approved_tasks),
            'total_tasks': len(monday_tasks_with_approval)
        })
        
    except Exception as e:
        print(f"❌ Error submitting approval: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-approved', methods=['GET', 'POST'])
def get_approved():
    """Get approved tasks for N8N (supports both GET and POST)"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            execution_id = data.get('execution_id')
        else:
            execution_id = request.args.get('execution_id')
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check for approved results
        cursor.execute('''
            SELECT approved_tasks, approved_count, total_tasks, submitted_at, method
            FROM approvals 
            WHERE execution_id = ?
        ''', (execution_id,))
        
        result = cursor.fetchone()
        
        if result:
            # Found approval - return and clean up
            approved_json, approved_count, total_tasks, submitted_at, method = result
            
            # Clean up both tables (self-destruct)
            cursor.execute('DELETE FROM approvals WHERE execution_id = ?', (execution_id,))
            cursor.execute('DELETE FROM executions WHERE execution_id = ?', (execution_id,))
            conn.commit()
            conn.close()
            
            response_data = {
                'execution_id': execution_id,
                'approved_monday_tasks': json.loads(approved_json),
                'approved_count': approved_count,
                'total_tasks': total_tasks,
                'timestamp': submitted_at,
                'source': 'TaskForge_HITL_Railway',
                'method': method
            }
            
            print(f"✅ Self-destructed data for {execution_id} - returned {approved_count} approved tasks")
            return jsonify(response_data)
        
        # Check if execution still exists (pending)
        cursor.execute('SELECT status FROM executions WHERE execution_id = ?', (execution_id,))
        exec_result = cursor.fetchone()
        conn.close()
        
        if exec_result:
            print(f"⏳ Tasks exist but not yet approved for: {execution_id}")
            return jsonify({'status': 'pending', 'message': 'Tasks not yet approved'}), 202
        
        print(f"❌ No data found for execution: {execution_id}")
        return jsonify({'error': 'Execution ID not found or already processed'}), 404
        
    except Exception as e:
        print(f"❌ Error getting approved tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM executions')
        pending_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM approvals')
        approved_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'pending_executions': pending_count,
            'completed_approvals': approved_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# ============================================================================
# 🚀 APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    # Initial cleanup
    cleanup_expired()
    
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 TaskForge HITL Server starting on port {port}")
    print(f"📊 Database: {DB_FILE}")
    print(f"⏰ Auto-approval timeout: 15 minutes")
    print(f"🧹 Background cleanup: Active")
    
    app.run(host='0.0.0.0', port=port, debug=True) 