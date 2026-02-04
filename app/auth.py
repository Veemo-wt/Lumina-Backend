import os
import hashlib
from fastapi import Request, HTTPException

def _hash_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()

def get_user_id(request: Request) -> str:
    # 1) API KEY (publiczne API z kluczem)
    expected = os.getenv("LUMINA_API_KEY")
    if expected:
        got = request.headers.get("X-API-Key")
        if got and got == expected:
            # stały user_id dla "publicznych" klientów (albo można zrobić per-key)
            return _hash_email("api-key-user@lumina-suite")

    # 2) Cloudflare Access (dla prywatnych endpointów)
    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if email:
        return _hash_email(email)

    # 3) DEV
    dev_email = os.getenv("LUMINA_DEV_EMAIL")
    if dev_email:
        return _hash_email(dev_email)

    raise HTTPException(status_code=401, detail="Unauthorized")


def get_user_email(request: Request) -> str:
    # jeśli wszedł API-Key, to nie mamy real email — zwróć np. "api-key-user"
    expected = os.getenv("LUMINA_API_KEY")
    got = request.headers.get("X-API-Key")
    if expected and got == expected:
        return "api-key-user"

    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if email:
        return email

    dev_email = os.getenv("LUMINA_DEV_EMAIL")
    if dev_email:
        return dev_email

    raise HTTPException(status_code=401, detail="Unauthorized")