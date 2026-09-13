"""
config.py
Configuración leída de variables de entorno. En local se cargan desde el archivo
.env (ver .env.example); en Render se definen en el dashboard del servicio.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _normalizar_url(url):
    # SQLAlchemy necesita saber qué driver usar: "mysql://" se traduce a PyMySQL.
    if url and url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+pymysql://", 1)
    return url


def _booleano(nombre, defecto="true"):
    return os.environ.get(nombre, defecto).strip().lower() in ("1", "true", "si", "sí", "yes")


class Config:
    SQLALCHEMY_DATABASE_URI = _normalizar_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SECRET_KEY = os.environ.get("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    DIAN_SIMULACION = _booleano("DIAN_SIMULACION")
    PASARELA_SIMULACION = _booleano("PASARELA_SIMULACION")
