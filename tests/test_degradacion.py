"""Si MongoDB no responde, lo que depende de MySQL debe seguir funcionando."""
import pytest

from api import crear_app
from tests.conftest import ADMIN, ConfigPruebas


class ConfigMongoCaido(ConfigPruebas):
    MONGO_URI = "mongodb://127.0.0.1:1"   # puerto donde no hay ningún MongoDB
    MONGO_TIMEOUT_MS = 300


@pytest.fixture(scope="module")
def cliente_sin_mongo(app):
    # Depende de `app` para que la base MySQL de pruebas ya exista.
    return crear_app(ConfigMongoCaido).test_client()


def test_api_arranca_y_mysql_sigue_respondiendo(cliente_sin_mongo, catalogo):
    assert cliente_sin_mongo.post("/api/v1/auth/login", json=ADMIN).status_code == 200
    assert cliente_sin_mongo.get("/api/v1/productos").status_code == 200


def test_producto_completo_devuelve_la_parte_de_mysql(cliente_sin_mongo, catalogo):
    respuesta = cliente_sin_mongo.get(f"/api/v1/productos/{catalogo['camiseta']}/completo")
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["nosql_disponible"] is False
    assert datos["variantes"]
    assert "ficha_tecnica" not in datos


def test_endpoints_solo_nosql_responden_503(cliente_sin_mongo, catalogo):
    respuesta = cliente_sin_mongo.get(f"/api/v1/productos/{catalogo['camiseta']}/resenas")
    assert respuesta.status_code == 503
    assert "MongoDB" in respuesta.get_json()["detail"]
