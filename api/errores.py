"""
errores.py
Excepción de dominio de la API y manejadores que convierten cualquier error
en una respuesta JSON {"detail": "...", ...extra}.
"""
from flask import jsonify
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from api.modelos import db

MENSAJES_HTTP = {
    400: "Petición mal formada",
    404: "Recurso no encontrado",
    405: "Método no permitido para esta ruta",
    415: "Tipo de contenido no soportado; use application/json",
    500: "Error interno del servidor",
}


class ErrorApi(Exception):
    def __init__(self, codigo, detalle, **extra):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle
        self.extra = extra

    def respuesta(self):
        return {"detail": self.detalle, **self.extra}


def registrar_errores(app):
    @app.errorhandler(ErrorApi)
    def error_api(error):
        db.session.rollback()
        return jsonify(error.respuesta()), error.codigo

    @app.errorhandler(IntegrityError)
    def error_integridad(_error):
        db.session.rollback()
        return jsonify({"detail": "La operación viola una restricción de integridad de la base de datos"}), 409

    @app.errorhandler(DataError)
    def error_datos(_error):
        db.session.rollback()
        return jsonify({"detail": "Un valor enviado no es válido para la base de datos (longitud o formato)"}), 422

    @app.errorhandler(OperationalError)
    def error_conexion(error):
        db.session.rollback()
        app.logger.error("Error de base de datos: %s", error.orig)
        return jsonify({"detail": "No se pudo completar la operación en la base de datos"}), 503

    @app.errorhandler(HTTPException)
    def error_http(error):
        return jsonify({"detail": MENSAJES_HTTP.get(error.code, error.description)}), error.code
