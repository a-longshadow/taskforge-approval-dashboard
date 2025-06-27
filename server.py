#!/usr/bin/env python3
from flask import Flask, send_from_directory, request, jsonify
import os
import requests
import json

app = Flask(__name__)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/submit', methods=['POST'])
def submit_to_n8n():
    try:
        # Get the payload from the frontend
        payload = request.get_json()
        
        if not payload:
            return jsonify({'error': 'No payload received'}), 400
            
        # Extract webhook URL and remove it from payload
        webhook_url = payload.pop('webhook_url', None)
        
        if not webhook_url:
            return jsonify({'error': 'No webhook URL provided'}), 400
            
        print(f"🔄 Forwarding to N8N webhook: {webhook_url}")
        print(f"📋 Payload: {json.dumps(payload, indent=2)}")
        
        # Forward to N8N webhook (server-to-server, no CORS issues)
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📡 N8N Response Status: {response.status_code}")
        print(f"📋 N8N Response: {response.text}")
        
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
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        return jsonify({
            'error': 'Failed to connect to TaskForge webhook',
            'details': str(e)
        }), 500
        
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True) 