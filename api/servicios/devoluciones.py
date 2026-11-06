"""
devoluciones.py
Caso de uso 2.3.13, Devoluciones y cambios (diagrama 2210_devoluciones):

  - El CLIENTE solicita una devolución o un cambio de uno de sus pedidos (queda SOLICITADA).
  - El TRABAJADOR registra la devolución o el cambio en su sede, o completa una
    solicitud. Registrar incluye:
      * reintegrar el stock a la sede donde se recibe la prenda (movimiento DEVOLUCION),
        que no tiene que ser la sede que vendió;
      * en un cambio, entregar la prenda nueva (movimiento VENTA en esa misma sede);
      * generar la nota crédito sobre la factura del pedido y validarla ante la DIAN
        (simulada). Si la DIAN falla, la nota queda PENDIENTE y la devolución se conserva.

Cada unidad comprada se puede devolver una sola vez: las cantidades se descuentan de
lo que ya está en devoluciones no rechazadas.
"""
import hashlib
from datetime import datetime
from decimal import Decimal

from flask import current_app
from sqlalchemy import func, select

from api.errores import ErrorApi
from api.modelos import (
    DetalleDevolucion, Devolucion, EstadoDevolucion, EstadoDian, EstadoPedido,
    MovimientoInventario, NotaCredito, TipoDevolucion, TipoMovimiento, db,
)
from api.serializadores import precio_final
from api.servicios.comun import codigo_temporal, obtener_sede_activa, obtener_variante_activa
from api.servicios.inventario import (
    conflicto_existencias, disponible, obtener_stock, registrar_movimiento,
)
from api.validacion import a_entero, a_enum, exigir, lista_items, texto

PREFIJO_NOTA = "NC-SOL"
ESTADOS_DEVOLVIBLES = {EstadoPedido.PAGADO, EstadoPedido.PREPARANDO,
                       EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO}
REFERENCIA = "DEVOLUCION"


def _ya_devuelto(id_detalle_pedido, excluir=None):
    """Unidades de una línea que ya están en devoluciones no rechazadas."""
    consulta = (
        select(func.coalesce(func.sum(DetalleDevolucion.cantidad), 0))
        .join(Devolucion, Devolucion.id_devolucion == DetalleDevolucion.id_devolucion)
        .where(DetalleDevolucion.id_detalle_pedido == id_detalle_pedido,
               Devolucion.estado != EstadoDevolucion.RECHAZADA)
    )
    if excluir is not None:
        consulta = consulta.where(Devolucion.id_devolucion != excluir)
    return int(db.session.scalar(consulta))


def _leer_items(datos, pedido, tipo):
    """Valida los ítems contra el pedido. Devuelve [(detalle_pedido, cantidad, variante_cambio)]."""
    lineas = {d.id_detalle_pedido: d for d in pedido.detalles}
    pedidas = {}
    resultado = []
    for i, item in enumerate(lista_items(datos)):
        id_detalle = a_entero(item.get("id_detalle_pedido"), f"items[{i}].id_detalle_pedido", 1)
        cantidad = a_entero(item.get("cantidad"), f"items[{i}].cantidad", 1)
        detalle = lineas.get(id_detalle)
        if detalle is None:
            raise ErrorApi(422, f"La línea {id_detalle} no pertenece al pedido {pedido.id_pedido}")
        pedidas[id_detalle] = pedidas.get(id_detalle, 0) + cantidad
        restante = detalle.cantidad - _ya_devuelto(id_detalle)
        if pedidas[id_detalle] > restante:
            raise ErrorApi(409, "Se piden más unidades de las que se pueden devolver",
                           id_detalle_pedido=id_detalle, sku=detalle.variante.sku,
                           comprado=detalle.cantidad, disponible_para_devolver=max(restante, 0))

        variante_cambio = None
        if tipo == TipoDevolucion.CAMBIO:
            if item.get("id_variante_cambio") is None:
                raise ErrorApi(422, f"items[{i}].id_variante_cambio es obligatorio en un CAMBIO")
            variante_cambio = obtener_variante_activa(
                a_entero(item["id_variante_cambio"], f"items[{i}].id_variante_cambio", 1))
            if variante_cambio.id_producto != detalle.variante.id_producto:
                raise ErrorApi(422, "El cambio debe ser por otra talla o color de la misma prenda")
            if variante_cambio.id_variante == detalle.id_variante:
                raise ErrorApi(422, "La prenda de cambio es la misma que se devuelve")
            if precio_final(variante_cambio) > detalle.precio_unitario:
                raise ErrorApi(422, "La prenda de cambio cuesta más que la comprada; "
                                    "regístrela como una venta nueva")
        elif item.get("id_variante_cambio") is not None:
            raise ErrorApi(422, "Una DEVOLUCION no lleva id_variante_cambio (use tipo CAMBIO)")
        resultado.append((detalle, cantidad, variante_cambio))
    return resultado


def _nueva_devolucion(pedido, datos, usuario, id_sede, estado):
    if pedido.estado not in ESTADOS_DEVOLVIBLES:
        raise ErrorApi(409, f"Un pedido en estado {pedido.estado.value} no admite devoluciones")
    exigir(datos, "tipo", "motivo")
    tipo = a_enum(TipoDevolucion, datos["tipo"], "tipo")
    motivo = texto(datos, "motivo", 200, obligatorio=True)
    items = _leer_items(datos, pedido, tipo)
    devolucion = Devolucion(
        id_pedido=pedido.id_pedido, id_sede=obtener_sede_activa(id_sede).id_sede,
        id_usuario=usuario.id_usuario, tipo=tipo, motivo=motivo, estado=estado,
    )
    db.session.add(devolucion)
    db.session.flush()
    for detalle, cantidad, variante_cambio in items:
        db.session.add(DetalleDevolucion(
            id_devolucion=devolucion.id_devolucion, id_detalle_pedido=detalle.id_detalle_pedido,
            cantidad=cantidad,
            id_variante_cambio=variante_cambio.id_variante if variante_cambio else None,
        ))
    db.session.flush()
    return devolucion


# ---------------------------------------------------------------------
# Casos de uso
# ---------------------------------------------------------------------
def solicitar(pedido, datos, usuario):
    """CLIENTE: deja la solicitud. No mueve stock ni emite nada hasta que la tienda la reciba."""
    id_sede = a_entero(datos["id_sede"], "id_sede", 1) if datos.get("id_sede") else pedido.id_sede
    devolucion = _nueva_devolucion(pedido, datos, usuario, id_sede, EstadoDevolucion.SOLICITADA)
    db.session.commit()
    return devolucion


def registrar(pedido, datos, usuario, id_sede):
    """TRABAJADOR: recibe las prendas en su sede y completa la devolución en una sola operación."""
    devolucion = _nueva_devolucion(pedido, datos, usuario, id_sede, EstadoDevolucion.APROBADA)
    return completar(devolucion, usuario)


def completar(devolucion, usuario):
    """Reintegra el stock, entrega las prendas de cambio y emite la nota crédito."""
    if devolucion.estado not in (EstadoDevolucion.SOLICITADA, EstadoDevolucion.APROBADA):
        raise ErrorApi(409, f"La devolución está {devolucion.estado.value} y no se puede completar")
    pedido = devolucion.pedido
    if pedido.factura is None:
        raise ErrorApi(409, "El pedido no tiene factura; emítala antes de registrar la devolución")

    # Una solicitud se revisa otra vez: entre tanto pudo cambiar el stock o devolverse algo.
    for d in devolucion.detalles:
        restante = d.detalle_pedido.cantidad - _ya_devuelto(d.id_detalle_pedido, excluir=devolucion.id_devolucion)
        if d.cantidad > restante:
            raise ErrorApi(409, "Esas unidades ya fueron devueltas", sku=d.detalle_pedido.variante.sku)

    sede = devolucion.id_sede
    entregas = {}
    for d in devolucion.detalles:
        if d.variante_cambio is not None:
            entregas[d.variante_cambio.id_variante] = entregas.get(d.variante_cambio.id_variante, 0) + d.cantidad
    conflictos = []
    for id_variante, cantidad in entregas.items():
        stock = obtener_stock(sede, id_variante)
        libre = disponible(stock)
        if libre < cantidad:
            variante = next(d.variante_cambio for d in devolucion.detalles
                            if d.variante_cambio and d.variante_cambio.id_variante == id_variante)
            conflictos.append(conflicto_existencias(variante, sede, cantidad, libre))
    if conflictos:
        db.session.rollback()
        raise ErrorApi(409, "No hay existencias de la prenda de cambio en esta sede", conflictos=conflictos)

    monto = Decimal("0")
    for d in devolucion.detalles:
        linea = d.detalle_pedido
        registrar_movimiento(
            id_sede=sede, variante=linea.variante, tipo=TipoMovimiento.DEVOLUCION, cantidad=d.cantidad,
            usuario=usuario, tipo_referencia=REFERENCIA, id_referencia=devolucion.id_devolucion,
            observacion=f"{devolucion.tipo.value}: {devolucion.motivo}"[:200],
        )
        if d.variante_cambio is None:
            monto += linea.precio_unitario * d.cantidad
        else:
            registrar_movimiento(
                id_sede=sede, variante=d.variante_cambio, tipo=TipoMovimiento.VENTA, cantidad=-d.cantidad,
                usuario=usuario, tipo_referencia=REFERENCIA, id_referencia=devolucion.id_devolucion,
                observacion=f"Cambio por {linea.variante.sku}",
            )
            monto += (linea.precio_unitario - precio_final(d.variante_cambio)) * d.cantidad

    nota = NotaCredito(
        id_devolucion=devolucion.id_devolucion, id_factura=pedido.factura.id_factura,
        numero_nota=codigo_temporal(), monto=monto, estado_dian=EstadoDian.PENDIENTE,
    )
    db.session.add(nota)
    db.session.flush()
    nota.numero_nota = f"{PREFIJO_NOTA}-{nota.id_nota_credito:04d}"
    devolucion.estado = EstadoDevolucion.COMPLETADA
    devolucion.id_usuario = usuario.id_usuario  # queda quien la gestionó en la tienda
    db.session.commit()  # la devolución y la nota quedan aunque la DIAN falle
    transmitir_nota_a_dian(nota)
    return devolucion


def rechazar(devolucion):
    if devolucion.estado != EstadoDevolucion.SOLICITADA:
        raise ErrorApi(409, f"Solo se rechaza una solicitud; esta está {devolucion.estado.value}")
    devolucion.estado = EstadoDevolucion.RECHAZADA
    db.session.commit()
    return devolucion


def transmitir_nota_a_dian(nota):
    """DIAN simulada, igual que la factura: si falla, la nota queda PENDIENTE."""
    try:
        if not current_app.config["DIAN_SIMULACION"]:
            raise ConnectionError("La integración real con la DIAN no está configurada")
        ahora = datetime.now().replace(microsecond=0)
        semilla = f"{nota.numero_nota}|{nota.id_factura}|{nota.monto}|{ahora.isoformat()}"
        nota.cude = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
        nota.estado_dian = EstadoDian.VALIDADA
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falló la transmisión a la DIAN de %s", nota.numero_nota)
        return False


def movimientos_de(devolucion):
    return db.session.scalars(
        select(MovimientoInventario)
        .where(MovimientoInventario.tipo_referencia == REFERENCIA,
               MovimientoInventario.id_referencia == devolucion.id_devolucion)
        .order_by(MovimientoInventario.id_movimiento)
    ).all()


def unidades_devolvibles(pedido):
    """Para la interfaz: cuántas unidades de cada línea se pueden devolver todavía."""
    return {d.id_detalle_pedido: max(d.cantidad - _ya_devuelto(d.id_detalle_pedido), 0)
            for d in pedido.detalles}

