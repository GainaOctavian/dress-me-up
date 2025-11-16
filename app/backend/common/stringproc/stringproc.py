import bcrypt

import uuid

from pydantic import SecretStr


def generate_id() -> str:
    """Generate a unique identifier string"""
    return str(uuid.uuid4())


def hash_password(password: str | SecretStr) -> str:
    """Hash a password using bcrypt"""
    if isinstance(password, SecretStr):
        password = password.get_secret_value()

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str | SecretStr, hashed: str) -> bool:
    """Verify a password against a hashed password"""
    if isinstance(password, SecretStr):
        password = password.get_secret_value()

    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))