"""
fichas.py
Ficha técnica con atributos variables (MongoDB) y vistas combinadas del producto:
datos comerciales y stock desde MySQL + ficha, reseñas y escaneos desde MongoDB.
"""
from flask import Blueprint, current_app, g, jsonify, request
from pymongo.errors import PyMongoError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.errores import ErrorApi
from api.modelos import Producto, Variante, db
from api.seguridad import ADMINISTRADOR, requiere_auth
from api.serializadores import producto_detalle, producto_resumen, sedes_activas
from api.servicios import actividad, fichas, resenas
from api.validacion import leer_json

bp = Blueprint("fichas", __name__)


@bp.get("/productos/<int:id_producto>/ficha")
def obtener_ficha(id_producto):
    resenas.obtener_producto_activo(id_producto)
    ficha = fichas.obtener_ficha(id_producto)
    if ficha is None:
        raise ErrorApi(404, "El producto no tiene ficha técnica")
    return jsonify(ficha)


@bp.put("/productos/<int:id_producto>/ficha")
@requiere_auth(ADMINISTRADOR)
def guardar_ficha(id_producto):
    producto = resenas.obtener_producto_activo(id_producto)
    return jsonify(fichas.guardar_ficha(producto, leer_json(), g.usuario))


@bp.delete("/productos/<int:id_producto>/ficha")
@requiere_auth(ADMINISTRADOR)
def eliminar_ficha(id_producto):
    fichas.eliminar_ficha(id_producto)
    return "", 204


@bp.get("/productos/<int:id_producto>/completo")
def producto_completo(id_producto):
    """
    Vista 360° del producto para la tienda web:
      MySQL   -> nombre, precio, categoría, imágenes, variantes y stock por sede
      MongoDB -> ficha técnica, resumen y últimas reseñas, escaneos de los últimos 30 días
    Si MongoDB no responde, se devuelve igual la parte de MySQL.
    """
    producto = resenas.obtener_producto_activo(id_producto)
    respuesta = producto_detalle(producto, sedes_activas())
    try:
        respuesta["ficha_tecnica"] = fichas.obtener_ficha(id_producto)
        respuesta["resenas"] = {
            "resumen": resenas.resumen_resenas(id_producto),
            "recientes": resenas.listar_resenas(id_producto, 1, 5)["items"],
        }
        respuesta["escaneos_qr_30_dias"] = actividad.escaneos_recientes(id_producto)
        respuesta["nosql_disponible"] = True
    except PyMongoError as error:
        current_app.logger.warning("MongoDB no disponible en producto_completo: %s", error)
        respuesta["nosql_disponible"] = False
    return jsonify(respuesta)


@bp.get("/productos/buscar-atributos")
def buscar_por_atributos():
    """
    Busca en MongoDB por atributos que no existen como columnas en MySQL
    (?etiqueta=verano&atributos.material=algodon) y devuelve los productos con
    precio y stock vigentes leídos de MySQL.
    """
    filtro, ids = fichas.buscar_por_atributos(request.args)
    productos = []
    if ids:
        productos = db.session.scalars(
            select(Producto)
            .where(Producto.id_producto.in_(ids), Producto.activo.is_(True))
            .options(
                selectinload(Producto.categoria),
                selectinload(Producto.imagenes),
                selectinload(Producto.variantes).selectinload(Variante.stocks),
            )
            .order_by(Producto.id_producto)
        ).all()
    sedes = sedes_activas()
    return jsonify({
        "filtro_mongodb": filtro,
        "total": len(productos),
        "items": [producto_resumen(p, sedes) for p in productos],
    })
