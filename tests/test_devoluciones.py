"""
test_devoluciones.py
Caso de uso 2.3.13, devoluciones y cambios: reintegro de stock en la sede que recibe,
dos movimientos en un cambio de talla, nota crédito validada, límite de unidades,
permisos por rol y la solicitud del cliente. Solo necesitan MySQL.
"""
import pytest

pytestmark = pytest.mark.solo_mysql

API = "/api/v1"


def ok(respuesta, codigo=200):
    assert respuesta.status_code == codigo, respuesta.get_json()
    return respuesta.get_json()


def cantidad_en(client, auth, id_sede, id_variante):
    filas = ok(client.get(f"{API}/stock?id_sede={id_sede}&id_variante={id_variante}", headers=auth))
    return filas[0]["cantidad"] if filas else 0


@pytest.fixture(scope="module")
def pedido(client, auth, catalogo):
    """Pedido WEB pagado del fixture catalogo: 2 camisetas de la primera variante, sede 1."""
    return ok(client.get(f"{API}/devoluciones/pedido?codigo={catalogo['codigo_pedido']}", headers=auth))


@pytest.fixture(scope="module")
def trabajador(client, auth):
    ok(client.post(f"{API}/usuarios", headers=auth, json={
        "documento": "8100000001", "nombres": "Rosa", "apellidos": "Peña", "email": "rosa.sede1@solsticio.com",
        "password": "Trabajadora2026", "rol": "TRABAJADOR", "id_sede": 1}), 201)
    login = ok(client.post(f"{API}/auth/login", json={"email": "rosa.sede1@solsticio.com", "password": "Trabajadora2026"}))
    return {"Authorization": f"Bearer {login['access_token']}"}


def test_devolucion_reintegra_en_la_sede_que_recibe_y_emite_nota(client, auth, pedido):
    linea = pedido["items"][0]
    assert linea["devolvible"] == 2
    antes_sede3 = cantidad_en(client, auth, 3, linea["id_variante"])

    dev = ok(client.post(f"{API}/devoluciones", headers=auth, json={
        "id_pedido": pedido["id_pedido"], "id_sede": 3, "tipo": "DEVOLUCION", "motivo": "No le gustó el color",
        "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1}]}), 201)

    assert dev["estado"] == "COMPLETADA" and dev["sede"]["id_sede"] == 3
    assert [(m["tipo"], m["cantidad"]) for m in dev["movimientos_generados"]] == [("DEVOLUCION", 1)]
    assert dev["nota_credito"]["monto"] == linea["precio_unitario"]
    assert dev["nota_credito"]["estado_dian"] == "VALIDADA" and dev["nota_credito"]["cude"]
    assert dev["nota_credito"]["numero_nota"].startswith("NC-SOL-")
    # El stock vuelve a la sede que recibió (3), aunque el pedido salió de la sede 1.
    assert cantidad_en(client, auth, 3, linea["id_variante"]) == antes_sede3 + 1

    restante = ok(client.get(f"{API}/devoluciones/pedido?id_pedido={pedido['id_pedido']}", headers=auth))
    assert restante["items"][0]["devolvible"] == 1


def test_no_se_devuelve_mas_de_lo_comprado(client, auth, pedido):
    linea = pedido["items"][0]
    r = client.post(f"{API}/devoluciones", headers=auth, json={
        "id_pedido": pedido["id_pedido"], "id_sede": 1, "tipo": "DEVOLUCION", "motivo": "x",
        "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 5}]})
    assert r.status_code == 409 and r.get_json()["disponible_para_devolver"] == 1


def test_cambio_de_talla_genera_dos_movimientos_y_nota_en_cero(client, auth, pedido, catalogo):
    linea = pedido["items"][0]
    otra_talla = catalogo["variantes_camiseta"][1]["id_variante"]
    antes_devuelta = cantidad_en(client, auth, 1, linea["id_variante"])
    antes_entregada = cantidad_en(client, auth, 1, otra_talla)

    dev = ok(client.post(f"{API}/devoluciones", headers=auth, json={
        "id_pedido": pedido["id_pedido"], "id_sede": 1, "tipo": "CAMBIO", "motivo": "Le queda ajustada",
        "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1, "id_variante_cambio": otra_talla}]}), 201)

    assert [(m["tipo"], m["id_variante"], m["cantidad"]) for m in dev["movimientos_generados"]] == [
        ("DEVOLUCION", linea["id_variante"], 1), ("VENTA", otra_talla, -1)]
    assert dev["items"][0]["entregado"]["id_variante"] == otra_talla
    assert dev["items"][0]["diferencia_precio"] == 0 and dev["nota_credito"]["monto"] == 0
    assert cantidad_en(client, auth, 1, linea["id_variante"]) == antes_devuelta + 1
    assert cantidad_en(client, auth, 1, otra_talla) == antes_entregada - 1

    # Ya se devolvieron las 2 unidades.
    r = client.post(f"{API}/devoluciones", headers=auth, json={
        "id_pedido": pedido["id_pedido"], "id_sede": 1, "tipo": "DEVOLUCION", "motivo": "x",
        "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1}]})
    assert r.status_code == 409


def test_validaciones(client, auth, pedido, catalogo):
    linea = pedido["items"][0]
    base = {"id_pedido": pedido["id_pedido"], "id_sede": 1, "motivo": "x"}
    sin_variante = client.post(f"{API}/devoluciones", headers=auth, json={
        **base, "tipo": "CAMBIO", "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1}]})
    assert sin_variante.status_code in (409, 422)
    otra_prenda = client.post(f"{API}/devoluciones", headers=auth, json={
        **base, "tipo": "CAMBIO", "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1,
                                            "id_variante_cambio": catalogo["variantes_jean"][0]["id_variante"]}]})
    assert otra_prenda.status_code in (409, 422)
    ajena = client.post(f"{API}/devoluciones", headers=auth, json={
        **base, "tipo": "DEVOLUCION", "items": [{"id_detalle_pedido": 999999, "cantidad": 1}]})
    assert ajena.status_code == 422
    assert client.post(f"{API}/devoluciones", headers=auth, json={**base, "tipo": "REGALO", "items": []}).status_code == 422


def test_pedido_sin_pagar_no_admite_devolucion(client, auth, catalogo):
    variante = catalogo["variantes_camiseta"][1]["id_variante"]
    pendiente = ok(client.post(f"{API}/pedidos", json={
        "canal": "WEB", "id_sede": 1, "cliente": {"numero_documento": "8199999999", "nombres": "Sin pagar"},
        "items": [{"id_variante": variante, "cantidad": 1}]}), 201)
    detalle = pendiente["items"][0]["id_detalle_pedido"]
    r = client.post(f"{API}/devoluciones", headers=auth, json={
        "id_pedido": pendiente["id_pedido"], "id_sede": 1, "tipo": "DEVOLUCION", "motivo": "x",
        "items": [{"id_detalle_pedido": detalle, "cantidad": 1}]})
    assert r.status_code == 409


def test_permisos(client, trabajador, pedido):
    linea = pedido["items"][0]
    otra_sede = client.post(f"{API}/devoluciones", headers=trabajador, json={
        "id_pedido": pedido["id_pedido"], "id_sede": 2, "tipo": "DEVOLUCION", "motivo": "x",
        "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1}]})
    assert otra_sede.status_code == 403
    lista = ok(client.get(f"{API}/devoluciones", headers=trabajador))
    assert all(d["sede"]["id_sede"] == 1 for d in lista["items"])
    assert client.get(f"{API}/devoluciones").status_code == 401


def test_solicitud_del_cliente_y_atencion_en_tienda(client, auth, trabajador, catalogo):
    clienta = ok(client.post(f"{API}/auth/registro", json={
        "documento": "8100000050", "nombres": "Valentina", "apellidos": "Ríos",
        "email": "valentina.rios@correo.com", "password": "Valentina2026"}), 201)
    yo = {"Authorization": f"Bearer {clienta['access_token']}"}
    variante = catalogo["variantes_jean"][0]["id_variante"]
    pedido = ok(client.post(f"{API}/pedidos", headers=yo, json={
        "canal": "WEB", "id_sede": 1, "items": [{"id_variante": variante, "cantidad": 2}]}), 201)
    ok(client.post(f"{API}/pedidos/{pedido['id_pedido']}/pagos", json={"id_metodo_pago": 4, "monto": pedido["total"]}), 201)
    detalle = ok(client.get(f"{API}/cuenta/pedidos/{pedido['id_pedido']}", headers=yo))["items"][0]
    assert detalle["devolvible"] == 2
    antes = cantidad_en(client, auth, 1, variante)

    # El cliente solicita: queda pendiente y no mueve stock ni emite nota.
    solicitud = ok(client.post(f"{API}/cuenta/pedidos/{pedido['id_pedido']}/devoluciones", headers=yo, json={
        "tipo": "DEVOLUCION", "motivo": "Me quedó grande",
        "items": [{"id_detalle_pedido": detalle["id_detalle_pedido"], "cantidad": 1}]}), 201)
    assert solicitud["estado"] == "SOLICITADA" and solicitud["nota_credito"] is None
    assert cantidad_en(client, auth, 1, variante) == antes

    # Otra persona no puede pedir sobre ese pedido; el cliente no entra a la ruta del personal.
    otra = ok(client.post(f"{API}/auth/registro", json={
        "documento": "8100000051", "nombres": "Otro", "apellidos": "Cliente",
        "email": "otro.cliente@correo.com", "password": "OtroCliente2026"}), 201)
    ajena = client.post(f"{API}/cuenta/pedidos/{pedido['id_pedido']}/devoluciones",
                        headers={"Authorization": f"Bearer {otra['access_token']}"},
                        json={"tipo": "DEVOLUCION", "motivo": "x",
                              "items": [{"id_detalle_pedido": detalle["id_detalle_pedido"], "cantidad": 1}]})
    assert ajena.status_code == 404
    assert client.get(f"{API}/devoluciones", headers=yo).status_code == 403

    # La tienda la completa: ahora sí reintegra y emite la nota.
    pendientes = ok(client.get(f"{API}/devoluciones?estado=SOLICITADA", headers=trabajador))
    assert solicitud["id_devolucion"] in [d["id_devolucion"] for d in pendientes["items"]]
    hecha = ok(client.patch(f"{API}/devoluciones/{solicitud['id_devolucion']}", headers=trabajador, json={"accion": "COMPLETAR"}))
    assert hecha["estado"] == "COMPLETADA" and hecha["nota_credito"]["estado_dian"] == "VALIDADA"
    assert hecha["gestionado_por"] == "Rosa Peña"
    assert cantidad_en(client, auth, 1, variante) == antes + 1
    assert client.patch(f"{API}/devoluciones/{solicitud['id_devolucion']}", headers=trabajador,
                        json={"accion": "RECHAZAR"}).status_code == 409

    # Una segunda solicitud rechazada libera las unidades.
    segunda = ok(client.post(f"{API}/cuenta/pedidos/{pedido['id_pedido']}/devoluciones", headers=yo, json={
        "tipo": "DEVOLUCION", "motivo": "Tampoco",
        "items": [{"id_detalle_pedido": detalle["id_detalle_pedido"], "cantidad": 1}]}), 201)
    assert ok(client.get(f"{API}/cuenta/pedidos/{pedido['id_pedido']}", headers=yo))["items"][0]["devolvible"] == 0
    ok(client.patch(f"{API}/devoluciones/{segunda['id_devolucion']}", headers=trabajador, json={"accion": "RECHAZAR"}))
    assert ok(client.get(f"{API}/cuenta/pedidos/{pedido['id_pedido']}", headers=yo))["items"][0]["devolvible"] == 1

    mias = ok(client.get(f"{API}/cuenta/devoluciones", headers=yo))
    assert [d["estado"] for d in mias] == ["RECHAZADA", "COMPLETADA"]
