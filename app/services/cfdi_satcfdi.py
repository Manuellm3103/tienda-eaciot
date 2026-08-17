"""Native CFDI 4.0 issuance with satcfdi + PAC (no monthly limits).

Flow: build CFDI 4.0 -> sign with the CSD (.cer/.key + password) -> stamp
through a PAC. satcfdi 4.4.7 ships connectors for SW Sapien, Comercio
Digital, Diverza, Prodigia and mySuite (NOT Finkok). The PAC is pluggable
via settings.pac_provider.

The tax model: each line item is priced *sin IVA*; IVA is added as a
`Traslado` at settings.business_iva_rate (0.16 default, 0 for exempt).
Shipping, when present, is added as its own "Envío" concept in the same base.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from satcfdi.models import Signer
from satcfdi.create.cfd import cfdi40
from satcfdi.create.cfd.catalogos import (
    RegimenFiscal,
    UsoCFDI,
    MetodoPago,
    TipoDeComprobante,
    FormaPago,
    ObjetoImp,
    Exportacion,
)
from satcfdi.pacs import Environment, Accept

from app.config import settings

USO_CFDI_MAP = {
    "G01": "ADQUISICION_DE_MERCANCIAS",
    "G03": "GASTOS_EN_GENERAL",
    "P01": "POR_DEFINIR",
    "S01": "SIN_EFECTOS_FISCALES",
}

REGIMEN_MAP = {
    "601": "GENERAL_DE_LEY_PERSONAS_MORALES",
    "612": "PERSONAS_FISICAS_CON_ACTIVIDADES_EMPRESARIALES_Y_PROFESIONALES",
    "626": "REGIMEN_SIMPLIFICADO_DE_CONFIANZA",
}

PUBLICO_EN_GENERAL_RFC = "XAXX010101000"
PUBLICO_EN_GENERAL_NAME = "PUBLICO EN GENERAL"

# Clave de producto/servicio genérica. Idealmente cada producto debería llevar
# su clave del catálogo SAT (c_ClaveProdServ); se deja configurable por producto
# en un paso posterior.
CLAVE_PROD_SERV = "60131300"
CLAVE_UNIDAD = "H87"  # pieza


def _regimen(code: str) -> RegimenFiscal:
    attr = REGIMEN_MAP.get(code, "GENERAL_DE_LEY_PERSONAS_MORALES")
    return getattr(RegimenFiscal, attr, RegimenFiscal.GENERAL_DE_LEY_PERSONAS_MORALES)


def _uso_cfdi(code: str) -> UsoCFDI:
    attr = USO_CFDI_MAP.get(code, "GASTOS_EN_GENERAL")
    return getattr(UsoCFDI, attr, UsoCFDI.GASTOS_EN_GENERAL)


class SATCFDIIssuer:
    """Builds, signs and stamps a CFDI 4.0 using the configured CSD + PAC."""

    def __init__(self):
        self.signer = Signer.load(
            certificate=open(settings.csd_cert_path, "rb").read(),
            key=open(settings.csd_key_path, "rb").read(),
            password=settings.csd_password or None,
        )
        env = (
            Environment.TEST
            if settings.pac_environment.lower() == "test"
            else Environment.PRODUCTION
        )
        self.pac = self._build_pac(env)

    def _build_pac(self, env):
        if settings.pac_provider == "comerciodigital":
            from satcfdi.pacs.comerciodigital import ComercioDigital

            return ComercioDigital(
                user=settings.pac_username,
                password=settings.pac_password,
                environment=env,
            )
        if settings.pac_provider == "finkok":
            # Finkok has no satcfdi connector — use the manual SOAP client.
            from app.services.cfdi_finkok import finkok_client

            return finkok_client
        # default: SW Sapien
        from satcfdi.pacs.swsapien import SWSapien

        return SWSapien(
            user=settings.pac_username or None,
            password=settings.pac_password or None,
            environment=env,
        )

    def issue(
        self,
        *,
        customer_rfc: str,
        customer_name: str,
        uso_cfdi: str,
        items: list[dict],
        shipping_amount: Decimal = Decimal("0"),
        payment_method: str = "stripe",
    ) -> dict:
        """Build, sign and stamp. `items` = [{description, quantity, unit_price}]."""
        # IVA trasladado POR CONCEPTO. En satcfdi 4.4.7 cada Concepto lleva sus
        # Impuestos (dict con claves 'Traslados') y compute()/process() calculan
        # la Base e Importe de cada Traslado y los totales del Comprobante.
        # El Comprobante NO acepta el kwarg 'impuestos': se agregan solos.
        iva_rate = Decimal(str(settings.business_iva_rate or 0))
        concept_impuestos = None
        if iva_rate > 0:
            concept_impuestos = {
                "Traslados": [
                    {"Impuesto": "002", "TipoFactor": "Tasa", "TasaOCuota": iva_rate}
                ]
            }

        concepts = []
        for it in items:
            concepts.append(
                cfdi40.Concepto(
                    clave_prod_serv=CLAVE_PROD_SERV,
                    cantidad=int(it["quantity"]),
                    clave_unidad=CLAVE_UNIDAD,
                    descripcion=str(it["description"])[:300],
                    valor_unitario=Decimal(str(it["unit_price"])),
                    objeto_imp=ObjetoImp.SI_OBJETO_DE_IMPUESTO,
                    impuestos=concept_impuestos,
                )
            )
        if shipping_amount and shipping_amount > 0:
            concepts.append(
                cfdi40.Concepto(
                    clave_prod_serv="78102200",  # servicios de mensajería
                    cantidad=1,
                    clave_unidad="E48",  # servicio
                    descripcion="Envío",
                    valor_unitario=Decimal(str(shipping_amount)),
                    objeto_imp=ObjetoImp.SI_OBJETO_DE_IMPUESTO,
                    impuestos=concept_impuestos,
                )
            )

        rfc = (customer_rfc or "").strip().upper() or PUBLICO_EN_GENERAL_RFC
        name = customer_name or PUBLICO_EN_GENERAL_NAME

        forma_pago = FormaPago.TARJETA_DE_CREDITO
        if payment_method not in ("stripe", "card"):
            forma_pago = FormaPago.TRANSFERENCIA_ELECTRONICA_DE_FONDOS

        comprobante = cfdi40.Comprobante(
            fecha=datetime.now(),
            moneda="MXN",
            tipo_de_comprobante=TipoDeComprobante.INGRESO,
            exportacion=Exportacion.NO_APLICA,
            lugar_expedicion=settings.business_zip_code or "62000",
            metodo_pago=MetodoPago.PAGO_EN_UNA_SOLA_EXHIBICION,
            forma_pago=forma_pago,
            emisor=cfdi40.Emisor(
                rfc=settings.business_rfc,
                nombre=settings.business_name or "Tienda Eaciot",
                regimen_fiscal=_regimen(settings.business_tax_regime),
            ),
            receptor=cfdi40.Receptor(
                rfc=rfc,
                nombre=name,
                domicilio_fiscal_receptor="00000" if rfc == PUBLICO_EN_GENERAL_RFC else "00000",
                regimen_fiscal_receptor=RegimenFiscal.SIN_OBLIGACIONES_FISCALES,
                uso_cfdi=_uso_cfdi(uso_cfdi),
            ),
            conceptos=concepts,
        )

        comprobante.sign(self.signer)
        comprobante = comprobante.process()

        if settings.pac_provider == "finkok":
            # Manual SOAP client takes the signed XML string (synchronous).
            signed_xml = comprobante.xml_bytes(xml_declaration=True).decode("utf-8", errors="ignore")
            result = self.pac.stamp(signed_xml)
            xml_bytes = result["xml"].encode("utf-8")
            return {
                "xml": result["xml"],
                "uuid": result.get("uuid") or self._extract_uuid(xml_bytes),
            }

        doc = self.pac.stamp(cfdi=comprobante, accept=Accept.XML)
        xml_bytes = doc.xml if isinstance(doc.xml, bytes) else str(doc.xml).encode("utf-8")

        return {
            "xml": xml_bytes.decode("utf-8", errors="ignore"),
            "uuid": self._extract_uuid(xml_bytes),
        }

    @staticmethod
    def _extract_uuid(xml: bytes) -> Optional[str]:
        import re

        text = xml.decode("utf-8", errors="ignore")
        m = re.search(r'UUID="([0-9a-fA-F\-]{36})"', text)
        if m:
            return m.group(1)
        m = re.search(r"<tfd:UUID[^>]*>([0-9a-fA-F\-]{36})</tfd:UUID>", text)
        return m.group(1) if m else None
