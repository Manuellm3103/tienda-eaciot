#!/usr/bin/env python3
"""Script to create admin user"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import async_session
from app.models.user import User
from app.services.auth_service import get_password_hash


async def create_admin(email: str, password: str, name: str = "Admin"):
    """Create admin user"""
    async with async_session() as db:
        # Check if admin exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"User {email} already exists")
            return
        
        admin = User(
            email=email,
            hashed_password=get_password_hash(password),
            name=name,
            is_admin=True,
            email_verified=True,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Admin user created: {email}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [name]")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    asyncio.run(create_admin(email, password, name))
