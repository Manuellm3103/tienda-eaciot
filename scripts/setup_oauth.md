# Configurar OAuth Providers

## Google OAuth

### Paso 1: Crear proyecto en Google Cloud

1. Ir a https://console.cloud.google.com
2. Crear nuevo proyecto: "Tienda Eaciot"

### Paso 2: Habilitar APIs

1. Ir a "APIs & Services" → "Library"
2. Buscar y habilitar:
   - Google+ API
   - People API

### Paso 3: Configurar OAuth consent screen

1. Ir a "OAuth consent screen"
2. Seleccionar "External"
3. Completar información:
   - App name: Tienda Eaciot
   - User support email: tu-email@gmail.com
4. Agregar scopes:
   - email
   - profile
   - openid
5. Agregar test users (tus emails)

### Paso 4: Crear credenciales

1. Ir a "Credentials"
2. "Create Credentials" → "OAuth client ID"
3. Application type: Web application
4. Name: Tienda Eaciot
5. Authorized redirect URIs:
   - http://localhost:8000/auth/google/callback (desarrollo)
   - https://tienda.eaciot.com/auth/google/callback (producción)
6. Copiar Client ID y Client Secret

### Paso 5: Configurar .env

```env
GOOGLE_CLIENT_ID=123456789-xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GOOGLE_REDIRECT_URI=https://tienda.eaciot.com/auth/google/callback
```

---

## Microsoft OAuth

### Paso 1: Crear aplicación en Azure

1. Ir a https://portal.azure.com
2. Azure Active Directory → App registrations
3. "New registration"
4. Name: Tienda Eaciot
5. Supported account types: Cualquiera
6. Redirect URI:
   - Web: https://tienda.eaciot.com/auth/microsoft/callback

### Paso 2: Crear client secret

1. Ir a "Certificates & secrets"
2. "New client secret"
3. Description: Tienda Eaciot
4. Expiración: 24 meses
5. Copiar el valor del secret

### Paso 3: Configurar .env

```env
MICROSOFT_CLIENT_ID=xxxx-xxxx-xxxx
MICROSOFT_CLIENT_SECRET=xxxxx
MICROSOFT_REDIRECT_URI=https://tienda.eaciot.com/auth/microsoft/callback
```

---

## GitHub OAuth

### Paso 1: Crear OAuth App

1. Ir a https://github.com/settings/developers
2. "OAuth Apps" → "New OAuth App"
3. Application name: Tienda Eaciot
4. Homepage URL: https://tienda.eaciot.com
5. Authorization callback URL: https://tienda.eaciot.com/auth/github/callback

### Paso 2: Generar client secret

1. Ir a la aplicación creada
2. "Generate a new client secret"
3. Copiar el secret

### Paso 3: Configurar .env

```env
GITHUB_CLIENT_ID=xxxx
GITHUB_CLIENT_SECRET=xxxxx
GITHUB_REDIRECT_URI=https://tienda.eaciot.com/auth/github/callback
```

---

## Checklist

### Google
- [ ] Proyecto creado en Google Cloud
- [ ] APIs habilitadas (Google+, People)
- [ ] OAuth consent screen configurado
- [ ] Credenciales creadas
- [ ] Redirect URIs configurados

### Microsoft
- [ ] Aplicación registrada en Azure AD
- [ ] Client secret creado
- [ ] Redirect URI configurado

### GitHub
- [ ] OAuth App creada
- [ ] Client secret generado
- [ ] Callback URL configurado
