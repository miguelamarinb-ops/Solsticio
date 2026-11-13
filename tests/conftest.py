"""
conftest.py
Configuración compartida de las pruebas de integración.

Las pruebas usan MySQL y MongoDB reales, pero en bases aparte (solsticio_test),
así que nunca tocan los datos de desarrollo. Las credenciales salen del .env:
se toma DATABASE_URL y solo se cambia el nombre de la base.

    pip install -r requirements-dev.txt
    pytest

Variables opcionales: TEST_DATABASE_URL, TEST_MONGO_URI, TEST_MONGO_DB.
Si MySQL no responde, todas las pruebas se omiten (skip). Si solo falta MongoDB,
se ejecutan las marcadas con @pytest.mark.solo_mysql (autenticación y RBAC) y
se omiten las demás.
"""
import os
from pathlib import Path

import pymysql
import pytest
from pymysql.constants import CLIENT
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from sqlalchemy.engine import make_url

from api import crear_app
from api.config import Config

RAIZ = Path(__file__).resolve().parent.parent
BASE_PRUEBAS = "solsticio_test"
ADMIN = {"email": "admin.pruebas@solsticio.com", "password": "Pruebas12345"}


def _url_mysql_pruebas():
    if os.environ.get("TEST_DATABASE_URL"):
        return make_url(os.environ["TEST_DATABASE_URL"])
    if not Config.SQLALCHEMY_DATABASE_URI:
        pytest.skip("Falta DATABASE_URL en el .env (o TEST_DATABASE_URL)", allow_module_level=True)
    return make_url(Config.SQLALCHEMY_DATABASE_URI).set(database=BASE_PRUEBAS)


URL_MYSQL = _url_mysql_pruebas()
MONGO_URI = os.environ.get("TEST_MONGO_URI", Config.MONGO_URI)
MONGO_DB = os.environ.get("TEST_MONGO_DB", BASE_PRUEBAS)

if URL_MYSQL.database == make_url(Config.SQLALCHEMY_DATABASE_URI or "mysql://x/y").database \
        or MONGO_DB == Config.MONGO_DB:
    raise RuntimeError("Las pruebas no pueden usar la misma base que el desarrollo.")


class ConfigPruebas(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = URL_MYSQL.render_as_string(hide_password=False)
    MONGO_URI = MONGO_URI
    MONGO_DB = MONGO_DB
    MONGO_TIMEOUT_MS = 2000
    SECRET_KEY = Config.SECRET_KEY or "clave-solo-para-pruebas"


def _crear_base_mysql():
    """Ejecuta database/solsticio_schema.sql cambiando el nombre de la base."""
    script = (RAIZ / "database" / "solsticio_schema.sql").read_text(encoding="utf-8")
    script = (script
              .replace("DROP DATABASE IF EXISTS solsticio;", f"DROP DATABASE IF EXISTS {BASE_PRUEBAS};")
              .replace("CREATE DATABASE solsticio", f"CREATE DATABASE {BASE_PRUEBAS}")
              .replace("USE solsticio;", f"USE {BASE_PRUEBAS};"))
    try:
        conexion = pymysql.connect(
            host=URL_MYSQL.host or "localhost", port=URL_MYSQL.port or 3306,
            user=URL_MYSQL.username, password=URL_MYSQL.password or "",
            charset="utf8mb4", client_flag=CLIENT.MULTI_STATEMENTS,
            connect_timeout=5,
        )
    except pymysql.err.OperationalError as error:
        pytest.skip(f"MySQL no disponible para pruebas: {error}")
    with conexion, conexion.cursor() as cursor:
        cursor.execute(script)
        while cursor.nextset():
            pass
        conexion.commit()


def _limpiar_mongo():
    """Borra la base de pruebas de MongoDB. Devuelve el error si no responde."""
    try:
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        cliente.drop_database(MONGO_DB)
        cliente.close()
        return None
    except PyMongoError as error:
        return str(error).split(",")[0]


@pytest.fixture(scope="session")
def app():
    _crear_base_mysql()
    error_mongo = _limpiar_mongo()
    aplicacion = crear_app(ConfigPruebas)
    aplicacion.config["MONGO_ERROR_PRUEBAS"] = error_mongo
    with aplicacion.app_context():
        from api.servicios import usuarios
        usuarios.crear_usuario({
            **ADMIN, "documento": "7000000001", "nombres": "Admin", "apellidos": "Pruebas",
            "rol": "ADMINISTRADOR",
        })
    yield aplicacion
    aplicacion.extensions["mongo_cliente"].close()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def token(client):
    respuesta = client.post("/api/v1/auth/login", json=ADMIN)
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()["access_token"]


@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def mongo(app):
    if app.config["MONGO_ERROR_PRUEBAS"] is not None:
        pytest.skip(f"MongoDB no disponible para pruebas: {app.config['MONGO_ERROR_PRUEBAS']}")
    return app.extensions["mongo"]


@pytest.fixture(autouse=True)
def mongo_limpio(request, app):
    """Cada prueba empieza con las colecciones NoSQL vacías (los índices se conservan)."""
    if app.config["MONGO_ERROR_PRUEBAS"] is not None:
        if request.node.get_closest_marker("solo_mysql"):
            return
        pytest.skip(f"MongoDB no disponible para pruebas: {app.config['MONGO_ERROR_PRUEBAS']}")
    mongo = request.getfixturevalue("mongo")
    for nombre in mongo.list_collection_names():
        mongo[nombre].delete_many({})


@pytest.fixture(scope="session")
def catalogo(client, auth):
    """
    Datos estructurados en MySQL, creados una sola vez por la API:
    2 productos con variantes, stock en la sede 1 y un pedido WEB pagado.
    """
    def ok(respuesta, codigo=201):
        assert respuesta.status_code == codigo, respuesta.get_json()
        return respuesta.get_json()

    cat1 = ok(client.post("/api/v1/categorias", json={"nombre": "Camisetas"}, headers=auth))
    cat2 = ok(client.post("/api/v1/categorias", json={"nombre": "Jeans"}, headers=auth))
    camiseta = ok(client.post("/api/v1/productos", headers=auth, json={
        "id_categoria": cat1["id_categoria"], "nombre": "Camiseta oversize algodón",
        "precio_base": 79900, "genero": "UNISEX"}))
    jean = ok(client.post("/api/v1/productos", headers=auth, json={
        "id_categoria": cat2["id_categoria"], "nombre": "Jean slim tiro alto",
        "precio_base": 149900, "genero": "MUJER"}))
    var_cam = ok(client.post(f"/api/v1/productos/{camiseta['id_producto']}/variantes", headers=auth, json={
        "combinaciones": [{"id_talla": 3, "id_color": 1}, {"id_talla": 4, "id_color": 1}]}))["creadas"]
    var_jean = ok(client.post(f"/api/v1/productos/{jean['id_producto']}/variantes", headers=auth, json={
        "combinaciones": [{"id_talla": 2, "id_color": 2}]}))["creadas"]
    ok(client.post("/api/v1/inventario/ingresos", headers=auth, json={
        "id_sede": 1, "items": [{"id_variante": v["id_variante"], "cantidad": 20}
                                for v in var_cam + var_jean]}))
    pedido = ok(client.post("/api/v1/pedidos", json={
        "canal": "WEB", "id_sede": 1, "tipo_entrega": "DOMICILIO",
        "cliente": {"tipo_documento": "CC", "numero_documento": "1020304050",
                    "nombres": "Andrés", "apellidos": "Rivera", "email": "andres@correo.com"},
        "envio": {"direccion": "Carrera 15 # 82-30", "ciudad": "Bogotá",
                  "destinatario": "Andrés Rivera", "telefono_contacto": "3001234567"},
        "items": [{"id_variante": var_cam[0]["id_variante"], "cantidad": 2}]}))
    ok(client.post(f"/api/v1/pedidos/{pedido['id_pedido']}/pagos",
                   json={"id_metodo_pago": 4, "monto": pedido["total"]}))
    return {
        "camiseta": camiseta["id_producto"],
        "jean": jean["id_producto"],
        "variantes_camiseta": var_cam,
        "variantes_jean": var_jean,
        "codigo_pedido": pedido["codigo_qr"],
    }
