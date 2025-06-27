#!/usr/bin/env python3
from flask import Flask, send_from_directory, request, jsonify
import os
import requests
import json

app = Flask(__name__)

# In-memory storage for HTTP request approach
stored_tasks = {}
approved_results = {}

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/store-tasks', methods=['POST'])
def store_tasks():
    """Store tasks from n8n for HITL approval"""
    try:
        data = request.get_json()
        execution_id = data.get('execution_id')
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
            
        stored_tasks[execution_id] = data
        print(f"📦 Stored tasks for execution: {execution_id}")
        print(f"📋 Tasks count: {data.get('total_tasks', 0)}")
        
        return jsonify({
            'success': True, 
            'execution_id': execution_id,
            'stored_tasks': data.get('total_tasks', 0)
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

@app.route('/get-approved/<execution_id>', methods=['GET'])
def get_approved(execution_id):
    """Get approved tasks for n8n (with self-destruct)"""
    if execution_id in approved_results:
        result = approved_results.pop(execution_id)  # Self-destruct
        stored_tasks.pop(execution_id, None)  # Cleanup
        print(f"✅ Returning approved tasks for execution: {execution_id}")
        print(f"🗑️ Cleaned up storage for: {execution_id}")
        return jsonify(result)
    
    print(f"⏳ No approved results yet for execution: {execution_id}")
    return jsonify({'status': 'pending'}), 202

@app.route('/submit-approval', methods=['POST'])
def submit_approval():
    """Store approved tasks from UI"""
    try:
        data = request.get_json()
        execution_id = data.get('execution_id')
        
        if not execution_id:
            return jsonify({'error': 'No execution_id provided'}), 400
            
        approved_results[execution_id] = data
        print(f"✅ Stored approved results for execution: {execution_id}")
        print(f"📊 Approved tasks: {data.get('approved_count', 0)}")
        
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