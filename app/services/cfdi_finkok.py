"""Manual Finkok SOAP connector.

satcfdi 4.4.7 ships no Finkok PAC, so this is a raw-SOAP client for Finkok's
web services. The CFDI is signed locally by satcfdi; we only *stamp* it (the
`stamp` operation, not `sign_stamp`) and cancel it when required.

Endpoints + namespaces (verified against Finkok's live WSDLs):
- Stamp:          {demo-,}facturacion.finkok.com/servicios/soap/stamp
                  targetNamespace = http://facturacion.finkok.com/stamp
- Cancel:         {demo-,}facturacion.finkok.com/servicios/soap/cancel
                  targetNamespace = http://facturacion.finkok.com/cancel
- get_sat_status: SAME endpoint as cancel (/servicios/soap/cancel) — it is an
                  operation of the cancel service, not a separate WSDL.

Cancel (CFDI 4.0): the request carries a `<UUIDS>` list whose `<UUID>` element
uses *attributes* (UUID, Motivo, FolioSustitucion). Either attach the CSD
(base64 cer/key) for immediate cancellation, or `store_pending=true` to queue
a pending cancellation confirmed later in the Finkok portal.
"""
import base64
import re
from typing import Optional

import httpx

from app.config import settings

_STAMP_NS = "http://facturacion.finkok.com/stamp"
_CANCEL_NS = "http://facturacion.finkok.com/cancel"
_ROOT = "facturacion.finkok.com"
_TEST_ROOT = "demo-facturacion.finkok.com"


def _host() -> str:
    return _TEST_ROOT if settings.pac_environment.lower() == "test" else _ROOT


class FinkokClient:
    def stamp(self, xml: str) -> dict:
        """Stamp a signed CFDI (synchronous). Returns {"xml", "uuid"}."""
        b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
        body = (
            f'<stamp xmlns="{_STAMP_NS}"><xml>{b64}</xml>'
            f"<username>{settings.pac_username}</username>"
            f"<password>{settings.pac_password}</password>"
            "</stamp>"
        )
        text = self._post("stamp", "stamp", _STAMP_NS, body)
        return self._parse_stamp(text)

    def cancel(
        self,
        uuid: str,
        taxpayer_id: str,
        motivo: str = "01",
        folio_sustitucion: Optional[str] = None,
        cer_b64: Optional[str] = None,
        key_b64: Optional[str] = None,
        store_pending: bool = True,
    ) -> dict:
        """Cancel a stamped CFDI. Returns {"uuid", "estatus", "acuse", "codestatus"}."""
        sustitucion = folio_sustitucion or ""
        uuids = f'<UUIDS><UUID UUID="{uuid}" Motivo="{motivo}" FolioSustitucion="{sustitucion}"/></UUIDS>'
        parts = [uuids]
        parts.append(f"<username>{settings.pac_username}</username>")
        parts.append(f"<password>{settings.pac_password}</password>")
        parts.append(f"<taxpayer_id>{taxpayer_id}</taxpayer_id>")
        if cer_b64:
            parts.append(f"<cer>{cer_b64}</cer>")
        if key_b64:
            parts.append(f"<key>{key_b64}</key>")
        parts.append(f"<store_pending>{'true' if store_pending else 'false'}</store_pending>")
        body = f'<cancel xmlns="{_CANCEL_NS}">{"".join(parts)}</cancel>'
        text = self._post("cancel", "cancel", _CANCEL_NS, body)
        return self._parse_cancel(text)

    def get_sat_status(
        self,
        taxpayer_id: str,
        uuid: str,
        total: str,
        rfc_receptor: str,
    ) -> dict:
        """Corroborate the comprobante's SAT state (Vigente / Cancelado).

        Lives on the cancel service endpoint (see module docstring)."""
        body = (
            f'<get_sat_status xmlns="{_CANCEL_NS}">'
            f"<username>{settings.pac_username}</username>"
            f"<password>{settings.pac_password}</password>"
            f"<taxpayer_id>{taxpayer_id}</taxpayer_id>"
            f"<rtaxpayer_id>{rfc_receptor}</rtaxpayer_id>"
            f"<uuid>{uuid}</uuid>"
            f"<total>{total}</total>"
            "</get_sat_status>"
        )
        text = self._post("cancel", "get_sat_status", _CANCEL_NS, body)
        estado = self._first(text, "Estado")
        codigo = self._first(text, "CodigoEstatus")
        cancelable = self._first(text, "EsCancelable")
        if not estado and not codigo:
            self._raise_error(text)
        return {"estado": estado, "codestatus": codigo, "es_cancelable": cancelable}

    # ── internals ─────────────────────────────────────────────────────────

    def _post(self, operation: str, soap_action: str, namespace: str, body_xml: str) -> str:
        endpoint = f"https://{_host()}/servicios/soap/{operation}"
        envelope = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            f'xmlns:tns="{namespace}">'
            f"<soapenv:Body>{body_xml}</soapenv:Body></soapenv:Envelope>"
        )
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                endpoint,
                content=envelope,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": f'"{soap_action}"',
                },
            )
            # Finkok returns SOAP faults with HTTP 500 — parse the body, don't
            # let raise_for_status() mask the real error.
            if resp.status_code >= 500:
                self._raise_error(resp.text)
            return resp.text

    @staticmethod
    def _first(text: str, tag: str) -> Optional[str]:
        m = re.search(rf"<(?:[a-zA-Z_][\w.-]*:)?{tag}[^>]*>(.*?)</(?:[a-zA-Z_][\w.-]*:)?{tag}>", text, re.S)
        return m.group(1).strip() if m else None

    @staticmethod
    def _parse_stamp(soap_text: str) -> dict:
        xml = FinkokClient._first(soap_text, "xml")
        uuid = FinkokClient._first(soap_text, "UUID")
        if not xml:
            b64 = FinkokClient._first(soap_text, "xml_bytes_64")
            if b64:
                xml = base64.b64decode(b64).decode("utf-8", errors="ignore")
        if not xml:
            FinkokClient._raise_error(soap_text)
        if not uuid:
            um = re.search(r'UUID="([0-9a-fA-F\-]{36})"', xml)
            if not um:
                um = re.search(r"<tfd:UUID[^>]*>([0-9a-fA-F\-]{36})</tfd:UUID>", xml)
            if um:
                uuid = um.group(1)
        return {"xml": xml, "uuid": uuid}

    @staticmethod
    def _parse_cancel(soap_text: str) -> dict:
        uuid = FinkokClient._first(soap_text, "UUID")
        estatus = FinkokClient._first(soap_text, "EstatusUUID")
        codestatus = FinkokClient._first(soap_text, "CodEstatus")
        acuse = FinkokClient._first(soap_text, "Acuse")
        if not uuid and not estatus:
            FinkokClient._raise_error(soap_text)
        return {
            "uuid": uuid,
            "estatus": estatus,
            "acuse": acuse,
            "codestatus": codestatus,
        }

    @staticmethod
    def _raise_error(soap_text: str) -> None:
        msg = FinkokClient._first(soap_text, "MensajeIncidencia")
        if msg:
            raise RuntimeError(f"Finkok rechazó la factura: {msg[:300]}")
        # <Incidencia CodigoError="..." MensajeIncidencia="..."/> (attribute form)
        msg = re.search(r'MensajeIncidencia="([^"]+)"', soap_text)
        if msg:
            raise RuntimeError(f"Finkok rechazó la factura: {msg.group(1)[:300]}")
        fault = FinkokClient._first(soap_text, "faultstring")
        if fault:
            raise RuntimeError(f"Finkok error: {fault[:300]}")
        raise RuntimeError(f"Respuesta de Finkok no reconocida: {soap_text[:200]}")


finkok_client = FinkokClient()
