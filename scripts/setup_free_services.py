#!/usr/bin/env python3
"""
Interactive setup for free services
Guides you through setting up each service
"""

import os
import sys


def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_step(text):
    print(f"\n➤ {text}")


def get_input(prompt, default=""):
    if default:
        return input(f"{prompt} [{default}]: ").strip() or default
    return input(f"{prompt}: ").strip()


def update_env(key, value):
    """Update .env file with new value"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    if not os.path.exists(env_path):
        # Copy from example
        example_path = env_path + ".example"
        if os.path.exists(example_path):
            with open(example_path, 'r') as f:
                content = f.read()
        else:
            content = ""
    else:
        with open(env_path, 'r') as f:
            content = f.read()
    
    # Update or add key
    if f"{key}=" in content:
        # Replace existing
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                break
        content = '\n'.join(lines)
    else:
        # Add new
        content += f"\n{key}={value}"
    
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"  ✅ Updated {key} in .env")


def setup_supabase():
    """Setup Supabase PostgreSQL"""
    print_header("SUPABASE (PostgreSQL Database)")
    
    print("""
Steps to setup Supabase:
1. Go to https://supabase.com
2. Sign up with GitHub
3. Click "New Project"
4. Enter:
   - Name: tienda-eaciot
   - Database Password: (generate a strong password)
   - Region: East US
5. Wait ~2 minutes for setup
6. Go to Settings → Database
7. Copy the connection string
""")
    
    print_step("Enter your Supabase connection string")
    print("Format: postgresql://postgres.[ref]:[password]@[host]:5432/postgres")
    
    conn_string = get_input("Connection string")
    if conn_string:
        # Convert to async format
        async_url = conn_string.replace("postgresql://", "postgresql+asyncpg://")
        update_env("DATABASE_URL", async_url)
        return True
    return False


def setup_sendgrid():
    """Setup SendGrid for email"""
    print_header("SENDGRID (Email Service)")
    
    print("""
Steps to setup SendGrid:
1. Go to https://sendgrid.com
2. Sign up for free
3. Go to Settings → API Keys
4. Click "Create API Key"
5. Name: tienda-eaciot
6. Permissions: Full Access
7. Copy the API key (starts with SG.)
8. Go to Settings → Sender Authentication
9. Verify your email address
""")
    
    api_key = get_input("SendGrid API key (SG.xxx)")
    from_email = get_input("Verified sender email")
    
    if api_key and from_email:
        update_env("SMTP_HOST", "smtp.sendgrid.net")
        update_env("SMTP_PORT", "587")
        update_env("SMTP_USER", "apikey")
        update_env("SMTP_PASSWORD", api_key)
        update_env("SMTP_FROM", from_email)
        return True
    return False


def setup_sentry():
    """Setup Sentry for error tracking"""
    print_header("SENTRY (Error Tracking)")
    
    print("""
Steps to setup Sentry:
1. Go to https://sentry.io
2. Sign up with GitHub
3. Create organization: eaciot
4. Click "Create Project"
5. Platform: Python
6. Name: tienda-eaciot
7. Copy the DSN (https://xxx@sentry.io/xxx)
""")
    
    dsn = get_input("Sentry DSN")
    if dsn:
        update_env("SENTRY_DSN", dsn)
        return True
    return False


def setup_stripe():
    """Setup Stripe for payments"""
    print_header("STRIPE (Payment Processing)")
    
    print("""
Steps to setup Stripe:
1. Go to https://stripe.com
2. Create account
3. Go to Developers → API Keys
4. Copy:
   - Publishable key (pk_test_xxx)
   - Secret key (sk_test_xxx)
5. Go to Developers → Webhooks
6. Add endpoint: https://tu-dominio.com/payments/stripe/webhook
7. Select events: checkout.session.completed
8. Copy webhook secret (whsec_xxx)
""")
    
    publishable = get_input("Stripe Publishable Key (pk_test_xxx)")
    secret = get_input("Stripe Secret Key (sk_test_xxx)")
    webhook = get_input("Stripe Webhook Secret (whsec_xxx)")
    
    if secret:
        update_env("STRIPE_PUBLISHABLE_KEY", publishable)
        update_env("STRIPE_SECRET_KEY", secret)
        if webhook:
            update_env("STRIPE_WEBHOOK_SECRET", webhook)
        return True
    return False


def setup_paypal():
    """Setup PayPal for payments"""
    print_header("PAYPAL (Payment Processing)")
    
    print("""
Steps to setup PayPal:
1. Go to https://developer.paypal.com
2. Login with PayPal account
3. Go to Apps & Credentials
4. Create App:
   - Name: Tienda Eaciot
   - Sandbox: Yes (for testing)
5. Copy:
   - Client ID
   - Client Secret
""")
    
    client_id = get_input("PayPal Client ID")
    client_secret = get_input("PayPal Client Secret")
    
    if client_id and client_secret:
        update_env("PAYPAL_CLIENT_ID", client_id)
        update_env("PAYPAL_CLIENT_SECRET", client_secret)
        update_env("PAYPAL_MODE", "sandbox")
        return True
    return False


def setup_google_oauth():
    """Setup Google OAuth"""
    print_header("GOOGLE OAUTH (Optional)")
    
    print("""
Steps to setup Google OAuth:
1. Go to https://console.cloud.google.com
2. Create project: Tienda Eaciot
3. Go to APIs → OAuth consent screen
4. Configure:
   - App name: Tienda Eaciot
   - User support email: your email
5. Go to Credentials → Create Credentials → OAuth Client ID
6. Application type: Web application
7. Authorized redirect URIs:
   - http://localhost:8000/auth/google/callback
   - https://tu-dominio.com/auth/google/callback
8. Copy Client ID and Client Secret
""")
    
    setup = get_input("Setup Google OAuth? (y/n)", "n")
    if setup.lower() != 'y':
        return False
    
    client_id = get_input("Google Client ID")
    client_secret = get_input("Google Client Secret")
    
    if client_id and client_secret:
        update_env("GOOGLE_CLIENT_ID", client_id)
        update_env("GOOGLE_CLIENT_SECRET", client_secret)
        return True
    return False


def main():
    print_header("TIENDA EACIOT - FREE SERVICES SETUP")
    print("""
This wizard will help you setup all the free services
needed to run your store at $0/month.
""")
    
    services = [
        ("Supabase (Database)", setup_supabase),
        ("SendGrid (Email)", setup_sendgrid),
        ("Sentry (Monitoring)", setup_sentry),
        ("Stripe (Payments)", setup_stripe),
        ("PayPal (Payments)", setup_paypal),
        ("Google OAuth (Optional)", setup_google_oauth),
    ]
    
    completed = []
    
    for name, setup_func in services:
        print(f"\n{'─'*60}")
        print(f"Setting up: {name}")
        print(f"{'─'*60}")
        
        proceed = get_input(f"Setup {name}? (y/n)", "y")
        if proceed.lower() == 'y':
            if setup_func():
                completed.append(name)
            else:
                print(f"⚠️  Skipped {name}")
        else:
            print(f"⚠️  Skipped {name}")
    
    # Generate secret key
    print_header("GENERATING SECRET KEY")
    import secrets
    secret_key = secrets.token_hex(32)
    update_env("APP_SECRET_KEY", secret_key)
    print("✅ Generated secure APP_SECRET_KEY")
    
    # Summary
    print_header("SETUP SUMMARY")
    print(f"\nCompleted: {len(completed)}/{len(services)} services")
    for name in completed:
        print(f"  ✅ {name}")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("""
1. Update FRONTEND_URL in .env with your domain
2. Run: python scripts/setup_production.py
3. Deploy to your hosting
4. Test the complete flow
""")


if __name__ == "__main__":
    main()
