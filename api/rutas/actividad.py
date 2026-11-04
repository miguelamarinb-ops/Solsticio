"""
actividad.py
Endpoints que combinan MySQL (datos del usuario y del catálogo) con MongoDB
(bitácora de actividad y escaneos QR).
"""
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from api.errores import ErrorApi
from api.modelos import Usuario
from api.seguridad import ADMINISTRADOR, requiere_auth
from api.serializadores import sedes_activas, usuario_dict
from api.servicios import actividad
from api.validacion import a_fecha, arg_entero, obtener_o_404

bp = Blueprint("actividad", __name__)


def _perfil_con_actividad(usuario, limite):
    return {
        "usuario": usuario_dict(usuario),                                   # MySQL
        "fecha_registro": usuario.fecha_registro,                           # MySQL
        "ultimas_actividades": actividad.ultimas_actividades(usuario.id_usuario, limite),  # MongoDB
        "resumen_actividad": actividad.resumen_actividad(usuario.id_usuario),              # MongoDB
        "fuentes": {"usuario": "MySQL", "ultimas_actividades": "MongoDB", "resumen_actividad": "MongoDB"},
    }


@bp.get("/auth/perfil/actividad")
@requiere_auth()
def perfil_con_actividad():
    """Perfil del usuario autenticado (SQL) junto a sus últimas 10 acciones (NoSQL)."""
    limite = arg_entero("limite", 10, minimo=1, maximo=50)
    return jsonify(_perfil_con_actividad(g.usuario, limite))


@bp.get("/usuarios/<int:id_usuario>/actividad")
@requiere_auth(ADMINISTRADOR)
def actividad_de_usuario(id_usuario):
    usuario = obtener_o_404(Usuario, id_usuario, "Usuario no encontrado")
    limite = arg_entero("limite", 10, minimo=1, maximo=50)
    return jsonify(_perfil_con_actividad(usuario, limite))


@bp.get("/actividad")
@requiere_auth(ADMINISTRADOR)
def listar_actividad():
    """Bitácora completa con filtros: ?id_usuario=&accion=&exito=&desde=&hasta=&page=&size="""
    filtro = {}
    id_usuario = arg_entero("id_usuario", minimo=1)
    if id_usuario:
        filtro["id_usuario"] = id_usuario
    if request.args.get("accion"):
        filtro["accion"] = request.args["accion"].strip().upper()
    if request.args.get("exito") in ("true", "false"):
        filtro["exito"] = request.args["exito"] == "true"
    rango = {}
    for parametro, operador in (("desde", "$gte"), ("hasta", "$lt")):
        if request.args.get(parametro):
            dia = a_fecha(request.args[parametro], parametro)
            rango[operador] = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
    if rango:
        filtro["fecha"] = rango

    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 20, minimo=1, maximo=100)
    return jsonify(actividad.listar_actividad(filtro, pagina, tamano))


@bp.get("/reportes/qr-mas-escaneados")
@requiere_auth(ADMINISTRADOR)
def qr_mas_escaneados():
    """Ranking de escaneos (MongoDB) enriquecido con producto, precio y stock (MySQL)."""
    dias = arg_entero("dias", 30, minimo=1, maximo=365)
    limite = arg_entero("limite", 10, minimo=1, maximo=50)
    ranking = actividad.variantes_mas_escaneadas(dias, limite, sedes_activas())
    if not ranking:
        raise ErrorApi(404, f"No hay escaneos registrados en los últimos {dias} días")
    return jsonify({"dias": dias, "items": ranking})
