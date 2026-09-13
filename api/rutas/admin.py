"""
admin.py
Administración (solo ADMINISTRADOR): productos, variantes, categorías, sedes y usuarios.
"""
from flask import Blueprint, jsonify

from api.modelos import Producto
from api.seguridad import ADMINISTRADOR, requiere_auth
from api.serializadores import (
    categoria_dict, precio_final, producto_detalle, sede_dict, sedes_activas, usuario_dict,
)
from api.servicios import catalogo, usuarios
from api.validacion import leer_json, obtener_o_404

bp = Blueprint("admin", __name__)


@bp.post("/categorias")
@requiere_auth(ADMINISTRADOR)
def crear_categoria():
    return jsonify(categoria_dict(catalogo.crear_categoria(leer_json()))), 201


@bp.post("/sedes")
@requiere_auth(ADMINISTRADOR)
def crear_sede():
    return jsonify(sede_dict(catalogo.crear_sede(leer_json()))), 201


@bp.post("/usuarios")
@requiere_auth(ADMINISTRADOR)
def crear_usuario():
    return jsonify(usuario_dict(usuarios.crear_usuario(leer_json()))), 201


@bp.post("/productos")
@requiere_auth(ADMINISTRADOR)
def crear_producto():
    producto = catalogo.crear_producto(leer_json())
    return jsonify(producto_detalle(producto, sedes_activas())), 201


@bp.put("/productos/<int:id_producto>")
@requiere_auth(ADMINISTRADOR)
def actualizar_producto(id_producto):
    producto = obtener_o_404(Producto, id_producto, "Producto no encontrado")
    catalogo.actualizar_producto(producto, leer_json())
    return jsonify(producto_detalle(producto, sedes_activas()))


@bp.delete("/productos/<int:id_producto>")
@requiere_auth(ADMINISTRADOR)
def desactivar_producto(id_producto):
    catalogo.desactivar_producto(obtener_o_404(Producto, id_producto, "Producto no encontrado"))
    return "", 204


@bp.post("/productos/<int:id_producto>/variantes")
@requiere_auth(ADMINISTRADOR)
def crear_variantes(id_producto):
    producto = obtener_o_404(Producto, id_producto, "Producto no encontrado")
    creadas, omitidas = catalogo.crear_variantes(producto, leer_json())
    return jsonify({
        "id_producto": producto.id_producto,
        "creadas": [{"id_variante": v.id_variante, "sku": v.sku, "codigo_qr": v.codigo_qr,
                     "precio_final": precio_final(v)} for v in creadas],
        "omitidas": omitidas,
    }), 201
