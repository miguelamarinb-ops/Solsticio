"""MongoDB en vivo: muestra cada documento que la API escribe, en el momento en que lo escribe.

Escucha la base NoSQL de Solsticio con un change stream (funciona en Atlas y en un
MongoDB local con replica set) y, por cada inserción o cambio en las colecciones
de la aplicación, imprime la hora, la colección y el documento. Sirve para mostrar
que, mientras se usa la tienda o el panel, la bitácora, los escaneos de QR, las
opiniones y las fichas técnicas se guardan en MongoDB al instante.

Usa la MONGO_URI del archivo .env y nunca imprime el usuario ni la contraseña.

Uso, desde la raíz del proyecto (Ctrl + C para salir):
    python scripts/mongo_en_vivo.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient  # noqa: E402
from pymongo.errors import OperationFailure, PyMongoError  # noqa: E402

from api.config import Config  # noqa: E402

N, V, A, C, G, F = "\033[1m", "\033[32m", "\033[33m", "\033[36m", "\033[90m", "\033[0m"
COLECCIONES = ["actividad_usuario", "escaneos_qr", "resenas_producto", "fichas_producto"]
# Campos técnicos que no aportan en la demostración
OCULTOS = {"ip", "agente", "user_agent", "navegador"}


def servidor_sin_credenciales(uri):
    sin_esquema = uri.split("://", 1)[-1]
    return sin_esquema.rsplit("@", 1)[-1].split("/")[0].split("?")[0]


def resumen(coleccion, doc):
    """Una línea que dice en palabras qué pasó."""
    if coleccion == "actividad_usuario":
        estado = f"{V}{doc.get('estado_http')}{F}" if doc.get("exito") else f"\033[31m{doc.get('estado_http')}{F}"
        return f"{doc.get('rol', '')} hizo {N}{doc.get('accion')}{F} ({doc.get('metodo')} {doc.get('ruta')}) -> {estado}"
    if coleccion == "escaneos_qr":
        donde = f"sede {doc['id_sede']}" if doc.get("id_sede") else "sin sede"
        return (f"se escaneó {N}{doc.get('codigo_qr')}{F} por {doc.get('canal')} ({donde}): "
                + (f"{V}encontrado{F}" if doc.get("encontrado") else "\033[31mno existe\033[0m"))
    if coleccion == "resenas_producto":
        autor = (doc.get("autor") or {}).get("nombre", "?")
        return f"opinión de {N}{autor}{F} sobre la prenda {doc.get('id_producto')}: {doc.get('calificacion')}/5, {doc.get('estado')}"
    if coleccion == "fichas_producto":
        return f"ficha técnica de la prenda {N}{doc.get('_id')}{F}, versión {doc.get('version')}"
    return ""


def legible(doc):
    limpio = {k: v for k, v in doc.items() if k not in OCULTOS}
    return json.dumps(limpio, ensure_ascii=False, indent=2, default=str)


def main():
    cliente = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=10000)
    db = cliente[Config.MONGO_DB]
    try:
        version = cliente.admin.command("buildInfo")["version"]
    except PyMongoError as error:
        print(f"No se pudo conectar a MongoDB: {error}")
        return 1

    print(f"{N}MongoDB en vivo{F}  servidor {servidor_sin_credenciales(Config.MONGO_URI)} (MongoDB {version}), base '{Config.MONGO_DB}'")
    for nombre in COLECCIONES:
        print(f"  {nombre}: {db[nombre].estimated_document_count()} documentos")
    print(f"{G}Esperando cambios… usa la tienda o el panel y aquí aparece cada documento. Ctrl + C para salir.{F}\n")

    filtro = [{"$match": {"ns.coll": {"$in": COLECCIONES},
                          "operationType": {"$in": ["insert", "update", "replace", "delete"]}}}]
    try:
        with db.watch(filtro, full_document="updateLookup") as flujo:
            for cambio in flujo:
                coleccion = cambio["ns"]["coll"]
                operacion = {"insert": "NUEVO", "update": "CAMBIO", "replace": "CAMBIO", "delete": "BORRADO"}[cambio["operationType"]]
                hora = datetime.now().strftime("%H:%M:%S")
                doc = cambio.get("fullDocument") or {"_id": cambio["documentKey"]["_id"]}
                print(f"{A}{hora}{F}  {C}{coleccion}{F}  {N}{operacion}{F}  {resumen(coleccion, doc)}")
                print(f"{G}{legible(doc)}{F}\n", flush=True)
    except OperationFailure as error:
        print("Este MongoDB no permite change streams (hace falta Atlas o un replica set local).")
        print(f"Detalle: {error}")
        return 1
    except KeyboardInterrupt:
        print("\nListo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
