"""Manual Finkok SOAP connector.

satcfdi 4.4.7 ships no Finkok PAC, so this is a minimal raw-SOAP client for
Finkok's stamp service. The CFDI is already signed by satcfdi; we only stamp
it (the `stamp` operation, not `sign_stamp`).

Endpoints:
- Production: https://facturacion.finkok.com/servicios/soap/stamp
- Test:       https://demo-facturacion.finkok.com/servicios/soap/stamp
"""
import base64
import re
from typing import Optional

import httpx

from app.config import settings

FINKOK_PROD = "https://facturacion.finkok.com/servicios/soap/stamp"
FINKOK_TEST = "https://demo-facturacion.finkok.com/servicios/soap/stamp"


class FinkokClient:
    @property
    def endpoint(self) -> str:
        return FINKOK_TEST if settings.pac_environment.lower() == "test" else FINKOK_PROD

    def stamp(self, xml: str) -> dict:
        """Stamp a signed CFDI (synchronous, matching the satcfdi PAC API).

        Returns {"xml": <timbrado>, "uuid": <...>}.
        """
        envelope = self._build_envelope(xml)
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                self.endpoint,
                content=envelope,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": '"stamp"',
                },
            )
            resp.raise_for_status()
            return self._parse_response(resp.text)

    def _build_envelope(self, xml: str) -> str:
        b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:apps="apps.soap.ws.finkok.com">'
            "<soapenv:Body><apps:stamp>"
            f"<apps:xml>{b64}</apps:xml>"
            f"<apps:username>{settings.pac_username}</apps:username>"
            f"<apps:password>{settings.pac_password}</apps:password>"
            "</apps:stamp></soapenv:Body></soapenv:Envelope>"
        )

    @staticmethod
    def _parse_response(soap_text: str) -> dict:
        # Success: <stampResult><xml>...CFDI timbrado...</xml></stampResult>
        m = re.search(r"<stampResult>\s*<xml>(.*?)</xml>", soap_text, re.S)
        if m:
            xml = m.group(1)
            uuid = None
            um = re.search(r'UUID="([0-9a-fA-F\-]{36})"', xml)
            if not um:
                um = re.search(r"<tfd:UUID[^>]*>([0-9a-fA-F\-]{36})</tfd:UUID>", xml)
            if um:
                uuid = um.group(1)
            return {"xml": xml, "uuid": uuid}

        # Error: <Incidencias><Incidencia CodigoError=... MensajeIncidencia=...>...</Incidencia></Incidencias>
        err = re.search(r'<Incidencia[^>]*MensajeIncidencia="([^"]+)"', soap_text)
        if err:
            raise RuntimeError(f"Finkok rechazó la factura: {err.group(1)[:300]}")
        err2 = re.search(r"<Incidencias>.*?</Incidencias>", soap_text, re.S)
        if err2:
            raise RuntimeError(f"Finkok rechazó la factura: {err2.group(0)[:300]}")
        raise RuntimeError(f"Respuesta de Finkok no reconocida: {soap_text[:200]}")


finkok_client = FinkokClient()
