"""
web.py
Sirve la interfaz (carpeta web/ en la raíz del proyecto). Son páginas estáticas
que consumen /api/v1 con fetch; Flask solo entrega los archivos.

Tienda (clientes):
    /                 catálogo
    /producto?id=N    detalle de la prenda
    /escanear         lector del QR de la etiqueta
    /carrito          carrito y pago
Panel (personal):
    /panel            ventas en tienda, pedidos, inventario, catálogo y administración
Archivos:
    /recursos/...     CSS, JS, imágenes y librerías
"""
from pathlib import Path

from flask import Blueprint, send_from_directory

CARPETA_WEB = Path(__file__).resolve().parents[2] / "web"

PAGINAS = {
    "/": "index.html",
    "/producto": "producto.html",
    "/escanear": "escanear.html",
    "/carrito": "carrito.html",
    "/panel": "panel.html",
}

bp = Blueprint("web", __name__)


def _servir(archivo):
    def vista():
        return send_from_directory(CARPETA_WEB, archivo)
    vista.__name__ = f"pagina_{Path(archivo).stem}"
    return vista


for ruta, archivo in PAGINAS.items():
    bp.add_url_rule(ruta, view_func=_servir(archivo), methods=["GET"])


@bp.get("/recursos/<path:archivo>")
def recursos(archivo):
    # send_from_directory rechaza rutas que intenten salir de la carpeta (../).
    return send_from_directory(CARPETA_WEB / "recursos", archivo)
