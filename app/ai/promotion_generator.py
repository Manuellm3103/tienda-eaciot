from app.ai.ollama_client import ollama_client
import json


class PromotionGenerator:
    async def suggest_promotion(self, sales_data: dict, customer_segments: dict) -> dict:
        system = """Eres un experto en marketing de e-commerce.
Sugiere promociones basadas en datos de ventas y segmentos de clientes.
Responde en JSON."""
        
        prompt = f"""Datos de ventas:
{json.dumps(sales_data, indent=2)}

Segmentos de clientes:
{json.dumps(customer_segments, indent=2)}

Sugiere 3 promociones efectivas y responde en JSON:
{{
    "suggestions": [
        {{
            "title": "<título>",
            "description": "<descripción>",
            "discount_type": "<percentage/fixed>",
            "discount_value": <valor>,
            "target_segment": "<segmento>",
            "estimated_redemption": "<% estimado>",
            "reasoning": "<por qué funcionaría>"
        }}
    ]
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {"suggestions": []}
    
    async def generate_promo_text(self, promotion_data: dict) -> dict:
        system = """Genera textos de marketing atractivos para una promoción."""
        
        prompt = f"""Promoción:
- Título: {promotion_data['title']}
- Descuento: {promotion_data['discount_value']}%
- Productos: {promotion_data.get('products', 'todos')}

Genera:
1. Asunto de email atractivo
2. Cuerpo de email corto
3. Texto de banner

Responde en JSON:
{{
    "email_subject": "<asunto>",
    "email_body": "<cuerpo>",
    "banner_text": "<banner>"
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {
                "email_subject": f"¡{promotion_data['discount_value']}% de descuento!",
                "email_body": "Aprovecha esta oferta especial.",
                "banner_text": f"¡{promotion_data['discount_value']}% OFF!",
            }


promotion_generator = PromotionGenerator()
