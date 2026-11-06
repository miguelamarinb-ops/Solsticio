"""
usuarios.py
Autenticación contra MySQL (tabla usuario, contraseñas con bcrypt), creación de
usuarios del personal (ADMINISTRADOR / TRABAJADOR) y registro público de
clientes (rol CLIENTE).
"""
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Cliente, Rol, TipoDocumento, Usuario, db
from api.seguridad import (
    ADMINISTRADOR, CLIENTE, PERSONAL, TRABAJADOR, hashear_password, verificar_password,
)
from api.servicios.comun import obtener_sede_activa
from api.validacion import a_entero, a_enum, exigir, texto


def _validar_email(datos):
    email = texto(datos, "email", 120, obligatorio=True).lower()
    usuario, _, dominio = email.partition("@")
    if not usuario or "." not in dominio or " " in email:
        raise ErrorApi(422, "'email' no es válido")
    return email


def _validar_password(datos):
    """Mínimo 8 caracteres, con al menos una letra y un número. Nunca se guarda en claro."""
    password = str(datos["password"])
    if len(password) < 8 or len(password) > 72:
        raise ErrorApi(422, "La contraseña debe tener entre 8 y 72 caracteres")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ErrorApi(422, "La contraseña debe combinar letras y números")
    return password


def _exigir_unicos(documento, email):
    repetido = db.session.scalars(
        select(Usuario).where((Usuario.documento == documento) | (Usuario.email == email))
    ).first()
    if repetido is not None:
        raise ErrorApi(409, "Ya existe un usuario con ese documento o email")


def autenticar(datos):
    exigir(datos, "email", "password")
    usuario = db.session.scalars(
        select(Usuario).where(Usuario.email == str(datos["email"]).strip().lower())
    ).first()
    valida = verificar_password(str(datos["password"]), usuario.hash_password if usuario else None)
    if usuario is None or not usuario.activo or not valida:
        raise ErrorApi(401, "Credenciales incorrectas")
    return usuario


def crear_usuario(datos):
    exigir(datos, "documento", "nombres", "apellidos", "email", "password", "rol")
    # El administrador crea cuentas del personal. Los clientes se registran solos
    # en /auth/registro, así que CLIENTE no es un rol válido aquí.
    nombre_rol = str(datos["rol"]).strip().upper()
    rol = db.session.scalars(select(Rol).where(Rol.nombre == nombre_rol)).first()         if nombre_rol in PERSONAL else None
    if rol is None:
        raise ErrorApi(422, "Rol inválido", permitidos=[ADMINISTRADOR, TRABAJADOR])
    email = _validar_email(datos)
    password = _validar_password(datos)

    id_sede = None
    if rol.nombre == TRABAJADOR:
        exigir(datos, "id_sede")
        id_sede = obtener_sede_activa(a_entero(datos["id_sede"], "id_sede", 1)).id_sede
    elif datos.get("id_sede") is not None:
        raise ErrorApi(422, "El administrador es global y no lleva id_sede")

    documento = texto(datos, "documento", 20, obligatorio=True)
    _exigir_unicos(documento, email)

    usuario = Usuario(
        id_rol=rol.id_rol, id_sede=id_sede, documento=documento,
        nombres=texto(datos, "nombres", 80, obligatorio=True),
        apellidos=texto(datos, "apellidos", 80, obligatorio=True),
        email=email, hash_password=hashear_password(password), activo=True,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def registrar_cliente(datos):
    """Registro público de la tienda web. Crea el usuario con rol CLIENTE y su ficha
    en cliente, enlazadas por cliente.id_usuario, en una sola transacción.

    Si el comprador ya había comprado sin cuenta (existe en cliente con ese documento),
    la cuenta nueva se enlaza a esa ficha para que vea sus compras anteriores, pero
    solo si el email coincide con el que dejó al comprar; así nadie reclama el
    historial de otra persona conociendo solo su documento.
    """
    exigir(datos, "documento", "nombres", "apellidos", "email", "password")
    email = _validar_email(datos)
    password = _validar_password(datos)
    documento = texto(datos, "documento", 20, obligatorio=True)
    _exigir_unicos(documento, email)
    rol = db.session.scalars(select(Rol).where(Rol.nombre == CLIENTE)).first()
    if rol is None:
        raise ErrorApi(500, "Falta el rol CLIENTE en la base. Ejecute database/migraciones/001_rol_cliente.sql")

    nombres = texto(datos, "nombres", 80, obligatorio=True)
    apellidos = texto(datos, "apellidos", 80, obligatorio=True)
    usuario = Usuario(
        id_rol=rol.id_rol, id_sede=None, documento=documento, nombres=nombres,
        apellidos=apellidos, email=email, hash_password=hashear_password(password), activo=True,
    )
    db.session.add(usuario)
    db.session.flush()

    cliente = db.session.scalars(select(Cliente).where(Cliente.numero_documento == documento)).first()
    if cliente is None:
        cliente = Cliente(
            tipo_documento=a_enum(TipoDocumento, datos.get("tipo_documento", "CC"), "tipo_documento"),
            numero_documento=documento, nombres=nombres, apellidos=apellidos, email=email,
        )
        db.session.add(cliente)
    elif cliente.id_usuario is not None or (cliente.email or "").lower() != email:
        db.session.rollback()
        raise ErrorApi(409, "Ese documento ya tiene compras con otro correo. "
                            "Acérquese a una sede para vincular su cuenta.")
    cliente.id_usuario = usuario.id_usuario
    for campo, maximo in (("telefono", 20), ("direccion", 150)):
        valor = texto(datos, campo, maximo)
        if valor:
            setattr(cliente, campo, valor)
    db.session.commit()
    return usuario
