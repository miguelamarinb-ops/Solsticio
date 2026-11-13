"""
seguridad.py
Contraseñas con bcrypt y autenticación JWT (HS256) mediante la cabecera
Authorization: Bearer <token>.

Control de acceso por roles (RBAC), tres niveles:
    ADMINISTRADOR  personal con control total, sin sede (global)
    TRABAJADOR     personal que opera solo sobre su sede
    CLIENTE        comprador registrado en la tienda web; solo ve lo suyo
El rol se lee de la base en cada petición (no del token), así que un cambio
de rol o una desactivación surten efecto de inmediato.
"""
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import current_app, g, request

from api.errores import ErrorApi
from api.modelos import Usuario, db

ADMINISTRADOR = "ADMINISTRADOR"
TRABAJADOR = "TRABAJADOR"
CLIENTE = "CLIENTE"
PERSONAL = (ADMINISTRADOR, TRABAJADOR)
ROLES = (ADMINISTRADOR, TRABAJADOR, CLIENTE)

# Hash de relleno: si el email no existe se compara igual contra él, para que
# el tiempo de respuesta no delate qué correos están registrados.
_HASH_RELLENO = bcrypt.hashpw(b"solsticio-relleno", bcrypt.gensalt()).decode("utf-8")


def hashear_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password, hash_password):
    if hash_password is None:
        hash_password = _HASH_RELLENO
        bcrypt.checkpw(password.encode("utf-8"), hash_password.encode("utf-8"))
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hash_password.encode("utf-8"))
    except ValueError:
        return False


def crear_token(usuario):
    minutos = current_app.config["ACCESS_TOKEN_EXPIRE_MINUTES"]
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id_usuario),
        "rol": usuario.rol.nombre,
        "id_sede": usuario.id_sede,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token, minutos * 60


def _usuario_desde_token(obligatorio):
    cabecera = request.headers.get("Authorization", "")
    if not cabecera.startswith("Bearer "):
        if obligatorio:
            raise ErrorApi(401, "Se requiere la cabecera Authorization: Bearer <token>")
        return None

    try:
        payload = jwt.decode(
            cabecera[7:].strip(), current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise ErrorApi(401, "El token expiró, inicie sesión de nuevo") from None
    except jwt.InvalidTokenError:
        raise ErrorApi(401, "Token inválido") from None

    usuario = db.session.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise ErrorApi(401, "El usuario del token no existe o está inactivo")
    return usuario


def requiere_auth(*roles):
    """Exige token válido. Si se indican roles, el usuario debe tener uno de ellos."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            g.usuario = _usuario_desde_token(obligatorio=True)
            if roles and g.usuario.rol.nombre not in roles:
                raise ErrorApi(403, "No tiene permisos para esta operación")
            return vista(*args, **kwargs)
        # La documentación OpenAPI (api/documentacion.py) lee estos atributos para
        # mostrar quién puede usar cada ruta sin repetir la información a mano.
        envoltura.roles_permitidos = roles or ROLES
        return envoltura
    return decorador


def auth_opcional(vista):
    """Para endpoints públicos que cambian de comportamiento si llega un token."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        g.usuario = _usuario_desde_token(obligatorio=False)
        return vista(*args, **kwargs)
    envoltura.auth_opcional = True
    return envoltura


def es_admin(usuario):
    return usuario is not None and usuario.rol.nombre == ADMINISTRADOR


def es_personal(usuario):
    return usuario is not None and usuario.rol.nombre in PERSONAL


def es_cliente(usuario):
    return usuario is not None and usuario.rol.nombre == CLIENTE


def verificar_sede(usuario, id_sede):
    """Un trabajador solo opera sobre su propia sede; el administrador sobre todas."""
    if not es_admin(usuario) and usuario.id_sede != id_sede:
        raise ErrorApi(403, "Un trabajador solo puede operar sobre su propia sede")
