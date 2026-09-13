"""
comandos.py
Comandos de consola:  flask --app app verificar-bd  |  flask --app app crear-admin
"""
import click
from sqlalchemy import text

from api.errores import ErrorApi
from api.modelos import db
from api.seguridad import ADMINISTRADOR
from api.servicios import usuarios


def registrar_comandos(app):
    @app.cli.command("verificar-bd")
    def verificar_bd():
        """Comprueba la conexión a MySQL y cuenta las tablas del esquema."""
        tablas = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"
        )).scalar()
        click.echo(f"Conexión correcta. Tablas en la base de datos: {tablas}")

    @app.cli.command("crear-admin")
    @click.option("--email", prompt=True)
    @click.option("--documento", prompt=True)
    @click.option("--nombres", prompt=True)
    @click.option("--apellidos", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def crear_admin(email, documento, nombres, apellidos, password):
        """Crea el primer usuario ADMINISTRADOR para poder iniciar sesión."""
        try:
            usuario = usuarios.crear_usuario({
                "email": email, "documento": documento, "nombres": nombres,
                "apellidos": apellidos, "password": password, "rol": ADMINISTRADOR,
            })
        except ErrorApi as error:
            db.session.rollback()
            raise click.ClickException(error.detalle) from None
        click.echo(f"Administrador {usuario.email} creado.")
