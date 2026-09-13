"""
Capa de rutas: un blueprint por módulo de negocio, todos bajo /api/v1.
"""
from api.rutas.admin import bp as admin_bp
from api.rutas.auth import bp as auth_bp
from api.rutas.catalogo import bp as catalogo_bp
from api.rutas.inventario import bp as inventario_bp
from api.rutas.pedidos import bp as pedidos_bp

PREFIJO_API = "/api/v1"


def registrar_rutas(app):
    for blueprint in (auth_bp, catalogo_bp, inventario_bp, pedidos_bp, admin_bp):
        app.register_blueprint(blueprint, url_prefix=PREFIJO_API)
