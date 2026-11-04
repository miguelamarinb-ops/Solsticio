"""
resenas.py
Reseñas de productos guardadas en MongoDB (colección resenas_producto).

Cada reseña es un documento autocontenido: calificación, comentario, atributos
opcionales que cambian según la prenda (calidad de la tela, si encoge, si se ve
igual a la foto...), fotos y las respuestas de la tienda embebidas. La existencia
del producto y la compra verificada se validan contra MySQL.
"""
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError
from sqlalchemy import select

from api import nosql
from api.errores import ErrorApi
from api.modelos import EstadoPedido, Pedido, Producto, Variante, db
from api.serializadores import nombre_completo
from api.validacion import a_entero, exigir, texto

PUBLICADA = "PUBLICADA"
OCULTA = "OCULTA"
AJUSTES_TALLA = ("PEQUENA", "EXACTA", "GRANDE")
ESTADOS_COMPRA = (EstadoPedido.PAGADO, EstadoPedido.PREPARANDO, EstadoPedido.ENVIADO,
                  EstadoPedido.ENTREGADO)
MAX_ATRIBUTOS = 15
MAX_FOTOS = 5

# El email del autor se usa para evitar reseñas duplicadas, pero nunca se publica.
PROYECCION_PUBLICA = {"autor.email": 0}


def obtener_producto_activo(id_producto):
    producto = db.session.get(Producto, id_producto)
    if producto is None or not producto.activo:
        raise ErrorApi(404, "Producto no encontrado")
    return producto


def _atributos_libres(valor):
    """Diccionario plano y pequeño: {"calidad_tela": 4, "encoge": false, ...}."""
    if valor is None:
        return {}
    if not isinstance(valor, dict):
        raise ErrorApi(422, "'atributos' debe ser un objeto")
    if len(valor) > MAX_ATRIBUTOS:
        raise ErrorApi(422, f"'atributos' admite máximo {MAX_ATRIBUTOS} claves")
    limpio = {}
    for clave, dato in valor.items():
        clave = str(clave).strip()
        if not clave or len(clave) > 40 or clave.startswith("$") or "." in clave:
            raise ErrorApi(422, f"Clave de atributo inválida: '{clave}'")
        if isinstance(dato, str):
            dato = dato.strip()[:100]
        elif not isinstance(dato, (bool, int, float)) or dato is None:
            raise ErrorApi(422, f"El atributo '{clave}' debe ser texto, número o booleano")
        limpio[clave] = dato
    return limpio


def _fotos(valor):
    if valor is None:
        return []
    if not isinstance(valor, list) or len(valor) > MAX_FOTOS:
        raise ErrorApi(422, f"'fotos' debe ser una lista de máximo {MAX_FOTOS} URLs")
    for url in valor:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")) or len(url) > 300:
            raise ErrorApi(422, "Cada foto debe ser una URL http(s) de máximo 300 caracteres")
    return valor


def _compra_verificada(codigo_pedido, producto):
    """Una reseña con código de pedido se marca verificada si ese pedido (MySQL) incluyó el producto."""
    pedido = db.session.scalars(select(Pedido).where(Pedido.codigo_qr == codigo_pedido)).first()
    if pedido is None:
        raise ErrorApi(422, "El código de pedido no existe")
    if pedido.estado not in ESTADOS_COMPRA:
        raise ErrorApi(422, f"El pedido está {pedido.estado.value}: solo se verifican compras pagadas")
    if not any(d.variante.id_producto == producto.id_producto for d in pedido.detalles):
        raise ErrorApi(422, "El pedido indicado no incluye este producto")
    return True


def crear_resena(producto, datos):
    exigir(datos, "nombre", "email", "calificacion", "comentario")
    calificacion = a_entero(datos["calificacion"], "calificacion", 1)
    if calificacion > 5:
        raise ErrorApi(422, "'calificacion' debe estar entre 1 y 5")

    resena = {
        "id_producto": producto.id_producto,
        "autor": {
            "nombre": texto(datos, "nombre", 80, obligatorio=True),
            "email": texto(datos, "email", 120, obligatorio=True).lower(),
        },
        "calificacion": calificacion,
        "comentario": texto(datos, "comentario", 2000, obligatorio=True),
        "estado": PUBLICADA,
        "compra_verificada": False,
        "util": 0,
        "respuestas": [],
        "fecha": nosql.ahora(),
    }
    if datos.get("id_variante") is not None:
        variante = db.session.get(Variante, a_entero(datos["id_variante"], "id_variante", 1))
        if variante is None or variante.id_producto != producto.id_producto:
            raise ErrorApi(422, "La variante indicada no pertenece a este producto")
        resena.update(id_variante=variante.id_variante, talla=variante.talla.valor,
                      color=variante.color.nombre)
    if datos.get("ajuste_talla"):
        ajuste = str(datos["ajuste_talla"]).strip().upper()
        if ajuste not in AJUSTES_TALLA:
            raise ErrorApi(422, "Valor inválido para 'ajuste_talla'", permitidos=list(AJUSTES_TALLA))
        resena["ajuste_talla"] = ajuste
    if datos.get("codigo_pedido"):
        resena["codigo_pedido"] = texto(datos, "codigo_pedido", 80)
        resena["compra_verificada"] = _compra_verificada(resena["codigo_pedido"], producto)
    # Campos opcionales: solo existen en el documento si el cliente los envió.
    if texto(datos, "titulo", 120):
        resena["titulo"] = texto(datos, "titulo", 120)
    atributos = _atributos_libres(datos.get("atributos"))
    if atributos:
        resena["atributos"] = atributos
    fotos = _fotos(datos.get("fotos"))
    if fotos:
        resena["fotos"] = fotos

    try:
        resultado = nosql.coleccion(nosql.RESENAS).insert_one(resena)
    except DuplicateKeyError:
        raise ErrorApi(409, "Este email ya publicó una reseña para el producto") from None
    return obtener_resena(resultado.inserted_id, publica=True)


def obtener_resena(id_resena, publica=False):
    proyeccion = PROYECCION_PUBLICA if publica else None
    doc = nosql.coleccion(nosql.RESENAS).find_one({"_id": id_resena}, proyeccion)
    if doc is None or (publica and doc["estado"] != PUBLICADA):
        raise ErrorApi(404, "Reseña no encontrada")
    return nosql.documento(doc)


def listar_resenas(id_producto, pagina, tamano, orden="recientes", calificacion=None):
    filtro = {"id_producto": id_producto, "estado": PUBLICADA}
    if calificacion:
        filtro["calificacion"] = calificacion
    ordenes = {
        "recientes": [("fecha", DESCENDING)],
        "mejores": [("calificacion", DESCENDING), ("fecha", DESCENDING)],
        "peores": [("calificacion", 1), ("fecha", DESCENDING)],
        "utiles": [("util", DESCENDING), ("fecha", DESCENDING)],
    }
    if orden not in ordenes:
        raise ErrorApi(422, "Valor inválido para 'orden'", permitidos=list(ordenes))
    return nosql.paginar(nosql.RESENAS, filtro, ordenes[orden], pagina, tamano, PROYECCION_PUBLICA)


def resumen_resenas(id_producto):
    """Promedio, distribución de estrellas y opinión sobre la talla, en una sola agregación."""
    pipeline = [
        {"$match": {"id_producto": id_producto, "estado": PUBLICADA}},
        {"$facet": {
            "general": [{"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "promedio": {"$avg": "$calificacion"},
                "verificadas": {"$sum": {"$cond": ["$compra_verificada", 1, 0]}},
            }}],
            "estrellas": [{"$group": {"_id": "$calificacion", "n": {"$sum": 1}}}],
            "talla": [
                {"$match": {"ajuste_talla": {"$exists": True}}},
                {"$group": {"_id": "$ajuste_talla", "n": {"$sum": 1}}},
            ],
        }},
    ]
    faceta = next(nosql.coleccion(nosql.RESENAS).aggregate(pipeline))
    general = faceta["general"][0] if faceta["general"] else {"total": 0, "promedio": None, "verificadas": 0}
    estrellas = {str(i): 0 for i in range(5, 0, -1)}
    estrellas.update({str(e["_id"]): e["n"] for e in faceta["estrellas"]})
    return {
        "total": general["total"],
        "promedio": round(general["promedio"], 2) if general["promedio"] is not None else None,
        "compras_verificadas": general["verificadas"],
        "distribucion": estrellas,
        "ajuste_talla": {e["_id"]: e["n"] for e in faceta["talla"]},
    }


def marcar_util(id_resena):
    resultado = nosql.coleccion(nosql.RESENAS).find_one_and_update(
        {"_id": id_resena, "estado": PUBLICADA}, {"$inc": {"util": 1}},
        projection={"util": 1}, return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        raise ErrorApi(404, "Reseña no encontrada")
    return {"id": str(id_resena), "util": resultado["util"]}


def moderar_resena(id_resena, datos, usuario):
    """El administrador oculta/publica la reseña y/o agrega una respuesta de la tienda."""
    cambios, operacion = {}, {}
    if "estado" in datos:
        estado = str(datos["estado"]).strip().upper()
        if estado not in (PUBLICADA, OCULTA):
            raise ErrorApi(422, "Valor inválido para 'estado'", permitidos=[PUBLICADA, OCULTA])
        cambios["estado"] = estado
    respuesta = texto(datos, "respuesta", 1000)
    if respuesta:
        operacion["$push"] = {"respuestas": {
            "id_usuario": usuario.id_usuario,
            "nombre": nombre_completo(usuario),
            "texto": respuesta,
            "fecha": nosql.ahora(),
        }}
    if not cambios and not operacion:
        raise ErrorApi(422, "Envíe 'estado' y/o 'respuesta'")
    cambios["fecha_moderacion"] = nosql.ahora()
    operacion["$set"] = cambios

    resultado = nosql.coleccion(nosql.RESENAS).update_one({"_id": id_resena}, operacion)
    if resultado.matched_count == 0:
        raise ErrorApi(404, "Reseña no encontrada")
    return obtener_resena(id_resena)


def eliminar_resena(id_resena):
    if nosql.coleccion(nosql.RESENAS).delete_one({"_id": id_resena}).deleted_count == 0:
        raise ErrorApi(404, "Reseña no encontrada")
