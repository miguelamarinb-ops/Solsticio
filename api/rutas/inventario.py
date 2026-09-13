"""
inventario.py
Stock por sede, ingresos, ajustes, historial de movimientos y traslados.
"""
from datetime import timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.errores import ErrorApi
from api.modelos import MovimientoInventario, Stock, TipoMovimiento, Traslado, Variante, db
from api.seguridad import ADMINISTRADOR, PERSONAL, es_admin, requiere_auth
from api.serializadores import (
    movimiento_aplicado, movimiento_dict, nombre_completo, stock_dict, traslado_dict,
)
from api.servicios import inventario, traslados
from api.validacion import a_enum, a_fecha, arg_booleano, arg_entero, leer_json, obtener_o_404

bp = Blueprint("inventario", __name__)


@bp.get("/stock")
@requiere_auth(*PERSONAL)
def consultar_stock():
    consulta = (
        select(Stock)
        .join(Variante, Variante.id_variante == Stock.id_variante)
        .options(selectinload(Stock.sede), selectinload(Stock.variante))
        .order_by(Stock.id_sede, Stock.id_variante)
    )
    id_sede = arg_entero("id_sede", minimo=1)
    if not es_admin(g.usuario):
        if id_sede not in (None, g.usuario.id_sede):
            raise ErrorApi(403, "Un trabajador solo puede consultar el stock de su sede; "
                                "use /variantes/{id}/disponibilidad para ver otras sedes")
        id_sede = g.usuario.id_sede
    if id_sede:
        consulta = consulta.where(Stock.id_sede == id_sede)
    if arg_entero("id_variante", minimo=1):
        consulta = consulta.where(Stock.id_variante == arg_entero("id_variante"))
    if arg_entero("id_producto", minimo=1):
        consulta = consulta.where(Variante.id_producto == arg_entero("id_producto"))
    if arg_booleano("bajo_minimo"):
        consulta = consulta.where(Stock.cantidad <= Stock.stock_minimo)
    return jsonify([stock_dict(s) for s in db.session.scalars(consulta).all()])


def _respuesta_movimientos(sede, resultados):
    return {
        "id_sede": sede.id_sede,
        "sede": sede.nombre,
        "registrado_por": nombre_completo(g.usuario),
        "movimientos": [movimiento_aplicado(r) for r in resultados],
    }


@bp.post("/inventario/ingresos")
@requiere_auth(*PERSONAL)
def registrar_ingreso():
    sede, resultados = inventario.registrar_ingreso(leer_json(), g.usuario)
    return jsonify(_respuesta_movimientos(sede, resultados)), 201


@bp.post("/inventario/ajustes")
@requiere_auth(ADMINISTRADOR)
def registrar_ajuste():
    sede, resultados = inventario.registrar_ajuste(leer_json(), g.usuario)
    return jsonify(_respuesta_movimientos(sede, resultados)), 201


@bp.get("/inventario/movimientos")
@requiere_auth(ADMINISTRADOR)
def listar_movimientos():
    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 50, minimo=1, maximo=200)
    consulta = select(MovimientoInventario).order_by(MovimientoInventario.id_movimiento.desc())
    if arg_entero("id_sede", minimo=1):
        consulta = consulta.where(MovimientoInventario.id_sede == arg_entero("id_sede"))
    if arg_entero("id_variante", minimo=1):
        consulta = consulta.where(MovimientoInventario.id_variante == arg_entero("id_variante"))
    if request.args.get("tipo"):
        consulta = consulta.where(MovimientoInventario.tipo == a_enum(TipoMovimiento, request.args["tipo"], "tipo"))
    if request.args.get("desde"):
        consulta = consulta.where(MovimientoInventario.fecha >= a_fecha(request.args["desde"], "desde"))
    if request.args.get("hasta"):
        consulta = consulta.where(
            MovimientoInventario.fecha < a_fecha(request.args["hasta"], "hasta") + timedelta(days=1))
    resultado = db.paginate(consulta, page=pagina, per_page=tamano, error_out=False)
    return jsonify({
        "total": resultado.total,
        "page": pagina,
        "size": tamano,
        "items": [movimiento_dict(m) for m in resultado.items],
    })


@bp.post("/traslados")
@requiere_auth(ADMINISTRADOR)
def crear_traslado():
    traslado, disponibles = traslados.crear_traslado(leer_json(), g.usuario)
    return jsonify(traslado_dict(traslado, disponibles)), 201


@bp.get("/traslados/<int:id_traslado>")
@requiere_auth(*PERSONAL)
def obtener_traslado(id_traslado):
    return jsonify(traslado_dict(obtener_o_404(Traslado, id_traslado, "Traslado no encontrado")))


@bp.patch("/traslados/<int:id_traslado>/despachar")
@requiere_auth(*PERSONAL)
def despachar_traslado(id_traslado):
    traslado = obtener_o_404(Traslado, id_traslado, "Traslado no encontrado")
    resultados = traslados.despachar_traslado(traslado, g.usuario)
    return jsonify({**traslado_dict(traslado),
                    "movimientos_generados": [movimiento_aplicado(r) for r in resultados]})


@bp.patch("/traslados/<int:id_traslado>/recibir")
@requiere_auth(*PERSONAL)
def recibir_traslado(id_traslado):
    traslado = obtener_o_404(Traslado, id_traslado, "Traslado no encontrado")
    resultados = traslados.recibir_traslado(traslado, g.usuario)
    return jsonify({**traslado_dict(traslado),
                    "movimientos_generados": [movimiento_aplicado(r) for r in resultados]})
