"""
resenas.py
CRUD de reseñas de productos (MongoDB). Publicar y leer es público; moderar,
responder y eliminar es exclusivo del administrador.
"""
from flask import Blueprint, g, jsonify, request

from api import nosql
from api.seguridad import ADMINISTRADOR, requiere_auth
from api.servicios import resenas
from api.validacion import arg_entero, leer_json

bp = Blueprint("resenas", __name__)


@bp.get("/productos/<int:id_producto>/resenas")
def listar_resenas(id_producto):
    resenas.obtener_producto_activo(id_producto)
    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 10, minimo=1, maximo=50)
    calificacion = arg_entero("calificacion", minimo=1, maximo=5)
    respuesta = resenas.listar_resenas(
        id_producto, pagina, tamano, request.args.get("orden", "recientes"), calificacion
    )
    respuesta["resumen"] = resenas.resumen_resenas(id_producto)
    return jsonify(respuesta)


@bp.post("/productos/<int:id_producto>/resenas")
def crear_resena(id_producto):
    producto = resenas.obtener_producto_activo(id_producto)
    return jsonify(resenas.crear_resena(producto, leer_json())), 201


@bp.get("/resenas")
@requiere_auth(ADMINISTRADOR)
def listar_resenas_moderacion():
    """Bandeja de moderación: ?estado=PUBLICADA|OCULTA&id_producto=&calificacion=&page=&size="""
    return jsonify(resenas.listar_para_moderar(
        request.args.get("estado"),
        arg_entero("id_producto", minimo=1),
        arg_entero("calificacion", minimo=1, maximo=5),
        arg_entero("page", 1, minimo=1),
        arg_entero("size", 20, minimo=1, maximo=100),
    ))


@bp.get("/resenas/<id_resena>")
def obtener_resena(id_resena):
    return jsonify(resenas.obtener_resena(nosql.a_object_id(id_resena, "Reseña no encontrada"), publica=True))


@bp.post("/resenas/<id_resena>/util")
def marcar_util(id_resena):
    return jsonify(resenas.marcar_util(nosql.a_object_id(id_resena, "Reseña no encontrada")))


@bp.patch("/resenas/<id_resena>")
@requiere_auth(ADMINISTRADOR)
def moderar_resena(id_resena):
    id_doc = nosql.a_object_id(id_resena, "Reseña no encontrada")
    return jsonify(resenas.moderar_resena(id_doc, leer_json(), g.usuario))


@bp.delete("/resenas/<id_resena>")
@requiere_auth(ADMINISTRADOR)
def eliminar_resena(id_resena):
    resenas.eliminar_resena(nosql.a_object_id(id_resena, "Reseña no encontrada"))
    return "", 204
