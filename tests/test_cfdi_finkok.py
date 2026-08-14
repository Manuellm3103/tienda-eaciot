import base64
import pytest

from app.services.cfdi_finkok import FinkokClient, _host, _STAMP_NS, _CANCEL_NS


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self._text = text
        self.status_code = status_code

    def raise_for_status(self):
        pass

    @property
    def text(self):
        return self._text


class _FakeClient:
    def __init__(self, response_text, status_code=200):
        self.response_text = response_text
        self.status_code = status_code
        self.captured = None
        self.url = None
        self.headers = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, content, headers):
        self.url = url
        self.captured = content
        self.headers = headers
        return _FakeResponse(self.response_text, self.status_code)


def _patch_httpx(monkeypatch, response_text, status_code=200):
    fake = _FakeClient(response_text, status_code)
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.httpx, "Client", lambda *a, **k: fake)
    return fake


def test_stamp_envelope_and_parse(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_username", "user1")
    monkeypatch.setattr(mod.settings, "pac_password", "pass1")
    monkeypatch.setattr(mod.settings, "pac_environment", "production")
    soap = (
        "<Envelope><stampResult>"
        '<xml>CFDI con UUID="11111111-2222-3333-4444-555555555555"</xml>'
        "<UUID>11111111-2222-3333-4444-555555555555</UUID>"
        "</stampResult></Envelope>"
    )
    fake = _patch_httpx(monkeypatch, soap)

    result = FinkokClient().stamp("<cfdi/>")

    assert fake.url == "https://facturacion.finkok.com/servicios/soap/stamp"
    assert fake.headers["SOAPAction"] == '"stamp"'
    assert base64.b64encode(b"<cfdi/>").decode() in fake.captured
    assert _STAMP_NS in fake.captured
    assert "<username>user1</username>" in fake.captured
    assert "<password>pass1</password>" in fake.captured
    assert result["uuid"] == "11111111-2222-3333-4444-555555555555"


def test_parse_stamp_error_raises():
    soap = (
        "<Envelope><stampResponse>"
        '<Incidencias><Incidencia CodigoError="301" MensajeIncidencia="Certificado no valido">x</Incidencia></Incidencias>'
        "</stampResponse></Envelope>"
    )
    with pytest.raises(RuntimeError, match="Certificado no valido"):
        FinkokClient._parse_stamp(soap)


def test_parse_stamp_xml_bytes_64_fallback():
    xml = 'CFDI con UUID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"'
    b64 = base64.b64encode(xml.encode()).decode()
    soap = f"<Envelope><stampResult><xml_bytes_64>{b64}</xml_bytes_64></stampResult></Envelope>"
    result = FinkokClient._parse_stamp(soap)
    assert result["uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert "UUID" in result["xml"]


def test_parse_cancel():
    soap = (
        "<Envelope><cancelResult><Folios><Folio>"
        "<UUID>11111111-2222-3333-4444-555555555555</UUID>"
        "<EstatusUUID>202</EstatusUUID>"
        "</Folio></Folios><Acuse>ACUSE_B64</Acuse></cancelResult></Envelope>"
    )
    result = FinkokClient._parse_cancel(soap)
    assert result["uuid"] == "11111111-2222-3333-4444-555555555555"
    assert result["estatus"] == "202"


def test_cancel_envelope_uuids_and_store_pending(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_username", "u")
    monkeypatch.setattr(mod.settings, "pac_password", "p")
    monkeypatch.setattr(mod.settings, "pac_environment", "test")
    soap = (
        "<Envelope><cancelResult><Folios><Folio>"
        "<UUID>11111111-2222-3333-4444-555555555555</UUID>"
        "<EstatusUUID>201</EstatusUUID></Folio></Folios></cancelResult></Envelope>"
    )
    fake = _patch_httpx(monkeypatch, soap)

    FinkokClient().cancel(uuid="11111111-2222-3333-4444-555555555555", taxpayer_id="EAC2403183F0")

    assert fake.url == "https://demo-facturacion.finkok.com/servicios/soap/cancel"
    assert _CANCEL_NS in fake.captured
    assert '<UUID UUID="11111111-2222-3333-4444-555555555555" Motivo="01" FolioSustitucion=""/>' in fake.captured
    assert "<taxpayer_id>EAC2403183F0</taxpayer_id>" in fake.captured
    assert "<store_pending>true</store_pending>" in fake.captured


def test_get_sat_status(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_username", "u")
    monkeypatch.setattr(mod.settings, "pac_password", "p")
    monkeypatch.setattr(mod.settings, "pac_environment", "production")
    soap = "<Envelope><get_sat_statusResult><sat><Estado>Cancelado</Estado></sat></get_sat_statusResult></Envelope>"
    fake = _patch_httpx(monkeypatch, soap)

    result = FinkokClient().get_sat_status(
        taxpayer_id="EAC2403183F0", uuid="11111111-2222-3333-4444-555555555555",
        total="100.00", rfc_receptor="XAXX010101000",
    )
    # get_sat_status lives on the CANCEL service endpoint.
    assert fake.url == "https://facturacion.finkok.com/servicios/soap/cancel"
    assert fake.headers["SOAPAction"] == '"get_sat_status"'
    assert "<rtaxpayer_id>XAXX010101000</rtaxpayer_id>" in fake.captured
    assert result["estado"] == "Cancelado"


def test_http_500_fault_raises(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_username", "u")
    monkeypatch.setattr(mod.settings, "pac_password", "p")
    fault = "<Envelope><Body><Fault><faultstring>Method not found.</faultstring></Fault></Body></Envelope>"
    _patch_httpx(monkeypatch, fault, status_code=500)
    with pytest.raises(RuntimeError, match="Method not found"):
        FinkokClient().stamp("<cfdi/>")


def test_host_switch(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_environment", "test")
    assert _host() == "demo-facturacion.finkok.com"
    monkeypatch.setattr(mod.settings, "pac_environment", "production")
    assert _host() == "facturacion.finkok.com"
