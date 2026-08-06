# Configurar SMTP con Gmail

## Paso 1: Habilitar verificación en 2 pasos

1. Ir a https://myaccount.google.com/security
2. Buscar "Verificación en 2 pasos"
3. Activar si no está activo

## Paso 2: Crear App Password

1. Ir a https://myaccount.google.com/apppasswords
2. Seleccionar "Otra (nombre personalizado)"
3. Escribir: "Tienda Eaciot"
4. Click en "Generar"
5. Copiar la contraseña de 16 caracteres

## Paso 3: Configurar .env

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=abcd-efgh-ijkl-mnop  # La app password de 16 caracteres
SMTP_FROM=tu-email@gmail.com
SMTP_TLS=true
```

## Notas importantes

- La app password es diferente a tu contraseña normal
- Si cambias la contraseña de Google, debes regenerar la app password
- Para producción, considera usar un servicio como SendGrid o Mailgun
