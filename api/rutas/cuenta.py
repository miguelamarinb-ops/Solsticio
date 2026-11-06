"""
cuenta.py
Rutas del comprador registrado (rol CLIENTE): sus pedidos web y su seguimiento.
Un cliente solo ve los pedidos enlazados a su propia ficha; si pide uno ajeno
recibe 404, para no revelar siquiera que el pedido existe.
"""
from flask import Blueprint, g, jsonify
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Pedido, db
from api.seguridad import CLIENTE, requiere_auth
from api.serializadores import pedido_dict
from api.validacion import arg_entero

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


@bp.get("/cuenta/pedidos/<int:id_pedido>")
@requiere_auth(CLIENTE)
def mi_pedido(id_pedido):
    pedido = db.session.get(Pedido, id_pedido)
    if pedido is None or pedido.id_cliente != _id_cliente():
        raise ErrorApi(404, "Pedido no encontrado")
    return jsonify(pedido_dict(pedido))
