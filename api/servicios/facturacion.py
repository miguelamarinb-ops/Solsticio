"""
facturacion.py
Facturación electrónica con la DIAN simulada. La falla de la DIAN no bloquea la
venta: la factura queda PENDIENTE y puede reintentarse.
"""
import hashlib
from datetime import datetime

from flask import current_app

from api.errores import ErrorApi
from api.modelos import EstadoDian, EstadoPedido, Factura, db
from api.servicios.comun import codigo_temporal

PREFIJO_FACTURA = "SOL"
ESTADOS_FACTURABLES = {EstadoPedido.PAGADO, EstadoPedido.PREPARANDO,
                       EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO}


def emitir_factura(pedido):
    """Crea la factura (o reutiliza la pendiente) y la transmite. Devuelve (factura, validada)."""
    if pedido.estado not in ESTADOS_FACTURABLES:
        raise ErrorApi(409, "Solo se pueden facturar pedidos pagados")
    factura = pedido.factura
    if factura is not None and factura.estado_dian == EstadoDian.VALIDADA:
        raise ErrorApi(409, "El pedido ya tiene una factura validada por la DIAN",
                       id_factura=factura.id_factura)
    if factura is None:
        factura = Factura(
            id_pedido=pedido.id_pedido, numero_factura=codigo_temporal(), prefijo=PREFIJO_FACTURA,
            subtotal=pedido.subtotal, iva=pedido.impuestos, total=pedido.total,
            estado_dian=EstadoDian.PENDIENTE,
        )
        db.session.add(factura)
        db.session.flush()
        factura.numero_factura = f"{PREFIJO_FACTURA}-{factura.id_factura}"
        db.session.commit()  # la factura queda registrada aunque la DIAN falle
    return factura, transmitir_a_dian(factura)


def transmitir_a_dian(factura):
    try:
        if not current_app.config["DIAN_SIMULACION"]:
            raise ConnectionError("La integración real con la DIAN no está configurada")
        ahora = datetime.now().replace(microsecond=0)
        semilla = f"{factura.numero_factura}|{factura.fecha_emision.isoformat()}|{factura.total}|{ahora.isoformat()}"
        factura.cufe = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
        factura.estado_dian = EstadoDian.VALIDADA
        factura.fecha_validacion = ahora
        factura.url_xml = f"/facturas/{factura.numero_factura}.xml"
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falló la transmisión a la DIAN de %s", factura.numero_factura)
        return False
