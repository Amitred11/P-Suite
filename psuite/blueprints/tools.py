# psuite/blueprints/tools.py
import os
import uuid
import zipfile
import shutil
from flask import (Blueprint, render_template, request, jsonify, 
                   send_from_directory, current_app)
from flask_login import login_required, current_user
from psuite import socketio, db
from psuite.processing import (do_frontend_optimization, do_backend_analysis, 
                               do_security_scan, generate_critical_css,
                               send_status, cleanup)

tools_bp = Blueprint('tools', __name__, template_folder='../templates')

# --- TOOL PAGES ---
@tools_bp.route('/frontend-optimizer')
@login_required
def frontend_optimizer(): return render_template('frontend_optimizer.html')

@tools_bp.route('/backend-analyzer')
@login_required
def backend_analyzer(): return render_template('backend_analyzer.html')

@tools_bp.route('/security-scanner')
@login_required
def security_scanner(): return render_template('security_scanner.html')

# --- FILE HANDLING API ---
@tools_bp.route('/upload', methods=['POST'])
@login_required
def upload_files():
    # FIXED: The form sends a single file named 'file', not 'files[]'
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400
    if not file.filename.lower().endswith('.zip'):
        return jsonify({'error': 'Invalid file type. Please upload a ZIP file.'}), 400

    session_id = str(uuid.uuid4())
    unpacked_path = os.path.join(current_app.config['UNPACKED_FOLDER'], session_id)
    original_zip_path = os.path.join(current_app.config['ORIGINALS_FOLDER'], f"{session_id}.zip")
    
    os.makedirs(unpacked_path, exist_ok=True)
    os.makedirs(os.path.dirname(original_zip_path), exist_ok=True)
    
    try:
        file.save(original_zip_path)
        with zipfile.ZipFile(original_zip_path, 'r') as zf: zf.extractall(unpacked_path)
    except zipfile.BadZipFile:
        cleanup(unpacked_path); cleanup(original_zip_path)
        return jsonify({'error': 'The uploaded file is not a valid ZIP archive.'}), 400
    except Exception as e:
        cleanup(unpacked_path); cleanup(original_zip_path)
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500
        
    return jsonify({'session_id': session_id})


@tools_bp.route('/download-all/<filename>')
@login_required
def download_all_as_zip(filename):
    # ... (code is identical to the fixed app.py)
    if '..' in filename or filename.startswith('/'): return "Invalid filename", 400
    directory = current_app.config['PROCESSED_FOLDER']
    zip_path = os.path.join(directory, filename)
    if not os.path.exists(zip_path):
        return "File not found or has already been downloaded and cleaned up.", 404
    response = send_from_directory(directory, filename, as_attachment=True)
    @response.call_on_close
    def cleanup_zip():
        try: os.remove(zip_path)
        except Exception as e: print(f"Error cleaning up zip file {zip_path}: {e}")
    return response


# --- WEBSOCKET HANDLERS ---
# ... (code is identical to the fixed app.py, but now uses 'socketio' directly)
@socketio.on('run_frontend_optimization')
@login_required
def handle_frontend_optimization(data):
    if current_user.credits < 1: socketio.emit('processing_error', {'message': 'Insufficient credits.'}, room=request.sid); return
    current_user.credits -= 1; db.session.commit()
    
    sid, session_id, options = request.sid, data['session_id'], data.get('options', {})
    unpacked_path = os.path.join(current_app.config['UNPACKED_FOLDER'], session_id)
    processed_path = os.path.join(current_app.config['PROCESSED_FOLDER'], session_id)
    final_zip_name = f"optimized_{session_id}.zip"
    final_zip_path_base = os.path.join(current_app.config['PROCESSED_FOLDER'], f"optimized_{session_id}")
    
    try:
        file_reports = do_frontend_optimization(unpacked_path, processed_path, options, sid)
        if current_user.plan == 'pro' and options.get('generate_critical_css'):
            generate_critical_css(processed_path, sid)
        send_status(sid, "Finalizing and creating ZIP archive...", 'info')
        shutil.make_archive(final_zip_path_base, 'zip', processed_path)
        send_status(sid, "Archive created successfully.", 'success')
        socketio.emit('processing_complete', {'final_zip_name': final_zip_name, 'file_tree': file_reports}, room=sid)
    except Exception as e:
        send_status(sid, f"A critical error occurred: {e}", 'error')
        socketio.emit('processing_error', {'message': str(e)}, room=sid)
    finally:
        cleanup(unpacked_path); cleanup(processed_path)
        socketio.emit('credits_updated', {'credits': current_user.credits}, room=sid)


@socketio.on('run_backend_analysis')
@login_required
def handle_backend_analysis(data):
    if current_user.credits < 1: socketio.emit('processing_error', {'message': 'Insufficient credits.'}, room=request.sid); return
    current_user.credits -= 1; db.session.commit()
    sid, session_id = request.sid, data['session_id']
    unpacked_path = os.path.join(current_app.config['UNPACKED_FOLDER'], session_id)
    try:
        do_backend_analysis(unpacked_path, sid)
        socketio.emit('analysis_complete', room=sid)
    except Exception as e:
        send_status(sid, f"A critical error occurred: {e}", 'error')
    finally:
        cleanup(unpacked_path)
        socketio.emit('credits_updated', {'credits': current_user.credits}, room=sid)

# ... handle_security_scan follows the same pattern ...