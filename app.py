from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, random, uuid, importlib.util
from datetime import datetime
from cryptography.fernet import Fernet
import traceback
import hashlib
import secrets

def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

load_dotenv()

from config import get_config

config = get_config()
APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder='.', static_url_path='')
app.config.from_object(config)
CORS(app)

STOCK_FILE = config.STOCK_FILE
KEY_FILE = config.KEY_FILE
USERS_FILE = config.USERS_FILE
SESSIONS_FILE = config.SESSIONS_FILE
ADMIN_PASSWORD_HASH = hashlib.sha256(config.ADMIN_PASSWORD.encode()).hexdigest()

def log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode())

def _load_cookie_checker():
    module_path = os.path.join(APP_DIR, 'cookie_checker.py')
    spec = importlib.util.spec_from_file_location('cookie_checker', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_checker = _load_cookie_checker()

def validate_cookie_real_time(cookie_content):
    try:
        result = _checker.check_cookie(
            cookie_content,
            live=getattr(config, 'COOKIE_CHECK_LIVE', False),
            min_length=getattr(config, 'COOKIE_MIN_LENGTH', 50),
        )
        if result['valid'] and result['nftoken']:
            log(f"[OK] Cookie valid: {result['message']}")
            return result['nftoken'], result['message']
        return None, result.get('message', 'Cookie non valido')
    except Exception as e:
        log(f"Errore validazione: {e}")
        return None, f"Cookie non valido: {str(e)}"

def load_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    return key

cipher = Fernet(load_or_create_key())

def load_json(filename, default=None):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default or {}
    return default or {}

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def load_stock():
    if os.path.exists(STOCK_FILE):
        try:
            with open(STOCK_FILE, 'rb') as f:
                return json.loads(cipher.decrypt(f.read()))
        except Exception as e:
            print(f"Error loading stock: {e}")
            return []
    return []

def save_stock(stock):
    try:
        data = json.dumps(stock, ensure_ascii=False).encode('utf-8')
        with open(STOCK_FILE, 'wb') as f:
            f.write(cipher.encrypt(data))
    except Exception as e:
        print(f"Error saving stock: {e}")

def generate_key():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return f"NET-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}"

def verify_token(token):
    sessions = load_json(SESSIONS_FILE, {})
    return sessions.get(token, None)

def create_session(email):
    token = secrets.token_urlsafe(32)
    sessions = load_json(SESSIONS_FILE, {})
    sessions[token] = {
        'email': email,
        'created_at': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat()
    }
    save_json(SESSIONS_FILE, sessions)
    return token

# ==================== ROUTES ====================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email or '@' not in email:
            return jsonify({'success': False, 'error': 'Email non valida'}), 400
        
        users = load_json(USERS_FILE, {})
        if email not in users:
            users[email] = {
                'created_at': datetime.now().isoformat(),
                'keys_used': 0,
                'keys': []
            }
            save_json(USERS_FILE, users)
        
        token = create_session(email)
        return jsonify({'success': True, 'token': token, 'email': email})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            token = secrets.token_urlsafe(32)
            sessions = load_json(SESSIONS_FILE, {})
            sessions[token] = {
                'email': 'admin',
                'role': 'admin',
                'created_at': datetime.now().isoformat()
            }
            save_json(SESSIONS_FILE, sessions)
            log(f"[OK] Admin login successful")
            return jsonify({'success': True, 'token': token})
        
        return jsonify({'success': False, 'error': 'Password errata'}), 401
    except Exception as e:
        print(f"Admin login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-token', methods=['GET'])
def verify():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    session = verify_token(token)
    if session:
        return jsonify({'valid': True, 'session': session})
    return jsonify({'valid': False}), 401

@app.route('/api/stock', methods=['GET'])
def get_stock():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)
        
        if not session or session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 401
        
        stock = load_stock()
        return jsonify(stock)
    except Exception as e:
        print(f"Get stock error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/upload', methods=['POST'])
def upload_stock():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)
        
        if not session or session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        files = request.files.getlist('files')
        log(f"Received {len(files)} files")
        
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        stock = load_stock()
        added = 0
        errors = []

        for file in files:
            try:
                if not file or not file.filename:
                    continue
                    
                if not file.filename.endswith('.txt'):
                    errors.append(f"❌ {file.filename}: Not a .txt file")
                    continue
                
                content = file.read().decode('utf-8').strip()
                log(f"File: {file.filename}, Size: {len(content)} bytes")
                
                if len(content) < config.COOKIE_MIN_LENGTH:
                    errors.append(f"❌ {file.filename}: Too short (< {config.COOKIE_MIN_LENGTH} bytes)")
                    continue

                nftoken, msg = validate_cookie_real_time(content)
                key = generate_key()
                
                status = "Valido" if nftoken else "Non Valido"
                log(f"Processed: {file.filename} -> {status}")

                stock.append({
                    "id": str(uuid.uuid4()),
                    "key": key,
                    "nftoken": nftoken,
                    "full_cookie": content,
                    "raw_preview": content[:160] + "..." if len(content) > 160 else content,
                    "status": status,
                    "added": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "used": False
                })
                added += 1
            except Exception as e:
                error_msg = f"❌ {file.filename}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)

        save_stock(stock)
        log(f"Stock saved: {added} items added")
        
        return jsonify({
            'success': True, 
            'added': added,
            'errors': errors,
            'message': f'Aggiunti {added} cookie!' if added > 0 else 'Nessun cookie aggiunto'
        })
    except Exception as e:
        log(f"Upload error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stock/revalidate', methods=['POST'])
def revalidate_stock():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)

        if not session or session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401

        stock = load_stock()
        updated = 0
        valid = 0

        for item in stock:
            if not item.get('full_cookie'):
                continue
            nftoken, _ = validate_cookie_real_time(item['full_cookie'])
            if nftoken:
                item['nftoken'] = nftoken
                item['status'] = 'Valido'
                valid += 1
            else:
                item['nftoken'] = None
                item['status'] = 'Non Valido'
            updated += 1

        save_stock(stock)
        return jsonify({
            'success': True,
            'updated': updated,
            'valid': valid,
            'message': f'Rivalidati {updated} cookie, {valid} validi'
        })
    except Exception as e:
        log(f"Revalidate error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cookie/check', methods=['POST'])
def check_cookie_api():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)
        if not session or session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401

        data = request.get_json(silent=True) or {}
        cookie = data.get('cookie', '').strip()
        if not cookie:
            return jsonify({'success': False, 'error': 'Cookie mancante'}), 400

        result = _checker.check_cookie(
            cookie,
            live=getattr(config, 'COOKIE_CHECK_LIVE', False),
            min_length=config.COOKIE_MIN_LENGTH,
        )
        return jsonify({'success': result['valid'], **result})
    except Exception as e:
        log(f"Cookie check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stock/use', methods=['POST'])
def use_stock():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)
        
        if not session:
            return jsonify({'success': False, 'error': 'Non autenticato'}), 401

        data = request.get_json(silent=True) or {}
        key = data.get('key', '').strip().upper()

        if not key:
            return jsonify({'success': False, 'error': 'Inserisci una chiave di attivazione'}), 400

        stock = load_stock()
        account = next((s for s in stock if s.get('key', '').upper() == key), None)

        if not account:
            return jsonify({'success': False, 'error': 'Chiave non valida'}), 404

        if account.get('used', False):
            return jsonify({'success': False, 'error': 'Chiave gia utilizzata'}), 400

        if not account.get('nftoken') and account.get('full_cookie'):
            new_token, msg = validate_cookie_real_time(account['full_cookie'])
            if new_token:
                account['nftoken'] = new_token
                account['status'] = 'Valido'

        if not account.get('nftoken'):
            return jsonify({'success': False, 'error': 'Chiave non valida (cookie scaduto)'}), 400

        if account.get('full_cookie'):
            new_token, _ = validate_cookie_real_time(account['full_cookie'])
            if new_token:
                account['nftoken'] = new_token

        account['used'] = True
        account['used_date'] = datetime.now().strftime("%d/%m/%Y %H:%M")
        account['used_by'] = session.get('email')
        
        save_stock(stock)
        
        # Salva nella cronologia utente
        users = load_json(USERS_FILE, {})
        if session.get('email') in users:
            users[session['email']]['keys'].append({
                'key': account['key'],
                'nftoken': account['nftoken'],
                'date': datetime.now().isoformat()
            })
            users[session['email']]['keys_used'] += 1
            save_json(USERS_FILE, users)
        
        return jsonify({'success': True, **account})
    except Exception as e:
        print(f"Use stock error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/inventory', methods=['GET'])
def inventory():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)
        
        if not session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        email = session.get('email')
        users = load_json(USERS_FILE, {})
        user = users.get(email, {})
        
        return jsonify({
            'email': email,
            'keys_used': user.get('keys_used', 0),
            'keys': user.get('keys', []),
            'created_at': user.get('created_at', '')
        })
    except Exception as e:
        print(f"Inventory error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-renew', methods=['POST'])
def auto_renew():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = verify_token(token)
        
        if not session:
            return jsonify({'success': False, 'error': 'Non autenticato'}), 401
        
        data = request.get_json()
        nftoken = data.get('nftoken')
        
        stock = load_stock()
        for item in stock:
            if item.get('nftoken') == nftoken and item.get('used'):
                if item.get('full_cookie'):
                    new_token, _ = validate_cookie_real_time(item['full_cookie'])
                    if new_token:
                        item['nftoken'] = new_token
                        save_stock(stock)
                        return jsonify({
                            'success': True,
                            'nftoken': new_token,
                            'message': 'Account rinnovato con successo'
                        })
                return jsonify({'success': False, 'error': 'Impossibile rinnovare'}), 400
        
        return jsonify({'success': False, 'error': 'Token non trovato'}), 404
    except Exception as e:
        print(f"Auto-renew error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        sessions = load_json(SESSIONS_FILE, {})
        if token in sessions:
            del sessions[token]
            save_json(SESSIONS_FILE, sessions)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    log("NetKeys Server AVVIATO")
    log("Open: http://localhost:5000")
    log(f"Admin: http://localhost:5000/admin.html (password: {config.ADMIN_PASSWORD})")
    app.run(debug=config.DEBUG, port=5000, host='0.0.0.0')
