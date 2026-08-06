# Configurar Stripe

## Paso 1: Crear cuenta en Stripe

1. Ir a https://stripe.com
2. Crear cuenta
3. Completar verificación

## Paso 2: Obtener API Keys

1. Ir a https://dashboard.stripe.com/apikeys
2. Copiar:
   - Publishable key (pk_test_xxx o pk_live_xxx)
   - Secret key (sk_test_xxx o sk_live_xxx)

## Paso 3: Configurar Webhooks

1. Ir a https://dashboard.stripe.com/webhooks
2. "Add endpoint"
3. Endpoint URL: https://tienda.eaciot.com/payments/stripe/webhook
4. Events to send:
   - checkout.session.completed
   - checkout.session.async_payment_succeeded
   - checkout.session.async_payment_failed
5. Copiar Webhook signing secret (whsec_xxx)

## Paso 4: Configurar .env

```env
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
```

## Paso 5: Cambiar a producción

Cuando estés listo para producción:

1. Ir a https://dashboard.stripe.com/apikeys
2. Cambiar a "Live mode"
3. Generar nuevas API keys
4. Actualizar .env con las keys de producción
5. Actualizar webhook URL si es necesario

---

## Testing

### Tarjetas de prueba

| Tarjeta | Resultado |
|---------|-----------|
| 4242 4242 4242 4242 | Pago exitoso |
| 4000 0000 0000 0002 | Pago fallido |
| 4000 0025 0000 3155 | Requiere 3D Secure |

### Webhook testing

```bash
# Instalar Stripe CLI
stripe listen --forward-to localhost:8000/payments/stripe/webhook
```

---

## Checklist

- [ ] Cuenta Stripe creada
- [ ] API keys obtenidas
- [ ] Webhook configurado
- [ ] .env actualizado
- [ ] Pago de prueba exitoso
