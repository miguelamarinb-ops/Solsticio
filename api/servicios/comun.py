"""
comun.py
Utilidades compartidas por los servicios.
"""
import unicodedata
import uuid
from decimal import ROUND_HALF_UP, Decimal

from api.errores import ErrorApi
from api.modelos import Sede, Variante, db

TASA_IVA = Decimal("0.19")


def codigo_temporal():
    """Valor único provisional para columnas UNIQUE NOT NULL que dependen del id."""
    return f"T-{uuid.uuid4().hex[:24]}"  # 26 caracteres: cabe en numero_factura VARCHAR(30)


def prefijo_ascii(valor, largo=3):
    base = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode().upper()
    letras = "".join(c for c in base if c.isalnum())
    return letras[:largo] or "X"


def separar_iva(total):
    """Los precios del catálogo incluyen IVA: se separa la base del impuesto."""
    subtotal = (total / (1 + TASA_IVA)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return subtotal, total - subtotal


def obtener_sede_activa(id_sede):
    sede = db.session.get(Sede, id_sede)
    if sede is None or not sede.activo:
        raise ErrorApi(404, f"La sede {id_sede} no existe o está inactiva")
    return sede


def obtener_variante_activa(id_variante):
    variante = db.session.get(Variante, id_variante)
    if variante is None or not variante.activo or not variante.producto.activo:
        raise ErrorApi(404, f"La variante {id_variante} no existe o no está disponible")
    return variante
