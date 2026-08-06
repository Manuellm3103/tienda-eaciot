from app.ai.ollama_client import ollama_client
from typing import List, Dict
import json


class CustomerAnalyzer:
    async def analyze_customer(self, customer_data: dict) -> dict:
        system = """Eres un analista de clientes de e-commerce. 
Analiza los datos del cliente y proporciona:
1. Score RFM (Recency, Frequency, Monetary) del 0-100
2. Segmento (nuevo, frecuente, fiel, en riesgo, perdido)
3. Recomendación de acción
Responde en JSON."""
        
        prompt = f"""Datos del cliente:
- Total gastado: ${customer_data['total_spent']}
- Compras realizadas: {customer_data['purchase_count']}
- Última compra: {customer_data.get('last_purchase', 'N/A')}
- Nivel actual: {customer_data['loyalty_level']}
- Productos comprados: {customer_data.get('products', [])}

Analiza este cliente y responde en JSON con:
{{
    "fidel_score": <0-100>,
    "segment": "<segmento>",
    "recommendation": "<acción sugerida>",
    "risk_level": "<bajo/medio/alto>"
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {
                "fidel_score": 50,
                "segment": "unknown",
                "recommendation": "Manual review needed",
                "risk_level": "medium",
            }
    
    async def identify_fidel_customers(self, customers: List[dict]) -> List[dict]:
        system = """Identifica los clientes más fieles de esta lista.
Criterios: frecuencia de compra, monto total, recencia.
Devuelve los top 10 con justificación."""
        
        prompt = f"""Clientes:
{json.dumps(customers[:50], indent=2)}

Identifica los top 10 clientes más fieles y responde en JSON:
{{
    "fidel_customers": [
        {{"user_id": "<id>", "reason": "<por qué es fiel>", "suggested_reward": "<recompensa sugerida>"}}
    ]
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response).get("fidel_customers", [])
        except Exception:
            return []


customer_analyzer = CustomerAnalyzer()
