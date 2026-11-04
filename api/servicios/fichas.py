"""
fichas.py
Ficha técnica de cada producto en MongoDB (colección fichas_producto).

Una camiseta, un jean y unos tenis no comparten atributos: la camiseta tiene
gramaje y tipo de cuello, el jean tiro y elasticidad, los tenis suela y horma.
En MySQL eso exigiría columnas casi siempre vacías o un modelo EAV difícil de
consultar; en MongoDB cada ficha guarda solo los atributos que le aplican.
El _id del documento es el id_producto de MySQL (relación 1 a 1).
"""
import json

from pymongo import ASCENDING, ReturnDocument

from api import nosql
from api.errores import ErrorApi

MAX_BYTES_FICHA = 16_000
MAX_PROFUNDIDAD = 4
SIN_TILDES_NI_MAYUSCULAS = {"locale": "es", "strength": 1}


def _validar_estructura(valor, ruta="atributos", profundidad=0):
    """Permite objetos y listas anidados, pero bloquea operadores de MongoDB en las claves."""
    if profundidad > MAX_PROFUNDIDAD:
        raise ErrorApi(422, f"'{ruta}' tiene demasiados niveles de anidación")
    if isinstance(valor, dict):
        for clave, dato in valor.items():
            if not isinstance(clave, str) or not clave or clave.startswith("$") or "." in clave:
                raise ErrorApi(422, f"Clave inválida en '{ruta}': '{clave}'")
            _validar_estructura(dato, f"{ruta}.{clave}", profundidad + 1)
    elif isinstance(valor, list):
        for i, dato in enumerate(valor):
            _validar_estructura(dato, f"{ruta}[{i}]", profundidad + 1)
    elif valor is not None and not isinstance(valor, (str, int, float, bool)):
        raise ErrorApi(422, f"Valor no soportado en '{ruta}'")


def _lista_textos(datos, campo, maximo=20):
    valor = datos.get(campo, [])
    if not isinstance(valor, list) or len(valor) > maximo or not all(isinstance(v, str) for v in valor):
        raise ErrorApi(422, f"'{campo}' debe ser una lista de máximo {maximo} textos")
    return [v.strip() for v in valor if v.strip()]


def guardar_ficha(producto, datos, usuario):
    """PUT: crea la ficha o la reemplaza completa (upsert) e incrementa su versión."""
    atributos = datos.get("atributos")
    if not isinstance(atributos, dict) or not atributos:
        raise ErrorApi(422, "'atributos' debe ser un objeto con al menos una clave")
    _validar_estructura(atributos)
    if len(json.dumps(datos, ensure_ascii=False).encode()) > MAX_BYTES_FICHA:
        raise ErrorApi(422, f"La ficha supera el tamaño máximo de {MAX_BYTES_FICHA} bytes")

    ficha = nosql.coleccion(nosql.FICHAS).find_one_and_update(
        {"_id": producto.id_producto},
        {
            "$set": {
                # Copia del nombre y la categoría para filtrar sin ir a MySQL.
                "producto": producto.nombre,
                "categoria": producto.categoria.nombre,
                "atributos": atributos,
                "cuidados": _lista_textos(datos, "cuidados"),
                "etiquetas": [e.lower() for e in _lista_textos(datos, "etiquetas")],
                "actualizado_por": usuario.id_usuario,
                "fecha_actualizacion": nosql.ahora(),
            },
            "$inc": {"version": 1},
            "$setOnInsert": {"fecha_creacion": nosql.ahora()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return formatear(ficha)


def obtener_ficha(id_producto):
    return formatear(nosql.coleccion(nosql.FICHAS).find_one({"_id": id_producto}))


def eliminar_ficha(id_producto):
    if nosql.coleccion(nosql.FICHAS).delete_one({"_id": id_producto}).deleted_count == 0:
        raise ErrorApi(404, "El producto no tiene ficha técnica")


def buscar_por_atributos(args):
    """
    Filtra fichas por etiqueta, categoría o cualquier atributo dinámico:
    ?etiqueta=verano&atributos.material=Algodón&atributos.cuello=redondo
    Devuelve los id_producto encontrados; los datos comerciales se piden luego a MySQL.
    """
    filtro = {}
    for clave, valor in args.items():
        if clave in ("page", "size"):
            continue
        if clave == "etiqueta":
            filtro["etiquetas"] = valor.strip().lower()
        elif clave == "categoria":
            filtro["categoria"] = valor.strip()
        elif clave.startswith("atributos.") and "$" not in clave and len(clave) <= 80:
            filtro[clave] = _valor_consulta(valor)
        else:
            raise ErrorApi(422, f"Filtro no soportado: '{clave}'",
                           permitidos=["etiqueta", "categoria", "atributos.<clave>"])
    if not filtro:
        raise ErrorApi(422, "Indique al menos un filtro: etiqueta, categoria o atributos.<clave>")
    cursor = (
        nosql.coleccion(nosql.FICHAS)
        .find(filtro, {"_id": 1})
        .collation(SIN_TILDES_NI_MAYUSCULAS)  # "algodon" encuentra "Algodón"
        .sort("_id", ASCENDING)
    )
    return filtro, [d["_id"] for d in cursor]


def _valor_consulta(valor):
    """Los parámetros llegan como texto: se prueba también como número o booleano."""
    opciones = [valor]
    if valor.lower() in ("true", "false"):
        opciones.append(valor.lower() == "true")
    try:
        opciones.append(int(valor))
    except ValueError:
        try:
            opciones.append(float(valor))
        except ValueError:
            pass
    return opciones[0] if len(opciones) == 1 else {"$in": opciones}


def formatear(ficha):
    if ficha is None:
        return None
    ficha = dict(ficha)
    ficha["id_producto"] = ficha.pop("_id")
    return ficha
