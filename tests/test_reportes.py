"""
test_reportes.py
Caso de uso 2.3.9, analítica y reportes: ventas por periodo, prendas más vendidas y
rotación de inventario. Cada prueba filtra por una sede creada aquí, así los números
no dependen de lo que hagan las demás pruebas. Solo necesitan MySQL.
"""
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.solo_mysql

API = "/api/v1"
CAMISETA, JEAN = 79900, 149900


def ok(respuesta, codigo=200):
    assert respuesta.status_code == codigo, respuesta.get_json()
    return respuesta.get_json()


def vender(client, auth, id_sede, items, pagar=True):
    pedido = ok(client.post(f"{API}/pedidos", headers=auth, json={
        "canal": "TIENDA", "id_sede": id_sede,
        "items": [{"id_variante": v, "cantidad": c} for v, c in items]}), 201)
    if pagar:
        ok(client.post(f"{API}/pedidos/{pedido['id_pedido']}/pagos", headers=auth,
                       json={"id_metodo_pago": 1, "monto": pedido["total"]}), 201)
    return pedido


@pytest.fixture(scope="module")
def escenario(client, auth, catalogo):
    """
    Sede nueva con 10 camisetas M, 10 camisetas L y 4 jeans S.
    Venta 1 (pagada): 3 camisetas M y 1 jean. Venta 2 (pagada): 1 camiseta L.
    Venta 3: 1 camiseta M sin pagar (no cuenta). Luego se devuelve 1 camiseta M de la venta 1.
    """
    sede = ok(client.post(f"{API}/sedes", headers=auth, json={
        "nombre": "Solsticio Reportes", "direccion": "Calle 100 # 15-20"}), 201)["id_sede"]
    m, l = (v["id_variante"] for v in catalogo["variantes_camiseta"])
    jean = catalogo["variantes_jean"][0]["id_variante"]
    ok(client.post(f"{API}/inventario/ingresos", headers=auth, json={
        "id_sede": sede, "items": [{"id_variante": m, "cantidad": 10}, {"id_variante": l, "cantidad": 10},
                                   {"id_variante": jean, "cantidad": 4}]}), 201)
    venta1 = vender(client, auth, sede, [(m, 3), (jean, 1)])
    vender(client, auth, sede, [(l, 1)])
    vender(client, auth, sede, [(m, 1)], pagar=False)

    buscado = ok(client.get(f"{API}/devoluciones/pedido?id_pedido={venta1['id_pedido']}", headers=auth))
    linea = next(i for i in buscado["items"] if i["id_variante"] == m)
    ok(client.post(f"{API}/devoluciones", headers=auth, json={
        "id_pedido": venta1["id_pedido"], "id_sede": sede, "tipo": "DEVOLUCION", "motivo": "Talla pequeña",
        "items": [{"id_detalle_pedido": linea["id_detalle_pedido"], "cantidad": 1}]}), 201)
    return {"sede": sede, "camiseta": catalogo["camiseta"], "jean": catalogo["jean"]}


@pytest.fixture(scope="module")
def trabajador(client, auth):
    ok(client.post(f"{API}/usuarios", headers=auth, json={
        "documento": "8200000001", "nombres": "Luis", "apellidos": "Gómez", "email": "luis.reportes@solsticio.com",
        "password": "Trabajador2026", "rol": "TRABAJADOR", "id_sede": 1}), 201)
    login = ok(client.post(f"{API}/auth/login", json={"email": "luis.reportes@solsticio.com",
                                                       "password": "Trabajador2026"}))
    return {"Authorization": f"Bearer {login['access_token']}"}


def test_reporte_de_ventas(client, auth, escenario):
    r = ok(client.get(f"{API}/reportes/ventas?id_sede={escenario['sede']}", headers=auth))
    hoy = date.today()
    assert r["periodo"] == {"desde": (hoy - timedelta(days=29)).isoformat(), "hasta": hoy.isoformat(), "dias": 30}
    brutos = 3 * CAMISETA + JEAN + CAMISETA
    assert r["resumen"] == {
        "total_pedidos": 2,                 # el pedido sin pagar no cuenta
        "unidades_vendidas": 5,
        "ingresos_brutos": brutos,
        "devoluciones": 1,
        "monto_devuelto": CAMISETA,
        "ingresos_netos": brutos - CAMISETA,
        "ticket_promedio": brutos / 2,
    }
    assert r["por_canal"] == [{"canal": "WEB", "pedidos": 0, "ingresos": 0},
                              {"canal": "TIENDA", "pedidos": 2, "ingresos": brutos}]
    assert r["por_dia"] == [{"fecha": hoy.isoformat(), "pedidos": 2, "ingresos": brutos}]

    solo_web = ok(client.get(f"{API}/reportes/ventas?id_sede={escenario['sede']}&canal=web", headers=auth))
    assert solo_web["resumen"]["total_pedidos"] == 0 and solo_web["resumen"]["devoluciones"] == 0
    assert solo_web["filtros"] == {"id_sede": escenario["sede"], "canal": "WEB"}


def test_periodo_sin_ventas(client, auth, escenario):
    r = ok(client.get(f"{API}/reportes/ventas?id_sede={escenario['sede']}&desde=2025-01-01&hasta=2025-01-31",
                      headers=auth))
    assert r["resumen"]["total_pedidos"] == 0 and r["resumen"]["ticket_promedio"] == 0
    assert r["por_dia"] == []


def test_productos_mas_vendidos(client, auth, escenario):
    r = ok(client.get(f"{API}/reportes/productos-mas-vendidos?id_sede={escenario['sede']}", headers=auth))
    assert r["items"] == [
        {"posicion": 1, "id_producto": escenario["camiseta"], "producto": "Camiseta oversize algodón",
         "categoria": "Camisetas", "unidades_vendidas": 4, "ingresos": 4 * CAMISETA, "talla_mas_vendida": "M"},
        {"posicion": 2, "id_producto": escenario["jean"], "producto": "Jean slim tiro alto",
         "categoria": "Jeans", "unidades_vendidas": 1, "ingresos": JEAN, "talla_mas_vendida": "S"},
    ]
    uno = ok(client.get(f"{API}/reportes/productos-mas-vendidos?id_sede={escenario['sede']}&limite=1",
                        headers=auth))
    assert [i["id_producto"] for i in uno["items"]] == [escenario["camiseta"]]


def test_rotacion_de_inventario(client, auth, escenario):
    r = ok(client.get(f"{API}/reportes/rotacion-inventario?id_sede={escenario['sede']}", headers=auth))
    jean, camiseta = r["items"]   # primero lo que más rota
    # Camiseta: entran 20, salen 4 por venta, vuelve 1 → 17. Promedio (0 + 17) / 2 = 8.5; 4 / 8.5 = 0.47.
    assert camiseta == {
        "id_producto": escenario["camiseta"], "producto": "Camiseta oversize algodón", "categoria": "Camisetas",
        "unidades_vendidas": 4, "unidades_devueltas": 1, "stock_inicial": 0, "stock_final": 17,
        "stock_actual": 17, "indice_rotacion": 0.47, "dias_inventario": 128, "clasificacion": "MEDIA",
    }
    # Jean: entran 4, sale 1 → 3. Promedio 1.5; 1 / 1.5 = 0.67. A 1 unidad cada 30 días, 3 alcanzan para 90.
    assert (jean["id_producto"], jean["indice_rotacion"], jean["stock_final"], jean["dias_inventario"]) == (
        escenario["jean"], 0.67, 3, 90)
    assert r["resumen"] == {"ALTA": 0, "MEDIA": 2, "BAJA": 0, "SIN_VENTAS": 0}


def test_rotacion_reconstruye_el_stock_de_un_periodo_pasado(client, auth, escenario):
    """Antes de los ingresos de hoy la sede no tenía nada: el stock al cierre de ese periodo es 0."""
    ayer = date.today() - timedelta(days=1)
    r = ok(client.get(f"{API}/reportes/rotacion-inventario?id_sede={escenario['sede']}"
                      f"&desde={(ayer - timedelta(days=6)).isoformat()}&hasta={ayer.isoformat()}", headers=auth))
    assert {(i["stock_inicial"], i["stock_final"], i["stock_actual"], i["clasificacion"]) for i in r["items"]} == {
        (0, 0, 17, "SIN_VENTAS"), (0, 0, 3, "SIN_VENTAS")}


def test_validaciones(client, auth, escenario):
    base = f"{API}/reportes/ventas"
    assert client.get(f"{base}?desde=2026-02-01&hasta=2026-01-01", headers=auth).status_code == 422
    assert client.get(f"{base}?desde=2024-01-01&hasta=2026-01-01", headers=auth).status_code == 422
    assert client.get(f"{base}?desde=01/01/2026", headers=auth).status_code == 422
    assert client.get(f"{base}?canal=TELEFONO", headers=auth).status_code == 422
    assert client.get(f"{base}?id_sede=99999", headers=auth).status_code == 404


@pytest.mark.parametrize("ruta", ["ventas", "productos-mas-vendidos", "rotacion-inventario"])
def test_solo_el_administrador(client, trabajador, ruta):
    assert client.get(f"{API}/reportes/{ruta}").status_code == 401
    assert client.get(f"{API}/reportes/{ruta}", headers=trabajador).status_code == 403
