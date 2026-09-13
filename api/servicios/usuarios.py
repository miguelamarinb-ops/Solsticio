"""
usuarios.py
Autenticación y creación de usuarios del personal (ADMINISTRADOR / TRABAJADOR).
"""
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Rol, Usuario, db
from api.seguridad import ADMINISTRADOR, TRABAJADOR, hashear_password, verificar_password
from api.servicios.comun import obtener_sede_activa
from api.validacion import a_entero, exigir, texto


def autenticar(datos):
    exigir(datos, "email", "password")
    usuario = db.session.scalars(
        select(Usuario).where(Usuario.email == str(datos["email"]).strip().lower())
    ).first()
    if usuario is None or not usuario.activo or not verificar_password(str(datos["password"]), usuario.hash_password):
        raise ErrorApi(401, "Credenciales incorrectas")
    return usuario


def crear_usuario(datos):
    exigir(datos, "documento", "nombres", "apellidos", "email", "password", "rol")
    rol = db.session.scalars(select(Rol).where(Rol.nombre == str(datos["rol"]).strip().upper())).first()
    if rol is None:
        raise ErrorApi(422, "Rol inválido", permitidos=[ADMINISTRADOR, TRABAJADOR])
    email = texto(datos, "email", 120, obligatorio=True).lower()
    if "@" not in email:
        raise ErrorApi(422, "'email' no es válido")
    password = str(datos["password"])
    if len(password) < 8:
        raise ErrorApi(422, "La contraseña debe tener al menos 8 caracteres")

    id_sede = None
    if rol.nombre == TRABAJADOR:
        exigir(datos, "id_sede")
        id_sede = obtener_sede_activa(a_entero(datos["id_sede"], "id_sede", 1)).id_sede
    elif datos.get("id_sede") is not None:
        raise ErrorApi(422, "El administrador es global y no lleva id_sede")

    documento = texto(datos, "documento", 20, obligatorio=True)
    repetido = db.session.scalars(
        select(Usuario).where((Usuario.documento == documento) | (Usuario.email == email))
    ).first()
    if repetido is not None:
        raise ErrorApi(409, "Ya existe un usuario con ese documento o email")

    usuario = Usuario(
        id_rol=rol.id_rol, id_sede=id_sede, documento=documento,
        nombres=texto(datos, "nombres", 80, obligatorio=True),
        apellidos=texto(datos, "apellidos", 80, obligatorio=True),
        email=email, hash_password=hashear_password(password), activo=True,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario
