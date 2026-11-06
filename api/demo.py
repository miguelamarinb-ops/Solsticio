"""
demo.py
Catálogo de ejemplo para mostrar la tienda: categorías, prendas con ilustración,
variantes, existencias repartidas en las sedes (MySQL), fichas técnicas y
opiniones (MongoDB).

    flask --app app sembrar-demo

Usa los mismos servicios que la API, así que respeta todas las reglas de negocio
(cada existencia queda con su movimiento INGRESO). Se puede ejecutar varias
veces: lo que ya existe no se duplica.
"""
import random
from types import SimpleNamespace

from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import Categoria, Color, ImagenProducto, Producto, Sede, Talla, TipoMovimiento, db
from api.servicios import catalogo, fichas, resenas
from api.servicios.inventario import registrar_movimiento

SISTEMA = SimpleNamespace(id_usuario=None)

CATEGORIAS = {
    "Camisetas": "Camisetas y polos de algodón",
    "Jeans": "Pantalones de denim",
    "Buzos": "Buzos y sudaderas para el frío de Bogotá",
    "Chaquetas": "Chaquetas para la lluvia y la noche",
    "Vestidos": "Vestidos y enterizos",
    "Accesorios": "Gorras y complementos",
}

# nombre, categoría, género, precio, ilustración, tallas, colores, descripción, ficha
PRENDAS = [
    ("Camiseta oversize algodón", "Camisetas", "UNISEX", 79900, "camiseta-oversize", ["S", "M", "L", "XL"], ["Negro", "Blanco"],
     "Corte amplio y hombro caído, en algodón peinado de 240 g que no se transparenta.",
     {"atributos": {"composicion": [{"fibra": "algodón peinado", "porcentaje": 100}], "gramaje_gsm": 240,
                    "cuello": "redondo", "manga": "corta", "fit": "oversize", "pais_origen": "Colombia"},
      "cuidados": ["Lavar a máquina en frío", "No usar blanqueador", "Planchar a temperatura media"],
      "etiquetas": ["verano", "básicos", "unisex"]}),
    ("Camiseta básica cuello V", "Camisetas", "HOMBRE", 49900, "camiseta-cuello-v", ["S", "M", "L", "XL"], ["Blanco", "Gris"],
     "La básica de todos los días, ajustada sin apretar.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 95}, {"fibra": "elastano", "porcentaje": 5}],
                    "gramaje_gsm": 180, "cuello": "en V", "manga": "corta", "fit": "regular", "pais_origen": "Colombia"},
      "cuidados": ["Lavar a máquina en frío", "Secar a la sombra"], "etiquetas": ["básicos", "verano"]}),
    ("Camiseta manga larga", "Camisetas", "MUJER", 59900, "camiseta-manga-larga", ["XS", "S", "M", "L"], ["Beige", "Azul"],
     "Manga larga en punto suave, para las mañanas frías.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 60}, {"fibra": "modal", "porcentaje": 40}],
                    "gramaje_gsm": 200, "cuello": "redondo", "manga": "larga", "fit": "ajustado"},
      "cuidados": ["Lavar a mano o en ciclo delicado", "No usar secadora"], "etiquetas": ["todo el año"]}),
    ("Camiseta infantil Sol", "Camisetas", "INFANTIL", 39900, "camiseta-infantil", ["XS", "S"], ["Blanco", "Azul"],
     "Para los más pequeños, en algodón suave y sin etiquetas que piquen.",
     {"atributos": {"composicion": [{"fibra": "algodón orgánico", "porcentaje": 100}], "gramaje_gsm": 160,
                    "cuello": "redondo", "manga": "corta", "edad": "4 a 10 años", "pais_origen": "Colombia"},
      "cuidados": ["Lavar a máquina en frío", "Lavar con colores similares"], "etiquetas": ["niños", "verano"]}),
    ("Buzo con capota Monserrate", "Buzos", "UNISEX", 139900, "buzo-capota", ["S", "M", "L", "XL"], ["Gris", "Azul", "Negro"],
     "Perchado por dentro, con capota doble y bolsillo canguro.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 80}, {"fibra": "poliéster", "porcentaje": 20}],
                    "gramaje_gsm": 320, "interior": "perchado", "capota": "doble", "bolsillos": 1, "pais_origen": "Colombia"},
      "cuidados": ["Lavar al revés", "No planchar el estampado"], "etiquetas": ["frío", "unisex"]}),
    ("Buzo cuello redondo", "Buzos", "UNISEX", 119900, "buzo-cuello-redondo", ["S", "M", "L"], ["Beige", "Gris"],
     "Sudadera clásica con puños y cintura en rib.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 70}, {"fibra": "poliéster", "porcentaje": 30}],
                    "gramaje_gsm": 300, "interior": "perchado", "puños": "rib"},
      "cuidados": ["Lavar al revés en frío", "Secar a la sombra"], "etiquetas": ["frío", "básicos"]}),
    ("Chaqueta de jean clásica", "Chaquetas", "UNISEX", 189900, "chaqueta-jean", ["S", "M", "L", "XL"], ["Azul"],
     "Denim rígido que se amolda con el uso, botones metálicos.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 100}], "peso_denim": "13 oz",
                    "lavado": "medio", "cierre": "botones metálicos", "bolsillos": 4, "pais_origen": "Colombia"},
      "cuidados": ["Lavar poco y al revés", "No usar blanqueador"], "etiquetas": ["denim", "todo el año"]}),
    ("Chaqueta impermeable La Calera", "Chaquetas", "HOMBRE", 229900, "chaqueta-impermeable", ["M", "L", "XL"], ["Negro", "Azul"],
     "Para el aguacero de las 4: costuras selladas y capota ajustable.",
     {"atributos": {"composicion": [{"fibra": "poliéster reciclado", "porcentaje": 100}], "impermeable": True,
                    "columna_agua_mm": 10000, "costuras": "selladas", "capota": "ajustable", "bolsillos": 3},
      "cuidados": ["Lavar a mano", "No usar suavizante", "No planchar"], "etiquetas": ["lluvia", "frío"]}),
    ("Jean slim tiro alto", "Jeans", "MUJER", 149900, "jean-slim", ["XS", "S", "M", "L"], ["Azul", "Negro"],
     "Tiro alto y pierna ajustada con un toque de elasticidad.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 98}, {"fibra": "elastano", "porcentaje": 2}],
                    "tiro": "alto", "elasticidad": "media", "lavado": "stone wash", "bolsillos": 5, "cierre": "cremallera YKK"},
      "cuidados": ["Lavar al revés", "No secar en secadora"], "etiquetas": ["denim", "todo el año"]}),
    ("Jean recto 90s", "Jeans", "HOMBRE", 159900, "jean-recto", ["S", "M", "L", "XL"], ["Azul", "Negro"],
     "Pierna recta y tiro medio, como los de antes.",
     {"atributos": {"composicion": [{"fibra": "algodón", "porcentaje": 100}], "tiro": "medio", "elasticidad": "ninguna",
                    "lavado": "oscuro", "bolsillos": 5, "cierre": "botones"},
      "cuidados": ["Lavar poco y al revés", "Secar a la sombra"], "etiquetas": ["denim"]}),
    ("Vestido midi de lino", "Vestidos", "MUJER", 169900, "vestido-midi", ["XS", "S", "M", "L"], ["Beige", "Blanco"],
     "Largo midi, tiras ajustables y forro de algodón.",
     {"atributos": {"composicion": [{"fibra": "lino", "porcentaje": 55}, {"fibra": "algodón", "porcentaje": 45}],
                    "largo": "midi", "forro": "algodón", "tiras": "ajustables", "pais_origen": "Colombia"},
      "cuidados": ["Lavar a mano en frío", "Planchar húmedo"], "etiquetas": ["verano", "lino"]}),
    ("Gorra Solsticio", "Accesorios", "UNISEX", 59900, "gorra", ["M"], ["Negro", "Beige"],
     "Seis paneles, visera curva y correa ajustable.",
     {"atributos": {"composicion": [{"fibra": "algodón twill", "porcentaje": 100}], "paneles": 6,
                    "visera": "curva", "ajuste": "correa metálica"},
      "cuidados": ["Limpiar con paño húmedo", "No lavar en lavadora"], "etiquetas": ["accesorios", "unisex"]}),
]

OPINIONES = [
    ("Camiseta oversize algodón", "Laura M.", "laura.m@correo.com", 5, "Ahora es mi favorita",
     "La tela es gruesa, no se transparenta y después de varias lavadas sigue igual.", "GRANDE",
     {"calidad_tela": 5, "encoge": False}),
    ("Camiseta oversize algodón", "Sebastián R.", "sebas.r@correo.com", 4, None,
     "Muy cómoda. Pedí mi talla de siempre y sí queda bastante amplia, como debe ser.", "GRANDE", {}),
    ("Buzo con capota Monserrate", "Camila P.", "camila.p@correo.com", 5, "Abriga de verdad",
     "Lo uso para subir a Monserrate y no paso frío. La capota doble es un detalle muy bueno.", "EXACTA",
     {"abriga": 5}),
    ("Buzo con capota Monserrate", "Andrés V.", "andres.v@correo.com", 3, "Bonito pero motea",
     "El color es lindo, pero después de un mes le salieron motas en las mangas.", "EXACTA",
     {"calidad_tela": 3, "igual_a_la_foto": True}),
    ("Chaqueta impermeable La Calera", "Felipe G.", "felipe.g@correo.com", 5, "Pasó la prueba del aguacero",
     "Me cogió el aguacero en la séptima y llegué seco. Las costuras selladas funcionan.", "EXACTA",
     {"impermeable": True}),
    ("Jean slim tiro alto", "Valentina C.", "vale.c@correo.com", 4, None,
     "Horma muy bien y estiliza. Le bajo una estrella porque el ruedo es un poco largo para mí.", "EXACTA",
     {"elasticidad": 4}),
    ("Jean slim tiro alto", "Mariana T.", "mariana.t@correo.com", 5, "El jean que buscaba",
     "Tiro alto de verdad y no se baja al sentarse.", "PEQUENA", {}),
    ("Vestido midi de lino", "Natalia B.", "natalia.b@correo.com", 5, "Fresco y elegante",
     "Lo usé en un matrimonio en tierra caliente y fue perfecto.", "EXACTA", {"igual_a_la_foto": True}),
    ("Chaqueta de jean clásica", "Juan D.", "juan.d@correo.com", 4, None,
     "Al principio es rígida, pero a la semana ya se siente como mía.", "GRANDE", {}),
    ("Gorra Solsticio", "Daniela F.", "daniela.f@correo.com", 5, None, "Buena calidad y el bordado es muy fino.", None, {}),
]


def _uno(modelo, columna, valor):
    return db.session.scalars(select(modelo).where(columna == valor)).first()


def sembrar(semilla=7, con_mongo=True):
    """con_mongo=False carga solo la parte de MySQL (sin fichas ni opiniones)."""
    azar = random.Random(semilla)
    resumen = {"categorias": 0, "productos": 0, "variantes": 0, "ingresos": 0, "fichas": 0, "opiniones": 0}
    tallas = {t.valor: t.id_talla for t in db.session.scalars(select(Talla))}
    colores = {c.nombre: c.id_color for c in db.session.scalars(select(Color))}
    sedes = db.session.scalars(select(Sede).where(Sede.activo.is_(True)).order_by(Sede.id_sede)).all()

    categorias = {}
    for nombre, descripcion in CATEGORIAS.items():
        categoria = _uno(Categoria, Categoria.nombre, nombre)
        if categoria is None:
            categoria = catalogo.crear_categoria({"nombre": nombre, "descripcion": descripcion})
            resumen["categorias"] += 1
        categorias[nombre] = categoria

    productos = {}
    for nombre, cat, genero, precio, imagen, lista_tallas, lista_colores, descripcion, ficha in PRENDAS:
        url = f"/recursos/img/prendas/{imagen}.svg"
        producto = _uno(Producto, Producto.nombre, nombre)
        if producto is None:
            producto = catalogo.crear_producto({
                "id_categoria": categorias[cat].id_categoria, "nombre": nombre, "descripcion": descripcion,
                "precio_base": precio, "genero": genero,
                "imagenes": [{"url": url, "orden": 1, "es_principal": True}],
            })
            resumen["productos"] += 1
        elif not any(i.url == url for i in producto.imagenes):
            # Prendas creadas antes (p. ej. con Postman): se les pone la ilustración como principal.
            for img in producto.imagenes:
                img.es_principal = False
            db.session.add(ImagenProducto(id_producto=producto.id_producto, url=url, orden=0, es_principal=True))
            db.session.commit()
        productos[nombre] = producto

        combinaciones = [{"id_talla": tallas[t], "id_color": colores[c],
                          "precio_adicional": 5000 if t == "XL" else 0}
                         for t in lista_tallas for c in lista_colores]
        try:
            creadas, _ = catalogo.crear_variantes(producto, {"combinaciones": combinaciones})
            resumen["variantes"] += len(creadas)
        except ErrorApi:
            pass  # ya existían todas
        db.session.refresh(producto)

        for variante in producto.variantes:
            if variante.stocks:
                continue
            reparto = [azar.choice([0, 0, 2, 4, 6, 8, 12, 15]) for _ in sedes]
            if not any(reparto):
                reparto[azar.randrange(len(sedes))] = 4  # cada variante queda en al menos una sede
            for sede, cantidad in zip(sedes, reparto):
                if cantidad:
                    registrar_movimiento(id_sede=sede.id_sede, variante=variante, tipo=TipoMovimiento.INGRESO,
                                         cantidad=cantidad, usuario=None, tipo_referencia="INGRESO",
                                         observacion="Inventario inicial de demostración")
                    resumen["ingresos"] += 1
        db.session.commit()

        if con_mongo and fichas.obtener_ficha(producto.id_producto) is None:
            fichas.guardar_ficha(producto, ficha, SISTEMA)
            resumen["fichas"] += 1

    for nombre, autor, email, nota, titulo, texto, ajuste, atributos in (OPINIONES if con_mongo else ()):
        datos = {"nombre": autor, "email": email, "calificacion": nota, "comentario": texto}
        if titulo:
            datos["titulo"] = titulo
        if ajuste:
            datos["ajuste_talla"] = ajuste
        if atributos:
            datos["atributos"] = atributos
        try:
            resenas.crear_resena(productos[nombre], datos)
            resumen["opiniones"] += 1
        except ErrorApi:
            pass  # esa persona ya opinó sobre la prenda
    return resumen
