"""
serializadores.py
Convierte los modelos en diccionarios para las respuestas JSON, con la forma
documentada en Contexto/Solsticio_API_Seccion_4.md.
"""
from sqlalchemy import select

from api.modelos import EstadoPago, EstadoPedido, Sede, TipoEntrega, db


def sedes_activas():
    return db.session.scalars(
        select(Sede).where(Sede.activo.is_(True)).order_by(Sede.id_sede)
    ).all()


def nombre_completo(persona):
    if persona is None:
        return None
    return " ".join(p for p in (persona.nombres, persona.apellidos) if p)


# =====================================================================
# SEDES, CATEGORÍAS Y USUARIOS
# =====================================================================

def sede_corta(sede):
    if sede is None:
        return None
    return {"id_sede": sede.id_sede, "nombre": sede.nombre}


def sede_dict(sede):
    return {
        "id_sede": sede.id_sede,
        "nombre": sede.nombre,
        "direccion": sede.direccion,
        "ciudad": sede.ciudad,
        "telefono": sede.telefono,
        "activo": sede.activo,
    }


def categoria_dict(categoria):
    return {
        "id_categoria": categoria.id_categoria,
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion,
        "activo": categoria.activo,
    }


def usuario_dict(usuario):
    return {
        "id_usuario": usuario.id_usuario,
        "documento": usuario.documento,
        "nombres": usuario.nombres,
        "apellidos": usuario.apellidos,
        "email": usuario.email,
        "rol": usuario.rol.nombre,
        "sede": sede_corta(usuario.sede),
        "activo": usuario.activo,
    }


# =====================================================================
# CATÁLOGO
# =====================================================================

def precio_final(variante):
    return variante.producto.precio_base + variante.precio_adicional


def descripcion_variante(variante):
    return f"{variante.producto.nombre} - {variante.talla.valor} - {variante.color.nombre}"


def imagen_principal(producto):
    if not producto.imagenes:
        return None
    principal = next((i for i in producto.imagenes if i.es_principal), producto.imagenes[0])
    return principal.url


def _variantes_activas(producto):
    return sorted(
        (v for v in producto.variantes if v.activo),
        key=lambda v: (v.talla.orden, v.color.nombre),
    )


def disponibilidad(variante, sedes):
    """Existencias desglosadas por sede: una entrada por cada sede activa, aunque tenga 0."""
    por_sede = {s.id_sede: s.cantidad for s in variante.stocks}
    return [
        {"id_sede": sede.id_sede, "sede": sede.nombre, "cantidad": por_sede.get(sede.id_sede, 0)}
        for sede in sedes
    ]


def producto_resumen(producto, sedes):
    ids_sedes = {s.id_sede for s in sedes}
    stock_total = 0
    tallas = []
    for variante in _variantes_activas(producto):
        cantidad = sum(s.cantidad for s in variante.stocks if s.id_sede in ids_sedes)
        stock_total += cantidad
        if cantidad > 0 and variante.talla.valor not in tallas:
            tallas.append(variante.talla.valor)
    return {
        "id_producto": producto.id_producto,
        "nombre": producto.nombre,
        "categoria": producto.categoria.nombre,
        "genero": producto.genero,
        "precio_base": producto.precio_base,
        "imagen_principal": imagen_principal(producto),
        "stock_total": stock_total,
        "tallas_disponibles": tallas,
    }


def variante_dict(variante, sedes):
    disp = disponibilidad(variante, sedes)
    return {
        "id_variante": variante.id_variante,
        "sku": variante.sku,
        "codigo_qr": variante.codigo_qr,
        "talla": variante.talla.valor,
        "color": {"nombre": variante.color.nombre, "codigo_hex": variante.color.codigo_hex},
        "precio_adicional": variante.precio_adicional,
        "precio_final": precio_final(variante),
        "disponibilidad": disp,
        "stock_total": sum(d["cantidad"] for d in disp),
    }


def producto_detalle(producto, sedes):
    return {
        "id_producto": producto.id_producto,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "categoria": {
            "id_categoria": producto.categoria.id_categoria,
            "nombre": producto.categoria.nombre,
        },
        "genero": producto.genero,
        "precio_base": producto.precio_base,
        "activo": producto.activo,
        "fecha_creacion": producto.fecha_creacion,
        "imagenes": [
            {"url": i.url, "orden": i.orden, "es_principal": i.es_principal}
            for i in producto.imagenes
        ],
        "variantes": [variante_dict(v, sedes) for v in _variantes_activas(producto)],
    }


def variante_por_qr(variante, sedes):
    producto = variante.producto
    return {
        "id_variante": variante.id_variante,
        "sku": variante.sku,
        "codigo_qr": variante.codigo_qr,
        "talla": variante.talla.valor,
        "color": variante.color.nombre,
        "producto": {
            "id_producto": producto.id_producto,
            "nombre": producto.nombre,
            "precio_base": producto.precio_base,
            "imagen_principal": imagen_principal(producto),
        },
        "precio_final": precio_final(variante),
        "disponibilidad": disponibilidad(variante, sedes),
        "url_catalogo": f"/productos/{producto.id_producto}?variante={variante.id_variante}",
    }


def disponibilidad_detallada(variante, sedes):
    por_sede = {s.id_sede: s for s in variante.stocks}
    filas = []
    for sede in sedes:
        stock = por_sede.get(sede.id_sede)
        cantidad = stock.cantidad if stock else 0
        reservada = stock.cantidad_reservada if stock else 0
        filas.append({
            "id_sede": sede.id_sede,
            "nombre": sede.nombre,
            "direccion": sede.direccion,
            "telefono": sede.telefono,
            "cantidad": cantidad,
            "cantidad_reservada": reservada,
            "disponible": cantidad - reservada,
        })
    return {
        "id_variante": variante.id_variante,
        "sku": variante.sku,
        "descripcion": descripcion_variante(variante),
        "stock_total": sum(f["cantidad"] for f in filas),
        "sedes": filas,
    }


# =====================================================================
# INVENTARIO
# =====================================================================

def stock_dict(stock):
    variante = stock.variante
    return {
        "id_sede": stock.id_sede,
        "sede": stock.sede.nombre,
        "id_variante": stock.id_variante,
        "sku": variante.sku,
        "descripcion": descripcion_variante(variante),
        "cantidad": stock.cantidad,
        "cantidad_reservada": stock.cantidad_reservada,
        "disponible": stock.cantidad - stock.cantidad_reservada,
        "stock_minimo": stock.stock_minimo,
        "bajo_minimo": stock.cantidad <= stock.stock_minimo,
    }


def movimiento_dict(movimiento):
    return {
        "id_movimiento": movimiento.id_movimiento,
        "fecha": movimiento.fecha,
        "tipo": movimiento.tipo,
        "id_sede": movimiento.id_sede,
        "sede": movimiento.sede.nombre,
        "id_variante": movimiento.id_variante,
        "sku": movimiento.variante.sku,
        "cantidad": movimiento.cantidad,
        "registrado_por": nombre_completo(movimiento.usuario),
        "tipo_referencia": movimiento.tipo_referencia,
        "id_referencia": movimiento.id_referencia,
        "observacion": movimiento.observacion,
    }


def movimiento_aplicado(resultado):
    """Resultado de servicios.inventario.registrar_movimiento, con el stock antes y después."""
    movimiento = resultado["movimiento"]
    return {
        "id_movimiento": movimiento.id_movimiento,
        "id_sede": movimiento.id_sede,
        "id_variante": movimiento.id_variante,
        "sku": movimiento.variante.sku,
        "tipo": movimiento.tipo,
        "cantidad": movimiento.cantidad,
        "stock_anterior": resultado["stock_anterior"],
        "stock_actual": resultado["stock_actual"],
    }


def traslado_dict(traslado, disponibles_origen=None):
    items = []
    for detalle in traslado.detalles:
        item = {
            "id_variante": detalle.id_variante,
            "sku": detalle.variante.sku,
            "descripcion": descripcion_variante(detalle.variante),
            "cantidad": detalle.cantidad,
        }
        if disponibles_origen is not None:
            item["disponible_en_origen"] = disponibles_origen.get(detalle.id_variante)
        items.append(item)
    return {
        "id_traslado": traslado.id_traslado,
        "estado": traslado.estado,
        "sede_origen": sede_corta(traslado.sede_origen),
        "sede_destino": sede_corta(traslado.sede_destino),
        "solicitado_por": nombre_completo(traslado.usuario_solicita),
        "recibido_por": nombre_completo(traslado.usuario_recibe),
        "items": items,
        "fecha_solicitud": traslado.fecha_solicitud,
        "fecha_recepcion": traslado.fecha_recepcion,
    }


# =====================================================================
# VENTAS, PAGOS Y FACTURACIÓN
# =====================================================================

def cliente_dict(cliente):
    if cliente is None:
        return None
    return {
        "id_cliente": cliente.id_cliente,
        "tipo_documento": cliente.tipo_documento,
        "numero_documento": cliente.numero_documento,
        "nombres": cliente.nombres,
        "apellidos": cliente.apellidos,
        "email": cliente.email,
        "telefono": cliente.telefono,
    }


def detalle_pedido_dict(detalle):
    return {
        "id_detalle_pedido": detalle.id_detalle_pedido,
        "id_variante": detalle.id_variante,
        "sku": detalle.variante.sku,
        "descripcion": descripcion_variante(detalle.variante),
        "cantidad": detalle.cantidad,
        "precio_unitario": detalle.precio_unitario,
        "subtotal_linea": detalle.subtotal_linea,
    }


def envio_dict(envio):
    if envio is None:
        return None
    return {
        "direccion": envio.direccion,
        "ciudad": envio.ciudad,
        "destinatario": envio.destinatario,
        "telefono_contacto": envio.telefono_contacto,
        "transportadora": envio.transportadora,
        "numero_guia": envio.numero_guia,
        "estado": envio.estado,
        "fecha_despacho": envio.fecha_despacho,
        "fecha_entrega": envio.fecha_entrega,
    }


def pago_dict(pago):
    return {
        "id_pago": pago.id_pago,
        "id_pedido": pago.id_pedido,
        "metodo_pago": pago.metodo_pago.nombre,
        "monto": pago.monto,
        "estado": pago.estado,
        "referencia_transaccion": pago.referencia_transaccion,
        "fecha_pago": pago.fecha_pago,
    }


def factura_dict(factura):
    if factura is None:
        return None
    return {
        "id_factura": factura.id_factura,
        "id_pedido": factura.id_pedido,
        "numero_factura": factura.numero_factura,
        "prefijo": factura.prefijo,
        "cufe": factura.cufe,
        "estado_dian": factura.estado_dian,
        "subtotal": factura.subtotal,
        "iva": factura.iva,
        "total": factura.total,
        "fecha_emision": factura.fecha_emision,
        "fecha_validacion": factura.fecha_validacion,
        "url_xml": factura.url_xml,
    }


def pedido_dict(pedido):
    return {
        "id_pedido": pedido.id_pedido,
        "canal": pedido.canal,
        "estado": pedido.estado,
        "tipo_entrega": pedido.tipo_entrega,
        "codigo_qr": pedido.codigo_qr,
        "sede": sede_corta(pedido.sede),
        "cliente": cliente_dict(pedido.cliente),
        "vendido_por": nombre_completo(pedido.usuario),
        "items": [detalle_pedido_dict(d) for d in pedido.detalles],
        "subtotal": pedido.subtotal,
        "impuestos": pedido.impuestos,
        "total": pedido.total,
        "envio": envio_dict(pedido.envio),
        "pagos": [pago_dict(p) for p in pedido.pagos],
        "factura": factura_dict(pedido.factura),
        "fecha_pedido": pedido.fecha_pedido,
    }


def accion_sugerida(pedido):
    estado = pedido.estado
    domicilio = pedido.tipo_entrega == TipoEntrega.DOMICILIO
    if estado == EstadoPedido.PENDIENTE:
        return "COBRAR"
    if estado == EstadoPedido.PAGADO:
        return "PREPARAR_ENVIO" if domicilio else "ENTREGAR_EN_TIENDA"
    if estado == EstadoPedido.PREPARANDO:
        return "DESPACHAR" if domicilio else "ENTREGAR_EN_TIENDA"
    if estado == EstadoPedido.ENVIADO:
        return "CONFIRMAR_ENTREGA"
    return "NINGUNA"


def pedido_por_qr(pedido):
    aprobados = [p for p in pedido.pagos if p.estado == EstadoPago.APROBADO]
    pago = aprobados[-1] if aprobados else (pedido.pagos[-1] if pedido.pagos else None)
    cliente = pedido.cliente
    return {
        "id_pedido": pedido.id_pedido,
        "codigo_qr": pedido.codigo_qr,
        "canal": pedido.canal,
        "estado": pedido.estado,
        "tipo_entrega": pedido.tipo_entrega,
        "sede": sede_corta(pedido.sede),
        "cliente": None if cliente is None else {
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos,
            "numero_documento": cliente.numero_documento,
        },
        "items": [
            {"sku": d.variante.sku, "descripcion": descripcion_variante(d.variante), "cantidad": d.cantidad}
            for d in pedido.detalles
        ],
        "total": pedido.total,
        "pago": None if pago is None else {
            "estado": pago.estado,
            "metodo": pago.metodo_pago.nombre,
            "fecha_pago": pago.fecha_pago,
        },
        "factura": None if pedido.factura is None else {
            "numero_factura": pedido.factura.numero_factura,
            "estado_dian": pedido.factura.estado_dian,
        },
        "accion_sugerida": accion_sugerida(pedido),
        "fecha_pedido": pedido.fecha_pedido,
    }
