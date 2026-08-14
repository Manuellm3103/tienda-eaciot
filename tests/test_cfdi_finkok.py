import pytest
from app.services.cfdi_finkok import FinkokClient


def test_finkok_envelope_contains_b64_xml_and_creds(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_username", "user1")
    monkeypatch.setattr(mod.settings, "pac_password", "pass1")

    client = FinkokClient()
    envelope = client._build_envelope("<cfdi/>")

    assert "<apps:stamp>" in envelope
    assert "<apps:username>user1</apps:username>" in envelope
    assert "<apps:password>pass1</apps:password>" in envelope
    # base64 of "<cfdi/>" is "PGNmZGkvPg=="
    assert "PGNmZGkvPg==" in envelope


def test_finkok_parse_success():
    soap = (
        '<?xml version="1.0"?>'
        "<soap:Envelope><soap:Body><stampResponse><stampResult>"
        '<xml>CFDI con UUID="11111111-2222-3333-4444-555555555555"</xml>'
        "</stampResult></stampResponse></soap:Body></soap:Envelope>"
    )
    result = FinkokClient._parse_response(soap)
    assert result["uuid"] == "11111111-2222-3333-4444-555555555555"
    assert "UUID" in result["xml"]


def test_finkok_parse_error_raises():
    soap = (
        '<?xml version="1.0"?>'
        "<soap:Envelope><soap:Body><stampResponse>"
        '<Incidencias><Incidencia CodigoError="301" MensajeIncidencia="Certificado no valido">x</Incidencia></Incidencias>'
        "</stampResponse></soap:Body></soap:Envelope>"
    )
    with pytest.raises(RuntimeError, match="Certificado no valido"):
        FinkokClient._parse_response(soap)


def test_finkok_endpoint_switch(monkeypatch):
    import app.services.cfdi_finkok as mod

    monkeypatch.setattr(mod.settings, "pac_environment", "test")
    assert FinkokClient().endpoint.endswith("demo-facturacion.finkok.com/servicios/soap/stamp")
    monkeypatch.setattr(mod.settings, "pac_environment", "production")
    assert FinkokClient().endpoint.endswith("facturacion.finkok.com/servicios/soap/stamp")
