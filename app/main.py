import os, re, json, time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_user_id, get_user_email

DATA_ROOT = Path(os.getenv("LUMINA_DATA_ROOT", "./data/lumina")).resolve()
DATA_ROOT.mkdir(parents=True, exist_ok=True)

MAX_SESSIONS_DEFAULT = int(os.getenv("LUMINA_MAX_SESSIONS", "500"))

def _safe(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", (s or "").strip())

def user_dir(user_id: str) -> Path:
    """Create user directory based on hashed user ID."""
    d = DATA_ROOT / "users" / user_id[:24]
    d.mkdir(parents=True, exist_ok=True)
    return d

def app_dir(user_id: str, app: str) -> Path:
    d = user_dir(user_id) / _safe(app)
    d.mkdir(parents=True, exist_ok=True)
    (d / "sessions").mkdir(parents=True, exist_ok=True)
    return d

def session_dir(user_id: str, app: str, session_id: str) -> Path:
    d = app_dir(user_id, app) / "sessions" / _safe(session_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "files").mkdir(parents=True, exist_ok=True)
    return d

def now_ms() -> int:
    return int(time.time() * 1000)

def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text("utf-8"))

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

def sessions_index_path(user_id: str, app: str) -> Path:
    return app_dir(user_id, app) / "sessions_index.json"

def list_sessions(user_id: str, app: str) -> List[Dict[str, Any]]:
    return load_json(sessions_index_path(user_id, app), [])

def save_sessions(user_id: str, app: str, sessions: List[Dict[str, Any]]):
    save_json(sessions_index_path(user_id, app), sessions)

def enforce_limit(user_id: str, app: str, max_sessions: int):
    sessions = list_sessions(user_id, app)
    if len(sessions) <= max_sessions:
        return
    sessions.sort(key=lambda s: s.get("lastUsedAt", 0))
    to_remove = sessions[:-max_sessions]
    keep = sessions[-max_sessions:]
    for s in to_remove:
        sid = s["id"]
        sdir = session_dir(user_id, app, sid)
        # delete recursively
        for p in sorted(sdir.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink(missing_ok=True)
            else:
                p.rmdir()
        sdir.rmdir()
    save_sessions(user_id, app, keep)

app = FastAPI(title="Lumina Backend API")

# Custom CORS origin validator to allow local network access
def cors_origin_validator(origin: str) -> bool:
    """
    Allow:
    - Production domains (*.lumina-suite.tech)
    - Localhost on any port
    - Local network IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x) on ports 5173-5177
    """
    if not origin:
        return True

    # Production domains
    if origin.endswith('.lumina-suite.tech') or origin == 'https://lumina-suite.tech':
        return True

    # Localhost
    if origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
        return True

    # Local network IPs (common private IP ranges)
    # Match http://192.168.x.x:port, http://10.x.x.x:port, http://172.16-31.x.x:port
    local_ip_pattern = r'^http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}):(5173|5174|5175|5176|5177|3001)$'
    if re.match(local_ip_pattern, origin):
        return True

    return False

# CORS: Allow production domains + localhost + local network IPs
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r'^(https://[a-z-]+\.lumina-suite\.tech|https://lumina-suite\.tech|http://localhost:\d+|http://127\.0\.0\.1:\d+|http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}):(5173|5174|5175|5176|5177|3001))$',
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all response headers to JavaScript
    max_age=3600,  # Cache preflight requests for 1 hour
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/me")
def me(request: Request):
    email = get_user_email(request)
    return {"email": email}

# --------- SESSIONS (generic for any app) ---------
@app.get("/api/{app}/sessions")
def api_list_sessions(app: str, request: Request):
    user_id = get_user_id(request)
    sessions = list_sessions(user_id, app)
    sessions.sort(key=lambda s: s.get("lastUsedAt", 0), reverse=True)
    return sessions

@app.post("/api/{app}/sessions")
async def api_create_session(app: str, request: Request):
    user_id = get_user_id(request)
    payload = await request.json()
    sid = _safe(payload.get("id") or f"{now_ms()}")
    name = payload.get("name") or sid
    max_sessions = int(payload.get("maxSessions") or MAX_SESSIONS_DEFAULT)

    sessions = list_sessions(user_id, app)
    now = now_ms()
    meta = {"id": sid, "name": name, "createdAt": now, "lastUsedAt": now}
    sessions = [s for s in sessions if s.get("id") != sid] + [meta]
    save_sessions(user_id, app, sessions)
    enforce_limit(user_id, app, max_sessions)

    return meta

@app.get("/api/{app}/sessions/{session_id}/state")
def api_get_state(app: str, session_id: str, request: Request):
    user_id = get_user_id(request)
    sdir = session_dir(user_id, app, session_id)
    return load_json(sdir / "state.json", {})

@app.put("/api/{app}/sessions/{session_id}/state")
async def api_put_state(app: str, session_id: str, request: Request):
    user_id = get_user_id(request)
    payload = await request.json()
    sdir = session_dir(user_id, app, session_id)
    save_json(sdir / "state.json", payload)

    # bump lastUsedAt
    sessions = list_sessions(user_id, app)
    for s in sessions:
        if s.get("id") == session_id:
            s["lastUsedAt"] = now_ms()
    save_sessions(user_id, app, sessions)

    return {"ok": True}

@app.delete("/api/{app}/sessions/{session_id}")
def api_delete_session(app: str, session_id: str, request: Request):
    user_id = get_user_id(request)
    sdir = session_dir(user_id, app, session_id)
    for p in sorted(sdir.rglob("*"), reverse=True):
        if p.is_file():
            p.unlink(missing_ok=True)
        else:
            p.rmdir()
    sdir.rmdir()

    sessions = [s for s in list_sessions(user_id, app) if s.get("id") != session_id]
    save_sessions(user_id, app, sessions)
    return {"ok": True}

# --------- FILES (optional) ---------
@app.post("/api/{app}/sessions/{session_id}/files")
async def api_upload_file(app: str, session_id: str, request: Request, file: UploadFile = File(...)):
    user_id = get_user_id(request)
    sdir = session_dir(user_id, app, session_id)
    fname = _safe(file.filename or "upload.bin")
    target = sdir / "files" / fname
    data = await file.read()
    target.write_bytes(data)
    return {"ok": True, "name": fname, "size": len(data)}

@app.get("/api/{app}/sessions/{session_id}/files")
def api_list_files(app: str, session_id: str, request: Request):
    user_id = get_user_id(request)
    sdir = session_dir(user_id, app, session_id)
    out = []
    for p in (sdir / "files").iterdir():
        if p.is_file():
            out.append({"name": p.name, "size": p.stat().st_size})
    return out