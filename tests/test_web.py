"""Tienda web servida por Flask y filtro de stock por sede que usa el catálogo."""


def test_la_raiz_sirve_la_tienda(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.content_type
    assert b"/recursos/js/catalogo.js" in respuesta.data


def test_paginas_y_recursos_estaticos(client):
    assert client.get("/producto").status_code == 200
    assert client.get("/recursos/css/estilos.css").status_code == 200
    assert client.get("/recursos/js/comun.js").status_code == 200
    assert client.get("/recursos/no-existe.js").status_code == 404
    assert client.get("/recursos/../app.py").status_code == 404


def test_informacion_de_la_api_en_su_prefijo(client):
    assert client.get("/api/v1").get_json()["version"] == "v1"


def test_productos_filtrados_por_sede(client, catalogo):
    # El catálogo solo tiene stock en la sede 1 (ingreso de 20 unidades por variante).
    def camiseta(sede):
        datos = client.get(f"/api/v1/productos?sede={sede}").get_json()
        return next(p for p in datos["items"] if p["id_producto"] == catalogo["camiseta"])

    en_sede_1 = camiseta(1)
    assert en_sede_1["stock_total"] > 0
    assert en_sede_1["tallas_disponibles"] == ["M", "L"]

    en_sede_2 = camiseta(2)
    assert en_sede_2["stock_total"] == 0
    assert en_sede_2["tallas_disponibles"] == []


def test_sede_inexistente(client):
    assert client.get("/api/v1/productos?sede=999").status_code == 404
