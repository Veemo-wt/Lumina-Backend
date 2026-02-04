import os
import hashlib
from fastapi import Request, HTTPException

def _hash_username(username: str) -> str:
    """Hash username to create a unique user_id"""
    return hashlib.sha256(username.encode()).hexdigest()

def get_user_id(request: Request) -> str:
    """
    Get hashed user ID. Priority:
    1. X-Username header (manual username from frontend)
    2. API KEY (for programmatic access)
    3. Cloudflare Access email (legacy)
    4. DEV email (local development)
    """
    # 1) X-Username (manual username from frontend)
    username = request.headers.get("X-Username")
    if username:
        return _hash_username(username)

    # 2) API KEY (publiczne API z kluczem)
    expected = os.getenv("LUMINA_API_KEY")
    if expected:
        got = request.headers.get("X-API-Key")
        if got and got == expected:
            return _hash_username("api-key-user")

    # 3) Cloudflare Access (dla prywatnych endpointów - legacy)
    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if email:
        return _hash_username(email)

    # 4) DEV
    dev_email = os.getenv("LUMINA_DEV_EMAIL")
    if dev_email:
        return _hash_username(dev_email)

    raise HTTPException(status_code=401, detail="Unauthorized: Missing X-Username header")


def get_user_email(request: Request) -> str:
    """Get username/email for display purposes"""
    # 1) X-Username (manual username from frontend)
    username = request.headers.get("X-Username")
    if username:
        return username

    # 2) jeśli wszedł API-Key, to nie mamy real email — zwróć np. "api-key-user"
    expected = os.getenv("LUMINA_API_KEY")
    got = request.headers.get("X-API-Key")
    if expected and got == expected:
        return "api-key-user"

    # 3) Cloudflare Access (legacy)
    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if email:
        return email

    # 4) DEV
    dev_email = os.getenv("LUMINA_DEV_EMAIL")
    if dev_email:
        return dev_email

    raise HTTPException(status_code=401, detail="Unauthorized: Missing X-Username header")
