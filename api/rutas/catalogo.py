"""
catalogo.py
Consultas públicas del catálogo: categorías, sedes, productos, variantes y QR.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.errores import ErrorApi
from api.modelos import Categoria, Color, Genero, Producto, Talla, Variante, db
from api.serializadores import (
    categoria_dict, disponibilidad_detallada, producto_detalle, producto_resumen, sede_dict,
    sedes_activas, variante_por_qr,
)
from api.validacion import a_enum, arg_entero

bp = Blueprint("catalogo", __name__)


@bp.get("/categorias")
def listar_categorias():
    categorias = db.session.scalars(
        select(Categoria).where(Categoria.activo.is_(True)).order_by(Categoria.nombre)
    ).all()
    return jsonify([categoria_dict(c) for c in categorias])


@bp.get("/sedes")
def listar_sedes():
    return jsonify([sede_dict(s) for s in sedes_activas()])


@bp.get("/tallas")
def listar_tallas():
    tallas = db.session.scalars(select(Talla).order_by(Talla.orden)).all()
    return jsonify([{"id_talla": t.id_talla, "valor": t.valor, "orden": t.orden} for t in tallas])


@bp.get("/colores")
def listar_colores():
    colores = db.session.scalars(select(Color).order_by(Color.nombre)).all()
    return jsonify([{"id_color": c.id_color, "nombre": c.nombre, "codigo_hex": c.codigo_hex} for c in colores])


@bp.get("/productos")
def listar_productos():
    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 20, minimo=1, maximo=100)
    consulta = (
        select(Producto)
        .where(Producto.activo.is_(True))
        .options(
            selectinload(Producto.categoria),
            selectinload(Producto.imagenes),
            selectinload(Producto.variantes).selectinload(Variante.stocks),
            selectinload(Producto.variantes).selectinload(Variante.talla),
            selectinload(Producto.variantes).selectinload(Variante.color),
        )
        .order_by(Producto.id_producto)
    )
    categoria = arg_entero("categoria", minimo=1)
    if categoria:
        consulta = consulta.where(Producto.id_categoria == categoria)
    if request.args.get("genero"):
        consulta = consulta.where(Producto.genero == a_enum(Genero, request.args["genero"], "genero"))
    if request.args.get("q"):
        consulta = consulta.where(Producto.nombre.ilike(f"%{request.args['q'].strip()}%"))

    resultado = db.paginate(consulta, page=pagina, per_page=tamano, error_out=False)
    sedes = sedes_activas()
    return jsonify({
        "total": resultado.total,
        "page": pagina,
        "size": tamano,
        "items": [producto_resumen(p, sedes) for p in resultado.items],
    })


@bp.get("/productos/<int:id_producto>")
def obtener_producto(id_producto):
    producto = db.session.get(Producto, id_producto)
    if producto is None or not producto.activo:
        raise ErrorApi(404, "Producto no encontrado")
    return jsonify(producto_detalle(producto, sedes_activas()))


@bp.get("/variantes/qr/<codigo_qr>")
def resolver_qr_variante(codigo_qr):
    variante = db.session.scalars(select(Variante).where(Variante.codigo_qr == codigo_qr)).first()
    if variante is None or not variante.activo:
        raise ErrorApi(404, "El código QR no corresponde a ninguna referencia registrada")
    return jsonify(variante_por_qr(variante, sedes_activas()))


@bp.get("/variantes/<int:id_variante>/disponibilidad")
def disponibilidad_variante(id_variante):
    variante = db.session.get(Variante, id_variante)
    if variante is None or not variante.activo:
        raise ErrorApi(404, "Variante no encontrada")
    return jsonify(disponibilidad_detallada(variante, sedes_activas()))
