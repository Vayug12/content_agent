import os
import json
import time
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from utils.logger import log

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_PORT = 8099
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
SCOPES = "openid email profile"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    auth_error = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            OAuthCallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Sign-in successful!</h1><p>You can close this tab.</p>")
        elif "error" in query:
            OAuthCallbackHandler.auth_error = query["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Error: {query['error'][0]}</h1>".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def _get_env_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


def _read_env():
    env = {}
    path = _get_env_path()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _save_jwt_to_env(jwt: str, refresh_token: str = None):
    path = _get_env_path()
    lines = []
    jwt_found = False
    refresh_found = False

    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()

    for i, line in enumerate(lines):
        if line.strip().startswith("VAYUG_JWT="):
            lines[i] = f"VAYUG_JWT={jwt}\n"
            jwt_found = True
        elif line.strip().startswith("VAYUG_REFRESH_TOKEN="):
            if refresh_token:
                lines[i] = f"VAYUG_REFRESH_TOKEN={refresh_token}\n"
            refresh_found = True

    if not jwt_found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1].rstrip() + "\n"
        lines.append(f"VAYUG_JWT={jwt}\n")

    if refresh_token and not refresh_found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1].rstrip() + "\n"
        lines.append(f"VAYUG_REFRESH_TOKEN={refresh_token}\n")

    with open(path, "w") as f:
        f.writelines(lines)

    os.environ["VAYUG_JWT"] = jwt
    if refresh_token:
        os.environ["VAYUG_REFRESH_TOKEN"] = refresh_token


def _exchange_code(code: str, client_id: str, client_secret: str) -> dict:
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    })
    resp.raise_for_status()
    return resp.json()


def _refresh_jwt(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh token se naya JWT le aao - browser ki zaroorat nahi"""
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        })
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log("AUTH", f"Refresh token failed: {str(e)}")
        return {}


def is_jwt_valid(jwt: str) -> bool:
    if not jwt:
        return False
    try:
        parts = jwt.split(".")
        if len(parts) != 3:
            return False
        import base64
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        exp = payload.get("exp", 0)
        return time.time() < exp - 60
    except:
        return False


def authenticate() -> str:
    env = _read_env()
    client_id = env.get("GOOGLE_CLIENT_ID", "")
    client_secret = env.get("GOOGLE_CLIENT_SECRET", "")
    jwt = env.get("VAYUG_JWT", "")
    refresh_token = env.get("VAYUG_REFRESH_TOKEN", "")

    # Agar JWT valid hai toh direct return
    if jwt and is_jwt_valid(jwt):
        log("AUTH", "JWT valid hai, login ki zaroorat nahi")
        return jwt

    # Agar refresh token hai toh try karo (browser nahi khulega)
    if refresh_token and client_id and client_secret:
        log("AUTH", "JWT expire hua hai, refresh token se naya le rahe hain...")
        token_data = _refresh_jwt(client_id, client_secret, refresh_token)
        new_jwt = token_data.get("id_token", "")
        if new_jwt:
            _save_jwt_to_env(new_jwt, refresh_token)
            log("AUTH", "JWT refresh successful! Browser ki zaroorat nahi.")
            return new_jwt
        else:
            log("AUTH", "Refresh failed, browser sign-in zaroori hai...")

    if not client_id or not client_secret:
        log("AUTH", "ERROR: GOOGLE_CLIENT_ID aur GOOGLE_CLIENT_SECRET .env mein nahi hain")
        log("AUTH", "Ye credentials Google Cloud Console se lo:")
        log("AUTH", "  1. https://console.cloud.google.com/apis/credentials jao")
        log("AUTH", "  2. OAuth 2.0 Client ID banao (Desktop app type)")
        log("AUTH", "  3. Client ID aur Secret .env mein daalo")
        return ""

    log("AUTH", "Browser khul raha hai Google Sign-In ke liye...")
    auth_url = (
        f"{GOOGLE_AUTH_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    server = HTTPServer(("localhost", REDIRECT_PORT), OAuthCallbackHandler)
    server.timeout = 120

    log("AUTH", f"Browser khul raha hai Google Sign-In ke liye...")
    webbrowser.open(auth_url)

    log("AUTH", "Sign-in karo browser mein... (120 second ka time hai)")
    while OAuthCallbackHandler.auth_code is None and OAuthCallbackHandler.auth_error is None:
        server.handle_request()

    server.server_close()

    if OAuthCallbackHandler.auth_error:
        log("AUTH", f"Auth failed: {OAuthCallbackHandler.auth_error}")
        return ""

    code = OAuthCallbackHandler.auth_code
    OAuthCallbackHandler.auth_code = None

    log("AUTH", "Code mila, JWT generate ho raha hai...")
    token_data = _exchange_code(code, client_id, client_secret)

    new_jwt = token_data.get("id_token", "")
    new_refresh = token_data.get("refresh_token", "")
    if not new_jwt:
        log("AUTH", "ERROR: id_token nahi mila")
        return ""

    # JWT aur refresh_token dono save karo
    _save_jwt_to_env(new_jwt, new_refresh if new_refresh else refresh_token)
    log("AUTH", "Login successful! JWT aur Refresh Token store ho gaya .env mein")
    return new_jwt


def get_jwt() -> str:
    env = _read_env()
    jwt = env.get("VAYUG_JWT", "")
    refresh_token = env.get("VAYUG_REFRESH_TOKEN", "")
    client_id = env.get("GOOGLE_CLIENT_ID", "")
    client_secret = env.get("GOOGLE_CLIENT_SECRET", "")

    # Agar JWT valid hai toh direct return
    if jwt and is_jwt_valid(jwt):
        return jwt

    # Agar refresh token hai toh try karo (browser nahi khulega)
    if refresh_token and client_id and client_secret:
        log("AUTH", "JWT expire hua hai, refresh token se try kar rahe hain...")
        token_data = _refresh_jwt(client_id, client_secret, refresh_token)
        new_jwt = token_data.get("id_token", "")
        if new_jwt:
            _save_jwt_to_env(new_jwt, refresh_token)
            log("AUTH", "JWT refresh successful!")
            return new_jwt

    # Last resort: browser sign-in
    return authenticate()
