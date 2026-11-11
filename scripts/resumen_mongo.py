"""Resumen de la base NoSQL de Solsticio: servidor, colecciones, índices y datos de ejemplo.

Usa la MONGO_URI del archivo .env, así que sirve igual para MongoDB local y para Atlas.
Nunca imprime el usuario ni la contraseña de la cadena de conexión.

Uso, desde la raíz del proyecto:
    python scripts/resumen_mongo.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient  # noqa: E402

from api.config import Config  # noqa: E402

N, V, A, G, F = "\033[1m", "\033[32m", "\033[33m", "\033[90m", "\033[0m"


def servidor_sin_credenciales(uri):
    """Deja solo el host: quita el esquema, el usuario, la contraseña y las opciones."""
    sin_esquema = uri.split("://", 1)[-1]
    return sin_esquema.rsplit("@", 1)[-1].split("/")[0].split("?")[0]


def main():
    cliente = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=10000)
    info = cliente.admin.command("hello")
    base = cliente[Config.MONGO_DB]
    es_atlas = Config.MONGO_URI.startswith("mongodb+srv://")

    print(f"{N}Solsticio: base NoSQL en {'MongoDB Atlas' if es_atlas else 'MongoDB local'}{F}")
    nota = "(mongodb+srv, credenciales ocultas)" if es_atlas else "(mongodb)"
    print(f"  Servidor     {servidor_sin_credenciales(Config.MONGO_URI)}  {G}{nota}{F}")
    print(f"  Versión      MongoDB {cliente.server_info()['version']}")
    if info.get("setName"):
        print(f"  Replica set  {info['setName']}  ({len(info.get('hosts', []))} nodos)")
    print(f"  Base         {Config.MONGO_DB}\n")

    print(f"{N}  {'Colección':<20} {'Docs':>5}  Índices{F}")
    for nombre in sorted(base.list_collection_names()):
        indices = ", ".join(i["name"] for i in base[nombre].list_indexes())
        print(f"  {nombre:<20} {V}{base[nombre].count_documents({}):>5}{F}  {G}{indices}{F}")

    print(f"\n{N}  Ejemplo de reseña (resenas_producto){F}")
    resena = base.resenas_producto.find_one(
        {}, {"_id": 0, "id_producto": 1, "autor": 1, "calificacion": 1, "estado": 1, "titulo": 1}
    )
    print("  " + json.dumps(resena, ensure_ascii=False, default=str))

    print(f"\n{N}  Ranking de QR más escaneados (agregación){F}")
    ranking = base.escaneos_qr.aggregate([
        {"$group": {"_id": "$codigo_qr", "escaneos": {"$sum": 1}}},
        {"$sort": {"escaneos": -1, "_id": 1}},
        {"$limit": 5},
    ])
    for fila in ranking:
        print(f"  {fila['_id']:<16} {A}{fila['escaneos']}{F}")

    print(f"\n{N}  Últimas acciones en la bitácora (actividad_usuario){F}")
    ultimas = base.actividad_usuario.find({}, {"_id": 0, "accion": 1, "fecha": 1}).sort("fecha", -1).limit(5)
    for evento in ultimas:
        print("  " + json.dumps(evento, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
