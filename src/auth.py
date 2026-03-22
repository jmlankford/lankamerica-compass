"""
auth.py — Authentication helpers for LankAmerica Compass
"""
import bcrypt
from typing import Optional


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt. Returns string."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_user(db, username: str, password: str, display_name: str) -> int:
    """
    Create a new user in the database.
    Returns the new user's id.
    Raises ValueError if username is already taken.
    """
    existing = db.get_user_by_username(username)
    if existing is not None:
        raise ValueError(f"Username '{username}' is already taken.")
    if not username.strip():
        raise ValueError("Username cannot be empty.")
    if not password:
        raise ValueError("Password cannot be empty.")
    if not display_name.strip():
        raise ValueError("Display name cannot be empty.")
    pw_hash = hash_password(password)
    user_id = db.create_user(username.strip(), pw_hash, display_name.strip())
    return user_id


def authenticate(db, username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user. Returns a user dict if successful, else None.
    """
    user = db.get_user_by_username(username)
    if user is None:
        return None
    if verify_password(password, user['password_hash']):
        return user
    return None
