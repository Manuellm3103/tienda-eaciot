from app.ai.ollama_client import ollama_client
import json


class WelcomeGenerator:
    async def generate_welcome_message(self, customer_data: dict, event_type: str) -> dict:
        system = """Genera mensajes de felicitación personalizados y cálidos para clientes fieles.
El tono debe ser cercano y agradecido."""
        
        prompt = f"""Cliente:
- Nombre: {customer_data.get('name', 'Cliente')}
- Nivel: {customer_data['loyalty_level']}
- Total gastado: ${customer_data['total_spent']}
- Compras realizadas: {customer_data['purchase_count']}
- Evento: {event_type}

Genera un mensaje de felicitación personalizado y responde en JSON:
{{
    "subject": "<asunto del email>",
    "greeting": "<saludo personalizado>",
    "body": "<cuerpo del mensaje>",
    "call_to_action": "<texto del botón>",
    "ps": "<post data opcional>"
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {
                "subject": "¡Felicidades por tu logro!",
                "greeting": f"¡Hola {customer_data.get('name', '')}!",
                "body": "Gracias por ser un cliente tan valioso para nosotros.",
                "call_to_action": "Ver tu recompensa",
                "ps": "",
            }
    
    async def suggest_congratulation_rule(self, customer_data: dict) -> dict:
        system = """Basado en datos de clientes, sugiere reglas de felicitación efectivas."""
        
        prompt = f"""Datos de clientes:
{json.dumps(customer_data, indent=2)}

Sugiere 3 reglas de felicitación y responde en JSON:
{{
    "rules": [
        {{
            "name": "<nombre>",
            "event_type": "<total_spent/purchase_count/loyalty_level_up>",
            "event_value": <valor>,
            "reward_type": "<coupon/points>",
            "reward_value": <valor>,
            "reasoning": "<por qué>"
        }}
    ]
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {"rules": []}


welcome_generator = WelcomeGenerator()
