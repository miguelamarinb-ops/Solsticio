"""
inventario.py
Existencias por sede, movimientos de inventario, ingresos y ajustes.
"""
from sqlalchemy import select

from api.errores import ErrorApi
from api.modelos import MovimientoInventario, Sede, Stock, TipoMovimiento, db
from api.seguridad import verificar_sede
from api.servicios.comun import obtener_sede_activa, obtener_variante_activa
from api.validacion import a_entero, consolidar_items, exigir, lista_items, texto


def obtener_stock(id_sede, id_variante, crear=False):
    """Lee la fila de stock bloqueándola (SELECT ... FOR UPDATE) hasta el commit."""
    stock = db.session.scalars(
        select(Stock)
        .where(Stock.id_sede == id_sede, Stock.id_variante == id_variante)
        .with_for_update()
    ).first()
    if stock is None and crear:
        stock = Stock(id_sede=id_sede, id_variante=id_variante,
                      cantidad=0, cantidad_reservada=0, stock_minimo=0)
        db.session.add(stock)
    return stock


def disponible(stock):
    return 0 if stock is None else stock.cantidad - stock.cantidad_reservada


def otras_sedes_con_existencias(id_variante, id_sede_excluida):
    libre = Stock.cantidad - Stock.cantidad_reservada
    filas = db.session.execute(
        select(Sede.id_sede, Sede.nombre, libre.label("disponible"))
        .join(Stock, Stock.id_sede == Sede.id_sede)
        .where(Stock.id_variante == id_variante, Sede.id_sede != id_sede_excluida,
               Sede.activo.is_(True), libre > 0)
        .order_by(Sede.id_sede)
    ).all()
    return [{"id_sede": f.id_sede, "nombre": f.nombre, "disponible": f.disponible} for f in filas]


def conflicto_existencias(variante, id_sede, solicitado, disponible_actual):
    return {
        "id_variante": variante.id_variante,
        "sku": variante.sku,
        "solicitado": solicitado,
        "disponible": max(disponible_actual, 0),
        "otras_sedes": otras_sedes_con_existencias(variante.id_variante, id_sede),
    }


def registrar_movimiento(*, id_sede, variante, tipo, cantidad, usuario=None,
                         tipo_referencia=None, id_referencia=None, observacion=None):
    """Aplica una variación de existencias y deja su fila en movimiento_inventario."""
    stock = obtener_stock(id_sede, variante.id_variante, crear=True)
    anterior = stock.cantidad
    nuevo = anterior + cantidad
    if nuevo < 0:
        raise ErrorApi(409, "Existencias insuficientes",
                       conflictos=[conflicto_existencias(variante, id_sede, -cantidad, anterior)])
    stock.cantidad = nuevo
    movimiento = MovimientoInventario(
        id_variante=variante.id_variante, id_sede=id_sede, tipo=tipo, cantidad=cantidad,
        id_usuario=usuario.id_usuario if usuario else None,
        tipo_referencia=tipo_referencia, id_referencia=id_referencia, observacion=observacion,
    )
    db.session.add(movimiento)
    db.session.flush()
    return {"movimiento": movimiento, "stock_anterior": anterior, "stock_actual": nuevo}


def registrar_ingreso(datos, usuario):
    exigir(datos, "id_sede")
    id_sede = a_entero(datos["id_sede"], "id_sede", 1)
    verificar_sede(usuario, id_sede)
    sede = obtener_sede_activa(id_sede)
    observacion = texto(datos, "observacion", 200)
    resultados = []
    for id_variante, cantidad in consolidar_items(lista_items(datos)).items():
        resultados.append(registrar_movimiento(
            id_sede=id_sede, variante=obtener_variante_activa(id_variante),
            tipo=TipoMovimiento.INGRESO, cantidad=cantidad, usuario=usuario,
            tipo_referencia="INGRESO", observacion=observacion,
        ))
    db.session.commit()
    return sede, resultados


def registrar_ajuste(datos, usuario):
    """Conteo físico: items [{id_variante, cantidad_contada}] fija la cantidad real."""
    exigir(datos, "id_sede", "observacion")
    id_sede = a_entero(datos["id_sede"], "id_sede", 1)
    sede = obtener_sede_activa(id_sede)
    observacion = texto(datos, "observacion", 200, obligatorio=True)
    resultados = []
    for i, item in enumerate(lista_items(datos)):
        variante = obtener_variante_activa(a_entero(item.get("id_variante"), f"items[{i}].id_variante", 1))
        contada = a_entero(item.get("cantidad_contada"), f"items[{i}].cantidad_contada", 0)
        stock = obtener_stock(id_sede, variante.id_variante, crear=True)
        if contada < stock.cantidad_reservada:
            raise ErrorApi(409, f"La cantidad de {variante.sku} no puede quedar por debajo de "
                                f"las {stock.cantidad_reservada} unidades reservadas")
        delta = contada - stock.cantidad
        if delta != 0:
            resultados.append(registrar_movimiento(
                id_sede=id_sede, variante=variante, tipo=TipoMovimiento.AJUSTE, cantidad=delta,
                usuario=usuario, tipo_referencia="AJUSTE", observacion=observacion,
            ))
    db.session.commit()
    return sede, resultados
