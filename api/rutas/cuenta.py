"""
cuenta.py
Rutas del comprador registrado (rol CLIENTE): sus pedidos, su seguimiento y sus
solicitudes de devolución o cambio.
Un cliente solo ve los pedidos enlazados a su propia ficha; si pide uno ajeno
recibe 404, para no revelar siquiera que el pedido existe.
"""
from flask import Blueprint, g, jsonify
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Devolucion, Pedido, db
from api.seguridad import CLIENTE, requiere_auth
from api.serializadores import devolucion_dict, pedido_dict
from api.servicios import devoluciones
from api.validacion import arg_entero, leer_json

bp = Blueprint("cuenta", __name__)


def _id_cliente():
    if g.usuario.cliente is None:
        raise ErrorApi(409, "La cuenta no tiene ficha de cliente asociada")
    return g.usuario.cliente.id_cliente


@bp.get("/cuenta/pedidos")
@requiere_auth(CLIENTE)
def mis_pedidos():
    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 20, minimo=1, maximo=100)
    consulta = (select(Pedido).where(Pedido.id_cliente == _id_cliente())
                .order_by(Pedido.id_pedido.desc()))
    resultado = db.paginate(consulta, page=pagina, per_page=tamano, error_out=False)
    return jsonify({
        "total": resultado.total,
        "page": pagina,
        "size": tamano,
        "items": [pedido_dict(p) for p in resultado.items],
    })


def _pedido_propio(id_pedido):
    pedido = db.session.get(Pedido, id_pedido)
    if pedido is None or pedido.id_cliente != _id_cliente():
        raise ErrorApi(404, "Pedido no encontrado")
    return pedido


@bp.get("/cuenta/pedidos/<int:id_pedido>")
@requiere_auth(CLIENTE)
def mi_pedido(id_pedido):
    pedido = _pedido_propio(id_pedido)
    datos = pedido_dict(pedido)
    devolvibles = devoluciones.unidades_devolvibles(pedido)
    for item in datos["items"]:
        item["devolvible"] = devolvibles[item["id_detalle_pedido"]]
    return jsonify(datos)


@bp.post("/cuenta/pedidos/<int:id_pedido>/devoluciones")
@requiere_auth(CLIENTE)
def solicitar_devolucion(id_pedido):
    """El cliente pide devolver o cambiar prendas; queda SOLICITADA hasta que la sede la reciba.
    {"tipo": "DEVOLUCION"|"CAMBIO", "motivo": "...", "id_sede": opcional,
     "items": [{"id_detalle_pedido", "cantidad", "id_variante_cambio" (solo CAMBIO)}]}"""
    devolucion = devoluciones.solicitar(_pedido_propio(id_pedido), leer_json(), g.usuario)
    return jsonify(devolucion_dict(devolucion)), 201


@bp.get("/cuenta/devoluciones")
@requiere_auth(CLIENTE)
def mis_devoluciones():
    consulta = (select(Devolucion).join(Pedido, Pedido.id_pedido == Devolucion.id_pedido)
                .where(Pedido.id_cliente == _id_cliente())
                .order_by(Devolucion.id_devolucion.desc()))
    return jsonify([devolucion_dict(d) for d in db.session.scalars(consulta).all()])
