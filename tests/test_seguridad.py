"""
test_seguridad.py
Entrega 3: autenticación contra MySQL (registro e inicio de sesión con bcrypt),
autorización con JWT y control de acceso por roles (ADMINISTRADOR, TRABAJADOR,
CLIENTE). Solo necesitan MySQL, así que corren aunque MongoDB no esté.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from api.modelos import Cliente, Usuario, db

pytestmark = pytest.mark.solo_mysql

API = "/api/v1"
CLIENTA = {
    "documento": "8000000001", "nombres": "Laura", "apellidos": "Gómez",
    "email": "laura.gomez@correo.com", "password": "Clienta2026", "telefono": "3015550101",
}
TRABAJADOR = {
    "documento": "8000000100", "nombres": "Pedro", "apellidos": "Suárez",
    "email": "pedro.sede1@solsticio.com", "password": "Trabajador2026", "rol": "TRABAJADOR", "id_sede": 1,
}


def cabecera(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def clienta(client):
    r = client.post(f"{API}/auth/registro", json=CLIENTA)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


@pytest.fixture(scope="module")
def auth_clienta(clienta):
    return cabecera(clienta["access_token"])


@pytest.fixture(scope="module")
def auth_trabajador(client, auth):
    r = client.post(f"{API}/usuarios", headers=auth, json=TRABAJADOR)
    assert r.status_code == 201, r.get_json()
    login = client.post(f"{API}/auth/login", json={"email": TRABAJADOR["email"], "password": TRABAJADOR["password"]})
    return cabecera(login.get_json()["access_token"])


# ---------------------------------------------------------------------
# Registro e inicio de sesión (MySQL + bcrypt)
# ---------------------------------------------------------------------
def test_registro_crea_usuario_cliente_con_hash_bcrypt(app, clienta):
    assert clienta["token_type"] == "bearer"
    assert clienta["usuario"]["rol"] == "CLIENTE"
    assert clienta["usuario"]["sede"] is None
    assert clienta["usuario"]["cliente"]["telefono"] == CLIENTA["telefono"]
    assert "password" not in clienta["usuario"] and "hash_password" not in clienta["usuario"]

    with app.app_context():
        usuario = db.session.scalars(select(Usuario).where(Usuario.email == CLIENTA["email"])).one()
        assert usuario.hash_password.startswith("$2b$")          # bcrypt, con sal
        assert CLIENTA["password"] not in usuario.hash_password   # nunca en claro
        ficha = db.session.scalars(select(Cliente).where(Cliente.id_usuario == usuario.id_usuario)).one()
        assert ficha.numero_documento == CLIENTA["documento"]


def test_registro_rechaza_duplicados_y_datos_invalidos(client, clienta):
    assert client.post(f"{API}/auth/registro", json=CLIENTA).status_code == 409
    otro = {**CLIENTA, "documento": "8000000002", "email": "otra@correo.com"}
    assert client.post(f"{API}/auth/registro", json={**otro, "password": "corta1"}).status_code == 422
    assert client.post(f"{API}/auth/registro", json={**otro, "password": "solamenteletras"}).status_code == 422
    assert client.post(f"{API}/auth/registro", json={**otro, "email": "sin-arroba"}).status_code == 422
    sin_nombre = {k: v for k, v in otro.items() if k != "nombres"}
    assert client.post(f"{API}/auth/registro", json=sin_nombre).status_code == 422


def test_login_correcto_e_incorrecto(client, clienta):
    ok = client.post(f"{API}/auth/login", json={"email": CLIENTA["email"].upper(), "password": CLIENTA["password"]})
    assert ok.status_code == 200
    assert ok.get_json()["usuario"]["rol"] == "CLIENTE"

    mala = client.post(f"{API}/auth/login", json={"email": CLIENTA["email"], "password": "Equivocada1"})
    inexistente = client.post(f"{API}/auth/login", json={"email": "nadie@correo.com", "password": "Equivocada1"})
    # El mismo mensaje en los dos casos: no se revela qué correos existen.
    assert mala.status_code == inexistente.status_code == 401
    assert mala.get_json()["detail"] == inexistente.get_json()["detail"]


def test_registro_enlaza_compras_previas_solo_con_el_mismo_correo(client, catalogo):
    # El fixture catalogo dejó un pedido web pagado del documento 1020304050.
    ajeno = client.post(f"{API}/auth/registro", json={
        "documento": "1020304050", "nombres": "Impostor", "apellidos": "X",
        "email": "impostor@correo.com", "password": "Impostor2026"})
    assert ajeno.status_code == 409

    dueno = client.post(f"{API}/auth/registro", json={
        "documento": "1020304050", "nombres": "Andrés", "apellidos": "Rivera",
        "email": "andres@correo.com", "password": "Andres2026"})
    assert dueno.status_code == 201, dueno.get_json()
    pedidos = client.get(f"{API}/cuenta/pedidos", headers=cabecera(dueno.get_json()["access_token"])).get_json()
    assert [p["codigo_qr"] for p in pedidos["items"]] == [catalogo["codigo_pedido"]]


# ---------------------------------------------------------------------
# Tokens JWT
# ---------------------------------------------------------------------
def test_rutas_protegidas_exigen_token_valido(app, client, clienta):
    assert client.get(f"{API}/auth/perfil").status_code == 401
    assert client.get(f"{API}/auth/perfil", headers={"Authorization": "Token abc"}).status_code == 401

    token = clienta["access_token"]
    alterado = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    assert client.get(f"{API}/auth/perfil", headers=cabecera(alterado)).status_code == 401

    payload = jwt.decode(token, options={"verify_signature": False})
    otra_clave = jwt.encode(payload, "clave-de-un-atacante", algorithm="HS256")
    assert client.get(f"{API}/auth/perfil", headers=cabecera(otra_clave)).status_code == 401

    sin_firma = jwt.encode(payload, None, algorithm="none")
    assert client.get(f"{API}/auth/perfil", headers=cabecera(sin_firma)).status_code == 401

    ahora = datetime.now(timezone.utc)
    vencido = jwt.encode({**payload, "iat": ahora - timedelta(hours=2), "exp": ahora - timedelta(hours=1)},
                         app.config["SECRET_KEY"], algorithm="HS256")
    r = client.get(f"{API}/auth/perfil", headers=cabecera(vencido))
    assert r.status_code == 401 and "expiró" in r.get_json()["detail"]

    assert client.get(f"{API}/auth/perfil", headers=cabecera(token)).status_code == 200


def test_el_rol_se_lee_de_la_base_y_no_del_token(app, client, clienta):
    """Un cliente que edita el rol de su token a ADMINISTRADOR invalida la firma;
    y aunque firmara, el servidor toma el rol de MySQL."""
    payload = jwt.decode(clienta["access_token"], options={"verify_signature": False})
    falso = jwt.encode({**payload, "rol": "ADMINISTRADOR"}, app.config["SECRET_KEY"], algorithm="HS256")
    assert client.get(f"{API}/usuarios", headers=cabecera(falso)).status_code == 403


def test_usuario_desactivado_pierde_el_acceso(client, auth):
    r = client.post(f"{API}/auth/registro", json={
        "documento": "8000000050", "nombres": "Temporal", "apellidos": "Prueba",
        "email": "temporal@correo.com", "password": "Temporal2026"})
    token, id_usuario = r.get_json()["access_token"], r.get_json()["usuario"]["id_usuario"]
    assert client.get(f"{API}/auth/perfil", headers=cabecera(token)).status_code == 200
    client.patch(f"{API}/usuarios/{id_usuario}", headers=auth, json={"activo": False})
    assert client.get(f"{API}/auth/perfil", headers=cabecera(token)).status_code == 401


# ---------------------------------------------------------------------
# Roles y permisos (RBAC)
# ---------------------------------------------------------------------
RUTAS_SOLO_ADMIN = [
    ("get", "/usuarios"), ("post", "/usuarios"), ("post", "/productos"), ("post", "/categorias"),
    ("post", "/sedes"), ("post", "/inventario/ajustes"), ("get", "/inventario/movimientos"),
    ("post", "/traslados"),
]
RUTAS_PERSONAL = [("get", "/stock"), ("get", "/pedidos"), ("get", "/traslados"), ("post", "/inventario/ingresos")]


@pytest.mark.parametrize("metodo,ruta", RUTAS_SOLO_ADMIN + RUTAS_PERSONAL)
def test_cliente_no_entra_a_rutas_del_personal(client, auth_clienta, metodo, ruta):
    r = getattr(client, metodo)(f"{API}{ruta}", headers=auth_clienta, json={})
    assert r.status_code == 403, (ruta, r.get_json())


@pytest.mark.parametrize("metodo,ruta", RUTAS_SOLO_ADMIN)
def test_trabajador_no_entra_a_rutas_del_administrador(client, auth_trabajador, metodo, ruta):
    r = getattr(client, metodo)(f"{API}{ruta}", headers=auth_trabajador, json={})
    assert r.status_code == 403, (ruta, r.get_json())


def test_trabajador_opera_solo_en_su_sede(client, auth_trabajador):
    assert client.get(f"{API}/stock", headers=auth_trabajador).status_code == 200
    assert client.get(f"{API}/stock?id_sede=2", headers=auth_trabajador).status_code == 403


def test_administrador_entra_a_todo(client, auth):
    for ruta in ("/usuarios", "/stock?id_sede=2", "/pedidos", "/inventario/movimientos?id_sede=1"):
        assert client.get(f"{API}{ruta}", headers=auth).status_code == 200, ruta


def test_admin_no_puede_crear_clientes_por_la_ruta_del_personal(client, auth):
    r = client.post(f"{API}/usuarios", headers=auth, json={
        **TRABAJADOR, "documento": "8000000101", "email": "x@solsticio.com", "rol": "CLIENTE"})
    assert r.status_code == 422


def test_cliente_no_registra_ventas_ni_pagos_de_tienda(client, auth_clienta, catalogo):
    variante = catalogo["variantes_camiseta"][0]["id_variante"]
    r = client.post(f"{API}/pedidos", headers=auth_clienta, json={
        "canal": "TIENDA", "id_sede": 1, "items": [{"id_variante": variante, "cantidad": 1}]})
    assert r.status_code == 403


# ---------------------------------------------------------------------
# Casos de uso del cliente: comprar con su cuenta y ver solo sus pedidos
# ---------------------------------------------------------------------
def test_cliente_compra_con_su_cuenta_y_ve_solo_sus_pedidos(client, auth, auth_clienta, catalogo):
    variante = catalogo["variantes_jean"][0]["id_variante"]
    r = client.post(f"{API}/pedidos", headers=auth_clienta, json={
        "canal": "WEB", "id_sede": 1, "tipo_entrega": "RECOGER_EN_TIENDA",
        "items": [{"id_variante": variante, "cantidad": 1}]})
    assert r.status_code == 201, r.get_json()
    pedido = r.get_json()
    assert pedido["cliente"]["numero_documento"] == CLIENTA["documento"]   # sin enviar sus datos

    pago = client.post(f"{API}/pedidos/{pedido['id_pedido']}/pagos",
                       json={"id_metodo_pago": 4, "monto": pedido["total"]})
    assert pago.status_code == 201

    mios = client.get(f"{API}/cuenta/pedidos", headers=auth_clienta).get_json()
    assert [p["id_pedido"] for p in mios["items"]] == [pedido["id_pedido"]]
    detalle = client.get(f"{API}/cuenta/pedidos/{pedido['id_pedido']}", headers=auth_clienta).get_json()
    assert detalle["estado"] == "PAGADO"

    # Otro cliente no ve el pedido: 404, no 403, para no confirmar que existe.
    otra = client.post(f"{API}/auth/registro", json={
        "documento": "8000000003", "nombres": "Sofía", "apellidos": "Ruiz",
        "email": "sofia.ruiz@correo.com", "password": "Sofia2026"}).get_json()
    ajeno = client.get(f"{API}/cuenta/pedidos/{pedido['id_pedido']}", headers=cabecera(otra["access_token"]))
    assert ajeno.status_code == 404
    assert client.get(f"{API}/cuenta/pedidos", headers=cabecera(otra["access_token"])).get_json()["total"] == 0

    # Las rutas de cuenta son del rol CLIENTE: el personal usa /pedidos.
    assert client.get(f"{API}/cuenta/pedidos", headers=auth).status_code == 403
    assert client.get(f"{API}/cuenta/pedidos").status_code == 401
