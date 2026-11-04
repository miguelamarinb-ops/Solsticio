"""Endpoints que se agregaron para el panel: listados de traslados, usuarios,
moderación de opiniones y productos desactivados."""


def test_listar_traslados_con_filtro(client, auth, catalogo):
    variante = catalogo["variantes_camiseta"][1]["id_variante"]
    creado = client.post("/api/v1/traslados", headers=auth, json={
        "id_sede_origen": 1, "id_sede_destino": 2, "items": [{"id_variante": variante, "cantidad": 1}]})
    assert creado.status_code == 201, creado.get_json()
    id_traslado = creado.get_json()["id_traslado"]

    todos = client.get("/api/v1/traslados", headers=auth).get_json()
    assert any(t["id_traslado"] == id_traslado for t in todos["items"])
    solicitados = client.get("/api/v1/traslados?estado=SOLICITADO", headers=auth).get_json()
    assert all(t["estado"] == "SOLICITADO" for t in solicitados["items"])
    otra_sede = client.get("/api/v1/traslados?id_sede=3", headers=auth).get_json()
    assert all(id_traslado != t["id_traslado"] for t in otra_sede["items"])
    assert client.get("/api/v1/traslados").status_code == 401


def test_listar_y_desactivar_usuarios(client, auth):
    creado = client.post("/api/v1/usuarios", headers=auth, json={
        "documento": "7000000099", "nombres": "Carlos", "apellidos": "Méndez", "email": "carlos.prueba@solsticio.com",
        "password": "Trabajador123", "rol": "TRABAJADOR", "id_sede": 1})
    assert creado.status_code == 201
    id_usuario = creado.get_json()["id_usuario"]

    trabajadores = client.get("/api/v1/usuarios?rol=TRABAJADOR", headers=auth).get_json()
    assert any(u["id_usuario"] == id_usuario for u in trabajadores)

    desactivado = client.patch(f"/api/v1/usuarios/{id_usuario}", headers=auth, json={"activo": False})
    assert desactivado.get_json()["activo"] is False
    login = client.post("/api/v1/auth/login", json={"email": "carlos.prueba@solsticio.com", "password": "Trabajador123"})
    assert login.status_code == 401

    assert client.patch(f"/api/v1/usuarios/{id_usuario}", headers=auth, json={"activo": "no"}).status_code == 422
    yo = client.get("/api/v1/auth/perfil", headers=auth).get_json()["id_usuario"]
    assert client.patch(f"/api/v1/usuarios/{yo}", headers=auth, json={"activo": False}).status_code == 409


def test_moderacion_incluye_ocultas_y_nombre_del_producto(client, auth, catalogo):
    url = f"/api/v1/productos/{catalogo['camiseta']}/resenas"
    visible = client.post(url, json={"nombre": "Ana", "email": "ana@x.com", "calificacion": 5, "comentario": "Linda"}).get_json()
    oculta = client.post(url, json={"nombre": "Spam", "email": "spam@x.com", "calificacion": 1, "comentario": "Promo"}).get_json()
    client.patch(f"/api/v1/resenas/{oculta['id']}", headers=auth, json={"estado": "OCULTA"})

    todas = client.get("/api/v1/resenas", headers=auth).get_json()
    assert todas["total"] == 2
    assert all(r["producto"] == "Camiseta oversize algodón" for r in todas["items"])   # nombre desde MySQL
    assert all("email" in r["autor"] for r in todas["items"])                          # el admin sí ve el email

    ocultas = client.get("/api/v1/resenas?estado=OCULTA", headers=auth).get_json()
    assert [r["id"] for r in ocultas["items"]] == [oculta["id"]]
    assert client.get("/api/v1/resenas?estado=RARO", headers=auth).status_code == 422
    assert client.get("/api/v1/resenas").status_code == 401
    assert visible["id"] != oculta["id"]


def test_productos_desactivados_solo_para_administrador(client, auth, catalogo):
    nuevo = client.post("/api/v1/productos", headers=auth, json={
        "id_categoria": 1, "nombre": "Prenda temporal", "precio_base": 10000}).get_json()
    client.delete(f"/api/v1/productos/{nuevo['id_producto']}", headers=auth)

    publico = client.get("/api/v1/productos?inactivos=true&size=100").get_json()
    assert all(p["id_producto"] != nuevo["id_producto"] for p in publico["items"])
    admin = client.get("/api/v1/productos?inactivos=true&size=100", headers=auth).get_json()
    assert any(p["id_producto"] == nuevo["id_producto"] and p["activo"] is False for p in admin["items"])

    assert client.get(f"/api/v1/productos/{nuevo['id_producto']}").status_code == 404
    assert client.get(f"/api/v1/productos/{nuevo['id_producto']}", headers=auth).status_code == 200

    reactivado = client.put(f"/api/v1/productos/{nuevo['id_producto']}", headers=auth, json={
        "id_categoria": 1, "nombre": "Prenda temporal", "precio_base": 10000, "activo": True})
    assert reactivado.get_json()["activo"] is True


def test_paginas_nuevas_de_la_interfaz(client):
    for ruta in ("/escanear", "/carrito", "/panel"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, ruta
        assert "text/html" in respuesta.content_type
    assert client.get("/recursos/js/panel/app.js").status_code == 200
    assert client.get("/recursos/vendor/qrcode.min.js").status_code == 200
    # La tipografía va incluida: la interfaz no depende de Google Fonts.
    assert client.get("/recursos/fuentes/archivo-latin.woff2").status_code == 200
    for ruta in ("/", "/producto", "/escanear", "/carrito", "/panel"):
        assert b"fonts.googleapis.com" not in client.get(ruta).data, ruta
