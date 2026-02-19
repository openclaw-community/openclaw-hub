"""
Credential encryption utilities for dashboard connections.
Uses Fernet symmetric encryption.
"""

import os
from cryptography.fernet import Fernet


def get_or_create_secret_key() -> str:
    """
    Returns the dashboard secret key from environment.
    If not set, generates one, appends to .env, and prints a warning.
    """
    key = os.environ.get("DASHBOARD_SECRET_KEY")
    if key:
        return key

    # Generate new key
    new_key = Fernet.generate_key().decode()

    # Find .env file (look in project root: aigateway/dashboard/ -> aigateway/ -> project root)
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    with open(env_path, "a") as f:
        f.write(f"\n# Dashboard credential encryption key (auto-generated)\nDASHBOARD_SECRET_KEY={new_key}\n")

    os.environ["DASHBOARD_SECRET_KEY"] = new_key
    print(f"⚠️  Generated DASHBOARD_SECRET_KEY and saved to .env. Keep this secret safe.")
    return new_key


def encrypt_value(value: str, key: str) -> str:
    if not value:
        return ""
    f = Fernet(key.encode())
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str, key: str) -> str:
    if not encrypted:
        return ""
    f = Fernet(key.encode())
    return f.decrypt(encrypted.encode()).decode()


def mask_value(value: str) -> str:
    """Show first 4 and last 4 characters only."""
    if not value or len(value) < 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"
