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
try:
    import psycopg2
    from psycopg2 import pool
except ImportError:
    psycopg2 = None  # Will fallback to SQLite

app = Flask(__name__)
CORS(app)

# ============================================================================
# 🛢️ DATABASE CONFIG: Postgres (locally & Railway)
# ============================================================================

# DATABASE_URL is supplied by Railway. Locally you can set it or fall back
DATABASE_URL = os.environ.get("DATABASE_URL")

USE_POSTGRES = bool(DATABASE_URL and psycopg2)

# ------------ Connection wrappers (uniform API) -------------

if USE_POSTGRES:
    # Create pool once
    pg_pool = pool.SimpleConnectionPool(minconn=1, maxconn=5, dsn=DATABASE_URL)

    class DBConn:
        """Context-manager wrapper with sqlite-like API on Postgres."""
        def __init__(self):
            self.conn = pg_pool.getconn()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            pg_pool.putconn(self.conn)

        def execute(self, query, params=()):
            query = query.replace("?", "%s")
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if query.strip().lower().startswith("select"):
                    return cur.fetchall()

        def cursor(self):
            return self.conn.cursor()

        def commit(self):
            self.conn.commit()

else:
    # Use local SQLite file
    LOCAL_DB_FILE = os.environ.get("DB_FILE", "hitl.db")

    class DBConn:
        def __init__(self):
            # Allow connections to be shared across Flask threads during local testing
            self.conn = sqlite3.connect(LOCAL_DB_FILE, check_same_thread=False)

        def __enter__(self):
            return self  # return wrapper for unified API

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

        def execute(self, query, params=()):
            cur = self.conn.execute(query, params)
            if query.strip().lower().startswith("select"):
                return cur.fetchall()
            return []

        def cursor(self):
            return self.conn.cursor()

        def commit(self):
            self.conn.commit()


def connect_db():
    """Return a DBConn context manager (Postgres or SQLite)."""
    return DBConn()

# Friendly log
if USE_POSTGRES:
    print(f"🔗 Using Postgres: {DATABASE_URL}")
else:
    print(f"🔗 Using local SQLite: {os.path.abspath(LOCAL_DB_FILE)}")

def init_database():
    """Initialise Postgres tables if they do not yet exist."""
    with connect_db() as conn:
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
        print("✅ Postgres database schema ensured")

def cleanup_expired():
    """Remove expired executions and old approvals"""
    now = datetime.now()
    yesterday = now - timedelta(hours=24)
    with connect_db() as conn:
        conn.execute('DELETE FROM executions WHERE expires_at < ?', (now,))
        conn.execute('DELETE FROM approvals WHERE submitted_at < ?', (yesterday,))

def auto_approve_expired():
    """Auto-approve tasks that have exceeded 15 minutes"""
    with connect_db() as conn:
        # Find executions that are expired but not yet approved
        now = datetime.now()
        expired_executions = conn.execute('''
            SELECT execution_id, monday_tasks, total_tasks 
            FROM executions 
            WHERE expires_at < ? AND status = 'pending'
        ''', (now,))
        
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
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO approvals (execution_id, approved_tasks, approved_count, total_tasks, method)
            VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (execution_id) DO UPDATE SET
                    approved_tasks = EXCLUDED.approved_tasks,
                    approved_count = EXCLUDED.approved_count,
                    total_tasks = EXCLUDED.total_tasks,
                    method = EXCLUDED.method
            ''', (exec_id, json.dumps(approved_tasks), len(approved_tasks), total_tasks, 'auto_timeout'))
            
            # Update execution status
            cursor.execute('''
                UPDATE executions SET status = 'auto_approved' WHERE execution_id = ?
            ''', (exec_id,))
            
            print(f"✅ Auto-approved {len(approved_tasks)} tasks for {exec_id}")
        
        # commit handled by context manager
        pass
    
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

# Background thread will be started later, after tables are ensured

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
        with connect_db() as conn:
            conn.execute('''
                INSERT INTO executions (execution_id, monday_tasks, meeting_title, meeting_organizer, 
             total_tasks, expires_at, meetings_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (execution_id) DO UPDATE SET
                    monday_tasks = EXCLUDED.monday_tasks,
                    meeting_title = EXCLUDED.meeting_title,
                    meeting_organizer = EXCLUDED.meeting_organizer,
                    total_tasks = EXCLUDED.total_tasks,
                    expires_at = EXCLUDED.expires_at,
                    meetings_data = EXCLUDED.meetings_data
            ''', (
                execution_id,
                json.dumps(monday_tasks),
                data.get('meeting_title', 'TaskForge Meeting'),
                data.get('meeting_organizer', ''),
                len(monday_tasks),
                expires_at,
                json.dumps(data.get('meetings', []))
            ))
        
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
        with connect_db() as conn:
            result_rows = conn.execute('''
            SELECT monday_tasks, meeting_title, meeting_organizer, total_tasks, 
                   created_at, expires_at, meetings_data, status
            FROM executions 
            WHERE execution_id = ?
        ''', (execution_id,))
            result = result_rows[0] if result_rows else None
        
        if not result:
            return jsonify({'error': 'Tasks not found'}), 404
        
        tasks_json, meeting_title, meeting_organizer, total_tasks, created_at, expires_at, meetings_json, status = result
        
        # Check if expired (Postgres returns datetime, SQLite returns str)
        if isinstance(expires_at, str):
            exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        else:  # already a datetime object
            exp_dt = expires_at

        now_dt = datetime.now(exp_dt.tzinfo) if hasattr(exp_dt, 'tzinfo') and exp_dt.tzinfo else datetime.now()
        if exp_dt < now_dt:
            return jsonify({'error': 'Tasks have expired'}), 410
        
        if status != 'pending':
            return jsonify({'error': 'Execution already processed'}), 410
        
        data = {
            'execution_id': execution_id,
            'monday_tasks': json.loads(tasks_json),
            'meeting_title': meeting_title,
            'meeting_organizer': meeting_organizer,
            'total_tasks': total_tasks,
            'created_at': created_at,
            'expires_at': exp_dt.isoformat(),
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
        with connect_db() as conn:
            conn.execute('''
                INSERT INTO approvals (execution_id, approved_tasks, approved_count, total_tasks, method)
            VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (execution_id) DO UPDATE SET
                    approved_tasks = EXCLUDED.approved_tasks,
                    approved_count = EXCLUDED.approved_count,
                    total_tasks = EXCLUDED.total_tasks,
                    method = EXCLUDED.method
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
@app.route('/approved', methods=['GET', 'POST'])
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
        
        with connect_db() as conn:
            result_rows = conn.execute('''
            SELECT approved_tasks, approved_count, total_tasks, submitted_at, method
            FROM approvals 
            WHERE execution_id = ?
        ''', (execution_id,))
            result = result_rows[0] if result_rows else None

            # -------------------------------------------------------------------
            # 🕒 If not yet approved, block-wait (max 5 min) instead of returning
            # -------------------------------------------------------------------
            if not result:
                MAX_WAIT = int(os.getenv('APPROVAL_WAIT_SEC', 300))  # 300 s default
                POLL_SEC = 2
                deadline = time.time() + MAX_WAIT

                while time.time() < deadline and not result:
                    time.sleep(POLL_SEC)
                    check_rows = conn.execute('''
                        SELECT approved_tasks, approved_count, total_tasks, submitted_at, method
                        FROM approvals 
                        WHERE execution_id = ?
                    ''', (execution_id,))
                    result = check_rows[0] if check_rows else None

            # After wait loop, result may now be available

            if result:
                # Found approval - return and clean up
                approved_json, approved_count, total_tasks, submitted_at, method = result
                
                # Clean up both tables (self-destruct)
                with connect_db() as conn:
                    conn.execute('DELETE FROM approvals WHERE execution_id = ?', (execution_id,))
                    conn.execute('DELETE FROM executions WHERE execution_id = ?', (execution_id,))
                
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
            with connect_db() as conn:
                exec_rows = conn.execute('SELECT monday_tasks, total_tasks, status FROM executions WHERE execution_id = ?', (execution_id,))
                exec_res = exec_rows[0] if exec_rows else None

            if exec_res:
                # -------------------------------------------------------------
                # 🚦 HITL timed-out ➜ auto-approve all remaining tasks
                # -------------------------------------------------------------
                tasks_json, total_tasks, current_status = exec_res

                # Parse tasks and mark every one as approved (if not already)
                tasks_list = json.loads(tasks_json)
                for t in tasks_list:
                    t['approved'] = True
                    # flag only if not manually approved earlier
                    if 'auto_approved' not in t:
                        t['auto_approved'] = True
                        t['approval_reason'] = 'auto_wait_timeout'

                approved_tasks_json = json.dumps(tasks_list)

                # Persist auto-approval
                with connect_db() as conn:
                    conn.execute('''
                        INSERT INTO approvals (execution_id, approved_tasks, approved_count, total_tasks, method)
                    VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (execution_id) DO UPDATE SET
                            approved_tasks = EXCLUDED.approved_tasks,
                            approved_count = EXCLUDED.approved_count,
                            total_tasks = EXCLUDED.total_tasks,
                            method = EXCLUDED.method
                    ''', (
                        execution_id,
                        approved_tasks_json,
                        len(tasks_list),
                        total_tasks,
                        'auto_wait_timeout'
                    ))

                    # Mark execution as processed
                    conn.execute('UPDATE executions SET status = ? WHERE execution_id = ?', ('auto_approved', execution_id))

                # Return the freshly approved list (and self-destruct)
                with connect_db() as conn:
                    conn.execute('DELETE FROM approvals WHERE execution_id = ?', (execution_id,))
                    conn.execute('DELETE FROM executions WHERE execution_id = ?', (execution_id,))

                print(f"✅ Auto-approved (wait timeout) and self-destructed data for {execution_id} – returned {len(tasks_list)} tasks")

                return jsonify({
                    'execution_id': execution_id,
                    'approved_monday_tasks': tasks_list,
                    'approved_count': len(tasks_list),
                    'total_tasks': total_tasks,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'TaskForge_HITL_Railway',
                    'method': 'auto_wait_timeout'
                })

            # No execution found at all
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
        with connect_db() as conn:
            pending_count = conn.execute('SELECT COUNT(*) FROM executions')[0][0]
            approved_count = conn.execute('SELECT COUNT(*) FROM approvals')[0][0]
        
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
    
    # Initial cleanup & start background thread AFTER tables exist
    cleanup_expired()
    cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
    cleanup_thread.start()
    
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 TaskForge HITL Server starting on port {port}")
    print(f"📊 Database: {DATABASE_URL}")
    print(f"⏰ Auto-approval timeout: 15 minutes")
    print(f"🧹 Background cleanup: Active")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode) 