"""
actividad.py
Eventos de alta frecuencia guardados en MongoDB: bitácora de actividad de los
usuarios y escaneos de códigos QR. Registrar un evento nunca debe tumbar la
petición de negocio: si MongoDB falla se escribe un aviso en el log y se sigue.
"""
from datetime import timedelta

from flask import current_app, g, request
from pymongo import DESCENDING
from pymongo.errors import PyMongoError
from sqlalchemy import select

from api import nosql
from api.modelos import Variante, db
from api.serializadores import descripcion_variante, disponibilidad, precio_final

# Nombre legible de cada endpoint. Lo que no esté aquí se guarda con el nombre interno.
ACCIONES = {
    "auth.login": "INICIO_SESION",
    "auth.perfil": "CONSULTA_PERFIL",
    "actividad.perfil_con_actividad": "CONSULTA_PERFIL_ACTIVIDAD",
    "actividad.actividad_de_usuario": "CONSULTA_ACTIVIDAD_USUARIO",
    "actividad.listar_actividad": "CONSULTA_BITACORA",
    "actividad.qr_mas_escaneados": "REPORTE_QR",
    "catalogo.resolver_qr_variante": "ESCANEO_QR",
    "pedidos.resolver_qr_pedido": "ESCANEO_QR_PEDIDO",
    "pedidos.crear_pedido": "VENTA_REGISTRADA",
    "pedidos.cambiar_estado_pedido": "PEDIDO_CAMBIO_ESTADO",
    "pedidos.registrar_pago": "PAGO_REGISTRADO",
    "pedidos.generar_factura": "FACTURA_EMITIDA",
    "inventario.registrar_ingreso": "INVENTARIO_INGRESO",
    "inventario.registrar_ajuste": "INVENTARIO_AJUSTE",
    "inventario.crear_traslado": "TRASLADO_CREADO",
    "inventario.despachar_traslado": "TRASLADO_DESPACHADO",
    "inventario.recibir_traslado": "TRASLADO_RECIBIDO",
    "admin.crear_producto": "PRODUCTO_CREADO",
    "admin.actualizar_producto": "PRODUCTO_ACTUALIZADO",
    "admin.desactivar_producto": "PRODUCTO_DESACTIVADO",
    "fichas.guardar_ficha": "FICHA_GUARDADA",
    "fichas.eliminar_ficha": "FICHA_ELIMINADA",
    "resenas.moderar_resena": "RESENA_MODERADA",
    "resenas.eliminar_resena": "RESENA_ELIMINADA",
}


def _cliente_http():
    return {
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent", "")[:200],
    }


def registrar_peticion(respuesta):
    """after_request: deja huella de toda petición hecha por un usuario autenticado."""
    usuario = g.get("usuario")
    if usuario is None or request.endpoint is None:
        return respuesta

    evento = {
        "id_usuario": usuario.id_usuario,
        "rol": usuario.rol.nombre,
        "id_sede": usuario.id_sede,
        "accion": ACCIONES.get(request.endpoint, request.endpoint),
        "metodo": request.method,
        "ruta": request.path,
        "estado_http": respuesta.status_code,
        "exito": respuesta.status_code < 400,
        "fecha": nosql.ahora(),
        **_cliente_http(),
    }
    # Solo se guardan los campos que aplican a esta acción: el esquema es flexible.
    if request.view_args:
        evento["parametros"] = request.view_args
    if request.args:
        evento["filtros"] = request.args.to_dict()
    if respuesta.status_code >= 400 and respuesta.is_json:
        evento["error"] = (respuesta.get_json(silent=True) or {}).get("detail")

    _insertar(nosql.ACTIVIDAD, evento)
    return respuesta


def registrar_escaneo(codigo_qr, variante, usuario, id_sede):
    evento = {
        "codigo_qr": codigo_qr,
        "encontrado": variante is not None,
        "canal": "TIENDA" if usuario else "WEB",
        "fecha": nosql.ahora(),
        **_cliente_http(),
    }
    if variante is not None:
        evento.update(id_variante=variante.id_variante, id_producto=variante.id_producto)
    if usuario is not None:
        evento["id_usuario"] = usuario.id_usuario
    if id_sede:
        evento["id_sede"] = id_sede
    _insertar(nosql.ESCANEOS, evento)


def _insertar(nombre_coleccion, evento):
    try:
        nosql.coleccion(nombre_coleccion).insert_one(evento)
    except PyMongoError as error:
        current_app.logger.warning("No se pudo registrar el evento en %s: %s", nombre_coleccion, error)


# =====================================================================
# CONSULTAS
# =====================================================================

def ultimas_actividades(id_usuario, limite=10):
    cursor = (
        nosql.coleccion(nosql.ACTIVIDAD)
        .find({"id_usuario": id_usuario}, {"id_usuario": 0})
        .sort("fecha", DESCENDING)
        .limit(limite)
    )
    return [nosql.documento(d) for d in cursor]


def resumen_actividad(id_usuario):
    """Cuántas veces hizo cada acción el usuario (pipeline de agregación)."""
    pipeline = [
        {"$match": {"id_usuario": id_usuario}},
        {"$group": {"_id": "$accion", "veces": {"$sum": 1}, "ultima": {"$max": "$fecha"}}},
        {"$sort": {"veces": -1}},
        {"$project": {"_id": 0, "accion": "$_id", "veces": 1, "ultima": 1}},
    ]
    return list(nosql.coleccion(nosql.ACTIVIDAD).aggregate(pipeline))


def listar_actividad(filtro, pagina, tamano):
    return nosql.paginar(nosql.ACTIVIDAD, filtro, [("fecha", DESCENDING)], pagina, tamano)


def escaneos_recientes(id_producto, dias=30):
    desde = nosql.ahora() - timedelta(days=dias)
    return nosql.coleccion(nosql.ESCANEOS).count_documents(
        {"id_producto": id_producto, "fecha": {"$gte": desde}}
    )


def variantes_mas_escaneadas(dias, limite, sedes):
    """Ranking calculado en MongoDB y completado con nombre, precio y stock desde MySQL."""
    desde = nosql.ahora() - timedelta(days=dias)
    pipeline = [
        {"$match": {"encontrado": True, "fecha": {"$gte": desde}}},
        {"$group": {
            "_id": "$id_variante",
            "escaneos": {"$sum": 1},
            "web": {"$sum": {"$cond": [{"$eq": ["$canal", "WEB"]}, 1, 0]}},
            "tienda": {"$sum": {"$cond": [{"$eq": ["$canal", "TIENDA"]}, 1, 0]}},
            "ultimo": {"$max": "$fecha"},
        }},
        {"$sort": {"escaneos": -1, "_id": 1}},
        {"$limit": limite},
    ]
    ranking = list(nosql.coleccion(nosql.ESCANEOS).aggregate(pipeline))

    ids = [r["_id"] for r in ranking]
    variantes = {
        v.id_variante: v
        for v in db.session.scalars(select(Variante).where(Variante.id_variante.in_(ids)))
    }
    resultado = []
    for posicion, fila in enumerate(ranking, start=1):
        variante = variantes.get(fila["_id"])
        if variante is None:
            continue
        disp = disponibilidad(variante, sedes)
        resultado.append({
            "posicion": posicion,
            "id_variante": variante.id_variante,
            "sku": variante.sku,
            "descripcion": descripcion_variante(variante),
            "precio_final": precio_final(variante),
            "stock_total": sum(d["cantidad"] for d in disp),
            "disponibilidad": disp,
            "escaneos": {"total": fila["escaneos"], "web": fila["web"], "tienda": fila["tienda"],
                         "ultimo": fila["ultimo"]},
        })
    return resultado
