"""
catalogo.py
Administración del catálogo: categorías, sedes, productos y variantes.
"""
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Categoria, Color, Genero, ImagenProducto, Producto, Sede, Talla, Variante, db
from api.servicios.comun import codigo_temporal, prefijo_ascii
from api.validacion import (
    a_decimal, a_entero, a_enum, exigir, lista_items, obtener_o_404, texto,
)


def _existe(modelo, columna, valor):
    return db.session.scalars(select(modelo).where(columna == valor)).first() is not None


def crear_categoria(datos):
    nombre = texto(datos, "nombre", 60, obligatorio=True)
    if _existe(Categoria, Categoria.nombre, nombre):
        raise ErrorApi(409, "Ya existe una categoría con ese nombre")
    categoria = Categoria(nombre=nombre, descripcion=texto(datos, "descripcion", 200), activo=True)
    db.session.add(categoria)
    db.session.commit()
    return categoria


def crear_sede(datos):
    nombre = texto(datos, "nombre", 80, obligatorio=True)
    if _existe(Sede, Sede.nombre, nombre):
        raise ErrorApi(409, "Ya existe una sede con ese nombre")
    sede = Sede(
        nombre=nombre,
        direccion=texto(datos, "direccion", 150, obligatorio=True),
        ciudad=texto(datos, "ciudad", 60) or "Bogota",
        telefono=texto(datos, "telefono", 20),
        activo=True,
    )
    db.session.add(sede)
    db.session.commit()
    return sede


def _leer_producto(datos):
    exigir(datos, "id_categoria", "nombre", "precio_base")
    categoria = db.session.get(Categoria, a_entero(datos["id_categoria"], "id_categoria", 1))
    if categoria is None or not categoria.activo:
        raise ErrorApi(404, "Categoría no encontrada")
    return {
        "id_categoria": categoria.id_categoria,
        "nombre": texto(datos, "nombre", 120, obligatorio=True),
        "descripcion": texto(datos, "descripcion", 5000),
        "precio_base": a_decimal(datos["precio_base"], "precio_base", positivo=True),
        "genero": a_enum(Genero, datos.get("genero", "UNISEX"), "genero"),
    }


def crear_producto(datos):
    producto = Producto(**_leer_producto(datos), activo=True)
    db.session.add(producto)
    db.session.flush()
    for i, imagen in enumerate(datos.get("imagenes") or []):
        if not isinstance(imagen, dict):
            raise ErrorApi(422, "Cada imagen debe ser un objeto {url, orden, es_principal}")
        db.session.add(ImagenProducto(
            id_producto=producto.id_producto,
            url=texto(imagen, "url", 255, obligatorio=True),
            orden=a_entero(imagen.get("orden", i + 1), "orden", 1),
            es_principal=imagen.get("es_principal") is True,
        ))
    db.session.commit()
    return producto


def actualizar_producto(producto, datos):
    for campo, valor in _leer_producto(datos).items():
        setattr(producto, campo, valor)
    if "activo" in datos:
        producto.activo = datos["activo"] is True
    db.session.commit()
    return producto


def desactivar_producto(producto):
    """Borrado lógico: el histórico de ventas y movimientos se conserva."""
    producto.activo = False
    db.session.commit()


def crear_variantes(producto, datos):
    """Genera variantes talla + color con SKU y código QR automáticos. Devuelve (creadas, omitidas)."""
    combinaciones = lista_items(datos, "combinaciones")
    existentes = {(v.id_talla, v.id_color): v.id_variante for v in producto.variantes}
    creadas, omitidas = [], []
    for i, combo in enumerate(combinaciones):
        talla = obtener_o_404(Talla, a_entero(combo.get("id_talla"), f"combinaciones[{i}].id_talla", 1),
                              "Talla no encontrada")
        color = obtener_o_404(Color, a_entero(combo.get("id_color"), f"combinaciones[{i}].id_color", 1),
                              "Color no encontrado")
        clave = (talla.id_talla, color.id_color)
        if clave in existentes:
            omitidas.append({"id_talla": talla.id_talla, "id_color": color.id_color,
                             "id_variante_existente": existentes[clave]})
            continue
        variante = Variante(
            id_producto=producto.id_producto, id_talla=talla.id_talla, id_color=color.id_color,
            sku=(f"{prefijo_ascii(producto.categoria.nombre)}-{producto.id_producto:03d}-"
                 f"{prefijo_ascii(talla.valor, 5)}-{prefijo_ascii(color.nombre)}"),
            codigo_qr=codigo_temporal(),
            precio_adicional=a_decimal(combo.get("precio_adicional", 0), "precio_adicional", no_negativo=True),
            activo=True,
        )
        db.session.add(variante)
        db.session.flush()
        variante.codigo_qr = f"SOL-V-{variante.id_variante:06d}"
        existentes[clave] = variante.id_variante
        creadas.append(variante)

    if not creadas:
        raise ErrorApi(409, "Una o más combinaciones ya existen para este producto", omitidas=omitidas)
    db.session.commit()
    return creadas, omitidas
