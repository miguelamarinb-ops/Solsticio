"""CRUD de reseñas (MongoDB) con verificación de compra contra MySQL."""
import pytest


def resena(**extra):
    return {"nombre": "Cliente", "email": "cliente@correo.com", "calificacion": 4,
            "comentario": "Buena prenda", **extra}


@pytest.fixture
def crear(client, catalogo):
    def _crear(producto=None, **extra):
        return client.post(f"/api/v1/productos/{producto or catalogo['camiseta']}/resenas",
                           json=resena(**extra))
    return _crear


def test_resena_con_compra_verificada(crear, catalogo):
    respuesta = crear(email="andres@correo.com", calificacion=5, codigo_pedido=catalogo["codigo_pedido"],
                      id_variante=catalogo["variantes_camiseta"][0]["id_variante"],
                      atributos={"calidad_tela": 5, "encoge": False})
    assert respuesta.status_code == 201
    datos = respuesta.get_json()
    assert datos["compra_verificada"] is True
    assert datos["talla"] == "M" and datos["color"]       # copiados de MySQL
    assert datos["atributos"] == {"calidad_tela": 5, "encoge": False}
    assert "email" not in datos["autor"]                  # el email nunca se publica


def test_campos_opcionales_no_se_guardan_si_no_llegan(crear, mongo):
    crear()
    documento = mongo.resenas_producto.find_one({})
    for campo in ("titulo", "atributos", "fotos", "ajuste_talla", "codigo_pedido"):
        assert campo not in documento


def test_un_email_solo_resena_una_vez_cada_producto(crear, catalogo):
    assert crear().status_code == 201
    assert crear(calificacion=1).status_code == 409
    assert crear(producto=catalogo["jean"]).status_code == 201   # otro producto sí


def test_pedido_que_no_incluye_el_producto(crear, catalogo):
    respuesta = crear(producto=catalogo["jean"], codigo_pedido=catalogo["codigo_pedido"])
    assert respuesta.status_code == 422
    assert "no incluye" in respuesta.get_json()["detail"]


@pytest.mark.parametrize("extra", [
    {"calificacion": 6},
    {"calificacion": 0},
    {"ajuste_talla": "ENORME"},
    {"codigo_pedido": "SOL-P-NOEXISTE"},
    {"id_variante": 99999},
    {"fotos": ["no-es-url"]},
    {"atributos": {"$gt": 1}},
])
def test_validaciones_de_resena(crear, extra):
    assert crear(**extra).status_code == 422


def test_resena_de_producto_inexistente(client):
    assert client.post("/api/v1/productos/99999/resenas", json=resena()).status_code == 404


def test_listar_con_resumen_agregado(client, crear, catalogo):
    crear(email="a@x.com", calificacion=5, ajuste_talla="GRANDE", codigo_pedido=catalogo["codigo_pedido"])
    crear(email="b@x.com", calificacion=4, ajuste_talla="EXACTA")
    crear(email="c@x.com", calificacion=3, ajuste_talla="GRANDE")

    datos = client.get(f"/api/v1/productos/{catalogo['camiseta']}/resenas?orden=mejores").get_json()
    assert [r["calificacion"] for r in datos["items"]] == [5, 4, 3]
    resumen = datos["resumen"]
    assert resumen["total"] == 3
    assert resumen["promedio"] == 4.0
    assert resumen["compras_verificadas"] == 1
    assert resumen["distribucion"] == {"5": 1, "4": 1, "3": 1, "2": 0, "1": 0}
    assert resumen["ajuste_talla"] == {"GRANDE": 2, "EXACTA": 1}


def test_marcar_util_incrementa(client, crear):
    id_resena = crear().get_json()["id"]
    client.post(f"/api/v1/resenas/{id_resena}/util")
    assert client.post(f"/api/v1/resenas/{id_resena}/util").get_json()["util"] == 2


def test_moderar_responder_ocultar_y_eliminar(client, auth, crear):
    id_resena = crear().get_json()["id"]

    respondida = client.patch(f"/api/v1/resenas/{id_resena}", headers=auth,
                              json={"respuesta": "¡Gracias por tu compra!"}).get_json()
    assert respondida["respuestas"][0]["texto"] == "¡Gracias por tu compra!"
    assert respondida["respuestas"][0]["nombre"] == "Admin Pruebas"

    client.patch(f"/api/v1/resenas/{id_resena}", headers=auth, json={"estado": "OCULTA"})
    assert client.get(f"/api/v1/resenas/{id_resena}").status_code == 404   # ya no es pública

    assert client.delete(f"/api/v1/resenas/{id_resena}", headers=auth).status_code == 204
    assert client.delete(f"/api/v1/resenas/{id_resena}", headers=auth).status_code == 404


def test_moderar_requiere_administrador(client, crear):
    id_resena = crear().get_json()["id"]
    assert client.patch(f"/api/v1/resenas/{id_resena}", json={"estado": "OCULTA"}).status_code == 401
    assert client.delete(f"/api/v1/resenas/{id_resena}").status_code == 401


def test_id_mal_formado_es_404(client):
    assert client.get("/api/v1/resenas/no-es-un-objectid").status_code == 404
