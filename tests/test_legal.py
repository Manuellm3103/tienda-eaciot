import pytest


@pytest.mark.asyncio
async def test_legal_pages_render(client):
    for path, keyword in [
        ("/terminos", "Términos y Condiciones"),
        ("/privacidad", "Política de Privacidad"),
        ("/cookies", "Aviso de Cookies"),
    ]:
        resp = await client.get(path)
        assert resp.status_code == 200
        assert keyword in resp.text
