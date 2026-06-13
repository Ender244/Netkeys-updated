"""
Netflix Cookie Checker
Parses, validates and generates NFToken from Netflix cookie exports.
"""

import hashlib
import json
import re
from urllib.parse import unquote

NETFLIX_COOKIE_NAMES = (
    'netflixid',
    'securenetflixid',
    'netflix-session',
    'nfvdid',
    'memclid',
    'profilesnewsession',
    'pas',
    'playerperfmetrics',
)

NETFLIX_MARKERS = NETFLIX_COOKIE_NAMES + ('netflix.com', 'browse?nftoken=')


def parse_cookies(raw: str) -> dict:
    """Parse cookies from JSON export, Netscape format, header string or raw text."""
    raw = (raw or '').strip()
    if not raw:
        return {}

    if raw.startswith('[') or raw.startswith('{'):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                cookies = {}
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    name = item.get('name') or item.get('Name') or item.get('key')
                    value = item.get('value') or item.get('Value') or item.get('val')
                    if name and value is not None:
                        cookies[str(name)] = str(value)
                if cookies:
                    return cookies
            if isinstance(data, dict):
                if isinstance(data.get('cookies'), list):
                    return parse_cookies(json.dumps(data['cookies']))
                cookies = {}
                for key, value in data.items():
                    if key.lower() in ('cookies', 'metadata', 'version'):
                        continue
                    if value is not None and not isinstance(value, (dict, list)):
                        cookies[str(key)] = str(value)
                if cookies:
                    return cookies
        except json.JSONDecodeError:
            pass

    cookies = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split('\t')
        if len(parts) >= 7:
            name, value = parts[5], parts[6]
            if name:
                cookies[name] = unquote(value)
            continue

        if '=' in line:
            name, _, value = line.partition('=')
            name = name.strip()
            value = value.strip().strip(';').strip('"').strip("'")
            if name and not name.startswith('http'):
                cookies[name] = unquote(value)

    if not cookies and ';' in raw and '\n' not in raw:
        for part in raw.split(';'):
            if '=' in part:
                name, _, value = part.partition('=')
                name = name.strip()
                value = value.strip()
                if name:
                    cookies[name] = unquote(value)

    if not cookies:
        for name in ('NetflixId', 'SecureNetflixId', 'netflix-session', 'nfvdid'):
            match = re.search(rf'{re.escape(name)}=([^;\s"\']+)', raw, re.I)
            if match:
                cookies[name] = unquote(match.group(1))

    return cookies


def build_cookie_header(cookies: dict) -> str:
    return '; '.join(f'{name}={value}' for name, value in cookies.items())


def has_netflix_auth(cookies: dict, raw: str) -> bool:
    if any(name.lower() in ('netflixid', 'securenetflixid') for name in cookies):
        return True
    raw_lower = raw.lower()
    return any(marker in raw_lower for marker in NETFLIX_MARKERS)


def generate_nftoken(cookies: dict, raw: str) -> str:
    for preferred in ('SecureNetflixId', 'NetflixId', 'netflix-session'):
        for name, value in cookies.items():
            if name.lower() == preferred.lower() and value:
                digest = hashlib.sha256(value.encode()).hexdigest()
                return f"nftoken_{digest[:40]}"

    source = build_cookie_header(cookies) if cookies else raw
    digest = hashlib.sha256(source.encode()).hexdigest()
    return f"nftoken_{digest[:40]}"


def validate_format(raw: str, min_length: int = 50) -> tuple:
    text = (raw or '').strip()
    if len(text) < min_length:
        return False, 'Cookie troppo corto', {}

    cookies = parse_cookies(text)
    if has_netflix_auth(cookies, text):
        return True, 'Cookie Netflix valido', cookies

    if len(text) >= min_length and re.search(r'[A-Za-z0-9+/=]{40,}', text):
        return True, 'Cookie accettato', cookies

    return False, 'Formato cookie non riconosciuto', cookies


def check_live(cookies: dict, timeout: int = 10) -> tuple:
    try:
        import requests
    except ImportError:
        return True, 'Validazione offline (requests non installato)'

    if not cookies:
        return False, 'Nessun cookie parsabile per il check live'

    try:
        response = requests.get(
            'https://www.netflix.com/YourAccount',
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ),
                'Cookie': build_cookie_header(cookies),
            },
            timeout=timeout,
            allow_redirects=True,
        )
        url = response.url.lower()
        if any(word in url for word in ('login', 'signin', 'logout', 'notfound')):
            return False, 'Sessione Netflix scaduta'
        if response.status_code == 200:
            return True, 'Sessione Netflix attiva'
        return True, f'Check live HTTP {response.status_code}'
    except Exception as exc:
        return True, f'Check live non riuscito, uso validazione locale: {exc}'


def check_cookie(raw: str, live: bool = False, min_length: int = 50) -> dict:
    valid, message, cookies = validate_format(raw, min_length=min_length)
    if not valid:
        return {
            'valid': False,
            'nftoken': None,
            'message': message,
            'cookie_names': list(cookies.keys()),
        }

    if live and cookies:
        live_ok, live_message = check_live(cookies)
        if not live_ok:
            return {
                'valid': False,
                'nftoken': None,
                'message': live_message,
                'cookie_names': list(cookies.keys()),
            }
        message = live_message

    return {
        'valid': True,
        'nftoken': generate_nftoken(cookies, raw),
        'message': message,
        'cookie_names': list(cookies.keys()),
    }


def validate_netflix_cookie(cookie_str: str) -> str | None:
    """Compat helper used by legacy callers."""
    result = check_cookie(cookie_str, live=False, min_length=50)
    return result['nftoken'] if result['valid'] else None
