#!/usr/bin/env python3
"""
Setup script for production deployment
Run this after configuring .env with all service credentials
"""

import asyncio
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings


async def check_database():
    """Check database connection"""
    print("\n📦 Checking database connection...")
    try:
        from app.database import engine
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def check_email():
    """Check email configuration"""
    print("\n📧 Checking email configuration...")
    try:
        from app.services.email_service import email_service
        if email_service.smtp_user and email_service.smtp_password:
            print("✅ Email configuration found")
            return True
        else:
            print("⚠️  Email not configured (optional)")
            return True
    except Exception as e:
        print(f"❌ Email configuration error: {e}")
        return False


async def run_migrations():
    """Run database migrations"""
    print("\n🔄 Running database migrations...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        if result.returncode == 0:
            print("✅ Migrations completed successfully")
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False


async def create_admin():
    """Create admin user"""
    print("\n👤 Creating admin user...")
    
    email = input("Admin email (admin@eaciot.com): ").strip() or "admin@eaciot.com"
    password = input("Admin password: ").strip()
    
    if not password:
        print("❌ Password is required")
        return False
    
    name = input("Admin name (Admin): ").strip() or "Admin"
    
    try:
        from app.database import async_session
        from app.models.user import User
        from app.services.auth_service import get_password_hash
        from sqlalchemy import select
        
        async with async_session() as db:
            # Check if admin exists
            result = await db.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⚠️  User {email} already exists")
                return True
            
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
            print(f"✅ Admin user created: {email}")
            return True
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        return False


async def create_sample_data():
    """Create sample categories and products"""
    print("\n📦 Creating sample data...")
    
    try:
        from app.database import async_session
        from app.models.product import Category, Product
        from sqlalchemy import select
        
        async with async_session() as db:
            # Check if categories exist
            result = await db.execute(select(Category).limit(1))
            if result.scalar_one_or_none():
                print("⚠️  Sample data already exists")
                return True
            
            # Create categories
            categories = [
                Category(name="Ebooks", slug="ebooks", description="Libros digitales"),
                Category(name="Cursos", slug="cursos", description="Cursos online"),
                Category(name="Software", slug="software", description="Licencias de software"),
                Category(name="Templates", slug="templates", description="Plantillas y diseños"),
                Category(name="Productos Físicos", slug="fisicos", description="Productos físicos"),
            ]
            
            for cat in categories:
                db.add(cat)
            
            await db.commit()
            print("✅ Sample categories created")
            return True
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False


async def verify_setup():
    """Verify the complete setup"""
    print("\n🔍 Verifying setup...")
    
    checks = [
        ("Database", check_database()),
        ("Email", check_email()),
    ]
    
    results = []
    for name, check in checks:
        result = await check
        results.append((name, result))
    
    print("\n" + "="*50)
    print("SETUP VERIFICATION SUMMARY")
    print("="*50)
    
    all_ok = True
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if not result:
            all_ok = False
    
    return all_ok


async def main():
    """Main setup function"""
    print("="*50)
    print("TIENDA EACIOT - PRODUCTION SETUP")
    print("="*50)
    
    # Check if .env exists
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        print("\n❌ .env file not found!")
        print("Please copy .env.example to .env and configure it first.")
        return
    
    # Run setup steps
    print("\n🚀 Starting setup...")
    
    # 1. Run migrations
    if not await run_migrations():
        print("\n❌ Setup failed at migrations")
        return
    
    # 2. Create admin
    if not await create_admin():
        print("\n❌ Setup failed at admin creation")
        return
    
    # 3. Create sample data
    await create_sample_data()
    
    # 4. Verify setup
    if await verify_setup():
        print("\n" + "="*50)
        print("✅ SETUP COMPLETED SUCCESSFULLY!")
        print("="*50)
        print("\nYour store is ready at:", settings.frontend_url)
        print("\nNext steps:")
        print("1. Visit your store and login")
        print("2. Add products via admin panel")
        print("3. Configure payment methods")
        print("4. Test the complete flow")
    else:
        print("\n" + "="*50)
        print("⚠️  SETUP COMPLETED WITH WARNINGS")
        print("="*50)
        print("\nPlease fix the issues above before going to production.")


if __name__ == "__main__":
    asyncio.run(main())
