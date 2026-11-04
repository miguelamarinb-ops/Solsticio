"""
nosql.py
Conexión a MongoDB, la base documental de Solsticio (persistencia políglota).

MySQL guarda los datos estructurados y transaccionales (productos, stock, pedidos,
facturas). MongoDB guarda lo que no encaja en tablas rígidas o llega con alta
frecuencia:

  actividad_usuario  bitácora de cada petición autenticada (alta frecuencia, TTL)
  escaneos_qr        cada lectura de un código QR de prenda (alta frecuencia, TTL)
  resenas_producto   reseñas con atributos variables y respuestas embebidas
  fichas_producto    ficha técnica con atributos distintos según el tipo de prenda

Los documentos se enlazan con MySQL por identificador (id_usuario, id_producto,
id_variante): MongoDB nunca duplica precios ni existencias.
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import current_app
from pymongo import ASCENDING, DESCENDING, IndexModel, MongoClient
from pymongo.errors import PyMongoError

from api.errores import ErrorApi

ACTIVIDAD = "actividad_usuario"
ESCANEOS = "escaneos_qr"
RESENAS = "resenas_producto"
FICHAS = "fichas_producto"

DIAS_RETENCION_ACTIVIDAD = 180
DIAS_RETENCION_ESCANEOS = 365

INDICES = {
    ACTIVIDAD: [
        IndexModel([("id_usuario", ASCENDING), ("fecha", DESCENDING)], name="usuario_fecha"),
        IndexModel([("accion", ASCENDING), ("fecha", DESCENDING)], name="accion_fecha"),
        IndexModel([("fecha", ASCENDING)], name="ttl_fecha",
                   expireAfterSeconds=DIAS_RETENCION_ACTIVIDAD * 86400),
    ],
    ESCANEOS: [
        IndexModel([("id_variante", ASCENDING), ("fecha", DESCENDING)], name="variante_fecha"),
        IndexModel([("id_producto", ASCENDING), ("fecha", DESCENDING)], name="producto_fecha"),
        IndexModel([("fecha", ASCENDING)], name="ttl_fecha",
                   expireAfterSeconds=DIAS_RETENCION_ESCANEOS * 86400),
    ],
    RESENAS: [
        IndexModel([("id_producto", ASCENDING), ("estado", ASCENDING), ("fecha", DESCENDING)],
                   name="producto_estado_fecha"),
        IndexModel([("id_producto", ASCENDING), ("autor.email", ASCENDING)], name="producto_autor",
                   unique=True),
    ],
    FICHAS: [
        IndexModel([("categoria", ASCENDING)], name="categoria"),
        IndexModel([("etiquetas", ASCENDING)], name="etiquetas"),
    ],
}


def iniciar_mongo(app):
    """Crea el cliente (la conexión real se abre en la primera operación) e índices."""
    cliente = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=app.config["MONGO_TIMEOUT_MS"],
        tz_aware=True,
        appname="solsticio-api",
    )
    app.extensions["mongo_cliente"] = cliente
    app.extensions["mongo"] = cliente[app.config["MONGO_DB"]]
    try:
        crear_indices(app.extensions["mongo"])
    except PyMongoError as error:
        # La API sigue arrancando: lo estructurado (MySQL) no depende de MongoDB.
        app.logger.warning("MongoDB no disponible al iniciar (%s). Se reintentará en cada uso.", error)


def crear_indices(base):
    for nombre, indices in INDICES.items():
        base[nombre].create_indexes(indices)


def coleccion(nombre):
    return current_app.extensions["mongo"][nombre]


def ahora():
    return datetime.now(timezone.utc)


def a_object_id(valor, mensaje="Documento no encontrado"):
    """Convierte el id de la URL en ObjectId; un id mal formado se trata como inexistente."""
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError):
        raise ErrorApi(404, mensaje) from None


def documento(doc):
    """Documento listo para JSON: _id pasa a 'id' como texto."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc = {"id": str(doc.pop("_id")), **doc}
    return doc


def paginar(nombre_coleccion, filtro, orden, pagina, tamano, proyeccion=None):
    col = coleccion(nombre_coleccion)
    total = col.count_documents(filtro)
    cursor = col.find(filtro, proyeccion).sort(orden).skip((pagina - 1) * tamano).limit(tamano)
    return {"total": total, "page": pagina, "size": tamano, "items": [documento(d) for d in cursor]}
