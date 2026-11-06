"""
test_documentacion.py
La documentación OpenAPI se arma desde las rutas reales de Flask; estas pruebas
fallan si una ruta nueva queda sin describir o si los permisos documentados no
coinciden con los decoradores de seguridad.
"""
import pytest

from api.documentacion import ENDPOINTS

pytestmark = pytest.mark.solo_mysql


def test_todas_las_rutas_estan_documentadas(app):
    rutas_api = {r.endpoint for r in app.url_map.iter_rules() if r.rule.startswith("/api/v1")}
    sin_documentar = rutas_api - ENDPOINTS.keys()
    assert not sin_documentar, f"Describa estas rutas en api/documentacion.py: {sorted(sin_documentar)}"
    assert not (ENDPOINTS.keys() - rutas_api), "Hay descripciones de rutas que ya no existen"


def test_especificacion_openapi_y_permisos(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.get_json()
    assert spec["openapi"].startswith("3.")
    assert spec["components"]["securitySchemes"]["bearerAuth"]["bearerFormat"] == "JWT"

    rutas = spec["paths"]
    assert "security" not in rutas["/api/v1/auth/registro"]["post"]
    assert rutas["/api/v1/usuarios"]["get"]["x-roles"] == ["ADMINISTRADOR"]
    assert rutas["/api/v1/cuenta/pedidos"]["get"]["x-roles"] == ["CLIENTE"]
    assert set(rutas["/api/v1/stock"]["get"]["x-roles"]) == {"ADMINISTRADOR", "TRABAJADOR"}
    assert "403" in rutas["/api/v1/stock"]["get"]["responses"]
    assert "{id_pedido}" in "".join(rutas)


def test_swagger_ui(client):
    r = client.get("/api/docs")
    assert r.status_code == 200 and b"swagger-ui" in r.data
