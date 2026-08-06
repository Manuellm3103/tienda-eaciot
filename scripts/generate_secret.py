#!/usr/bin/env python3
"""Generate a secure secret key"""

import secrets
import string


def generate_secret_key(length: int = 64) -> str:
    """Generate a secure random secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


if __name__ == "__main__":
    key = generate_secret_key()
    print(f"Tu clave secreta (copia a .env como APP_SECRET_KEY):")
    print(f"\n{key}\n")
