import os
import shutil
import zipfile
import subprocess
import json
import re
from PIL import Image
import cssmin
import minify_html
from bs4 import BeautifulSoup
from flask import current_app
from . import socketio

# --- HELPER FUNCTIONS ---

def send_status(sid, message, status_type='info'):
    """Sends a status update to a specific client via WebSocket."""
    socketio.emit('status_update', {'message': message, 'type': status_type}, room=sid)
    socketio.sleep(0.01) # Give the server a moment to send the message

def cleanup(path):
    """Safely removes a file or directory."""
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.isfile(path) and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

def _run_command(cmd, cwd, timeout_seconds=300, check_exit_code=True):
    """
    Executes a shell command and returns the result.
    check_exit_code=False is crucial for tools that use non-zero exits to report findings.
    """
    return subprocess.run(
        cmd, 
        cwd=cwd, 
        shell=True, 
        check=check_exit_code, 
        capture_output=True, 
        text=True, 
        timeout=timeout_seconds
    )

def _build_file_tree(directory):
    """Builds a nested dictionary representing a file tree."""
    tree = []
    for item in sorted(os.listdir(directory)):
        path = os.path.join(directory, item)
        node = {'name': item}
        if os.path.isdir(path):
            node['type'] = 'directory'
            node['children'] = _build_file_tree(path)
        else:
            node['type'] = 'file'
        tree.append(node)
    return tree

# --- INDIVIDUAL PROCESSING MODULES (Largely unchanged, minor robustness improvements) ---
def _optimize_image(in_path, out_path):
    with Image.open(in_path) as img:
        img_data = list(img.getdata())
        stripped_img = Image.new(img.mode, img.size)
        stripped_img.putdata(img_data)
        stripped_img.save(out_path, optimize=True, quality=80)
    return "Optimized"

def _process_js(in_path, out_path, options):
    info, current_input, tmp_path = "", in_path, None
    if options.get('obfuscate_js', 'none') != 'none':
        tmp_path = out_path + ".tmp.js"
        info = f"Obfuscated ({options['obfuscate_js']})"
        cmd = ['javascript-obfuscator', current_input, '--output', tmp_path, '--compact', 'true']
        if options['obfuscate_js'] == 'strong':
            cmd.extend(['--string-array', 'true', '--transform-object-keys', 'true'])
        try:
            _run_command(cmd, cwd=os.path.dirname(in_path))
            current_input = tmp_path
        except subprocess.TimeoutExpired:
            raise Exception("JS Obfuscation timed out.")
        except Exception as e:
            print(f"Obfuscation failed: {e}")
    try:
        _run_command(['terser', current_input, '-o', out_path, '--compress', '--mangle'], cwd=os.path.dirname(in_path))
        info += " & Minified"
    except subprocess.TimeoutExpired:
        raise Exception("JS Minification (Terser) timed out.")
    finally:
        if tmp_path:
            cleanup(tmp_path)
    return info.strip(" &")

def _process_svg(in_path, out_path):
    try:
        _run_command(['svgo', in_path, '-o', out_path], cwd=os.path.dirname(in_path), timeout_seconds=120)
        return "SVG Optimized"
    except subprocess.TimeoutExpired:
        raise Exception("SVG Optimization timed out.")

def _harden_html(in_path, out_path, options):
    with open(in_path, 'r', encoding='utf-8') as f:
        code = f.read()
    info = ""
    if options.get('add_csp'):
        soup = BeautifulSoup(code, 'html.parser')
        # Remove any existing CSP meta tags to avoid conflicts
        for tag in soup.find_all('meta', attrs={'http-equiv': 'Content-Security-Policy'}):
            tag.decompose()
        csp_tag = soup.new_tag('meta')
        csp_tag['http-equiv'] = 'Content-Security-Policy'
        # A reasonably strict but common CSP
        csp_tag['content'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:;"
        if soup.head:
            soup.head.insert(0, csp_tag)
        code = str(soup)
        info = "Hardened (CSP) & "
    minified = minify_html.minify(code, minify_js=True, minify_css=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(minified)
    return info + "Minified"

def _purge_css(processed_dir):
    content_files = [os.path.join(r, f) for r, _, fs in os.walk(processed_dir) for f in fs if f.endswith(('.html', '.js'))]
    css_files = [os.path.join(r, f) for r, _, fs in os.walk(processed_dir) for f in fs if f.endswith('.css')]
    if css_files and content_files:
        try:
            # Safelist classes that are added dynamically by JS
            cmd = ['purgecss', '--css'] + css_files + ['--content'] + content_files + ['--output', processed_dir, '--safelist', 'drag-over']
            _run_command(cmd, cwd=processed_dir, timeout_seconds=180)
        except subprocess.TimeoutExpired:
            raise Exception("PurgeCSS timed out.")
        except Exception as e:
            print(f"PurgeCSS failed: {e}")

def _minify_css(file_path):
    with open(file_path, 'r+', encoding='utf-8') as f:
        minified = cssmin.cssmin(f.read())
        f.seek(0)
        f.write(minified)
        f.truncate()

def generate_critical_css(processed_dir, sid):
    html_files = [os.path.join(r, f) for r, _, fs in os.walk(processed_dir) for f in fs if f.endswith('.html')]
    if not html_files:
        return
    send_status(sid, "Generating Critical CSS (Pro feature)...")
    try:
        for html_path in html_files:
            _run_command(['critical', html_path, '--inline', '--base', processed_dir, '-w', '1200', '-h', '900', '--extract'], cwd=processed_dir)
        send_status(sid, "Critical CSS has been inlined.", 'success')
    except subprocess.TimeoutExpired:
        send_status(sid, "Critical CSS generation timed out.", 'error')
    except Exception as e:
        send_status(sid, f"Critical CSS generation failed: {e}", 'error')


# --- HIGH-LEVEL TOOL FUNCTIONS ---

def do_frontend_optimization(unpacked_path, processed_path, options, sid):
    send_status(sid, "Optimizing assets...")
    reports_dict = {}
    for root, _, files in os.walk(unpacked_path):
        for filename in files:
            in_path = os.path.join(root, filename)
            rel_path = os.path.relpath(in_path, unpacked_path)
            out_path = os.path.join(processed_path, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            report = {'name': filename, 'path': rel_path.replace('\\', '/'), 'original_size': os.path.getsize(in_path), 'status': 'error', 'message': 'Unknown error.'}
            try:
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                if ext in {'png', 'jpg', 'jpeg'}:
                    report['message'], report['status'] = _optimize_image(in_path, out_path), 'success'
                elif ext == 'svg':
                    report['message'], report['status'] = _process_svg(in_path, out_path), 'success'
                elif ext == 'js':
                    report['message'], report['status'] = _process_js(in_path, out_path, options), 'success'
                elif ext == 'html':
                    report['message'], report['status'] = _harden_html(in_path, out_path, options), 'success'
                elif ext == 'css':
                    shutil.copy2(in_path, out_path)
                    report['message'], report['status'] = 'Copied, pending final processing.', 'info'
                else:
                    shutil.copy2(in_path, out_path)
                    report['message'], report['status'] = 'Copied as-is.', 'warning'
                report['new_size'] = os.path.getsize(out_path)
            except Exception as e:
                report['message'] = str(e)
                report['new_size'] = report['original_size']
                if not os.path.exists(out_path): shutil.copy2(in_path, out_path)
            reports_dict[rel_path] = report

    if options.get('purge_css'):
        send_status(sid, "Purging unused CSS...")
        _purge_css(processed_path)
    
    send_status(sid, "Minifying all CSS...")
    for path, report in reports_dict.items():
        if path.endswith('.css'):
            css_file_path = os.path.join(processed_path, path)
            _minify_css(css_file_path)
            report['new_size'] = os.path.getsize(css_file_path)
            report['message'] = 'Purged & Minified' if options.get('purge_css') else 'Minified'
            report['status'] = 'success'
            
    send_status(sid, "File processing complete.", 'success')
    return list(reports_dict.values())

def do_backend_analysis(unpacked_path, sid):
    if not any(f.endswith('.py') for r, _, fs in os.walk(unpacked_path) for f in fs):
        send_status(sid, "This tool currently only supports Python projects for backend analysis.", 'error')
        return

    send_status(sid, "Python project detected. Running linters...")
    tools = {'Flake8 (Code Style)': ['flake8', '.'], 'Vulture (Dead Code)': ['vulture', '.']}
    for name, cmd in tools.items():
        try:
            send_status(sid, f"----- Running {name} -----", 'info')
            result = _run_command(cmd, cwd=unpacked_path, timeout_seconds=120, check_exit_code=False)
            if result.stdout:
                for line in result.stdout.splitlines():
                    send_status(sid, line.strip(), 'warning')
            elif result.returncode != 0:
                raise Exception(result.stderr or f"{name} failed with exit code {result.returncode}")
            else:
                send_status(sid, f"{name} found no issues.", 'success')
        except subprocess.TimeoutExpired:
            send_status(sid, f"{name} analysis timed out.", 'error')
        except Exception as e:
            send_status(sid, f"Failed to run {name}. Is it installed? Error: {e}", 'error')

def do_security_scan(unpacked_path, sid, plan):
    findings = 0
    pip_cache_dir = os.path.join(current_app.config['CACHE_FOLDER'], 'pip')
    
    if os.path.exists(os.path.join(unpacked_path, 'requirements.txt')):
        send_status(sid, "--- Scanning Python Dependencies ---", 'info')
        try:
            req_path = os.path.join(unpacked_path, 'requirements.txt')
            send_status(sid, "Auditing requirements.txt with pip-audit...")
            cmd = ['pip-audit', '-r', req_path, '--cache-dir', pip_cache_dir]
            result = _run_command(cmd, cwd=unpacked_path, timeout_seconds=180, check_exit_code=False)

            if "vulnerabilities found" in result.stdout:
                for line in result.stdout.splitlines():
                    if line.strip(): send_status(sid, line.strip(), 'error'); findings += 1
            elif result.returncode != 0:
                 raise Exception(result.stderr or f"pip-audit failed with exit code {result.returncode}")
            else:
                send_status(sid, "No known vulnerabilities found in Python dependencies.", 'success')
        except subprocess.TimeoutExpired:
            send_status(sid, "Python dependency scan timed out.", 'error')
        except Exception as e:
            send_status(sid, f"Failed to run pip-audit: {e}", 'error')

    if plan in ['premium', 'pro'] and os.path.exists(os.path.join(unpacked_path, 'package-lock.json')):
        send_status(sid, "--- Scanning Node.js Dependencies (Premium) ---", 'info')
        try:
            send_status(sid, "Running 'npm install' to prepare for audit (max 5 mins)...")
            _run_command(['npm', 'install'], cwd=unpacked_path, timeout_seconds=300)
            send_status(sid, "Auditing with 'npm audit' (max 2 mins)...")
            result = _run_command(['npm', 'audit', '--json'], cwd=unpacked_path, timeout_seconds=120, check_exit_code=False)
            
            if result.stdout:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get('vulnerabilities', {})
                if vulnerabilities:
                    for name, details in vulnerabilities.items():
                        send_status(sid, f"VULNERABILITY: {name} ({details['severity']}) in {details.get('via', ['N/A'])[0]}", 'error'); findings += 1
                else:
                    send_status(sid, "No known vulnerabilities found in Node.js dependencies.", 'success')
            elif result.returncode != 0:
                raise Exception(result.stderr or "npm audit failed without providing a reason.")
            else:
                send_status(sid, "No known vulnerabilities found in Node.js dependencies.", 'success')
        except subprocess.TimeoutExpired:
            send_status(sid, "Node.js dependency installation (npm install) timed out.", 'error')
        except Exception as e:
            send_status(sid, f"Failed to run npm audit: {e}", 'error')

    send_status(sid, "--- Scanning Source Code for Secrets & Debug Flags ---", 'info')
    secret_pattern = re.compile(r'(API_KEY|SECRET|PASSWORD|TOKEN)\s*[:=]\s*["\']([A-Za-z0-9_\\-]{16,})["\']', re.IGNORECASE)
    secrets_found, debug_found = 0, 0
    for root, _, files in os.walk(unpacked_path):
        for filename in files:
            if filename.endswith(('.py', '.js', '.json', '.env', '.yml', '.yaml', '.conf', '.cfg', '.ini')):
                try:
                    rel_file_path = os.path.relpath(os.path.join(root, filename), unpacked_path)
                    with open(os.path.join(root, filename), 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if "DEBUG" in line.upper() and "TRUE" in line.upper().replace(" ", ""):
                                send_status(sid, f"HIGH RISK: Potential debug mode in '{rel_file_path}' on line {i}.", 'error'); findings += 1; debug_found += 1
                            if secret_pattern.search(line):
                                send_status(sid, f"HIGH RISK: Potential hardcoded secret in '{rel_file_path}' on line {i}.", 'error'); findings += 1; secrets_found += 1
                except Exception:
                    pass
    if secrets_found == 0:
        send_status(sid, "No obvious hardcoded secrets found.", 'success')
    if debug_found == 0:
        send_status(sid, "No obvious debug flags found enabled.", 'success')

    if findings == 0:
        send_status(sid, "Scan complete. No obvious high-risk issues found.", 'success')
    else:
        send_status(sid, f"Scan complete. Found {findings} potential issue(s). Review log carefully.", 'warning')