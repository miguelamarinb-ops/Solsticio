"""
Recorrido de punta a punta de la interfaz de Solsticio con Playwright.

Hace clic en la tienda y en el panel como lo haría una persona: crea una prenda, registra
inventario, traslada, vende, mueve pedidos por todos sus estados, modera opiniones, entra
como trabajador para comprobar los permisos, simula un pago rechazado y revisa la vista de
celular. Corre contra la API de pruebas (e2e/preparar_entorno.ps1), nunca contra la base de
desarrollo, porque crea y cancela datos.

Uso:
    python e2e/recorrido_interfaz.py [carpeta_de_capturas]

Variables opcionales:
    E2E_URL     dirección de la API de pruebas (por defecto http://127.0.0.1:5001)
    E2E_CANAL   navegador: "chrome" (Chrome instalado, por defecto) o "chromium"
                (el de Playwright, tras `python -m playwright install chromium`)

Cada paso se registra como OK o FALLA, con una captura en la carpeta de salida.
El proceso termina con código 1 si algún paso falla.
"""
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_URL", "http://127.0.0.1:5001").rstrip("/")
API = BASE + "/api/v1"
SALIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "resultados"
SALIDA.mkdir(parents=True, exist_ok=True)
# Administrador que crea e2e/preparar_entorno.ps1 (solo existe en las bases solsticio_e2e)
ADMIN = {"email": "admin.e2e@solsticio.com", "password": "AdminE2E12345"}
SUFIJO = time.strftime("%H%M%S")
TRAB = {"email": f"trabajador.{SUFIJO}@solsticio.com", "password": "TrabajadorE2E1"}
PRENDA = f"Camisa E2E {SUFIJO}"
resultados = []
errores_consola = []
expect.set_options(timeout=8000)


def paso(nombre, pagina=None):
    def decorador(funcion):
        try:
            detalle = funcion() or ""
            resultados.append(("OK", nombre, detalle))
            print("OK   ", nombre, detalle)
        except Exception as error:  # noqa: BLE001
            resultados.append(("FALLA", nombre, f"{type(error).__name__}: {str(error).splitlines()[0][:220]}"))
            print("FALLA", nombre, error)
            traceback.print_exc(limit=1)
        finally:
            if pagina is not None:
                archivo = re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-")[:60]
                try:
                    pagina.screenshot(path=str(SALIDA / f"{len(resultados):02d}-{archivo}.png"), full_page=True)
                except Exception:  # noqa: BLE001
                    pass
        return funcion
    return decorador


def vigilar(pagina, etiqueta):
    pagina.on("pageerror", lambda e: errores_consola.append(f"[{etiqueta}] {e}"))
    pagina.on("response", lambda r: errores_consola.append(f"[{etiqueta}] HTTP {r.status} {r.request.method} {r.url.replace(BASE, '')}") if r.status >= 400 else None)


def iniciar_sesion(pagina, credenciales):
    pagina.goto(f"{BASE}/panel")
    pagina.fill("#login-email", credenciales["email"])
    pagina.fill("#login-clave", credenciales["password"])
    pagina.click(".login__form button[type=submit]")
    expect(pagina.locator(".panel__principal h1")).to_be_visible()


def ir(pagina, ruta, titulo=None):
    pagina.goto(f"{BASE}/panel{ruta}")
    if titulo:
        expect(pagina.locator(".panel__principal h1")).to_contain_text(titulo)
    pagina.wait_for_timeout(300)


def toast(pagina, texto):
    expect(pagina.locator(".toast").filter(has_text=texto).last).to_be_visible()


def dialogo(pagina, boton):
    d = pagina.locator("dialog.dialogo[open]")
    expect(d).to_be_visible()
    d.get_by_role("button", name=boton, exact=True).click()


def agregar_variante(pagina, texto, contenedor=None):
    """Usa el buscador de variantes: escribe, abre la prenda y agrega la primera variante."""
    zona = contenedor or pagina
    zona.locator("input[aria-label='Buscar prenda']").fill(texto)
    plegable = zona.locator("details.variantes-de").first
    expect(plegable).to_be_visible()
    if not plegable.evaluate("d => d.open"):
        plegable.locator("summary").click()
    boton = plegable.locator("button.variante-opcion").first
    expect(boton).to_be_visible()
    boton.click()


def api(pagina, metodo, ruta, cuerpo=None, token=None):
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    r = pagina.request.fetch(API + ruta, method=metodo, headers=cabeceras, data=json.dumps(cuerpo) if cuerpo else None)
    return r.status, (r.json() if r.body() else None)


with sync_playwright() as p:
    canal = os.environ.get("E2E_CANAL", "chrome")
    nav = p.chromium.launch(channel=None if canal == "chromium" else canal)

    # =====================================================================
    # ADMINISTRADOR
    # =====================================================================
    adm = nav.new_context(viewport={"width": 1366, "height": 900}).new_page()
    vigilar(adm, "admin")
    estado = {}

    @paso("Admin: iniciar sesión", adm)
    def _():
        iniciar_sesion(adm, ADMIN)
        estado["token"] = adm.evaluate("JSON.parse(sessionStorage.getItem('solsticio.panel')).token")

    @paso("Prendas: crear una prenda nueva", adm)
    def _():
        ir(adm, "#/productos/nuevo", "Nueva prenda")
        adm.fill("input[name=nombre]", PRENDA)
        adm.select_option("select[name=id_categoria]", label="Camisetas")
        adm.select_option("select[name=genero]", "UNISEX")
        adm.fill("input[name=precio_base]", "65000")
        adm.fill("textarea[name=descripcion]", "Prenda creada por la prueba automática")
        adm.select_option("select[name=ilustracion]", index=1)
        adm.get_by_role("button", name="Crear prenda").click()
        toast(adm, "Prenda creada")
        adm.wait_for_url(re.compile(r".*#/productos/\d+/variantes"))
        estado["id_producto"] = int(re.search(r"#/productos/(\d+)/", adm.url).group(1))
        return f"id_producto={estado['id_producto']}"

    @paso("Prendas: crear tallas y colores", adm)
    def _():
        for talla in ("M", "L"):
            adm.locator("label.opcion", has_text=re.compile(rf"^{talla}$")).click()
        adm.locator("label.opcion", has_text="Negro").click()
        adm.get_by_role("button", name="Crear variantes").click()
        toast(adm, "2 variantes creadas")
        expect(adm.locator(".tabla tbody tr")).to_have_count(2)

    @paso("Prendas: guardar ficha técnica (MongoDB) con vista previa", adm)
    def _():
        ir(adm, f"#/productos/{estado['id_producto']}/ficha")
        adm.locator("[data-k=fibra]").first.fill("algodón")
        adm.locator("[data-k=porcentaje]").first.fill("100")
        adm.locator("[data-k=clave]").first.fill("cuello")
        adm.locator("[data-k=valor]").first.fill("redondo")
        expect(adm.locator(".vista-etiqueta .etiqueta__composicion")).to_contain_text("100% algodón")
        adm.get_by_role("button", name="Guardar ficha").click()
        toast(adm, "Ficha guardada (versión 1)")

    @paso("Prendas: etiquetas QR para imprimir", adm)
    def _():
        ir(adm, f"#/productos/{estado['id_producto']}/etiquetas")
        expect(adm.locator(".colgante-impreso")).to_have_count(2)
        expect(adm.locator(".colgante-impreso .qr svg").first).to_be_visible()

    @paso("Prendas: desactivar y reactivar", adm)
    def _():
        ir(adm, f"#/productos/{estado['id_producto']}")
        adm.get_by_role("button", name="Desactivar prenda").click()
        dialogo(adm, "Desactivar")
        toast(adm, "Prenda desactivada")
        expect(adm.locator(".aviso", has_text="está desactivada")).to_be_visible()
        adm.get_by_role("button", name="Reactivar prenda").click()
        toast(adm, "Prenda reactivada")

    @paso("Prendas: editar precio", adm)
    def _():
        ir(adm, f"#/productos/{estado['id_producto']}")
        adm.fill("input[name=precio_base]", "69900")
        adm.get_by_role("button", name="Guardar cambios").click()
        toast(adm, "Cambios guardados")
        expect(adm.locator(".pagina__cabeza p")).to_contain_text("69.900")

    @paso("Inventario: registrar ingreso", adm)
    def _():
        ir(adm, "#/inventario/ingreso")
        agregar_variante(adm, PRENDA)
        cantidad = adm.locator(".venta input[type=number]").first
        cantidad.fill("10")
        cantidad.press("Tab")
        adm.fill("input[name=observacion]", "Remisión E2E")
        adm.get_by_role("button", name="Registrar ingreso").click()
        toast(adm, "movimientos registrados")
        expect(adm.locator("table").last).to_contain_text("+10")

    @paso("Inventario: ajuste por conteo físico", adm)
    def _():
        ir(adm, "#/inventario/ajuste")
        agregar_variante(adm, PRENDA)
        expect(adm.locator(".venta .nota").first).to_contain_text("En sistema: 10")
        cantidad = adm.locator(".venta input[type=number]").first
        cantidad.fill("8")
        cantidad.press("Tab")
        adm.fill("input[name=observacion]", "Conteo E2E")
        adm.get_by_role("button", name="Aplicar ajuste").click()
        toast(adm, "movimientos registrados")
        expect(adm.locator("table").last).to_contain_text("-2")

    @paso("Inventario: existencias e historial de movimientos", adm)
    def _():
        ir(adm, "#/inventario")
        adm.locator(".filtros-barra input[type=search]").fill(PRENDA)
        expect(adm.locator(".tabla tbody tr").first).to_contain_text("8")
        ir(adm, "#/inventario/movimientos")
        adm.select_option("select[name=tipo]", "AJUSTE")
        expect(adm.locator(".tabla tbody tr").first).to_contain_text("Conteo E2E")

    @paso("Traslados: crear, despachar y recibir", adm)
    def _():
        ir(adm, "#/traslados/nuevo", "Nuevo traslado")
        adm.select_option("select[name=destino]", "2")
        agregar_variante(adm, PRENDA)
        cantidad = adm.locator(".venta input[type=number]").first
        cantidad.fill("2")
        cantidad.press("Tab")
        adm.get_by_role("button", name="Crear traslado").click()
        toast(adm, "creado")
        adm.wait_for_url(re.compile(r".*#/traslados/\d+$"))
        adm.get_by_role("button", name="Despachar").click()
        dialogo(adm, "Despachar")
        toast(adm, "Traslado despachado")
        expect(adm.locator(".estado-pedido")).to_contain_text("En tránsito")
        adm.get_by_role("button", name="Confirmar recepción").click()
        dialogo(adm, "Confirmar recepción")
        toast(adm, "Traslado recibido")
        expect(adm.locator(".estado-pedido")).to_contain_text("Recibido")

    @paso("Mostrador: venta en tienda con cliente y factura", adm)
    def _():
        ir(adm, "#/mostrador", "Mostrador")
        agregar_variante(adm, PRENDA)
        adm.locator("summary", has_text="Factura a nombre del cliente").click()
        adm.fill("input[name=numero_documento]", "1090000001")
        adm.fill("input[name=nombres]", "Cliente E2E")
        adm.get_by_role("button", name="Cobrar").click()
        expect(adm.locator("h1")).to_contain_text("Venta registrada")
        expect(adm.locator(".tarjeta", has_text="Factura electrónica")).to_contain_text("VALIDADA")
        estado["pedido_tienda"] = adm.locator(".pagina__cabeza p").inner_text().split(",")[0]
        return estado["pedido_tienda"]

    @paso("Pedidos: entregar una venta de tienda", adm)
    def _():
        adm.get_by_role("link", name="Ver el pedido").click()
        expect(adm.locator(".estado-pedido")).to_contain_text("Pagado")
        adm.get_by_role("button", name="Marcar entregado").click()
        toast(adm, "entregado")
        expect(adm.locator(".estado-pedido")).to_contain_text("Entregado")

    # Pedidos web creados por la API pública (como los haría la tienda)
    def pedido_web(domicilio=True, pagar=True):
        _, var = api(adm, "GET", f"/productos/{estado['id_producto']}")
        cuerpo = {"canal": "WEB", "id_sede": 1, "tipo_entrega": "DOMICILIO" if domicilio else "RECOGER_EN_TIENDA",
                  "cliente": {"numero_documento": f"10{SUFIJO}{int(time.time() * 1000) % 1000}", "nombres": "Web E2E", "email": "web@e2e.com"},
                  "items": [{"id_variante": var["variantes"][0]["id_variante"], "cantidad": 1}]}
        if domicilio:
            cuerpo["envio"] = {"direccion": "Calle 1 # 2-3", "ciudad": "Bogotá", "destinatario": "Web E2E", "telefono_contacto": "3000000000"}
        codigo, pedido = api(adm, "POST", "/pedidos", cuerpo)
        assert codigo == 201, pedido
        if pagar:
            codigo, pago = api(adm, "POST", f"/pedidos/{pedido['id_pedido']}/pagos", {"id_metodo_pago": 4, "monto": pedido["total"]})
            assert codigo == 201, pago
        return pedido

    @paso("Pedidos: domicilio preparar, enviar con guía y entregar", adm)
    def _():
        pedido = pedido_web(domicilio=True, pagar=True)
        ir(adm, f"#/pedidos/{pedido['id_pedido']}")
        adm.get_by_role("button", name="Marcar en preparación").click()
        toast(adm, "preparando")
        adm.get_by_role("button", name="Marcar enviado").click()
        d = adm.locator("dialog.dialogo[open]")
        d.locator("input[name=numero_guia]").fill("SV-E2E-1")
        d.get_by_role("button", name="Marcar enviado").click()
        toast(adm, "enviado")
        expect(adm.locator(".tarjeta", has_text="Envío")).to_contain_text("SV-E2E-1")
        adm.get_by_role("button", name="Marcar entregado").click()
        expect(adm.locator(".estado-pedido")).to_contain_text("Entregado")
        return pedido["codigo_qr"]

    @paso("Pedidos: cobrar un pedido pendiente desde el panel", adm)
    def _():
        pedido = pedido_web(domicilio=False, pagar=False)
        ir(adm, f"#/pedidos/{pedido['id_pedido']}")
        expect(adm.locator(".estado-pedido")).to_contain_text("Pendiente")
        adm.get_by_role("button", name="Cobrar", exact=True).click()
        dialogo(adm, "Registrar pago")
        toast(adm, "Pago registrado")
        expect(adm.locator(".estado-pedido")).to_contain_text("Pagado")

    @paso("Pedidos: cancelar un pedido pendiente", adm)
    def _():
        pedido = pedido_web(domicilio=False, pagar=False)
        ir(adm, f"#/pedidos/{pedido['id_pedido']}")
        adm.get_by_role("button", name="Cancelar pedido").click()
        dialogo(adm, "Cancelar pedido")
        expect(adm.locator(".estado-pedido")).to_contain_text("Cancelado")

    @paso("Pedidos: lista, filtro y búsqueda por código", adm)
    def _():
        ir(adm, "#/pedidos", "Pedidos")
        adm.select_option("select[name=estado]", "ENTREGADO")
        expect(adm.locator(".tabla tbody tr").first).to_contain_text("Entregado")
        adm.fill("#buscar-pedido", estado["pedido_tienda"])
        adm.get_by_role("button", name="Buscar pedido").click()
        adm.wait_for_url(re.compile(r".*#/pedidos/\d+$"))
        expect(adm.locator("h1")).to_contain_text(estado["pedido_tienda"])

    @paso("Categorías y sedes: crear una de cada una", adm)
    def _():
        ir(adm, "#/maestros", "Categorías y sedes")
        form = adm.locator("form", has=adm.get_by_role("button", name="Crear categoría"))
        form.locator("input[name=nombre]").fill(f"Categoría E2E {SUFIJO}")
        form.get_by_role("button", name="Crear categoría").click()
        toast(adm, "Categoría creada")
        form = adm.locator("form", has=adm.get_by_role("button", name="Crear sede"))
        form.locator("input[name=nombre]").fill(f"Solsticio E2E {SUFIJO}")
        form.locator("input[name=direccion]").fill("Calle E2E # 1-1")
        form.get_by_role("button", name="Crear sede").click()
        toast(adm, "Sede creada")
        expect(adm.locator(".tabla").last).to_contain_text(f"E2E {SUFIJO}")

    @paso("Usuarios: crear trabajador, desactivar y activar", adm)
    def _():
        ir(adm, "#/usuarios", "Usuarios")
        adm.fill("input[name=nombres]", "Trabajador")
        adm.fill("input[name=apellidos]", "E2E")
        adm.fill("input[name=documento]", f"77{SUFIJO}")
        adm.fill("input[name=email]", TRAB["email"])
        adm.fill("input[name=password]", TRAB["password"])
        adm.select_option("select[name=rol]", "TRABAJADOR")
        adm.select_option("select[name=id_sede]", "1")
        adm.get_by_role("button", name="Crear usuario").click()
        toast(adm, "Usuario creado")
        fila = adm.locator(".tabla tbody tr", has_text=TRAB["email"])
        fila.get_by_role("button", name="Desactivar").click()
        dialogo(adm, "Desactivar")
        toast(adm, "Usuario desactivado")
        fila = adm.locator(".tabla tbody tr", has_text=TRAB["email"])
        expect(fila).to_contain_text("Inactivo")
        fila.get_by_role("button", name="Activar").click()
        toast(adm, "Usuario activado")

    @paso("Opiniones: responder, ocultar, publicar y eliminar", adm)
    def _():
        codigo, _r = api(adm, "POST", f"/productos/{estado['id_producto']}/resenas",
                         {"nombre": "Cliente E2E", "email": f"e2e{SUFIJO}@correo.com", "calificacion": 4, "comentario": f"Opinión E2E {SUFIJO}"})
        assert codigo == 201, _r
        ir(adm, "#/opiniones", "Opiniones")
        tarjeta = adm.locator("article.opinion", has_text=f"Opinión E2E {SUFIJO}")
        tarjeta.locator("summary", has_text="Responder").click()
        tarjeta.locator("textarea").fill("Gracias por tu opinión")
        tarjeta.get_by_role("button", name="Publicar respuesta").click()
        toast(adm, "Respuesta publicada")
        tarjeta = adm.locator("article.opinion", has_text=f"Opinión E2E {SUFIJO}")
        expect(tarjeta.locator(".respuesta-tienda")).to_contain_text("Gracias por tu opinión")
        tarjeta.get_by_role("button", name="Ocultar").click()
        toast(adm, "oculta")
        tarjeta = adm.locator("article.opinion", has_text=f"Opinión E2E {SUFIJO}")
        expect(tarjeta).to_contain_text("Oculta")
        tarjeta.get_by_role("button", name="Publicar", exact=True).click()
        toast(adm, "Opinión publicada")
        tarjeta = adm.locator("article.opinion", has_text=f"Opinión E2E {SUFIJO}")
        tarjeta.get_by_role("button", name="Eliminar").click()
        dialogo(adm, "Eliminar")
        toast(adm, "Opinión eliminada")
        expect(adm.locator("article.opinion", has_text=f"Opinión E2E {SUFIJO}")).to_have_count(0)

    @paso("Bitácora: filtrar por acción", adm)
    def _():
        ir(adm, "#/bitacora", "Bitácora")
        adm.select_option("select[name=accion]", "TRASLADO_DESPACHADO")
        expect(adm.locator(".tabla tbody tr").first).to_contain_text("Traslado despachado")

    @paso("Reportes y Mi perfil", adm)
    def _():
        ir(adm, "#/reportes", "Reportes")
        expect(adm.locator(".cifras .cifra").first).to_be_visible()
        adm.select_option("select[name=canal]", "TIENDA")
        adm.wait_for_timeout(500)
        ir(adm, "#/reportes/mas-vendidas", "Reportes")
        expect(adm.locator(".tabla tbody tr").first).to_be_visible()
        ir(adm, "#/reportes/rotacion", "Reportes")
        expect(adm.locator(".tabla tbody tr").first).to_be_visible()
        ir(adm, "#/reportes/qr", "Reportes")
        adm.select_option("select[name=dias]", "7")
        adm.wait_for_timeout(500)
        ir(adm, "#/perfil", "Mi perfil")
        expect(adm.locator(".barras li").first).to_be_visible()
        expect(adm.locator(".tabla tbody tr").first).to_be_visible()

    # =====================================================================
    # TRABAJADOR (sede Chapinero)
    # =====================================================================
    adm.context.close()
    trab = nav.new_context(viewport={"width": 1366, "height": 900}).new_page()
    vigilar(trab, "trabajador")

    @paso("Trabajador: iniciar sesión y menú limitado", trab)
    def _():
        iniciar_sesion(trab, TRAB)
        menu = trab.locator("#menu").inner_text()
        for prohibido in ("Prendas", "Usuarios", "Bitácora", "Reportes", "Opiniones"):
            assert prohibido not in menu, f"El trabajador ve '{prohibido}' en el menú"
        for permitido in ("Mostrador", "Pedidos", "Inventario", "Traslados"):
            assert permitido in menu, f"Falta '{permitido}' en el menú"
        expect(trab.locator(".menu__usuario")).to_contain_text("Chapinero")

    @paso("Trabajador: secciones de administración bloqueadas", trab)
    def _():
        for ruta in ("#/usuarios", "#/productos", "#/bitacora", "#/inventario/ajuste"):
            trab.goto(f"{BASE}/panel{ruta}")
            expect(trab.locator(".panel__principal")).to_contain_text("solo para administración")
        ir(trab, "#/inventario", "Inventario")
        expect(trab.locator(".pestanas a")).to_have_count(2)

    @paso("Trabajador: vende solo en su sede", trab)
    def _():
        ir(trab, "#/mostrador", "Mostrador")
        expect(trab.locator(".cobro")).to_contain_text("Venta en Chapinero")
        assert trab.locator("select[name=id_sede]").count() == 0
        agregar_variante(trab, PRENDA)
        trab.get_by_role("button", name="Cobrar").click()
        expect(trab.locator("h1")).to_contain_text("Venta registrada")
        expect(trab.locator(".pagina__cabeza p")).to_contain_text("Chapinero")

    @paso("Trabajador: pedidos y traslados solo de su sede", trab)
    def _():
        _, pedidos = api(trab, "GET", "/pedidos?size=100",
                         token=trab.evaluate("JSON.parse(sessionStorage.getItem('solsticio.panel')).token"))
        sedes = {p["sede"]["id_sede"] for p in pedidos["items"]}
        assert sedes <= {1}, f"El trabajador ve pedidos de otras sedes: {sedes}"
        ir(trab, "#/pedidos", "Pedidos")
        assert trab.locator("select[name=id_sede]").count() == 0
        ir(trab, "#/traslados", "Traslados")
        assert trab.get_by_role("link", name="Nuevo traslado").count() == 0
        return f"{len(pedidos['items'])} pedidos, todos de la sede 1"

    # =====================================================================
    # TIENDA: pago rechazado
    # =====================================================================
    trab.context.close()
    tienda = nav.new_context(viewport={"width": 1366, "height": 900}).new_page()
    vigilar(tienda, "tienda")

    @paso("Tienda: pago rechazado conserva el carrito", tienda)
    def _():
        tienda.goto(f"{BASE}/producto?id={estado['id_producto']}")
        expect(tienda.locator(".detalle__nombre")).to_contain_text(PRENDA)
        tienda.get_by_role("button", name="Agregar al carrito").click()
        expect(tienda.locator("#contador-carrito")).to_have_text("1")
        tienda.goto(f"{BASE}/carrito")
        tienda.fill("#cli-numero", f"55{SUFIJO}")
        tienda.fill("#cli-nombres", "Cliente Rechazo")
        tienda.fill("#cli-email", "rechazo@e2e.com")
        tienda.locator("label.casilla").click()
        tienda.get_by_role("button", name=re.compile("^Pagar")).click()
        expect(tienda.locator("h1")).to_contain_text("Tu banco no aprobó el pago")
        tienda.get_by_role("button", name="Intentar de nuevo").click()
        expect(tienda.locator(".linea")).to_have_count(1)

    @paso("Tienda: el mismo carrito se paga bien después del rechazo", tienda)
    def _():
        tienda.fill("#cli-numero", f"56{SUFIJO}")
        tienda.fill("#cli-nombres", "Cliente Reintento")
        tienda.fill("#cli-email", "reintento@e2e.com")
        tienda.get_by_role("button", name=re.compile("^Pagar")).click()
        expect(tienda.locator("h1")).to_contain_text("Gracias")
        expect(tienda.locator(".confirmacion__qr .qr svg")).to_be_visible()

    # =====================================================================
    # CELULAR (390 x 844)
    # =====================================================================
    tienda.context.close()
    movil_ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    movil = movil_ctx.new_page()
    vigilar(movil, "celular")

    def sin_desborde(pagina):
        ancho = pagina.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert ancho[0] <= ancho[1] + 1, f"La página se desborda: {ancho[0]}px de contenido en {ancho[1]}px"

    @paso("Celular: catálogo con filtros plegables", movil)
    def _():
        movil.goto(BASE + "/")
        expect(movil.locator(".prenda").first).to_be_visible()
        boton = movil.locator("#boton-filtros")
        expect(boton).to_be_visible()
        expect(movil.locator("#cuerpo-filtros")).to_be_hidden()
        primera = movil.locator(".prenda").first.bounding_box()
        assert primera["y"] < 844, f"La primera prenda empieza en y={primera['y']:.0f}, fuera de la primera pantalla"
        boton.click()
        expect(movil.locator("#cuerpo-filtros")).to_be_visible()
        movil.locator("#filtro-categoria label", has_text="Jeans").click()
        expect(boton).to_contain_text("1 activo")
        sin_desborde(movil)

    @paso("Celular: detalle con el nombre arriba de la foto", movil)
    def _():
        movil.goto(f"{BASE}/producto?id=6")
        expect(movil.locator(".detalle__nombre")).to_be_visible()
        nombre = movil.locator(".detalle__nombre").bounding_box()
        foto = movil.locator(".detalle__foto").bounding_box()
        assert nombre["y"] < foto["y"], "El nombre quedó debajo de la foto"
        assert nombre["y"] < 300, f"El nombre aparece muy abajo (y={nombre['y']:.0f})"
        sin_desborde(movil)

    @paso("Celular: carrito y escáner sin desborde", movil)
    def _():
        movil.goto(f"{BASE}/carrito")
        expect(movil.locator("h1")).to_be_visible()
        sin_desborde(movil)
        movil.goto(f"{BASE}/escanear?codigo=SOL-V-000001")
        expect(movil.locator(".ficha-qr")).to_be_visible()
        sin_desborde(movil)

    @paso("Celular: menú del panel con Escape y foco", movil)
    def _():
        iniciar_sesion(movil, ADMIN)
        abrir = movil.locator(".menu__abrir")
        expect(abrir).to_be_visible()
        expect(movil.locator("#menu")).to_be_hidden()
        abrir.click()
        expect(movil.locator("#menu")).to_be_visible()
        assert movil.evaluate("document.activeElement.closest('#menu') !== null"), "El foco no entró al menú"
        movil.keyboard.press("Escape")
        expect(movil.locator("#menu")).to_be_hidden()
        assert movil.evaluate("document.activeElement.classList.contains('menu__abrir')"), "El foco no volvió al botón"
        sin_desborde(movil)

    @paso("Celular: tablas del panel como tarjetas", movil)
    def _():
        ir(movil, "#/pedidos", "Pedidos")
        expect(movil.locator(".tabla thead")).to_be_hidden()
        sin_desborde(movil)

    nav.close()

# ---------------------------------------------------------------------------
ok = sum(1 for r in resultados if r[0] == "OK")
print(f"\n{ok} de {len(resultados)} pasos OK")
reales = [e for e in errores_consola if "favicon" not in e]
print(f"Errores de JavaScript en consola: {len(reales)}")
for e in reales[:15]:
    print("  ", e[:200])
(SALIDA / "resultados.json").write_text(json.dumps({"pasos": resultados, "consola": reales}, ensure_ascii=False, indent=1), encoding="utf-8")
sys.exit(0 if ok == len(resultados) else 1)
