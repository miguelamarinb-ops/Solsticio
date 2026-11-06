"""
Capa de rutas: un blueprint por módulo de negocio, todos bajo /api/v1.
actividad, resenas y fichas usan MongoDB (persistencia políglota).
web sirve la tienda (carpeta web/) en la raíz del sitio.
"""
from api.rutas.actividad import bp as actividad_bp
from api.rutas.admin import bp as admin_bp
from api.rutas.auth import bp as auth_bp
from api.rutas.catalogo import bp as catalogo_bp
from api.rutas.cuenta import bp as cuenta_bp
from api.rutas.fichas import bp as fichas_bp
from api.rutas.inventario import bp as inventario_bp
from api.rutas.pedidos import bp as pedidos_bp
from api.rutas.resenas import bp as resenas_bp
from api.rutas.web import bp as web_bp
from api.documentacion import bp as documentacion_bp

PREFIJO_API = "/api/v1"


def registrar_rutas(app):
    blueprints = (
        auth_bp, catalogo_bp, inventario_bp, pedidos_bp, admin_bp, cuenta_bp,  # MySQL
        actividad_bp, resenas_bp, fichas_bp,                        # MongoDB + MySQL
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint, url_prefix=PREFIJO_API)
    app.register_blueprint(web_bp)  # tienda web, fuera de /api/v1
    app.register_blueprint(documentacion_bp)  # OpenAPI en /api/openapi.json y Swagger UI en /api/docs
