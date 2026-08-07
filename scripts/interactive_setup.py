#!/usr/bin/env python3
"""
Setup interactivo para TDAH - Paso a paso con feedback visual
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# Colores para la terminal (Windows compatible)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_slow(text, delay=0.02):
    """Print text slowly"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def print_header(text):
    clear_screen()
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}  {text}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_step(step_num, total, text):
    progress = "#" * step_num + "." * (total - step_num)
    percentage = int((step_num / total) * 100)
    print(f"\n{Colors.YELLOW}[{progress}] {percentage}%{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}>>> Paso {step_num}/{total}:{Colors.END} {text}\n")

def print_success(text):
    print(f"{Colors.GREEN}  [OK] {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}  [ERROR] {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}  [INFO] {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}  [!] {text}{Colors.END}")

def get_input(prompt, default=""):
    if default:
        return input(f"\n  {prompt} [{default}]: ").strip() or default
    return input(f"\n  {prompt}: ").strip()

def wait_for_key():
    input(f"\n  Presiona ENTER para continuar...")

def update_env(key, value):
    """Update .env file"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    if not os.path.exists(env_path):
        example_path = env_path + ".example"
        if os.path.exists(example_path):
            with open(example_path, 'r') as f:
                content = f.read()
        else:
            content = ""
    else:
        with open(env_path, 'r') as f:
            content = f.read()
    
    if f"{key}=" in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                break
        content = '\n'.join(lines)
    else:
        content += f"\n{key}={value}"
    
    with open(env_path, 'w') as f:
        f.write(content)

# ==================== PASOS DEL SETUP ====================

def paso_bienvenida():
    """Paso 0: Bienvenida"""
    print_header("TIENDA EACIOT - SETUP INTERACTIVO")
    
    print(f"""
{Colors.BOLD}Hola!{Colors.END}

Voy a ayudar a configurar tu tienda online {Colors.GREEN}paso a paso{Colors.END}.

{Colors.CYAN}Esto tomara ~30 minutos.{Colors.END}

{Colors.YELLOW}Lo que haremos:{Colors.END}
  1. Configurar base de datos (Supabase - gratis)
  2. Configurar emails (SendGrid - gratis)
  3. Configurar pagos (Stripe + PayPal)
  4. Configurar monitoreo (Sentry - gratis)
  5. Deploy a tu hosting

{Colors.BOLD}Empecemos!{Colors.END}
""")
    wait_for_key()

def paso_1_supabase():
    """Paso 1: Configurar Supabase"""
    print_step(1, 6, "Configurar Base de Datos (Supabase)")
    
    print(f"""
{Colors.BOLD}Que es Supabase?{Colors.END}
  Es tu base de datos en la nube. {Colors.GREEN}Gratis hasta 500MB.{Colors.END}

{Colors.YELLOW}Pasos:{Colors.END}
  1. Ve a https://supabase.com
  2. Crea cuenta con GitHub
  3. Click "New Project"
  4. Nombre: tienda-eaciot
  5. Contrasena: (guardala)
  6. Region: East US
  7. Espera ~2 minutos
  8. Ve a Settings -> Database
  9. Copia la connection string
""")
    
    wait_for_key()
    
    print(f"\n{Colors.BOLD}Pega tu connection string:{Colors.END}")
    print(f"{Colors.BLUE}(Empieza con postgresql://...){Colors.END}")
    
    conn_string = get_input("Connection string")
    
    if conn_string and "postgresql://" in conn_string:
        async_url = conn_string.replace("postgresql://", "postgresql+asyncpg://")
        update_env("DATABASE_URL", async_url)
        print_success("Base de datos configurada!")
        time.sleep(1)
        return True
    else:
        print_error("Connection string no valido")
        print_info("Formato: postgresql://postgres.xxx:password@host:5432/postgres")
        wait_for_key()
        return False

def paso_2_sendgrid():
    """Paso 2: Configurar SendGrid"""
    print_step(2, 6, "Configurar Emails (SendGrid)")
    
    print(f"""
{Colors.BOLD}Que es SendGrid?{Colors.END}
  Servicio de emails. {Colors.GREEN}Gratis 100 emails/dia.{Colors.END}

{Colors.YELLOW}Pasos:{Colors.END}
  1. Ve a https://sendgrid.com
  2. Crea cuenta gratis
  3. Ve a Settings -> API Keys
  4. Click "Create API Key"
  5. Nombre: tienda-eaciot
  6. Permisos: Full Access
  7. Copia la key (empieza con SG.)
  8. Ve a Settings -> Sender Authentication
  9. Verifica tu email
""")
    
    wait_for_key()
    
    api_key = get_input("API Key de SendGrid (SG.xxx)")
    from_email = get_input("Tu email verificado")
    
    if api_key and from_email:
        update_env("SMTP_HOST", "smtp.sendgrid.net")
        update_env("SMTP_PORT", "587")
        update_env("SMTP_USER", "apikey")
        update_env("SMTP_PASSWORD", api_key)
        update_env("SMTP_FROM", from_email)
        print_success("Emails configurados!")
        time.sleep(1)
        return True
    else:
        print_error("Faltan datos")
        return False

def paso_3_stripe():
    """Paso 3: Configurar Stripe"""
    print_step(3, 6, "Configurar Pagos (Stripe)")
    
    print(f"""
{Colors.BOLD}Que es Stripe?{Colors.END}
  Procesador de pagos con tarjeta.
  {Colors.YELLOW}Cobra 2.9% + $0.30 por transaccion.{Colors.END}

{Colors.YELLOW}Pasos:{Colors.END}
  1. Ve a https://stripe.com
  2. Crea cuenta
  3. Ve a Developers -> API Keys
  4. Copia:
     - Publishable key (pk_test_xxx)
     - Secret key (sk_test_xxx)
""")
    
    wait_for_key()
    
    publishable = get_input("Publishable Key (pk_test_xxx)")
    secret = get_input("Secret Key (sk_test_xxx)")
    
    if secret:
        update_env("STRIPE_PUBLISHABLE_KEY", publishable)
        update_env("STRIPE_SECRET_KEY", secret)
        print_success("Stripe configurado!")
        print_info("Webhook: Configuralo despues en Stripe Dashboard")
        time.sleep(1)
        return True
    else:
        print_error("Falta la Secret Key")
        return False

def paso_4_paypal():
    """Paso 4: Configurar PayPal"""
    print_step(4, 6, "Configurar Pagos (PayPal)")
    
    print(f"""
{Colors.BOLD}Por que PayPal?{Colors.END}
  Da mas opciones a tus clientes.
  {Colors.YELLOW}Mismo costo que Stripe.{Colors.END}

{Colors.YELLOW}Pasos:{Colors.END}
  1. Ve a https://developer.paypal.com
  2. Login con tu PayPal
  3. Apps & Credentials -> Create App
  4. Nombre: Tienda Eaciot
  5. Sandbox: Si
  6. Copia Client ID y Secret
""")
    
    wait_for_key()
    
    setup = get_input("Configurar PayPal? (s/n)", "s")
    
    if setup.lower() == 's':
        client_id = get_input("Client ID")
        client_secret = get_input("Client Secret")
        
        if client_id and client_secret:
            update_env("PAYPAL_CLIENT_ID", client_id)
            update_env("PAYPAL_CLIENT_SECRET", client_secret)
            update_env("PAYPAL_MODE", "sandbox")
            print_success("PayPal configurado!")
            time.sleep(1)
            return True
    
    print_info("PayPal opcional - puedes configurarlo despues")
    return True

def paso_5_sentry():
    """Paso 5: Configurar Sentry"""
    print_step(5, 6, "Configurar Monitoreo (Sentry)")
    
    print(f"""
{Colors.BOLD}Que es Sentry?{Colors.END}
  Detecta errores automaticamente.
  {Colors.GREEN}Gratis hasta 5,000 errores/mes.{Colors.END}

{Colors.YELLOW}Pasos:{Colors.END}
  1. Ve a https://sentry.io
  2. Crea cuenta con GitHub
  3. Create Project -> Python
  4. Nombre: tienda-eaciot
  5. Copia el DSN
""")
    
    wait_for_key()
    
    setup = get_input("Configurar Sentry? (s/n)", "s")
    
    if setup.lower() == 's':
        dsn = get_input("Sentry DSN (https://xxx@sentry.io/xxx)")
        
        if dsn:
            update_env("SENTRY_DSN", dsn)
            print_success("Sentry configurado!")
            time.sleep(1)
            return True
    
    print_info("Sentry opcional - puedes configurarlo despues")
    return True

def paso_6_verificar():
    """Paso 6: Verificar todo"""
    print_step(6, 6, "Verificar Configuracion")
    
    print(f"\n{Colors.BOLD}Verificando servicios...{Colors.END}\n")
    
    # Check .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        print_success("Archivo .env existe")
        
        with open(env_path, 'r') as f:
            content = f.read()
        
        checks = [
            ("DATABASE_URL", "postgresql+asyncpg://" in content),
            ("SMTP_PASSWORD", "SMTP_PASSWORD=SG." in content),
            ("STRIPE_SECRET_KEY", "STRIPE_SECRET_KEY=sk_" in content),
        ]
        
        for name, ok in checks:
            if ok:
                print_success(f"{name} configurado")
            else:
                print_warning(f"{name} pendiente")
    else:
        print_error("Archivo .env no encontrado")
    
    # Generate secret key
    import secrets
    secret_key = secrets.token_hex(32)
    update_env("APP_SECRET_KEY", secret_key)
    print_success("Secret key generado")
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}  CONFIGURACION COMPLETADA!{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")

def paso_final():
    """Mostrar pasos finales"""
    print_header("SIGUIENTE PASO!")
    
    print(f"""
{Colors.BOLD}Tu tienda esta configurada.{Colors.END}

{Colors.YELLOW}Ahora necesitas:{Colors.END}

  {Colors.CYAN}1.{Colors.END} Subir archivos a tu hosting (cPanel)
     - Usa File Manager o Git
     
  {Colors.CYAN}2.{Colors.END} En cPanel, ejecutar:
     {Colors.GREEN}pip install -r requirements.txt{Colors.END}
     {Colors.GREEN}alembic upgrade head{Colors.END}
     {Colors.GREEN}python scripts/create_admin.py admin@eaciot.com TU_PASSWORD{Colors.END}
     
  {Colors.CYAN}3.{Colors.END} Configurar Python App en cPanel
     - Application root: /home/USER/tienda
     - Application URL: tienda.eaciot.com
     - Startup file: passenger_wsgi.py
     
  {Colors.CYAN}4.{Colors.END} Probar!
     {Colors.GREEN}curl https://tienda.eaciot.com/health{Colors.END}

{Colors.BOLD}Necesitas ayuda con algun paso?{Colors.END}
""")
    
    print(f"\n{Colors.GREEN}Exito con tu tienda!{Colors.END}\n")

# ==================== MAIN ====================

def main():
    try:
        paso_bienvenida()
        
        # Paso 1: Supabase
        while not paso_1_supabase():
            retry = get_input("Reintentar? (s/n)", "s")
            if retry.lower() != 's':
                break
        
        # Paso 2: SendGrid
        while not paso_2_sendgrid():
            retry = get_input("Reintentar? (s/n)", "s")
            if retry.lower() != 's':
                break
        
        # Paso 3: Stripe
        while not paso_3_stripe():
            retry = get_input("Reintentar? (s/n)", "s")
            if retry.lower() != 's':
                break
        
        # Paso 4: PayPal
        paso_4_paypal()
        
        # Paso 5: Sentry
        paso_5_sentry()
        
        # Paso 6: Verificar
        paso_6_verificar()
        
        wait_for_key()
        
        # Paso final
        paso_final()
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup cancelado. Puedes continuar despues.{Colors.END}\n")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")

if __name__ == "__main__":
    main()
