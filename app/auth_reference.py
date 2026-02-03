"""
Quick Reference: Using Authentication in Lumina Backend
"""

# ============================================================
# ✅ CORRECT USAGE
# ============================================================

from fastapi import Request
from app.auth import get_user_id, get_user_email

# For any endpoint that accesses user data:
@app.post("/api/{app}/sessions")
async def create_session(app: str, request: Request):
    user_id = get_user_id(request)  # ✅ Use this for data access
    sessions = list_sessions(user_id, app)
    # ...

# For displaying user info:
@app.get("/api/me")
def me(request: Request):
    email = get_user_email(request)  # ✅ Use this ONLY for display
    return {"email": email}


# ============================================================
# ❌ INCORRECT USAGE
# ============================================================

# DON'T use email for data access:
@app.post("/api/{app}/sessions")
async def create_session(app: str, request: Request):
    email = get_user_email(request)  # ❌ WRONG!
    sessions = list_sessions(email, app)  # ❌ Security issue!
    # ...

# DON'T access headers directly:
@app.post("/api/{app}/sessions")
async def create_session(app: str, request: Request):
    email = request.headers.get("Cf-Access-Authenticated-User-Email")  # ❌ WRONG!
    # Always use get_user_id() or get_user_email()


# ============================================================
# 🔐 DEVELOPMENT MODE
# ============================================================

# Set environment variable:
# export LUMINA_DEV_EMAIL="dev@localhost.local"

# Or in .env file:
# LUMINA_DEV_EMAIL=dev@localhost.local


# ============================================================
# 📝 REMEMBER
# ============================================================

# 1. Use get_user_id() for ALL data access
# 2. Use get_user_email() ONLY for display
# 3. Both functions raise 401 if not authenticated
# 4. In production, Cloudflare Access provides the email header
# 5. In dev mode, use LUMINA_DEV_EMAIL environment variable
