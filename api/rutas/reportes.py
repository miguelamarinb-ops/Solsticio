"""
reportes.py
Caso de uso 2.3.9, analítica y reportes. Solo el ADMINISTRADOR.
El periodo se pasa con ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD (incluye los dos días);
si no se indica, son los últimos 30 días hasta hoy.
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from api.errores import ErrorApi
from api.modelos import Canal, Sede
from api.seguridad import ADMINISTRADOR, requiere_auth
from api.servicios import reportes
from api.validacion import a_enum, a_fecha, arg_entero, obtener_o_404

bp = Blueprint("reportes", __name__)

DIAS_POR_DEFECTO = 30
DIAS_MAXIMOS = 366


def _periodo():
    hasta = a_fecha(request.args["hasta"], "hasta") if request.args.get("hasta") else date.today()
    if request.args.get("desde"):
        desde = a_fecha(request.args["desde"], "desde")
    else:
        desde = hasta - timedelta(days=DIAS_POR_DEFECTO - 1)
    if desde > hasta:
        raise ErrorApi(422, "'desde' no puede ser posterior a 'hasta'")
    if (hasta - desde).days + 1 > DIAS_MAXIMOS:
        raise ErrorApi(422, f"El periodo no puede superar {DIAS_MAXIMOS} días")
    return desde, hasta


def _sede():
    id_sede = arg_entero("id_sede", minimo=1)
    if id_sede:
        obtener_o_404(Sede, id_sede, "Sede no encontrada")
    return id_sede


@bp.get("/reportes/ventas")
@requiere_auth(ADMINISTRADOR)
def reporte_ventas():
    """Pedidos, unidades, ingresos brutos y netos de devoluciones, por canal y por día."""
    desde, hasta = _periodo()
    canal = a_enum(Canal, request.args["canal"], "canal") if request.args.get("canal") else None
    return jsonify(reportes.ventas(desde, hasta, _sede(), canal))


@bp.get("/reportes/productos-mas-vendidos")
@requiere_auth(ADMINISTRADOR)
def reporte_productos_mas_vendidos():
    """Ranking de prendas por unidades vendidas, con ingresos y talla más vendida."""
    desde, hasta = _periodo()
    limite = arg_entero("limite", 5, minimo=1, maximo=50)
    return jsonify(reportes.productos_mas_vendidos(desde, hasta, limite, _sede()))


@bp.get("/reportes/rotacion-inventario")
@requiere_auth(ADMINISTRADOR)
def reporte_rotacion_inventario():
    """Unidades vendidas frente a existencias por prenda: índice de rotación y días de inventario."""
    desde, hasta = _periodo()
    return jsonify(reportes.rotacion_inventario(desde, hasta, _sede()))
