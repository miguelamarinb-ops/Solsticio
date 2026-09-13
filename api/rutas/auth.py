"""
auth.py
Inicio de sesión y perfil del usuario autenticado.
"""
from flask import Blueprint, g, jsonify

from api.seguridad import crear_token, requiere_auth
from api.serializadores import usuario_dict
from api.servicios import usuarios
from api.validacion import leer_json

bp = Blueprint("auth", __name__)


@bp.post("/auth/login")
def login():
    usuario = usuarios.autenticar(leer_json())
    token, segundos = crear_token(usuario)
    return jsonify({
        "access_token": token,
        "token_type": "bearer",
        "expira_en": segundos,
        "usuario": usuario_dict(usuario),
    })


@bp.get("/auth/perfil")
@requiere_auth()
def perfil():
    return jsonify(usuario_dict(g.usuario))
