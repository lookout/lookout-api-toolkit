"""
Lookout Application Submission Tool - Python Flask
Local web interface for submitting apps and viewing analysis reports.
Enhanced with improved UI/UX, accessibility, and mobile responsiveness.

Run: python app_improved.py
Open: http://localhost:5000
"""

import os
import json
import hashlib
import time
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max
app.secret_key = os.urandom(24)

# Load configuration
try:
    import config
    API_HOST = getattr(config, 'API_HOST', '')
    APP_KEY = getattr(config, 'APP_KEY', '')
    BEARER_TOKEN = getattr(config, 'BEARER_TOKEN', '')
except ImportError:
    API_HOST = ''
    APP_KEY = ''
    BEARER_TOKEN = ''

# Store submission history in memory (for demo purposes)
submission_history = []
cached_token = None
token_expiry = None

def get_oauth_token(host, app_key, token_path='/oauth2/token', max_retries=3, base_delay=2):
    """Exchange Application Key for OAuth2 Bearer Token with retry logic"""
    global token_expiry
    
    url = f"https://{host.replace('https://', '').replace('http://', '')}{token_path}"
    
    headers = {
        'Authorization': f'Bearer {app_key}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    data = {
        'grant_type': 'client_credentials'
    }
    
    # Debug logging (disable in production)
    # print(f"[DEBUG] OAuth token request URL: {url}")
    # print(f"[DEBUG] OAuth token request headers: {dict((k, v[:50] + '...' if k == 'Authorization' and len(v) > 50 else v) for k, v in headers.items())}")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            
            # Debug logging (disable in production)
            # print(f"[DEBUG] OAuth token response status: {response.status_code}")
            # print(f"[DEBUG] OAuth token response body: {response.text[:500] if response.text else 'empty'}")
            
            if response.status_code >= 200 and response.status_code < 300:
                result = response.json()
                if 'access_token' in result:
                    expires_in = result.get('expires_in', 3600)
                    token_expiry = datetime.now().timestamp() + expires_in - 60
                    # print(f"[DEBUG] OAuth token obtained successfully (expires_in: {expires_in}s)")
                    return result['access_token']
            
            if response.status_code in (502, 503, 504, 429):
                delay = base_delay * (2 ** attempt)
                print(f"[WARN] Retryable error {response.status_code}, attempt {attempt + 1}/{max_retries}, waiting {delay}s...")
                time.sleep(delay)
                continue
            
            try:
                error_data = response.json()
                error_msg = error_data.get('error_description', error_data.get('error', str(error_data)))
            except:
                error_msg = response.text or 'Unknown error'
            raise Exception(f"Token generation failed (HTTP {response.status_code}): {error_msg}")
            
        except requests.exceptions.RequestException as e:
            last_error = e
            delay = base_delay * (2 ** attempt)
            print(f"[WARN] Request error: {e}, attempt {attempt + 1}/{max_retries}, waiting {delay}s...")
            time.sleep(delay)
    
    raise Exception(f"Token generation failed after {max_retries} attempts: {last_error or 'Unknown error'}")


def submit_store_url(host, token, store_url):
    """Submit app via Apple/Google Play Store URL"""
    url = f"https://{host.replace('https://', '').replace('http://', '')}/api/v1/applications/submissions/store"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    response = requests.post(url, params={'url': store_url}, headers=headers, timeout=60)
    return response.status_code, response.json()


def submit_file(host, token, file_path, file_name):
    """Submit app via file upload"""
    url = f"https://{host.replace('https://', '').replace('http://', '')}/api/v1/applications/submissions/file"
    
    # Calculate MD5 hash (base64 encoded)
    import hashlib
    import base64
    with open(file_path, 'rb') as f:
        md5_digest = hashlib.md5(f.read()).digest()
        file_md5 = base64.b64encode(md5_digest).decode('utf-8')
    
    # Determine MIME type
    ext = file_name.lower().split('.')[-1]
    mime_types = {
        'ipa': 'application/octet-stream',
        'apk': 'application/vnd.android.package-archive',
        'aab': 'application/x-authorware-bin'
    }
    mime_type = mime_types.get(ext, 'application/octet-stream')
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
        # 'Content-MD5': file_md5  # Optional - uncomment if needed
    }
    
    # Debug logging (disable in production)
    # print(f"[DEBUG] Submitting to: {url}")
    # print(f"[DEBUG] File MD5: {file_md5}")
    # print(f"[DEBUG] MIME type: {mime_type}")
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f, mime_type)}
        response = requests.post(url, headers=headers, files=files, timeout=300)
    
    try:
        return response.status_code, response.json()
    except:
        return response.status_code, {'error': response.text or 'No response body'}


def get_analysis_status(host, token, reference_id):
    """Get analysis details for a specific reference ID"""
    url = f"https://{host.replace('https://', '').replace('http://', '')}/api/v1/applications/analyses/{reference_id}"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code, response.json()


def get_all_analyses(host, token):
    """Get all app submissions/analyses"""
    url = f"https://{host.replace('https://', '').replace('http://', '')}/api/v1/applications/analyses"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code, response.json()


# Enhanced HTML Template with Improved UI/UX
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lookout App Submission Tool</title>
    <style>
        :root {
            /* Design System - 8px Grid */
            --space-1: 8px;
            --space-2: 16px;
            --space-3: 24px;
            --space-4: 32px;
            --space-5: 40px;
            
            /* Colors - Enhanced Contrast for Accessibility */
            --primary: #2E7D32;
            --primary-hover: #1B5E20;
            --primary-light: #E8F5E9;
            --bg: #F5F5F5;
            --surface: #FFFFFF;
            --border: #BDBDBD;
            --text: #212121;
            --text-secondary: #616161;
            --text-muted: #9E9E9E;
            --success: #2E7D32;
            --success-bg: #E8F5E9;
            --error: #D32F2F;
            --error-bg: #FFEBEE;
            --info: #1976D2;
            --info-bg: #E3F2FD;
            --warning: #F57C00;
            --warning-bg: #FFF3E0;
            
            /* Shadows */
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
            
            /* Border Radius */
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 12px;
        }
        
        * { box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: var(--space-5);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        @media (max-width: 768px) {
            body {
                padding: var(--space-2);
            }
            .container {
                max-width: 100%;
            }
        }
        
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: var(--space-4);
            gap: var(--space-2);
        }
        
        .header h1 {
            margin: 0;
            color: var(--text);
            font-size: 28px;
            font-weight: 600;
        }
        
        .header .badge {
            background: var(--primary-light);
            color: var(--primary);
            padding: var(--space-1) var(--space-2);
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 500;
        }
        
        .help-button {
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: var(--space-1) var(--space-2);
            border-radius: var(--radius-md);
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        
        .help-button:hover {
            background: var(--bg);
            border-color: var(--text-secondary);
        }
        
        .config-status {
            background: var(--success-bg);
            color: #1B5E20;
            padding: var(--space-2) var(--space-3);
            border-radius: var(--radius-md);
            margin-bottom: var(--space-4);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: var(--space-2);
            border: 1px solid #C8E6C9;
        }
        
        .config-status.error {
            background: var(--error-bg);
            color: #C62828;
            border-color: #FFCDD2;
        }
        
        .card {
            background: var(--surface);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border);
            padding: var(--space-4);
            margin-bottom: var(--space-4);
        }
        
        .card h2 {
            margin: 0 0 var(--space-3) 0;
            font-size: 20px;
            font-weight: 600;
            color: var(--text);
        }
        
        .main-tabs {
            display: flex;
            background: var(--surface);
            border-radius: var(--radius-md);
            padding: var(--space-1);
            margin-bottom: var(--space-4);
            border: 1px solid var(--border);
            gap: var(--space-1);
        }
        
        .main-tab {
            flex: 1;
            padding: var(--space-2) var(--space-3);
            text-align: center;
            cursor: pointer;
            border-radius: var(--radius-sm);
            font-weight: 500;
            font-size: 14px;
            color: var(--text-secondary);
            transition: all 0.2s;
            border: none;
            background: transparent;
        }
        
        .main-tab:hover { 
            background: var(--bg); 
            color: var(--text);
        }
        
        .main-tab.active { 
            background: var(--primary); 
            color: white; 
            box-shadow: var(--shadow-sm);
        }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .form-group { margin-bottom: var(--space-3); }
        
        label {
            display: block;
            margin-bottom: var(--space-1);
            font-weight: 500;
            font-size: 14px;
            color: var(--text);
        }
        
        input[type="text"], input[type="password"], select, textarea {
            width: 100%;
            max-width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 14px;
            color: var(--text);
            transition: all 0.2s;
            font-family: inherit;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-light);
        }
        
        input:disabled, select:disabled {
            background: var(--bg);
            cursor: not-allowed;
        }
        
        .hint {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: var(--space-1);
        }
        
        .validation-message {
            font-size: 13px;
            margin-top: var(--space-1);
            display: none;
        }
        
        .validation-message.error {
            color: var(--error);
            display: block;
        }
        
        .validation-message.success {
            color: var(--success);
            display: block;
        }
        
        .sub-tabs {
            display: flex;
            border-bottom: 2px solid var(--border);
            margin-bottom: var(--space-4);
            gap: var(--space-3);
        }
        
        .sub-tab {
            padding: var(--space-2) var(--space-1);
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
            color: var(--text-muted);
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
            position: relative;
        }
        
        .sub-tab:hover { color: var(--text); }
        
        .sub-tab.active { 
            color: var(--primary); 
            border-bottom-color: var(--primary);
        }
        
        .sub-content { display: none; }
        .sub-content.active { display: block; }
        
        .file-upload {
            border: 2px dashed var(--border);
            border-radius: var(--radius-md);
            padding: var(--space-5);
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            background: var(--bg);
        }
        
        .file-upload:hover { 
            border-color: var(--primary); 
            background: var(--primary-light);
        }
        
        .file-upload.dragover { 
            border-color: var(--primary); 
            background: var(--primary-light);
            transform: scale(1.02);
        }
        
        .file-upload input { display: none; }
        
        .file-upload-icon {
            font-size: 48px;
            margin-bottom: var(--space-2);
            opacity: 0.6;
        }
        
        .file-upload-text { 
            color: var(--text-secondary); 
            font-size: 14px;
        }
        
        .file-upload-text strong { 
            color: var(--primary); 
            font-weight: 600;
        }
        
        .selected-file {
            background: var(--success-bg);
            padding: var(--space-2) var(--space-3);
            border-radius: var(--radius-md);
            margin-top: var(--space-2);
            display: none;
            font-size: 14px;
            border: 1px solid #C8E6C9;
        }
        
        .selected-file.show { display: flex; }
        
        .selected-file strong {
            font-weight: 600;
            margin-right: var(--space-1);
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-1);
            padding: 10px 20px;
            border: none;
            border-radius: var(--radius-md);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }
        
        .btn-primary {
            background: var(--primary);
            color: white;
            width: 100%;
        }
        
        .btn-primary:hover { 
            background: var(--primary-hover);
            box-shadow: var(--shadow-md);
        }
        
        .btn-primary:active {
            transform: translateY(1px);
        }
        
        .btn-primary:disabled { 
            background: var(--text-muted); 
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-secondary {
            background: #EEEEEE;
            color: var(--text);
            border: none;
        }
        
        .btn-secondary:hover { 
            background: #E0E0E0;
        }
        
        .btn-icon {
            padding: var(--space-1) var(--space-2);
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-secondary);
        }
        
        .btn-icon:hover {
            background: var(--bg);
            border-color: var(--text-secondary);
        }
        
        .alert {
            padding: var(--space-2) var(--space-3);
            border-radius: var(--radius-md);
            margin-bottom: var(--space-4);
            display: none;
            font-size: 14px;
            border-left: 4px solid transparent;
        }
        
        .alert.show { display: flex; align-items: center; gap: var(--space-2); }
        .alert.success { 
            background: var(--success-bg); 
            color: #1B5E20; 
            border-left-color: var(--success);
        }
        .alert.error { 
            background: var(--error-bg); 
            color: #C62828;
            border-left-color: var(--error);
        }
        .alert.info { 
            background: var(--info-bg); 
            color: #0D47A1;
            border-left-color: var(--info);
        }
        
        .response-box {
            background: var(--bg);
            color: var(--text);
            padding: var(--space-3);
            border-radius: var(--radius-md);
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border);
        }
        
        .response-box .key { color: var(--success); font-weight: 600; }
        .response-box .string { color: var(--warning); }
        .response-box .number { color: var(--info); }
        .response-box .boolean { color: var(--error); }
        
        .history-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .history-table th, .history-table td {
            padding: var(--space-2);
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }
        
        .history-table th {
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: var(--bg);
        }
        
        .history-table tr:hover { background: var(--bg); }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-pending { 
            background: var(--warning-bg); 
            color: #E65100; 
        }
        .status-success { 
            background: var(--success-bg); 
            color: #1B5E20; 
        }
        .status-error { 
            background: var(--error-bg); 
            color: #C62828; 
        }
        
        .report-section {
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            margin-bottom: var(--space-3);
            overflow: hidden;
        }
        
        .report-header {
            background: var(--bg);
            padding: var(--space-3);
            font-weight: 500;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .report-header:hover {
            background: #EEEEEE;
        }
        
        .report-content { 
            padding: var(--space-3); 
            display: none; 
        }
        
        .report-content.show { display: block; }
        
        .loading {
            display: none;
            align-items: center;
            gap: var(--space-2);
            color: var(--text-secondary);
            margin-top: var(--space-2);
            font-size: 14px;
        }
        
        .loading.show { display: flex; }
        
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .empty-state {
            text-align: center;
            padding: 60px var(--space-3);
            color: var(--text-secondary);
        }
        
        .empty-state-icon { 
            font-size: 48px; 
            margin-bottom: var(--space-3); 
            opacity: 0.5; 
        }
        
        .copy-btn {
            padding: 6px 12px;
            font-size: 12px;
            background: #EEEEEE;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-weight: 500;
            color: var(--text);
            transition: all 0.2s;
        }
        
        .copy-btn:hover { 
            background: #E0E0E0;
            border-color: var(--text-secondary);
        }
        
        .ref-id-display {
            display: flex;
            align-items: center;
            gap: var(--space-2);
            background: var(--success-bg);
            padding: var(--space-2) var(--space-3);
            border-radius: var(--radius-md);
            margin-top: var(--space-2);
            flex-wrap: wrap;
            border: 1px solid #C8E6C9;
        }
        
        .ref-id-display strong {
            font-weight: 600;
            color: #1B5E20;
        }
        
        .ref-id-display code {
            flex: 1;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            color: #1B5E20;
            word-break: break-all;
            min-width: 200px;
            background: white;
            padding: 4px 8px;
            border-radius: var(--radius-sm);
        }
        
        /* Progress Bar */
        .progress-container {
            margin-top: var(--space-3);
            display: none;
        }
        
        .progress-container.show {
            display: block;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--border);
            border-radius: var(--radius-sm);
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: var(--primary);
            transition: width 0.3s ease;
            border-radius: var(--radius-sm);
        }
        
        .progress-text {
            display: flex;
            justify-content: space-between;
            margin-top: var(--space-1);
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        /* Toast Notifications */
        .toast-container {
            position: fixed;
            top: var(--space-3);
            right: var(--space-3);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: var(--space-2);
        }
        
        .toast {
            background: var(--surface);
            padding: var(--space-2) var(--space-3);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            border-left: 4px solid var(--primary);
            min-width: 300px;
            max-width: 400px;
            animation: slideIn 0.3s ease;
        }
        
        .toast.success { border-left-color: var(--success); }
        .toast.error { border-left-color: var(--error); }
        .toast.info { border-left-color: var(--info); }
        
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 999;
        }
        
        .modal-overlay.show {
            display: flex;
        }
        
        .modal {
            background: var(--surface);
            padding: var(--space-4);
            border-radius: var(--radius-lg);
            max-width: 500px;
            width: 90%;
            box-shadow: var(--shadow-lg);
        }
        
        .modal h3 {
            margin: 0 0 var(--space-3) 0;
            font-size: 20px;
            color: var(--text);
        }
        
        .modal p {
            margin: var(--space-2) 0;
            color: var(--text-secondary);
            line-height: 1.6;
        }
        
        .modal-actions {
            display: flex;
            gap: var(--space-2);
            margin-top: var(--space-4);
            justify-content: flex-end;
        }
        
        /* File Preview */
        .file-preview {
            display: flex;
            align-items: center;
            gap: var(--space-2);
            padding: var(--space-2);
            background: var(--bg);
            border-radius: var(--radius-sm);
            margin-top: var(--space-2);
        }
        
        .file-icon {
            font-size: 32px;
            opacity: 0.6;
        }
        
        .file-info {
            flex: 1;
        }
        
        .file-name {
            font-weight: 500;
            font-size: 14px;
            color: var(--text);
        }
        
        .file-size {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .remove-file {
            background: none;
            border: none;
            color: var(--error);
            cursor: pointer;
            font-size: 18px;
            padding: var(--space-1);
        }
        
        .remove-file:hover {
            background: var(--error-bg);
            border-radius: var(--radius-sm);
        }
        
        /* Keyboard Shortcuts Modal */
        .keyboard-shortcut {
            display: flex;
            justify-content: space-between;
            padding: var(--space-2) 0;
            border-bottom: 1px solid var(--border);
        }
        
        .keyboard-shortcut:last-child {
            border-bottom: none;
        }
        
        .shortcut-keys {
            display: flex;
            gap: var(--space-1);
        }
        
        .key {
            background: var(--bg);
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            font-family: monospace;
            font-size: 12px;
            border: 1px solid var(--border);
        }
        
        /* Accessibility */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border-width: 0;
        }
        
        @media (max-width: 768px) {
            .main-tabs {
                flex-wrap: wrap;
            }
            
            .main-tab {
                flex: 1 1 calc(50% - var(--space-1));
                min-width: 120px;
            }
            
            .btn {
                width: 100%;
            }
            
            .history-table {
                display: block;
                overflow-x: auto;
            }
            
            .ref-id-display {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .ref-id-display code {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <!-- Skip to content for accessibility -->
    <a href="#main-content" class="sr-only">Skip to main content</a>
    
    <!-- Toast Container -->
    <div class="toast-container" id="toastContainer"></div>
    
    <!-- Help Modal -->
    <div class="modal-overlay" id="helpModal">
        <div class="modal">
            <h3>📖 Quick Guide</h3>
            <p><strong>Submit Apps:</strong> Use the "Submit App" tab to upload files or paste store URLs.</p>
            <p><strong>Check Status:</strong> Enter a Reference ID to see analysis progress.</p>
            <p><strong>History:</strong> View all your submissions in the current session.</p>
            <p><strong>Reports:</strong> Generate detailed reports in JSON, Summary, or CSV format.</p>
            
            <h4 style="margin: var(--space-3) 0 var(--space-2) 0; font-size: 16px;">⌨️ Keyboard Shortcuts</h4>
            <div class="keyboard-shortcut">
                <span>Submit App</span>
                <div class="shortcut-keys">
                    <span class="key">Ctrl</span>
                    <span class="key">Enter</span>
                </div>
            </div>
            <div class="keyboard-shortcut">
                <span>Open Help</span>
                <div class="shortcut-keys">
                    <span class="key">Ctrl</span>
                    <span class="key">K</span>
                </div>
            </div>
            <div class="keyboard-shortcut">
                <span>Close Modal</span>
                <div class="shortcut-keys">
                    <span class="key">Esc</span>
                </div>
            </div>
            
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="closeHelpModal()">Got it!</button>
            </div>
        </div>
    </div>
    
    <div class="container" id="main-content">
        <div class="header">
            <div>
                <h1>Lookout App Submission Tool</h1>
                <span class="badge">Enhanced Edition</span>
            </div>
            <button class="help-button" onclick="openHelpModal()" aria-label="Open help">
                ❓ Help
            </button>
        </div>
        
        <!-- Config Status -->
        <div class="config-status {{ 'error' if not config_valid else '' }}" role="alert">
            {% if config_valid %}
                ✅ Connected to <strong>{{ api_host }}</strong>
            {% else %}
                ⚠️ Please configure <strong>config.py</strong> with your API credentials
            {% endif %}
        </div>
        
        <!-- Main Navigation Tabs -->
        <nav class="main-tabs" role="tablist">
            <button class="main-tab active" onclick="switchMainTab('submit')" role="tab" aria-selected="true">
                📱 Submit App
            </button>
            <button class="main-tab" onclick="switchMainTab('status')" role="tab" aria-selected="false">
                📊 Check Status
            </button>
            <button class="main-tab" onclick="switchMainTab('history')" role="tab" aria-selected="false">
                📋 History
            </button>
            <button class="main-tab" onclick="switchMainTab('reports')" role="tab" aria-selected="false">
                📄 Reports
            </button>
        </nav>
        
        <!-- Alert Messages -->
        <div id="alertBox" class="alert" role="alert" aria-live="polite"></div>
        
        <!-- SUBMIT TAB -->
        <div id="tab-submit" class="tab-content active" role="tabpanel">
            <div class="card">
                <h2>Submit Application</h2>
                
                <div class="sub-tabs" role="tablist">
                    <button class="sub-tab active" onclick="switchSubTab('store')" role="tab" aria-selected="true">
                        Store URL
                    </button>
                    <button class="sub-tab" onclick="switchSubTab('file')" role="tab" aria-selected="false">
                        File Upload
                    </button>
                </div>
                
                <!-- Store URL -->
                <div id="sub-store" class="sub-content active">
                    <div class="form-group">
                        <label for="storeUrl">Apple App Store / Google Play URL</label>
                        <input 
                            type="text" 
                            id="storeUrl" 
                            placeholder="https://play.google.com/store/apps/details?id=..."
                            aria-describedby="storeUrlHint"
                        >
                        <div id="storeUrlHint" class="hint">Paste the full store URL for the app you want to analyze</div>
                        <div id="storeUrlValidation" class="validation-message"></div>
                    </div>
                    
                    <div class="form-group">
                        <button class="btn btn-secondary" onclick="fillExampleUrl()" style="width: auto;">
                            ✨ Try Example URL
                        </button>
                    </div>
                </div>
                
                <!-- File Upload -->
                <div id="sub-file" class="sub-content">
                    <div class="file-upload" id="dropZone" onclick="document.getElementById('fileInput').click()" role="button" tabindex="0" aria-label="Upload file">
                        <div class="file-upload-icon">📱</div>
                        <div class="file-upload-text">
                            <strong>Click to upload</strong> or drag and drop<br>
                            IPA, APK, or AAB files (up to 2GB)
                        </div>
                        <input type="file" id="fileInput" accept=".ipa,.apk,.aab" aria-label="Select file to upload">
                    </div>
                    
                    <div class="file-preview" id="filePreview" style="display: none;">
                        <div class="file-icon" id="fileIcon">📄</div>
                        <div class="file-info">
                            <div class="file-name" id="fileName"></div>
                            <div class="file-size" id="fileSize"></div>
                        </div>
                        <button class="remove-file" onclick="removeFile()" aria-label="Remove file">×</button>
                    </div>
                </div>
                
                <!-- Progress Bar -->
                <div class="progress-container" id="progressContainer">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="progress-text">
                        <span id="progressStatus">Uploading...</span>
                        <span id="progressPercent">0%</span>
                    </div>
                </div>
                
                <button class="btn btn-primary" onclick="submitApp()" id="submitBtn" style="margin-top: var(--space-3);">
                    🚀 Submit for Analysis
                </button>
                
                <div class="loading" id="submitLoading" aria-live="polite">
                    <div class="spinner"></div>
                    <span>Submitting application...</span>
                </div>
                
                <div id="submitResult" style="margin-top: var(--space-3);"></div>
            </div>
        </div>
        
        <!-- STATUS TAB -->
        <div id="tab-status" class="tab-content" role="tabpanel">
            <div class="card">
                <h2>Check Analysis Status</h2>
                
                <div class="form-group">
                    <label for="referenceId">Reference ID</label>
                    <input 
                        type="text" 
                        id="referenceId" 
                        placeholder="e.g. c291cmNlMTIzX2luc3RhbmNlNDU2"
                        aria-describedby="referenceIdHint"
                    >
                    <div id="referenceIdHint" class="hint">Enter the Reference ID from your submission</div>
                </div>
                
                <div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">
                    <button class="btn btn-primary" onclick="checkStatus()" style="flex: 1;">
                        🔍 Check Status
                    </button>
                    <button class="btn btn-secondary" onclick="listAllAnalyses()">
                        📋 List All
                    </button>
                </div>
                
                <div class="loading" id="statusLoading" aria-live="polite">
                    <div class="spinner"></div>
                    <span>Fetching status...</span>
                </div>
                
                <div id="statusResult" style="margin-top: var(--space-3);"></div>
            </div>
        </div>
        
        <!-- HISTORY TAB -->
        <div id="tab-history" class="tab-content" role="tabpanel">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3);">
                    <h2 style="margin: 0;">Submission History</h2>
                    <button class="btn btn-secondary" onclick="clearHistory()" style="width: auto;">
                        🗑️ Clear
                    </button>
                </div>
                <div id="historyContent">
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <p>No submissions yet. Submit an app to see it here.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- REPORTS TAB -->
        <div id="tab-reports" class="tab-content" role="tabpanel">
            <div class="card">
                <h2>Generate Report</h2>
                
                <div class="form-group">
                    <label for="reportRefId">Reference ID</label>
                    <input 
                        type="text" 
                        id="reportRefId" 
                        placeholder="Reference ID from submission"
                        aria-describedby="reportRefIdHint"
                    >
                    <div id="reportRefIdHint" class="hint">Enter the Reference ID to generate a report</div>
                </div>
                
                <div class="form-group">
                    <label for="reportFormat">Report Format</label>
                    <select id="reportFormat">
                        <option value="json">📄 JSON (Full Details)</option>
                        <option value="summary">📊 Summary (Key Findings)</option>
                        <option value="csv">📈 CSV Export</option>
                    </select>
                </div>
                
                <button class="btn btn-primary" onclick="generateReport()">
                    📊 Generate Report
                </button>
                
                <div class="loading" id="reportLoading" aria-live="polite">
                    <div class="spinner"></div>
                    <span>Generating report...</span>
                </div>
                
                <div id="reportResult" style="margin-top: var(--space-3);"></div>
            </div>
        </div>
    </div>
    
    <script>
        let submissionHistory = JSON.parse(localStorage.getItem('submissionHistory') || '[]');
        let selectedFile = null;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            updateHistoryView();
            setupKeyboardShortcuts();
            setupValidation();
            
            // Show welcome for first-time users
            if (!localStorage.getItem('welcomeShown')) {
                setTimeout(() => {
                    openHelpModal();
                    localStorage.setItem('welcomeShown', 'true');
                }, 500);
            }
        });
        
        // Tab Switching
        function switchMainTab(tab) {
            document.querySelectorAll('.main-tab').forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            event.target.setAttribute('aria-selected', 'true');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        
        function switchSubTab(tab) {
            document.querySelectorAll('.sub-tab').forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            document.querySelectorAll('.sub-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            event.target.setAttribute('aria-selected', 'true');
            document.getElementById('sub-' + tab).classList.add('active');
        }
        
        // Alert handling
        function showAlert(message, type = 'info') {
            const alert = document.getElementById('alertBox');
            alert.textContent = message;
            alert.className = 'alert show ' + type;
            setTimeout(() => alert.classList.remove('show'), 5000);
        }
        
        // Toast Notifications
        function showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = 'toast ' + type;
            toast.innerHTML = `<span>${message}</span>`;
            container.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
        
        // Modal functions
        function openHelpModal() {
            document.getElementById('helpModal').classList.add('show');
            document.body.style.overflow = 'hidden';
        }
        
        function closeHelpModal() {
            document.getElementById('helpModal').classList.remove('show');
            document.body.style.overflow = '';
        }
        
        // Keyboard shortcuts
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ctrl+K or Cmd+K to open help
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    openHelpModal();
                }
                
                // Escape to close modal
                if (e.key === 'Escape') {
                    closeHelpModal();
                }
                
                // Ctrl+Enter to submit
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    submitApp();
                }
            });
        }
        
        // Real-time validation
        function setupValidation() {
            const storeUrlInput = document.getElementById('storeUrl');
            const validation = document.getElementById('storeUrlValidation');
            
            storeUrlInput.addEventListener('input', () => {
                const url = storeUrlInput.value.trim();
                
                if (url === '') {
                    validation.className = 'validation-message';
                    validation.textContent = '';
                    return;
                }
                
                try {
                    new URL(url);
                    if (url.includes('apple.com') || url.includes('google.com')) {
                        validation.className = 'validation-message success';
                        validation.textContent = '✓ Valid store URL';
                    } else {
                        validation.className = 'validation-message error';
                        validation.textContent = '⚠ Please enter a valid Apple App Store or Google Play URL';
                    }
                } catch {
                    validation.className = 'validation-message error';
                    validation.textContent = '⚠ Please enter a valid URL';
                }
            });
        }
        
        // Example URL
        function fillExampleUrl() {
            document.getElementById('storeUrl').value = 'https://play.google.com/store/apps/details?id=com.example.app';
            document.getElementById('storeUrl').dispatchEvent(new Event('input'));
            showToast('Example URL filled! You can modify it before submitting.', 'info');
        }
        
        // File Upload Handling
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'));
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'));
        });
        
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length) handleFile(files[0]);
        });
        
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) handleFile(fileInput.files[0]);
        });
        
        function handleFile(file) {
            const validExts = ['.ipa', '.apk', '.aab'];
            const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            
            if (!validExts.includes(ext)) {
                showToast('Invalid file type. Please upload .ipa, .apk, or .aab files.', 'error');
                return;
            }
            
            selectedFile = file;
            
            // Show file preview
            const icons = { '.ipa': '🍎', '.apk': '🤖', '.aab': '📦' };
            document.getElementById('fileIcon').textContent = icons[ext] || '📄';
            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileSize').textContent = formatFileSize(file.size);
            document.getElementById('filePreview').style.display = 'flex';
            document.getElementById('dropZone').style.display = 'none';
            
            showToast(`File selected: ${file.name}`, 'success');
        }
        
        function removeFile() {
            selectedFile = null;
            document.getElementById('fileInput').value = '';
            document.getElementById('filePreview').style.display = 'none';
            document.getElementById('dropZone').style.display = 'block';
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        // API Functions
        async function submitApp() {
            const storeUrl = document.getElementById('storeUrl').value.trim();
            const isStoreSubmit = document.getElementById('sub-store').classList.contains('active');
            
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('submitLoading');
            const progressContainer = document.getElementById('progressContainer');
            
            submitBtn.disabled = true;
            loading.classList.add('show');
            
            // Simulate progress for better UX
            if (!isStoreSubmit) {
                progressContainer.classList.add('show');
                simulateProgress();
            }
            
            try {
                let result;
                if (isStoreSubmit) {
                    if (!storeUrl) {
                        throw new Error('Please enter a Store URL');
                    }
                    
                    const res = await fetch('/api/submit/store', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ store_url: storeUrl })
                    });
                    result = await res.json();
                    if (!res.ok) throw new Error(result.error || 'Submission failed');
                } else {
                    if (!selectedFile) {
                        throw new Error('Please select a file to upload');
                    }
                    
                    const formData = new FormData();
                    formData.append('file', selectedFile);
                    
                    const res = await fetch('/api/submit/file', {
                        method: 'POST',
                        body: formData
                    });
                    result = await res.json();
                    if (!res.ok) throw new Error(result.error || 'Submission failed');
                }
                
                showToast('Submission successful!', 'success');
                
                const refId = result.reference_id || result.referenceId;
                document.getElementById('submitResult').innerHTML = `
                    <div class="ref-id-display">
                        <strong>📌 Reference ID:</strong>
                        <code>${refId}</code>
                        <button class="copy-btn" onclick="copyToClipboard('${refId}')" aria-label="Copy reference ID">📋 Copy</button>
                    </div>
                    <div class="response-box" style="margin-top: var(--space-2);">${formatJson(result)}</div>
                `;
                
                addToHistory({
                    reference_id: refId,
                    type: isStoreSubmit ? 'Store URL' : 'File Upload',
                    source: isStoreSubmit ? storeUrl : selectedFile.name,
                    timestamp: new Date().toISOString(),
                    status: 'pending'
                });
                
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                submitBtn.disabled = false;
                loading.classList.remove('show');
                progressContainer.classList.remove('show');
            }
        }
        
        function simulateProgress() {
            const fill = document.getElementById('progressFill');
            const percent = document.getElementById('progressPercent');
            const status = document.getElementById('progressStatus');
            let progress = 0;
            
            const interval = setInterval(() => {
                if (progress >= 90) {
                    clearInterval(interval);
                    return;
                }
                progress += Math.random() * 15;
                if (progress > 90) progress = 90;
                fill.style.width = progress + '%';
                percent.textContent = Math.round(progress) + '%';
                status.textContent = progress < 50 ? 'Uploading...' : 'Processing...';
            }, 300);
        }
        
        async function checkStatus() {
            const refId = document.getElementById('referenceId').value.trim();
            
            if (!refId) {
                showToast('Please enter a Reference ID', 'error');
                return;
            }
            
            const loading = document.getElementById('statusLoading');
            loading.classList.add('show');
            
            try {
                const res = await fetch('/api/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reference_id: refId })
                });
                const result = await res.json();
                
                document.getElementById('statusResult').innerHTML = `
                    <div class="response-box">${formatJson(result)}</div>
                `;
                
                showToast('Status retrieved successfully', 'success');
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                loading.classList.remove('show');
            }
        }
        
        async function listAllAnalyses() {
            const loading = document.getElementById('statusLoading');
            loading.classList.add('show');
            
            try {
                const res = await fetch('/api/analyses', { method: 'POST' });
                const result = await res.json();
                
                document.getElementById('statusResult').innerHTML = `
                    <div class="response-box">${formatJson(result)}</div>
                `;
                
                showToast('All analyses retrieved', 'success');
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                loading.classList.remove('show');
            }
        }
        
        async function generateReport() {
            const refId = document.getElementById('reportRefId').value.trim();
            const format = document.getElementById('reportFormat').value;
            
            if (!refId) {
                showToast('Please enter a Reference ID', 'error');
                return;
            }
            
            const loading = document.getElementById('reportLoading');
            loading.classList.add('show');
            
            try {
                const res = await fetch('/api/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reference_id: refId, format })
                });
                const result = await res.json();
                
                let reportHtml = '';
                
                if (format === 'summary') {
                    reportHtml = generateSummaryView(result);
                } else if (format === 'csv') {
                    const csvData = generateCSV(result);
                    reportHtml = `
                        <button class="btn btn-secondary" onclick="downloadCSV()" style="width: auto;">📥 Download CSV</button>
                        <div class="response-box" style="margin-top: var(--space-2);">${csvData}</div>
                    `;
                    window.csvData = csvData;
                } else {
                    reportHtml = `<div class="response-box">${formatJson(result)}</div>`;
                }
                
                document.getElementById('reportResult').innerHTML = reportHtml;
                showToast('Report generated successfully', 'success');
            } catch (err) {
                showToast(err.message, 'error');
            } finally {
                loading.classList.remove('show');
            }
        }
        
        // Utility Functions
        function formatJson(obj) {
            const json = JSON.stringify(obj, null, 2);
            return json
                .replace(/(".*?"):/g, '<span class="key">$1</span>:')
                .replace(/: (".*?")/g, ': <span class="string">$1</span>')
                .replace(/: (\\d+)/g, ': <span class="number">$1</span>')
                .replace(/: (true|false)/g, ': <span class="boolean">$1</span>');
        }
        
        function copyToClipboard(text) {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('Copied to clipboard!', 'success');
                }).catch(() => {
                    fallbackCopy(text);
                });
            } else {
                fallbackCopy(text);
            }
        }
        
        function fallbackCopy(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                showToast('Copied to clipboard!', 'success');
            } catch (e) {
                showToast('Copy failed - please select and copy manually', 'error');
            }
            document.body.removeChild(textarea);
        }
        
        function addToHistory(item) {
            submissionHistory.unshift(item);
            localStorage.setItem('submissionHistory', JSON.stringify(submissionHistory));
            updateHistoryView();
        }
        
        function updateHistoryView() {
            if (submissionHistory.length === 0) {
                document.getElementById('historyContent').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <p>No submissions yet. Submit an app to see it here.</p>
                    </div>
                `;
                return;
            }
            
            let html = `
                <table class="history-table">
                    <thead>
                        <tr>
                            <th style="width: 140px;">Reference ID</th>
                            <th style="width: 80px;">Type</th>
                            <th>Source</th>
                            <th style="width: 100px;">Time</th>
                            <th style="width: 80px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            submissionHistory.forEach(item => {
                const shortRefId = item.reference_id.length > 20 
                    ? item.reference_id.substring(0, 20) + '...' 
                    : item.reference_id;
                const shortSource = item.source.length > 30 
                    ? item.source.substring(0, 30) + '...' 
                    : item.source;
                html += `
                    <tr>
                        <td><code title="${item.reference_id}" style="cursor: pointer; font-size: 11px;" onclick="copyToClipboard('${item.reference_id}')" aria-label="Copy reference ID">${shortRefId}</code></td>
                        <td>${item.type}</td>
                        <td title="${item.source}" style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${shortSource}</td>
                        <td style="font-size: 12px;">${new Date(item.timestamp).toLocaleTimeString()}</td>
                        <td><span class="status-badge status-${item.status}">${item.status}</span></td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            document.getElementById('historyContent').innerHTML = html;
        }
        
        function clearHistory() {
            if (confirm('Are you sure you want to clear all history?')) {
                submissionHistory = [];
                localStorage.removeItem('submissionHistory');
                updateHistoryView();
                showToast('History cleared', 'info');
            }
        }
        
        function generateSummaryView(data) {
            return `
                <div class="report-section">
                    <div class="report-header" onclick="toggleSection(this)">
                        <span>Application Info</span>
                        <span>▼</span>
                    </div>
                    <div class="report-content show">
                        <pre>${formatJson(data)}</pre>
                    </div>
                </div>
            `;
        }
        
        function toggleSection(header) {
            const content = header.nextElementSibling;
            content.classList.toggle('show');
        }
        
        function generateCSV(data) {
            const flatten = (obj, prefix = '') => {
                let result = {};
                for (let key in obj) {
                    const newKey = prefix ? `${prefix}.${key}` : key;
                    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                        Object.assign(result, flatten(obj[key], newKey));
                    } else {
                        result[newKey] = obj[key];
                    }
                }
                return result;
            };
            
            const flat = flatten(data);
            const headers = Object.keys(flat).join(',');
            const values = Object.values(flat).map(v => `"${v}"`).join(',');
            return headers + '\\n' + values;
        }
        
        function downloadCSV() {
            const blob = new Blob([window.csvData], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'lookout_report.csv';
            a.click();
            URL.revokeObjectURL(url);
            showToast('CSV downloaded', 'success');
        }
    </script>
</body>
</html>
'''


def is_token_expired():
    """Check if the cached token is expired or about to expire"""
    global token_expiry
    if token_expiry is None:
        return True
    return datetime.now().timestamp() >= token_expiry


def invalidate_token():
    """Invalidate the cached token (e.g., after a 401 response)"""
    global cached_token, token_expiry
    # print("[DEBUG] Invalidating cached token")
    cached_token = None
    token_expiry = None


def get_token(force_refresh=False):
    """Get or generate OAuth token, with automatic refresh on expiry"""
    global cached_token, token_expiry
    
    # Check if we need to refresh
    if force_refresh or cached_token is None or is_token_expired():
        if cached_token is not None:
            # print("[DEBUG] Token expired or refresh forced, re-authenticating...")
            pass
        
        if BEARER_TOKEN:
            cached_token = BEARER_TOKEN
            token_expiry = None  # Manual tokens don't have expiry tracking
            return cached_token
        if APP_KEY:
            cached_token = get_oauth_token(API_HOST, APP_KEY)
            return cached_token
        raise Exception("No authentication configured. Please set APP_KEY or BEARER_TOKEN in config.py")
    
    return cached_token


@app.route('/')
def index():
    config_valid = bool(API_HOST and (APP_KEY or BEARER_TOKEN))
    return render_template_string(HTML_TEMPLATE, config_valid=config_valid, api_host=API_HOST)


@app.route('/api/submit/store', methods=['POST'])
def api_submit_store():
    """Submit app via store URL with automatic token refresh on 401"""
    try:
        data = request.json
        token = get_token()
        status_code, result = submit_store_url(API_HOST, token, data['store_url'])
        
        # Retry with fresh token on 401
        if status_code == 401:
            # print("[DEBUG] Got 401, refreshing token and retrying...")
            invalidate_token()
            token = get_token(force_refresh=True)
            status_code, result = submit_store_url(API_HOST, token, data['store_url'])
        
        if status_code >= 200 and status_code < 300:
            return jsonify(result)
        else:
            return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/submit/file', methods=['POST'])
def api_submit_file():
    """Submit app via file upload with automatic token refresh on 401"""
    try:
        file = request.files['file']
        
        # Debug logging (disable in production)
        # print(f"[DEBUG] Uploading file: {file.filename}")
        # print(f"[DEBUG] API Host: {API_HOST}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            temp_path = tmp.name
            # print(f"[DEBUG] Temp file saved: {temp_path}, size: {os.path.getsize(temp_path)} bytes")
        
        try:
            # First attempt
            token = get_token()
            # print(f"[DEBUG] Token (first 50 chars): {token[:50]}...")
            status_code, result = submit_file(API_HOST, token, temp_path, file.filename)
            # print(f"[DEBUG] API Response: {status_code} - {result}")
            
            # Retry with fresh token on 401
            if status_code == 401:
                # print("[DEBUG] Got 401, refreshing token and retrying...")
                invalidate_token()
                token = get_token(force_refresh=True)
                # print(f"[DEBUG] New token (first 50 chars): {token[:50]}...")
                status_code, result = submit_file(API_HOST, token, temp_path, file.filename)
                # print(f"[DEBUG] Retry API Response: {status_code} - {result}")
            
            if status_code >= 200 and status_code < 300:
                return jsonify(result)
            else:
                return jsonify(result), status_code
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        import traceback
        print(f"[ERROR] File upload failed: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['POST'])
def api_check_status():
    """Check analysis status for a reference ID"""
    try:
        data = request.json
        token = get_token()
        status_code, result = get_analysis_status(API_HOST, token, data['reference_id'])
        
        if status_code == 401:
            invalidate_token()
            token = get_token(force_refresh=True)
            status_code, result = get_analysis_status(API_HOST, token, data['reference_id'])
        
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyses', methods=['POST'])
def api_list_analyses():
    """List all analyses"""
    try:
        token = get_token()
        status_code, result = get_all_analyses(API_HOST, token)
        
        if status_code == 401:
            invalidate_token()
            token = get_token(force_refresh=True)
            status_code, result = get_all_analyses(API_HOST, token)
        
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report', methods=['POST'])
def api_generate_report():
    """Generate report for a reference ID"""
    try:
        data = request.json
        token = get_token()
        status_code, result = get_analysis_status(API_HOST, token, data['reference_id'])
        
        if status_code == 401:
            invalidate_token()
            token = get_token(force_refresh=True)
            status_code, result = get_analysis_status(API_HOST, token, data['reference_id'])
        
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = 5001
    print("\n" + "="*50)
    print("  Lookout App Submission Tool - Enhanced Edition")
    print("="*50)
    print("\n  ✨ New Features:")
    print("     - Improved UI/UX with modern design")
    print("     - Toast notifications")
    print("     - Progress indicators")
    print("     - Keyboard shortcuts (Ctrl+K for help)")
    print("     - LocalStorage history persistence")
    print("     - Better mobile responsiveness")
    print("     - Accessibility improvements")
    print(f"\n  Open in browser: http://localhost:{port}\n")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=port)
