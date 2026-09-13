"""
pedidos.py
Venta unificada (canal WEB y TIENDA), pago con pasarela simulada y cambios de estado.
Las unidades se reservan al crear el pedido y se descuentan con movimiento VENTA
cuando el pago es aprobado.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import (
    Canal, Cliente, DetallePedido, Envio, EstadoEnvio, EstadoPago, EstadoPedido, MetodoPago,
    Pago, Pedido, TipoDocumento, TipoEntrega, TipoMovimiento, db,
)
from api.seguridad import es_admin
from api.serializadores import precio_final
from api.servicios.comun import (
    codigo_temporal, obtener_sede_activa, obtener_variante_activa, prefijo_ascii, separar_iva,
)
from api.servicios.inventario import (
    conflicto_existencias, disponible, obtener_stock, registrar_movimiento,
)
from api.validacion import (
    a_decimal, a_entero, a_enum, consolidar_items, exigir, lista_items, texto,
)


def _resolver_cliente(datos):
    """Busca el cliente por documento o lo crea (el cliente no necesita cuenta)."""
    if not isinstance(datos, dict):
        raise ErrorApi(422, "'cliente' debe ser un objeto")
    numero = texto(datos, "numero_documento", 20, obligatorio=True)
    cliente = db.session.scalars(select(Cliente).where(Cliente.numero_documento == numero)).first()
    if cliente is None:
        cliente = Cliente(
            tipo_documento=a_enum(TipoDocumento, datos.get("tipo_documento", "CC"), "tipo_documento"),
            numero_documento=numero,
            nombres=texto(datos, "nombres", 80, obligatorio=True),
        )
        db.session.add(cliente)
    for campo, maximo in (("apellidos", 80), ("email", 120), ("telefono", 20), ("direccion", 150)):
        valor = texto(datos, campo, maximo)
        if valor and not getattr(cliente, campo):
            setattr(cliente, campo, valor)
    db.session.flush()
    return cliente


def crear_pedido(datos, usuario):
    canal = a_enum(Canal, datos.get("canal"), "canal")
    if canal == Canal.TIENDA:
        if usuario is None:
            raise ErrorApi(401, "Las ventas en tienda requieren el token de un trabajador")
        if es_admin(usuario):
            exigir(datos, "id_sede")
            id_sede = a_entero(datos["id_sede"], "id_sede", 1)
        else:
            id_sede = usuario.id_sede
            if datos.get("id_sede") not in (None, id_sede):
                raise ErrorApi(403, "Un trabajador solo puede vender en su propia sede")
        tipo_entrega = a_enum(TipoEntrega, datos.get("tipo_entrega", "INMEDIATA"), "tipo_entrega")
        id_usuario = usuario.id_usuario
    else:
        exigir(datos, "id_sede", "cliente")
        id_sede = a_entero(datos["id_sede"], "id_sede", 1)
        tipo_entrega = a_enum(TipoEntrega, datos.get("tipo_entrega", "RECOGER_EN_TIENDA"), "tipo_entrega")
        if tipo_entrega == TipoEntrega.INMEDIATA:
            raise ErrorApi(422, "La entrega INMEDIATA solo aplica a ventas en tienda")
        id_usuario = None

    sede = obtener_sede_activa(id_sede)
    cantidades = consolidar_items(lista_items(datos))

    envio = None
    if tipo_entrega == TipoEntrega.DOMICILIO:
        datos_envio = datos.get("envio")
        if not isinstance(datos_envio, dict):
            raise ErrorApi(422, "Los pedidos a DOMICILIO requieren el objeto 'envio'")
        envio = Envio(
            direccion=texto(datos_envio, "direccion", 150, obligatorio=True),
            ciudad=texto(datos_envio, "ciudad", 60, obligatorio=True),
            destinatario=texto(datos_envio, "destinatario", 120, obligatorio=True),
            telefono_contacto=texto(datos_envio, "telefono_contacto", 20, obligatorio=True),
            estado=EstadoEnvio.PREPARANDO,
        )

    # El pedido descuenta únicamente de su sede: se valida lo disponible allí.
    lineas, conflictos = [], []
    for id_variante, cantidad in cantidades.items():
        variante = obtener_variante_activa(id_variante)
        stock = obtener_stock(sede.id_sede, id_variante)
        libre = disponible(stock)
        if libre < cantidad:
            conflictos.append(conflicto_existencias(variante, sede.id_sede, cantidad, libre))
        else:
            lineas.append((variante, stock, cantidad))
    if conflictos:
        raise ErrorApi(409, "Existencias insuficientes", conflictos=conflictos)

    cliente = _resolver_cliente(datos["cliente"]) if datos.get("cliente") else None
    pedido = Pedido(
        id_cliente=cliente.id_cliente if cliente else None, id_sede=sede.id_sede,
        id_usuario=id_usuario, canal=canal, tipo_entrega=tipo_entrega,
        estado=EstadoPedido.PENDIENTE, codigo_qr=codigo_temporal(),
    )
    db.session.add(pedido)
    db.session.flush()

    total = Decimal("0")
    for variante, stock, cantidad in lineas:
        precio = precio_final(variante)  # precio histórico: se copia y no se recalcula
        total += precio * cantidad
        db.session.add(DetallePedido(
            id_pedido=pedido.id_pedido, id_variante=variante.id_variante, cantidad=cantidad,
            precio_unitario=precio, subtotal_linea=precio * cantidad,
        ))
        stock.cantidad_reservada += cantidad

    pedido.total = total
    pedido.subtotal, pedido.impuestos = separar_iva(total)
    pedido.codigo_qr = f"SOL-P-{pedido.id_pedido:08d}"
    if envio is not None:
        envio.id_pedido = pedido.id_pedido
        db.session.add(envio)
    db.session.commit()
    return pedido


def _reserva_activa(pedido):
    """Las unidades siguen reservadas mientras el pedido esté pendiente y ningún pago se haya rechazado."""
    return (pedido.estado == EstadoPedido.PENDIENTE
            and not any(p.estado == EstadoPago.RECHAZADO for p in pedido.pagos))


def _liberar_reserva(pedido):
    for detalle in pedido.detalles:
        stock = obtener_stock(pedido.id_sede, detalle.id_variante)
        if stock is not None:
            stock.cantidad_reservada = max(stock.cantidad_reservada - detalle.cantidad, 0)


def registrar_pago(pedido, datos, usuario):
    """Pasarela simulada. Enviar "simular_rechazo": true para probar el rechazo."""
    if pedido.estado != EstadoPedido.PENDIENTE:
        raise ErrorApi(409, f"El pedido está en estado {pedido.estado.value} y no admite pagos")
    exigir(datos, "id_metodo_pago", "monto")
    metodo = db.session.get(MetodoPago, a_entero(datos["id_metodo_pago"], "id_metodo_pago", 1))
    if metodo is None or not metodo.activo:
        raise ErrorApi(404, "Método de pago no encontrado")
    monto = a_decimal(datos["monto"], "monto", positivo=True)
    if monto != pedido.total:
        raise ErrorApi(422, "El monto debe ser igual al total del pedido", total=pedido.total)

    reserva_activa = _reserva_activa(pedido)
    rechazado = datos.get("simular_rechazo") is True
    pago = Pago(
        id_pedido=pedido.id_pedido, id_metodo_pago=metodo.id_metodo_pago, monto=monto,
        estado=EstadoPago.RECHAZADO if rechazado else EstadoPago.APROBADO,
        referencia_transaccion=f"SIM-{prefijo_ascii(metodo.nombre, 8)}-{uuid.uuid4().hex[:8].upper()}",
    )

    if rechazado:
        if reserva_activa:
            _liberar_reserva(pedido)
    else:
        conflictos = []
        for detalle in pedido.detalles:
            stock = obtener_stock(pedido.id_sede, detalle.id_variante)
            if reserva_activa:
                stock.cantidad_reservada = max(stock.cantidad_reservada - detalle.cantidad, 0)
            elif disponible(stock) < detalle.cantidad:
                conflictos.append(conflicto_existencias(
                    detalle.variante, pedido.id_sede, detalle.cantidad, disponible(stock)))
        if conflictos:
            raise ErrorApi(409, "Existencias insuficientes", conflictos=conflictos)
        for detalle in pedido.detalles:
            registrar_movimiento(
                id_sede=pedido.id_sede, variante=detalle.variante, tipo=TipoMovimiento.VENTA,
                cantidad=-detalle.cantidad, usuario=usuario,
                tipo_referencia="PEDIDO", id_referencia=pedido.id_pedido,
            )
        pedido.estado = EstadoPedido.PAGADO

    db.session.add(pago)
    db.session.commit()
    return pago


TRANSICIONES = {
    EstadoPedido.PENDIENTE: {EstadoPedido.CANCELADO},
    EstadoPedido.PAGADO: {EstadoPedido.PREPARANDO, EstadoPedido.ENTREGADO},
    EstadoPedido.PREPARANDO: {EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO},
    EstadoPedido.ENVIADO: {EstadoPedido.ENTREGADO},
}


def cambiar_estado_pedido(pedido, datos):
    exigir(datos, "estado")
    nuevo = a_enum(EstadoPedido, datos["estado"], "estado")
    if nuevo == EstadoPedido.PAGADO:
        raise ErrorApi(409, "El estado PAGADO solo se alcanza registrando un pago aprobado")
    permitidos = TRANSICIONES.get(pedido.estado, set())
    if nuevo not in permitidos:
        raise ErrorApi(409, f"No se puede pasar de {pedido.estado.value} a {nuevo.value}",
                       permitidos=sorted(e.value for e in permitidos))
    domicilio = pedido.tipo_entrega == TipoEntrega.DOMICILIO
    if nuevo == EstadoPedido.ENVIADO and not domicilio:
        raise ErrorApi(409, "Solo los pedidos a DOMICILIO pasan por ENVIADO")
    if nuevo == EstadoPedido.ENTREGADO and domicilio and pedido.estado != EstadoPedido.ENVIADO:
        raise ErrorApi(409, "Un pedido a DOMICILIO debe estar ENVIADO antes de marcarse ENTREGADO")

    ahora = datetime.now().replace(microsecond=0)
    if nuevo == EstadoPedido.CANCELADO and _reserva_activa(pedido):
        _liberar_reserva(pedido)
    if pedido.envio is not None:
        if nuevo == EstadoPedido.ENVIADO:
            pedido.envio.estado = EstadoEnvio.DESPACHADO
            pedido.envio.fecha_despacho = ahora
            pedido.envio.transportadora = texto(datos, "transportadora", 60) or pedido.envio.transportadora
            pedido.envio.numero_guia = texto(datos, "numero_guia", 60) or pedido.envio.numero_guia
        elif nuevo == EstadoPedido.ENTREGADO:
            pedido.envio.estado = EstadoEnvio.ENTREGADO
            pedido.envio.fecha_entrega = ahora
    pedido.estado = nuevo
    db.session.commit()
    return pedido
