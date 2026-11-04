"""CRUD de fichas técnicas (MongoDB) y búsqueda por atributos combinada con MySQL."""

FICHA_CAMISETA = {
    "atributos": {
        "material": "Algodón",
        "composicion": [{"fibra": "algodón peinado", "porcentaje": 100}],
        "gramaje_gsm": 220,
        "cuello": "redondo",
    },
    "cuidados": ["Lavar en frío"],
    "etiquetas": ["Verano", "Básicos"],
}


def test_crear_actualizar_consultar_y_eliminar_ficha(client, auth, catalogo, mongo):
    url = f"/api/v1/productos/{catalogo['camiseta']}/ficha"

    creada = client.put(url, json=FICHA_CAMISETA, headers=auth)
    assert creada.status_code == 200
    ficha = creada.get_json()
    assert ficha["version"] == 1
    assert ficha["categoria"] == "Camisetas"          # copiado desde MySQL
    assert ficha["etiquetas"] == ["verano", "básicos"]  # normalizadas a minúsculas
    assert mongo.fichas_producto.find_one({"_id": catalogo["camiseta"]}) is not None

    cambio = {**FICHA_CAMISETA, "atributos": {**FICHA_CAMISETA["atributos"], "gramaje_gsm": 240}}
    actualizada = client.put(url, json=cambio, headers=auth).get_json()
    assert actualizada["version"] == 2
    assert actualizada["atributos"]["gramaje_gsm"] == 240

    assert client.get(url).get_json()["atributos"]["gramaje_gsm"] == 240

    assert client.delete(url, headers=auth).status_code == 204
    assert client.get(url).status_code == 404


def test_fichas_con_atributos_distintos_conviven(client, auth, catalogo, mongo):
    client.put(f"/api/v1/productos/{catalogo['camiseta']}/ficha", json=FICHA_CAMISETA, headers=auth)
    client.put(f"/api/v1/productos/{catalogo['jean']}/ficha", headers=auth, json={
        "atributos": {"material": "Denim", "tiro": "alto", "bolsillos": 5}})

    jean = mongo.fichas_producto.find_one({"_id": catalogo["jean"]})
    assert "tiro" in jean["atributos"] and "gramaje_gsm" not in jean["atributos"]


def test_guardar_ficha_requiere_administrador(client, catalogo):
    respuesta = client.put(f"/api/v1/productos/{catalogo['camiseta']}/ficha", json=FICHA_CAMISETA)
    assert respuesta.status_code == 401


def test_rechaza_operadores_de_mongodb_en_las_claves(client, auth, catalogo):
    for clave in ("$where", "color.base"):
        respuesta = client.put(f"/api/v1/productos/{catalogo['camiseta']}/ficha", headers=auth,
                               json={"atributos": {clave: "x"}})
        assert respuesta.status_code == 422, clave


def test_ficha_de_producto_inexistente_en_mysql(client, auth):
    respuesta = client.put("/api/v1/productos/99999/ficha", json=FICHA_CAMISETA, headers=auth)
    assert respuesta.status_code == 404


def test_buscar_por_atributos_ignora_tildes_y_trae_stock_de_mysql(client, auth, catalogo):
    client.put(f"/api/v1/productos/{catalogo['camiseta']}/ficha", json=FICHA_CAMISETA, headers=auth)

    datos = client.get("/api/v1/productos/buscar-atributos?atributos.material=algodon&etiqueta=verano").get_json()
    assert datos["total"] == 1
    producto = datos["items"][0]
    assert producto["id_producto"] == catalogo["camiseta"]
    assert producto["stock_total"] > 0                  # dato de MySQL
    assert producto["precio_base"] == 79900

    vacio = client.get("/api/v1/productos/buscar-atributos?atributos.material=lino").get_json()
    assert vacio["total"] == 0


def test_buscar_por_atributos_valida_filtros(client):
    assert client.get("/api/v1/productos/buscar-atributos").status_code == 422
    assert client.get("/api/v1/productos/buscar-atributos?precio=1").status_code == 422
