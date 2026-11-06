"""
devoluciones.py
Devoluciones y cambios del lado del personal (caso de uso 2.3.13).
El TRABAJADOR opera solo en su sede; el ADMINISTRADOR en cualquiera.
La solicitud del cliente está en rutas/cuenta.py.
"""
from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Devolucion, EstadoDevolucion, Pedido, TipoDevolucion, db
from api.seguridad import PERSONAL, es_admin, requiere_auth, verificar_sede
from api.serializadores import devolucion_dict, pedido_dict
from api.servicios import devoluciones
from api.validacion import a_entero, a_enum, arg_entero, exigir, leer_json, obtener_o_404

bp = Blueprint("devoluciones", __name__)


def _respuesta(devolucion):
    return devolucion_dict(devolucion, devoluciones.movimientos_de(devolucion))


def _devolucion_de_personal(id_devolucion):
    devolucion = obtener_o_404(Devolucion, id_devolucion, "Devolución no encontrada")
    verificar_sede(g.usuario, devolucion.id_sede)
    return devolucion


@bp.post("/devoluciones")
@requiere_auth(*PERSONAL)
def registrar_devolucion():
    """Recibe las prendas en la sede: reintegra stock, entrega el cambio y emite la nota crédito."""
    datos = leer_json()
    exigir(datos, "id_pedido")
    pedido = obtener_o_404(Pedido, a_entero(datos["id_pedido"], "id_pedido", 1), "Pedido no encontrado")
    if es_admin(g.usuario):
        exigir(datos, "id_sede")
        id_sede = a_entero(datos["id_sede"], "id_sede", 1)
    else:
        id_sede = g.usuario.id_sede
        if datos.get("id_sede") not in (None, id_sede):
            raise ErrorApi(403, "Un trabajador solo recibe devoluciones en su propia sede")
    devolucion = devoluciones.registrar(pedido, datos, g.usuario, id_sede)
    return jsonify(_respuesta(devolucion)), 201


@bp.get("/devoluciones")
@requiere_auth(*PERSONAL)
def listar_devoluciones():
    """?estado=SOLICITADA|COMPLETADA|RECHAZADA  ?tipo=CAMBIO|DEVOLUCION  ?id_pedido=  ?id_sede="""
    pagina = arg_entero("page", 1, minimo=1)
    tamano = arg_entero("size", 20, minimo=1, maximo=100)
    consulta = select(Devolucion).order_by(Devolucion.id_devolucion.desc())
    id_sede = arg_entero("id_sede", minimo=1)
    if not es_admin(g.usuario):
        id_sede = g.usuario.id_sede
    if id_sede:
        consulta = consulta.where(Devolucion.id_sede == id_sede)
    if request.args.get("estado"):
        consulta = consulta.where(Devolucion.estado == a_enum(EstadoDevolucion, request.args["estado"], "estado"))
    if request.args.get("tipo"):
        consulta = consulta.where(Devolucion.tipo == a_enum(TipoDevolucion, request.args["tipo"], "tipo"))
    if arg_entero("id_pedido", minimo=1):
        consulta = consulta.where(Devolucion.id_pedido == arg_entero("id_pedido"))
    resultado = db.paginate(consulta, page=pagina, per_page=tamano, error_out=False)
    return jsonify({
        "total": resultado.total, "page": pagina, "size": tamano,
        "items": [devolucion_dict(d) for d in resultado.items],
    })


@bp.get("/devoluciones/<int:id_devolucion>")
@requiere_auth(*PERSONAL)
def obtener_devolucion(id_devolucion):
    return jsonify(_respuesta(_devolucion_de_personal(id_devolucion)))


@bp.patch("/devoluciones/<int:id_devolucion>")
@requiere_auth(*PERSONAL)
def procesar_solicitud(id_devolucion):
    """Atiende una solicitud del cliente: {"accion": "COMPLETAR"} o {"accion": "RECHAZAR"}."""
    devolucion = _devolucion_de_personal(id_devolucion)
    accion = str(leer_json().get("accion", "")).strip().upper()
    if accion == "COMPLETAR":
        devolucion = devoluciones.completar(devolucion, g.usuario)
    elif accion == "RECHAZAR":
        devolucion = devoluciones.rechazar(devolucion)
    else:
        raise ErrorApi(422, "'accion' debe ser COMPLETAR o RECHAZAR")
    return jsonify(_respuesta(devolucion))


@bp.get("/devoluciones/pedido")
@requiere_auth(*PERSONAL)
def buscar_pedido_para_devolucion():
    """?codigo=SOL-P-...  o  ?id_pedido=N. Cualquier sede puede recibir la devolución de un
    pedido vendido en otra, así que aquí no se limita por sede (el stock vuelve a la sede
    que recibe). Devuelve el pedido, lo que aún se puede devolver y sus devoluciones."""
    codigo = (request.args.get("codigo") or "").strip()
    if codigo:
        pedido = db.session.scalars(select(Pedido).where(Pedido.codigo_qr == codigo)).first()
    elif arg_entero("id_pedido", minimo=1):
        pedido = db.session.get(Pedido, arg_entero("id_pedido"))
    else:
        raise ErrorApi(422, "Indique ?codigo= o ?id_pedido=")
    if pedido is None:
        raise ErrorApi(404, "Pedido no encontrado")
    devolvibles = devoluciones.unidades_devolvibles(pedido)
    datos = pedido_dict(pedido)
    for item in datos["items"]:
        item["devolvible"] = devolvibles[item["id_detalle_pedido"]]
    datos["devoluciones"] = [devolucion_dict(d) for d in sorted(pedido.devoluciones, key=lambda d: d.id_devolucion)]
    return jsonify(datos)
