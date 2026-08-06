# Configurar PayPal

## Paso 1: Crear cuenta PayPal Business

1. Ir a https://www.paypal.com/business
2. Crear cuenta business
3. Completar verificación

## Paso 2: Crear aplicación en Developer Dashboard

1. Ir a https://developer.paypal.com/dashboard
2. Iniciar sesión
3. "My Apps & Credentials"
4. "Create App"
5. App Name: Tienda Eaciot
6. Sandbox → Create

## Paso 3: Obtener credenciales

1. Ir a la aplicación creada
2. Copiar:
   - Client ID
   - Client Secret

## Paso 4: Configurar .env

```env
PAYPAL_CLIENT_ID=xxxx
PAYPAL_CLIENT_SECRET=xxxxx
PAYPAL_MODE=sandbox
```

## Paso 5: Cambiar a producción

1. En Developer Dashboard, cambiar a "Live"
2. Crear nueva app para producción
3. Obtener credenciales de producción
4. Actualizar .env:
   ```env
   PAYPAL_MODE=live
   ```

---

## Testing

### Cuentas de prueba

En https://developer.paypal.com → Sandbox → Accounts:
- Business account (vendedor)
- Personal account (comprador)

### Testing flow

1. Crear orden con sandbox credentials
2. Login con cuenta personal de prueba
3. Aprobar pago
4. Verificar webhook

---

## Checklist

- [ ] Cuenta PayPal Business creada
- [ ] App creada en Developer Dashboard
- [ ] Credenciales obtenidas
- [ ] .env actualizado
- [ ] Pago de prueba exitoso
