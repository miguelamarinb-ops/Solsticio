"""
validacion.py
Lectura y validación de los datos de entrada. Cada función lanza ErrorApi con un
mensaje legible, para que los datos inválidos no lleguen a la base de datos.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import request

from api.errores import ErrorApi
from api.modelos import db


def leer_json():
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        raise ErrorApi(400, "Se esperaba un cuerpo JSON (Content-Type: application/json)")
    return cuerpo


def exigir(datos, *campos):
    faltantes = [c for c in campos if datos.get(c) in (None, "", [])]
    if faltantes:
        raise ErrorApi(422, "Faltan campos obligatorios", campos=faltantes)


def a_entero(valor, campo, minimo=None):
    if isinstance(valor, bool) or (isinstance(valor, float) and not valor.is_integer()):
        raise ErrorApi(422, f"'{campo}' debe ser un número entero")
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ErrorApi(422, f"'{campo}' debe ser un número entero") from None
    if minimo is not None and numero < minimo:
        raise ErrorApi(422, f"'{campo}' debe ser mayor o igual a {minimo}")
    return numero


def a_decimal(valor, campo, positivo=False, no_negativo=False):
    """Los montos se leen como Decimal, nunca como float."""
    if isinstance(valor, bool) or valor is None:
        raise ErrorApi(422, f"'{campo}' debe ser un número")
    try:
        numero = Decimal(str(valor))
    except InvalidOperation:
        raise ErrorApi(422, f"'{campo}' debe ser un número") from None
    if not numero.is_finite():
        raise ErrorApi(422, f"'{campo}' debe ser un número")
    if positivo and numero <= 0:
        raise ErrorApi(422, f"'{campo}' debe ser mayor que cero")
    if no_negativo and numero < 0:
        raise ErrorApi(422, f"'{campo}' no puede ser negativo")
    return numero


def a_enum(enum_cls, valor, campo):
    try:
        return enum_cls(str(valor).strip().upper())
    except ValueError:
        raise ErrorApi(
            422, f"Valor inválido para '{campo}'", permitidos=[e.value for e in enum_cls]
        ) from None


def a_fecha(valor, campo):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ErrorApi(422, f"'{campo}' debe ser una fecha AAAA-MM-DD") from None


def texto(datos, campo, maximo, obligatorio=False):
    valor = datos.get(campo)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise ErrorApi(422, f"'{campo}' es obligatorio")
        return None
    if not isinstance(valor, str):
        raise ErrorApi(422, f"'{campo}' debe ser texto")
    valor = valor.strip()
    if len(valor) > maximo:
        raise ErrorApi(422, f"'{campo}' admite máximo {maximo} caracteres")
    return valor


def arg_entero(nombre, defecto=None, minimo=None, maximo=None):
    valor = request.args.get(nombre)
    if valor in (None, ""):
        return defecto
    numero = a_entero(valor, nombre, minimo)
    return min(numero, maximo) if maximo is not None else numero


def arg_booleano(nombre):
    return request.args.get(nombre, "").strip().lower() in ("1", "true", "si", "sí")


def lista_items(datos, campo="items"):
    items = datos.get(campo)
    if not isinstance(items, list) or not items:
        raise ErrorApi(422, f"'{campo}' debe ser una lista con al menos un elemento")
    if not all(isinstance(item, dict) for item in items):
        raise ErrorApi(422, f"Cada elemento de '{campo}' debe ser un objeto")
    return items


def consolidar_items(items):
    """Convierte [{id_variante, cantidad}] en {id_variante: cantidad}, sumando repetidos."""
    cantidades = {}
    for i, item in enumerate(items):
        id_variante = a_entero(item.get("id_variante"), f"items[{i}].id_variante", 1)
        cantidad = a_entero(item.get("cantidad"), f"items[{i}].cantidad", 1)
        cantidades[id_variante] = cantidades.get(id_variante, 0) + cantidad
    return cantidades


def obtener_o_404(modelo, identificador, mensaje):
    objeto = db.session.get(modelo, identificador)
    if objeto is None:
        raise ErrorApi(404, mensaje)
    return objeto
