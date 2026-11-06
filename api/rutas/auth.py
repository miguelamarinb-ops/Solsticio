"""
auth.py
Registro de clientes, inicio de sesión y perfil del usuario autenticado.
La autenticación se hace contra MySQL: tabla usuario y contraseñas con bcrypt.
"""
from flask import Blueprint, g, jsonify

from api.seguridad import crear_token, requiere_auth
from api.serializadores import usuario_dict
from api.servicios import usuarios
from api.validacion import leer_json

bp = Blueprint("auth", __name__)


def _respuesta_sesion(usuario):
    token, segundos = crear_token(usuario)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expira_en": segundos,
        "usuario": usuario_dict(usuario),
    }


@bp.post("/auth/registro")
def registro():
    """Registro público: crea una cuenta con rol CLIENTE y devuelve su token."""
    usuario = usuarios.registrar_cliente(leer_json())
    g.usuario = usuario  # para que el registro quede en la bitácora (MongoDB)
    return jsonify(_respuesta_sesion(usuario)), 201


@bp.post("/auth/login")
def login():
    usuario = usuarios.autenticar(leer_json())
    g.usuario = usuario  # para que el inicio de sesión quede en la bitácora (MongoDB)
    return jsonify(_respuesta_sesion(usuario))


@bp.get("/auth/perfil")
@requiere_auth()
def perfil():
    return jsonify(usuario_dict(g.usuario))
