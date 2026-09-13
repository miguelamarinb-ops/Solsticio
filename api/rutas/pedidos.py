"""
pedidos.py
Pedidos (web y tienda), pagos con pasarela simulada y facturación electrónica.
"""
from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Canal, EstadoPago, EstadoPedido, Factura, MetodoPago, Pedido, db
from api.seguridad import PERSONAL, auth_opcional, es_admin, requiere_auth, verificar_sede
from api.serializadores import factura_dict, pago_dict, pedido_dict, pedido_por_qr
from api.servicios import facturacion, pedidos
from api.validacion import a_enum, arg_entero, leer_json, obtener_o_404

bp = Blueprint("pedidos", __name__)


def _pedido_de_personal(id_pedido):
    pedido = obtener_o_404(Pedido, id_pedido, "Pedido no encontrado")
    verificar_sede(g.usuario, pedido.id_sede)
    return pedido


@bp.post("/pedidos")
@auth_opcional
def crear_pedido():
    pedido = pedidos.crear_pedido(leer_json(), g.usuario)
    return jsonify(pedido_dict(pedido)), 201


@bp.get("/pedidos")
@requiere_auth(*PERSONAL)
def listar_pedidos():
    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 20, minimo=1, maximo=100)
    consulta = select(Pedido).order_by(Pedido.id_pedido.desc())
    id_sede = arg_entero("id_sede", minimo=1)
    if not es_admin(g.usuario):
        id_sede = g.usuario.id_sede
    if id_sede:
        consulta = consulta.where(Pedido.id_sede == id_sede)
    if request.args.get("estado"):
        consulta = consulta.where(Pedido.estado == a_enum(EstadoPedido, request.args["estado"], "estado"))
    if request.args.get("canal"):
        consulta = consulta.where(Pedido.canal == a_enum(Canal, request.args["canal"], "canal"))
    resultado = db.paginate(consulta, page=pagina, per_page=tamano, error_out=False)
    return jsonify({
        "total": resultado.total,
        "page": pagina,
        "size": tamano,
        "items": [pedido_dict(p) for p in resultado.items],
    })


@bp.get("/pedidos/<int:id_pedido>")
@requiere_auth(*PERSONAL)
def obtener_pedido(id_pedido):
    return jsonify(pedido_dict(_pedido_de_personal(id_pedido)))


@bp.get("/pedidos/qr/<codigo_qr>")
@requiere_auth(*PERSONAL)
def resolver_qr_pedido(codigo_qr):
    pedido = db.session.scalars(select(Pedido).where(Pedido.codigo_qr == codigo_qr)).first()
    if pedido is None:
        raise ErrorApi(404, "El código QR no corresponde a ningún pedido")
    verificar_sede(g.usuario, pedido.id_sede)
    return jsonify(pedido_por_qr(pedido))


@bp.patch("/pedidos/<int:id_pedido>/estado")
@requiere_auth(*PERSONAL)
def cambiar_estado_pedido(id_pedido):
    pedido = pedidos.cambiar_estado_pedido(_pedido_de_personal(id_pedido), leer_json())
    return jsonify(pedido_dict(pedido))


@bp.get("/metodos-pago")
def listar_metodos_pago():
    metodos = db.session.scalars(
        select(MetodoPago).where(MetodoPago.activo.is_(True)).order_by(MetodoPago.id_metodo_pago)
    ).all()
    return jsonify([{"id_metodo_pago": m.id_metodo_pago, "nombre": m.nombre, "tipo": m.tipo} for m in metodos])


@bp.post("/pedidos/<int:id_pedido>/pagos")
@auth_opcional
def registrar_pago(id_pedido):
    pedido = obtener_o_404(Pedido, id_pedido, "Pedido no encontrado")
    if pedido.canal == Canal.TIENDA:
        if g.usuario is None:
            raise ErrorApi(401, "Los pagos de ventas en tienda requieren el token de un trabajador")
        verificar_sede(g.usuario, pedido.id_sede)

    pago = pedidos.registrar_pago(pedido, leer_json(), g.usuario)
    if pago.estado == EstadoPago.RECHAZADO:
        return jsonify({
            "detail": "La transacción fue rechazada por la pasarela",
            "estado": pago.estado,
            "referencia_transaccion": pago.referencia_transaccion,
            "motivo": "Rechazo simulado",
            "pedido_estado_actual": pedido.estado,
        }), 402

    # Facturación automática: si la DIAN falla, la venta y el pago se conservan.
    factura = None
    try:
        factura, _ = facturacion.emitir_factura(pedido)
    except Exception:
        db.session.rollback()
    return jsonify({**pago_dict(pago), "pedido_estado_actual": pedido.estado,
                    "factura": factura_dict(factura)}), 201


@bp.post("/pedidos/<int:id_pedido>/factura")
@requiere_auth(*PERSONAL)
def generar_factura(id_pedido):
    factura, validada = facturacion.emitir_factura(_pedido_de_personal(id_pedido))
    if not validada:
        return jsonify({
            "detail": "El servicio de la DIAN no respondió. La factura quedó en estado PENDIENTE.",
            "id_factura": factura.id_factura,
            "estado_dian": factura.estado_dian,
        }), 502
    return jsonify(factura_dict(factura)), 201


@bp.get("/facturas/<int:id_factura>")
@requiere_auth(*PERSONAL)
def obtener_factura(id_factura):
    factura = obtener_o_404(Factura, id_factura, "Factura no encontrada")
    verificar_sede(g.usuario, factura.pedido.id_sede)
    return jsonify(factura_dict(factura))
