"""Endpoints que combinan MySQL (estructurado) con MongoDB (actividad, escaneos, reseñas, fichas)."""
from tests.conftest import ADMIN


def test_perfil_sql_con_ultimas_actividades_nosql(client, auth):
    client.post("/api/v1/auth/login", json=ADMIN)          # queda INICIO_SESION en la bitácora
    for _ in range(12):
        client.get("/api/v1/auth/perfil", headers=auth)

    datos = client.get("/api/v1/auth/perfil/actividad", headers=auth).get_json()
    assert datos["usuario"]["email"] == ADMIN["email"]        # MySQL
    assert datos["usuario"]["rol"] == "ADMINISTRADOR"
    actividades = datos["ultimas_actividades"]                 # MongoDB
    assert len(actividades) == 10                              # solo las últimas 10
    fechas = [a["fecha"] for a in actividades]
    assert fechas == sorted(fechas, reverse=True)              # de la más reciente a la más antigua
    resumen = {r["accion"]: r["veces"] for r in datos["resumen_actividad"]}
    assert resumen["CONSULTA_PERFIL"] == 12
    assert resumen["INICIO_SESION"] == 1


def test_limite_de_actividades(client, auth):
    for _ in range(5):
        client.get("/api/v1/auth/perfil", headers=auth)
    datos = client.get("/api/v1/auth/perfil/actividad?limite=3", headers=auth).get_json()
    assert len(datos["ultimas_actividades"]) == 3


def test_perfil_con_actividad_requiere_token(client):
    assert client.get("/api/v1/auth/perfil/actividad").status_code == 401


def test_la_bitacora_guarda_errores_y_parametros(client, auth, mongo):
    client.get("/api/v1/traslados/99999", headers=auth)
    evento = mongo.actividad_usuario.find_one({"ruta": "/api/v1/traslados/99999"})
    assert evento["exito"] is False
    assert evento["estado_http"] == 404
    assert evento["parametros"] == {"id_traslado": 99999}
    assert evento["error"]


def test_peticiones_sin_token_no_se_registran(client, mongo):
    client.get("/api/v1/categorias")
    assert mongo.actividad_usuario.count_documents({}) == 0


def test_escaneos_qr_incluyen_codigos_inexistentes(client, auth, catalogo, mongo):
    qr = catalogo["variantes_camiseta"][0]["codigo_qr"]
    assert client.get(f"/api/v1/variantes/qr/{qr}?sede=1").status_code == 200
    assert client.get(f"/api/v1/variantes/qr/{qr}", headers=auth).status_code == 200
    assert client.get("/api/v1/variantes/qr/SOL-V-FALSO").status_code == 404

    web = mongo.escaneos_qr.find_one({"canal": "WEB", "encontrado": True})
    assert web["id_sede"] == 1 and "id_usuario" not in web
    tienda = mongo.escaneos_qr.find_one({"canal": "TIENDA"})
    assert tienda["id_usuario"]
    assert mongo.escaneos_qr.count_documents({"encontrado": False}) == 1


def test_ranking_qr_mongodb_enriquecido_con_mysql(client, auth, catalogo):
    qr_a = catalogo["variantes_camiseta"][0]["codigo_qr"]
    qr_b = catalogo["variantes_jean"][0]["codigo_qr"]
    for _ in range(3):
        client.get(f"/api/v1/variantes/qr/{qr_b}")
    client.get(f"/api/v1/variantes/qr/{qr_a}", headers=auth)

    datos = client.get("/api/v1/reportes/qr-mas-escaneados?dias=30", headers=auth).get_json()
    primero, segundo = datos["items"]
    assert primero["id_variante"] == catalogo["variantes_jean"][0]["id_variante"]
    assert primero["escaneos"]["total"] == 3 and primero["escaneos"]["web"] == 3
    assert primero["descripcion"].startswith("Jean slim tiro alto")   # MySQL
    assert primero["stock_total"] == 20                               # MySQL
    assert segundo["escaneos"]["tienda"] == 1


def test_ranking_qr_sin_escaneos(client, auth):
    assert client.get("/api/v1/reportes/qr-mas-escaneados", headers=auth).status_code == 404


def test_producto_completo_une_ambas_bases(client, auth, catalogo):
    id_producto = catalogo["camiseta"]
    client.put(f"/api/v1/productos/{id_producto}/ficha", headers=auth,
               json={"atributos": {"material": "Algodón"}})
    client.post(f"/api/v1/productos/{id_producto}/resenas", json={
        "nombre": "Ana", "email": "ana@x.com", "calificacion": 5, "comentario": "Excelente"})
    client.get(f"/api/v1/variantes/qr/{catalogo['variantes_camiseta'][0]['codigo_qr']}")

    datos = client.get(f"/api/v1/productos/{id_producto}/completo").get_json()
    assert datos["nosql_disponible"] is True
    assert datos["precio_base"] == 79900 and len(datos["variantes"]) == 2      # MySQL
    assert datos["variantes"][0]["disponibilidad"][0]["sede"]                  # MySQL
    assert datos["ficha_tecnica"]["atributos"]["material"] == "Algodón"        # MongoDB
    assert datos["resenas"]["resumen"]["promedio"] == 5.0                      # MongoDB
    assert len(datos["resenas"]["recientes"]) == 1
    assert datos["escaneos_qr_30_dias"] == 1


def test_bitacora_filtrada_para_administrador(client, auth, catalogo):
    client.put(f"/api/v1/productos/{catalogo['camiseta']}/ficha", headers=auth,
               json={"atributos": {"material": "Algodón"}})
    client.get("/api/v1/auth/perfil", headers=auth)

    datos = client.get("/api/v1/actividad?accion=FICHA_GUARDADA", headers=auth).get_json()
    assert datos["total"] == 1
    assert datos["items"][0]["parametros"] == {"id_producto": catalogo["camiseta"]}
