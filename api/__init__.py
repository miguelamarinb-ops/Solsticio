"""
Paquete de la API REST de Solsticio (Flask + Flask-SQLAlchemy + MySQL + MongoDB).
crear_app() arma la aplicación: configuración, bases de datos, rutas, errores y comandos.
"""
from datetime import date, datetime
from decimal import Decimal

from bson import ObjectId
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider

from api.comandos import registrar_comandos
from api.config import Config
from api.errores import registrar_errores
from api.modelos import db
from api.nosql import iniciar_mongo
from api.rutas import PREFIJO_API, registrar_rutas
from api.servicios.actividad import registrar_peticion


class ProveedorJson(DefaultJSONProvider):
    """Montos como números, fechas en ISO 8601 y tildes sin escapar."""
    ensure_ascii = False
    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        if isinstance(o, datetime):
            return o.isoformat(timespec="seconds")
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, ObjectId):
            return str(o)
        return DefaultJSONProvider.default(o)


def crear_app(configuracion=Config):
    app = Flask(__name__)
    app.config.from_object(configuracion)
    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("Falta DATABASE_URL. Copie .env.example a .env y complete la conexión a MySQL.")
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Falta SECRET_KEY en el archivo .env.")

    app.json = ProveedorJson(app)
    db.init_app(app)
    iniciar_mongo(app)
    registrar_rutas(app)
    app.after_request(registrar_peticion)  # bitácora de actividad en MongoDB
    registrar_errores(app)
    registrar_comandos(app)

    @app.get(PREFIJO_API)
    def inicio():
        return jsonify({"api": "Solsticio", "version": "v1", "base": PREFIJO_API})

    return app
