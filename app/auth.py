"""
Lumina Suite Authentication Module
Handles user authentication via Cloudflare Access headers
"""
import os
import hashlib
from fastapi import Request, HTTPException


def get_user_id(request: Request) -> str:
    """
    Get hashed user ID from authenticated email.

    In production: Extracts email from Cloudflare Access header and returns SHA256 hash.
    In development: Uses LUMINA_DEV_EMAIL environment variable.

    Raises:
        HTTPException: 401 Unauthorized if no authenticated email is found

    Returns:
        str: SHA256 hash of the user's email address
    """
    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if not email:
        # DEV MODE: Use mock email for local development
        dev_email = os.getenv("LUMINA_DEV_EMAIL")
        if dev_email:
            print(f"⚠️  DEV MODE: Using mock email: {dev_email}")
            return hashlib.sha256(dev_email.encode()).hexdigest()
        raise HTTPException(status_code=401, detail="Unauthorized")

    return hashlib.sha256(email.encode()).hexdigest()


def get_user_email(request: Request) -> str:
    """
    Get user email for display purposes only.

    WARNING: This should only be used when you need to show the email to the user.
    For data storage and access control, always use get_user_id() instead.

    Raises:
        HTTPException: 401 Unauthorized if no authenticated email is found

    Returns:
        str: The user's email address
    """
    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if not email:
        # DEV MODE: Use mock email for local development
        dev_email = os.getenv("LUMINA_DEV_EMAIL")
        if dev_email:
            print(f"⚠️  DEV MODE: Using mock email: {dev_email}")
            return dev_email
        raise HTTPException(status_code=401, detail="Unauthorized")

    return email
