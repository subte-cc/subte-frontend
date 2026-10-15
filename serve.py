#!/usr/bin/env python3
import argparse
import base64
import hashlib
import hmac
import http.cookies
import http.server
import ipaddress
import json
import mimetypes
import os
import re
import secrets
import socketserver
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')

PORT = 3000
BACKEND_URL = "http://127.0.0.1:3001"
BUILD_DIR = "build"

DEMO_MODE = False
AUTO_VERIFY = False
SESSION_MINUTES = 30
MAX_DOMAINS = 5

ALTCHA_COST = 5000
ALTCHA_KEY_LENGTH = 32
ALTCHA_KEY_PREFIX = "00"
ALTCHA_TTL_SECONDS = 300
ALTCHA_STRICT_POW = True
CAPTCHA_PROTECTED = {"/api/auth/register", "/api/auth/login"}

RESERVED_SUBDOMAINS = {"www", "api", "mail", "admin", "ns1", "ns2", "ftp", "smtp", "root"}
SUBDOMAIN_RE = re.compile(r'^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

STATE_LOCK = threading.RLock()
DEMO = {}


def now_dt():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now_dt()).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def b64u_dec(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def canonical_json(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'))


def sha256_hex(s):
    return hashlib.sha256(s.encode()).hexdigest()


def hash_password(password):
    salt = secrets.token_hex(16)
    iters = 100_000
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iters).hex()
    return f"pbkdf2${iters}${salt}${dk}"


def check_password(password, stored):
    try:
        _, iters, salt, dk = stored.split('$')
        calc = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iters)).hex()
        return hmac.compare_digest(calc, dk)
    except Exception:
        return False


def jwt_encode(claims):
    h = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(',', ':')).encode())
    p = b64u(json.dumps(claims, separators=(',', ':')).encode())
    sig = b64u(hmac.new(DEMO["jwt_secret"], f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def jwt_decode(token):
    try:
        h, p, s = token.split('.')
        expected = b64u(hmac.new(DEMO["jwt_secret"], f"{h}.{p}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, s):
            return None
        claims = json.loads(b64u_dec(p))
        if claims.get("exp", 0) < int(time.time()):
            return None
        return claims
    except Exception:
        return None


def valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except Exception:
        return False

def create_altcha_challenge():
    params = {
        "algorithm": "PBKDF2/SHA-256",
        "nonce": secrets.token_hex(16),
        "salt": secrets.token_hex(16),
        "cost": ALTCHA_COST,
        "keyLength": ALTCHA_KEY_LENGTH,
        "keyPrefix": ALTCHA_KEY_PREFIX,
        "expiresAt": int(time.time()) + ALTCHA_TTL_SECONDS,
    }
    sig = hmac.new(DEMO["altcha_secret"], canonical_json(params).encode(), hashlib.sha256).hexdigest()
    return {"parameters": params, "signature": sig}


def altcha_derive_key(params, counter):
    password = bytes.fromhex(params["nonce"]) + struct.pack('>I', counter)
    salt = bytes.fromhex(params["salt"])
    return hashlib.pbkdf2_hmac('sha256', password, salt, int(params["cost"]),
                               int(params["keyLength"])).hex()


def decode_altcha_payload(s):
    if not isinstance(s, str) or len(s) < 40:
        return None
    for decoder in (base64.b64decode, b64u_dec):
        try:
            raw = decoder(s + '=' * (-len(s) % 4))
            data = json.loads(raw)
            if isinstance(data, dict) and "challenge" in data and "solution" in data:
                return data
        except Exception:
            continue
    return None


def verify_altcha(data):
    try:
        challenge = data["challenge"]
        solution = data["solution"]
        params = challenge["parameters"]
        sig = challenge["signature"]
        counter = int(solution["counter"])
    except Exception:
        return False, "Invalid captcha payload"

    expected = hmac.new(DEMO["altcha_secret"], canonical_json(params).encode(),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, str(sig)):
        return False, "Invalid captcha signature"
    if params.get("expiresAt", 0) < int(time.time()):
        return False, "Captcha expired"
    if sig in DEMO["used_challenges"]:
        return False, "Captcha already used"

    if ALTCHA_STRICT_POW:
        try:
            derived = altcha_derive_key(params, counter)
        except Exception:
            return False, "Invalid captcha parameters"
        if not derived.startswith(params["keyPrefix"]):
            return False, "Captcha solution incorrect"
        if solution.get("derivedKey") and solution["derivedKey"] != derived:
            return False, "Captcha solution incorrect"

    DEMO["used_challenges"][sig] = params["expiresAt"]
    # purge expired entries
    now = int(time.time())
    for k in [k for k, v in DEMO["used_challenges"].items() if v < now]:
        del DEMO["used_challenges"][k]
    return True, None


def init_demo_state():
    now = iso()
    uid = str(uuid.uuid4())
    demo_key = "demo-api-key-12345"
    DEMO.clear()
    DEMO.update({
        "jwt_secret": secrets.token_bytes(32),
        "altcha_secret": secrets.token_bytes(32),
        "used_challenges": {},
        "users": {
            uid: {
                "id": uid,
                "email": "demo@demo.com",
                "password_hash": hash_password("demo"),
                "status": 1,
                "created_at": now,
                "updated_at": now,
                "verification_token": None,
                "token_generated_at": None,
            }
        },
        "email_index": {"demo@demo.com": uid},
        "verification_index": {},   # token -> uid
        "domains": {},
        "next_domain_id": 1,
        "api_keys": {sha256_hex(demo_key): uid},   # sha256(key) -> uid
        "demo_api_key": demo_key,
        "demo_user_id": uid,
    })
    for sub, ip in [("cabernet", "127.0.0.1"), ("malbec", "192.168.1.10"), ("merlot", "10.0.0.5")]:
        add_domain(uid, sub, ip)


def add_domain(uid, sub, ip):
    did = DEMO["next_domain_id"]
    DEMO["next_domain_id"] += 1
    now = iso()
    dom = {"id": did, "user_id": uid, "subdomain": sub, "ip": ip,
           "status": 1, "created_at": now, "updated_at": now}
    DEMO["domains"][did] = dom
    return dom


def user_domains(uid):
    return sorted((d for d in DEMO["domains"].values() if d["user_id"] == uid),
                  key=lambda d: d["id"])


def is_api_path(path):
    path = path.split('?')[0]
    return path.startswith('/api/') or path == '/up' or path.startswith('/up/')


class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = 0.0
        super().__init__(*args, directory=BUILD_DIR, **kwargs)

    def handle_one_request(self):
        self.start_time = time.time()
        super().handle_one_request()

    def log_request(self, code='-', size='-'):
        elapsed = (time.time() - self.start_time) * 1000
        self.log_message('"%s" %s %s [%.2fms]',
                         self.requestline, str(code), str(size), elapsed)

    def _send_json(self, status_code, obj, cookies=None, headers=None):
        data = json.dumps(obj).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        for c in (cookies or []):
            self.send_header('Set-Cookie', c)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length > 0 else b'{}'
            obj = json.loads(body.decode('utf-8') or '{}')
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _auth_user_id(self):
        token = None
        cookie_header = self.headers.get('Cookie', '')
        if cookie_header:
            try:
                c = http.cookies.SimpleCookie()
                c.load(cookie_header)
                if 'token' in c:
                    token = c['token'].value
            except Exception:
                pass
        if not token:
            auth = self.headers.get('Authorization', '')
            if auth.lower().startswith('bearer '):
                token = auth[7:].strip()
        if not token:
            return None
        claims = jwt_decode(token)
        if not claims:
            return None
        uid = claims.get('sub')
        return uid if uid in DEMO["users"] else None

    def _api_key_user_id(self, query):
        key = None
        auth = self.headers.get('Authorization', '')
        if auth.lower().startswith('bearer '):
            key = auth[7:].strip()
        key = key or self.headers.get('X-API-Key') or self.headers.get('api-key')
        key = key or (query.get('key') or query.get('token') or [None])[0]
        if not key:
            return None
        return DEMO["api_keys"].get(sha256_hex(key))

    def _session_cookies(self, uid):
        exp = int(time.time()) + SESSION_MINUTES * 60
        token = jwt_encode({"sub": uid, "iat": int(time.time()), "exp": exp})
        max_age = SESSION_MINUTES * 60
        return [
            f"token={token}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Strict",
            f"auth_status={exp}; Path=/; Max-Age={max_age}; SameSite=Strict",
        ]

    @staticmethod
    def _clear_cookies():
        return [
            'token=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict',
            'auth_status=; Path=/; Max-Age=0; SameSite=Strict',
        ]

    def _check_captcha(self, path, body):
        """Returns an error string, or None when OK / not required."""
        if path not in CAPTCHA_PROTECTED:
            return None
        payload = None
        hdr = self.headers.get('X-Altcha-Payload')
        if hdr:
            payload = decode_altcha_payload(hdr)
        if payload is None and isinstance(body, dict):
            for key in ('altcha', 'altcha_payload', 'captcha', 'captcha_token'):
                payload = decode_altcha_payload(body.get(key))
                if payload:
                    break
            if payload is None:
                for v in body.values():
                    payload = decode_altcha_payload(v)
                    if payload:
                        break
        if payload is None:
            return "Captcha verification required"
        ok, err = verify_altcha(payload)
        return None if ok else err

    def handle_demo_api(self, method):
        with STATE_LOCK:
            self._handle_demo_api_locked(method)

    def _handle_demo_api_locked(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/api/auth/config' and method == 'GET':
            return self._send_json(200, {
                "invite_required": False,
                "oauth_codeberg_enabled": False,
                "oauth_github_enabled": False,
                "oauth_google_enabled": False,
            })

        if path == '/api/auth/challenge' and method == 'GET':
            return self._send_json(200, create_altcha_challenge())

        if path == '/api/auth/register' and method == 'POST':
            req = self._read_json()
            if req is None:
                return self._send_json(400, {"error": "Invalid request format"})
            err = self._check_captcha(path, req)
            if err:
                return self._send_json(400, {"error": err})
            email = (req.get('email') or '').strip().lower()
            password = req.get('password') or ''
            if not EMAIL_RE.match(email):
                return self._send_json(400, {"error": "Invalid email address"})
            if len(password) < 6:
                return self._send_json(400, {"error": "Password must be at least 6 characters long!"})
            if len(password) > 72:
                return self._send_json(400, {"error": "Password must not exceed 72 characters!"})
            if email in DEMO["email_index"]:
                return self._send_json(400, {"error": "Email already registered"})
            now = iso()
            uid = str(uuid.uuid4())
            vtoken = secrets.token_urlsafe(24)
            DEMO["users"][uid] = {
                "id": uid, "email": email,
                "password_hash": hash_password(password),
                "status": 1 if AUTO_VERIFY else 0,
                "created_at": now, "updated_at": now,
                "verification_token": None if AUTO_VERIFY else vtoken,
                "token_generated_at": None,
            }
            DEMO["email_index"][email] = uid
            if not AUTO_VERIFY:
                DEMO["verification_index"][vtoken] = uid
                print(f"[demo] verification link for {email}: "
                      f"http://localhost:{PORT}/api/auth/verify?token={vtoken}", flush=True)
            return self._send_json(201, {
                "message": "Account created successfully! Please check your email to verify your account."})

        if path == '/api/auth/login' and method == 'POST':
            req = self._read_json()
            if req is None:
                return self._send_json(400, {"error": "Invalid request format"})
            err = self._check_captcha(path, req)
            if err:
                return self._send_json(400, {"error": err})
            email = (req.get('email') or '').strip().lower()
            password = req.get('password') or ''
            uid = DEMO["email_index"].get(email)
            user = DEMO["users"].get(uid) if uid else None
            if not user or not check_password(password, user["password_hash"]):
                return self._send_json(401, {"error": "Invalid credentials"})
            if user["status"] != 1:
                return self._send_json(403, {"error": "Please verify your email first"})
            return self._send_json(200, {"message": "Login successful"},
                                   cookies=self._session_cookies(uid))

        if path == '/api/auth/logout' and method == 'POST':
            return self._send_json(200, {"message": "Logged out"}, cookies=self._clear_cookies())

        if path == '/api/auth/verify' and method == 'GET':
            token = (query.get('token') or [''])[0]
            uid = DEMO["verification_index"].pop(token, None)
            if uid and uid in DEMO["users"]:
                u = DEMO["users"][uid]
                u["status"] = 1
                u["verification_token"] = None
                u["updated_at"] = iso()
                location = '/login?verified=true'
            else:
                location = '/login?verified=false'
            self.send_response(302)
            self.send_header('Location', location)
            self.end_headers()
            return

        if path == '/api/user/me' and method == 'GET':
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "user not found in token"})
            user = DEMO["users"][uid]
            return self._send_json(200, {
                "email": user["email"],
                "status": user["status"],
                "created_at": user["created_at"],
                "domain_count": len(user_domains(uid)),
                "token_generated_at": user["token_generated_at"],
            })

        if path == '/api/user/key' and method == 'POST':
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "user not found in token"})
            user = DEMO["users"][uid]
            if user["status"] != 1:
                return self._send_json(403, {"error": "Account must be verified to generate API keys"})
            DEMO["api_keys"] = {h: u for h, u in DEMO["api_keys"].items() if u != uid}
            key = secrets.token_urlsafe(32)
            DEMO["api_keys"][sha256_hex(key)] = uid
            user["token_generated_at"] = iso()
            return self._send_json(200, {"token": key})

        if path == '/api/user/password' and method == 'PUT':
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "user not found in token"})
            req = self._read_json()
            if req is None:
                return self._send_json(400, {"error": "Invalid request format"})
            cur = req.get('current_password') or ''
            newp = req.get('new_password') or ''
            if len(newp) < 6:
                return self._send_json(400, {"error": "New password must be at least 6 characters long!"})
            if len(newp) > 72:
                return self._send_json(400, {"error": "New password must not exceed 72 characters!"})
            user = DEMO["users"][uid]
            if not check_password(cur, user["password_hash"]):
                return self._send_json(401, {"error": "Invalid credentials"})
            user["password_hash"] = hash_password(newp)
            user["updated_at"] = iso()
            return self._send_json(200, {"message": "Password updated successfully"})

        if path == '/api/user/delete' and method == 'DELETE':
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "user not found in token"})
            user = DEMO["users"].pop(uid)
            DEMO["email_index"].pop(user["email"], None)
            DEMO["domains"] = {i: d for i, d in DEMO["domains"].items() if d["user_id"] != uid}
            DEMO["api_keys"] = {h: u for h, u in DEMO["api_keys"].items() if u != uid}
            return self._send_json(200, {"message": "User account deleted successfully"},
                                   cookies=self._clear_cookies())

        if path == '/api/domains' and method == 'GET':
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "Unauthorized"})
            return self._send_json(200, user_domains(uid))

        if path == '/api/domains' and method == 'POST':
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "Unauthorized"})
            req = self._read_json()
            if req is None:
                return self._send_json(400, {"error": "Invalid request format"})
            sub = (req.get('subdomain') or '').strip().lower()
            ip = (req.get('ip') or '').strip()
            if not SUBDOMAIN_RE.match(sub) or sub in RESERVED_SUBDOMAINS:
                return self._send_json(400, {"error": "Invalid domain"})
            if not valid_ip(ip):
                return self._send_json(400, {"error": "Invalid IP address"})
            if len(user_domains(uid)) >= MAX_DOMAINS:
                return self._send_json(400, {"error": "Maximum domains reached"})
            if any(d["subdomain"] == sub for d in DEMO["domains"].values()):
                return self._send_json(409, {"error": "Subdomain already taken"})
            return self._send_json(201, add_domain(uid, sub, ip))

        m = re.fullmatch(r'/api/domains/(\d+)', path)
        if m:
            uid = self._auth_user_id()
            if not uid:
                return self._send_json(401, {"error": "Unauthorized"})
            dom = DEMO["domains"].get(int(m.group(1)))
            if not dom or dom["user_id"] != uid:
                return self._send_json(404, {"error": "Not found"})
            if method == 'GET':
                return self._send_json(200, dom)
            if method == 'PUT':
                req = self._read_json()
                if req is None:
                    return self._send_json(400, {"error": "Invalid request format"})
                ip = (req.get('ip') or '').strip()
                if not valid_ip(ip):
                    return self._send_json(400, {"error": "Invalid IP address"})
                dom["ip"] = ip
                dom["updated_at"] = iso()
                return self._send_json(200, dom)
            if method == 'DELETE':
                del DEMO["domains"][dom["id"]]
                return self._send_json(200, {"message": "Domain deleted successfully"})
            return self._send_json(405, {"error": "Method not allowed"})

        if path == '/up' or path.startswith('/up/'):
            uid = self._api_key_user_id(query)
            if not uid:
                return self._send_json(401, {"error": "Unauthorized"})
            body = self._read_json() if method in ('POST', 'PUT', 'PATCH') else {}
            body = body or {}
            sub = (body.get('subdomain') or (query.get('subdomain') or [''])[0]).strip().lower()
            ip = (body.get('ip') or (query.get('ip') or [''])[0]).strip() or self.client_address[0]
            if not valid_ip(ip):
                return self._send_json(400, {"error": "Invalid IP address"})
            targets = [d for d in user_domains(uid) if not sub or d["subdomain"] == sub]
            if sub and not targets:
                return self._send_json(404, {"error": "Not found"})
            for d in targets:
                d["ip"] = ip
                d["updated_at"] = iso()
            return self._send_json(200, {"status": "ok", "ip": ip,
                                         "updated": [d["subdomain"] for d in targets]})

        return self._send_json(404, {"error": "Not found"})

    def _route_api(self, method):
        if DEMO_MODE:
            self.handle_demo_api(method)
        else:
            self.proxy_request(method)

    def do_GET(self):
        if is_api_path(self.path):
            return self._route_api('GET')
        clean_path = self.path.split('?')[0]
        if clean_path == '/':
            clean_path = '/index.html'
        filepath = os.path.join(self.directory, clean_path.lstrip('/'))
        if os.path.exists(filepath) and not os.path.isdir(filepath):
            self.path = clean_path
        elif os.path.exists(filepath + '.html'):
            self.path = clean_path + '.html'
        elif os.path.isdir(filepath):
            if os.path.exists(os.path.join(filepath, 'index.html')):
                self.path = clean_path.rstrip('/') + '/index.html'
            else:
                self.path = '/index.html'
        else:
            self.path = '/index.html'
        super().do_GET()

    def _do_api_only(self, method):
        if is_api_path(self.path):
            self._route_api(method)
        else:
            self.send_error(405, "Method Not Allowed")

    def do_POST(self):
        self._do_api_only('POST')

    def do_PUT(self):
        self._do_api_only('PUT')

    def do_DELETE(self):
        self._do_api_only('DELETE')

    def do_PATCH(self):
        self._do_api_only('PATCH')

    def proxy_request(self, method):
        url = BACKEND_URL + self.path
        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ['host', 'connection', 'accept-encoding']:
                headers[key] = value
        data = None
        if 'Content-Length' in self.headers:
            content_length = int(self.headers['Content-Length'])
            data = self.rfile.read(content_length)
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {str(e)}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    global DEMO_MODE, AUTO_VERIFY
    parser = argparse.ArgumentParser(description='Serve frontend build with optional demo mode')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode with mock API')
    parser.add_argument('--auto-verify', action='store_true',
                        help='Demo mode: new accounts are verified immediately (skip email link)')
    args = parser.parse_args()

    if args.demo:
        DEMO_MODE = True
        AUTO_VERIFY = args.auto_verify
        init_demo_state()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(BUILD_DIR):
        print(f"Error: '{BUILD_DIR}' directory not found. Please run the build script first.")
        exit(1)

    with ThreadedTCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
        print(f"Serving local testing environment at http://localhost:{PORT}")
        if DEMO_MODE:
            print("Running in DEMO mode - mocking /api/* and /up/* (ALTCHA enforced)")
            print("Demo user: demo@demo.com / demo")
            print("Preloaded domains: cabernet, malbec, merlot")
            print(f"Mock API key: {DEMO['demo_api_key']}")
            if AUTO_VERIFY:
                print("Auto-verify: ON")
            else:
                print("New accounts need verification: the link is printed here in the console")
        else:
            print(f"Proxying /api/* and /up/* to {BACKEND_URL}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == '__main__':
    main()