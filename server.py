#!/usr/bin/env python3
"""
Bot Dashboard Server
Manages execution of multiple bots via a web interface.
"""

import subprocess
import threading
import uuid
import os
import signal
import sys
from datetime import datetime
from flask import Flask, jsonify, request, make_response, abort, redirect
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# --- 🔐 SEGURIDAD HÍBRIDA: ARCHIVO O KEY DIRECTA ---" 
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN")

@app.before_request
def check_device_auth():
    if request.path.startswith('/activate/') or request.path.startswith('/static/') or request.path == '/api/auto-run-all':
        return None
    
    # Bypass para Google Cloud Scheduler
    if request.headers.get('X-CloudScheduler') == 'true':
        return None
    
    auth_cookie = request.cookies.get('device_auth')
    if auth_cookie != DEVICE_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

@app.route('/activate/<key>')
def activate_device(key):
    if key == DEVICE_TOKEN:
        resp = make_response(redirect('/'))
        resp.set_cookie('device_auth', DEVICE_TOKEN, max_age=31536000, httponly=True, samesite='Strict', secure=True)
        return resp
    return "<h1>❌ Llave no válida</h1>", 403

# --- 🤖 CONFIGURACIÓN DE BOTS ---
BOTS = {
    "shopify": {"id": "shopify", "name": "Shopify Bot", "path": "bots/BotComprasShopify-main", "color": "#96bf48", "icon": "🛍️"},
    "prestashop8": {"id": "prestashop8", "name": "PrestaShop 8 Bot", "path": "bots/Prestashop_8_bot", "color": "#df0067", "icon": "🏪"},
    "prestashop17": {"id": "prestashop17", "name": "PrestaShop 1.7 Bot", "path": "bots/Prestashop1.7_bot", "color": "#e97c0d", "icon": "🏬"},
    "woocommerce": {"id": "woocommerce", "name": "WooCommerce Bot", "path": "bots/woocommerce_bot", "color": "#7f54b3", "icon": "🛒"}
}

runs = {}
processes = {}

def stream_output(run_id, proc):
    try:
        for line in iter(proc.stdout.readline, b''):
            decoded = line.decode('utf-8', errors='replace')
            runs[run_id]['logs'].append({'time': datetime.now().strftime('%H:%M:%S'), 'text': decoded.rstrip(), 'type': 'stdout'})
        proc.wait()
        runs[run_id]['status'] = 'completed' if proc.returncode == 0 else 'failed'
        runs[run_id]['ended_at'] = datetime.now().isoformat()
    except Exception as e:
        runs[run_id]['status'] = 'failed'
    finally:
        if run_id in processes: del processes[run_id]

def execute_bot_logic(bot_id, orders=10, headless=True, extra_params=None):
    """Lógica centralizada para lanzar bots"""
    if bot_id not in BOTS: return None, "Bot no encontrado"
    
    bot = BOTS[bot_id]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bot_path = os.path.join(base_dir, bot['path'])
    main_py = os.path.join(bot_path, 'main.py')

    if not os.path.exists(main_py): return None, f"main.py no existe en {bot_path}"

    cmd = [sys.executable, 'main.py', '--orders', str(orders)]
    if headless: cmd.append('--headless')
    if extra_params:
        for k, v in extra_params.items():
            if v: cmd.extend([f'--{k}', str(v)])

    run_id = str(uuid.uuid4())[:8]
    runs[run_id] = {
        'id': run_id, 'bot_id': bot_id, 'bot_name': bot['name'], 'bot_icon': bot['icon'],
        'bot_color': bot['color'], 'status': 'running', 'started_at': datetime.now().isoformat(),
        'logs': [], 'orders': orders
    }

    try:
        proc = subprocess.Popen(cmd, cwd=bot_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
        processes[run_id] = proc
        threading.Thread(target=stream_output, args=(run_id, proc), daemon=True).start()
        return run_id, None
    except Exception as e:
        return None, str(e)

# --- 🚀 RUTAS DE API ---

@app.route('/api/auto-run-all', methods=['POST', 'GET'])
def auto_run_all():
    """Ruta para el Cloud Scheduler (Programación automática)"""
    is_scheduler = request.headers.get('X-CloudScheduler') == 'true'
    if not is_scheduler and request.cookies.get('device_auth') != DEVICE_TOKEN:
        abort(403)

    launched = []
    for b_id in BOTS.keys():
        run_id, error = execute_bot_logic(b_id, orders=10, headless=True)
        launched.append({"bot": b_id, "run_id": run_id, "error": error})
    
    return jsonify({"status": "Automation Triggered", "details": launched})

@app.route('/api/run', methods=['POST'])
def start_run():
    data = request.json
    run_id, error = execute_bot_logic(
        data.get('bot_id'), 
        orders=data.get('orders', 10), 
        headless=data.get('headless', False),
        extra_params=data.get('extra_params', {})
    )
    if error: return jsonify({'error': error}), 400
    return jsonify({'run_id': run_id, 'status': 'started'})

@app.route('/api/bots', methods=['GET'])
def get_bots():
    bot_list = []
    for bot_id, bot in BOTS.items():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        available = os.path.exists(os.path.join(base_dir, bot['path'], 'main.py'))
        bot_list.append({**bot, 'available': available})
    return jsonify(bot_list)

@app.route('/api/runs', methods=['GET'])
def get_runs(): return jsonify(list(runs.values()))

@app.route('/api/runs/<run_id>', methods=['GET'])
def get_run(run_id):
    if run_id not in runs: return jsonify({'error': 'Not found'}), 404
    return jsonify(runs[run_id])

@app.route('/api/runs/<run_id>/logs', methods=['GET'])
def get_logs(run_id):
    if run_id not in runs: return jsonify({'error': 'Not found'}), 404
    try:
        offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError):
        offset = 0
    return jsonify({'logs': runs[run_id]['logs'][offset:], 'status': runs[run_id]['status']})

@app.route('/api/run/<run_id>/stop', methods=['POST'])
def stop_run(run_id):
    if run_id in processes:
        processes[run_id].terminate()
        return jsonify({'status': 'stopped'})
    return jsonify({'error': 'Not running'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)