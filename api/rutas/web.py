"""
web.py
Sirve la tienda web (carpeta web/ en la raíz del proyecto). Son páginas estáticas
que consumen /api/v1 con fetch; Flask solo entrega los archivos.

    /                 catálogo
    /producto?id=N    detalle del producto
    /recursos/...     CSS, JS e imágenes
"""
from pathlib import Path

from flask import Blueprint, send_from_directory

CARPETA_WEB = Path(__file__).resolve().parents[2] / "web"

bp = Blueprint("web", __name__)


@bp.get("/")
def catalogo():
    return send_from_directory(CARPETA_WEB, "index.html")


@bp.get("/producto")
def producto():
    return send_from_directory(CARPETA_WEB, "producto.html")


@bp.get("/recursos/<path:archivo>")
def recursos(archivo):
    # send_from_directory rechaza rutas que intenten salir de la carpeta (../).
    return send_from_directory(CARPETA_WEB / "recursos", archivo)
