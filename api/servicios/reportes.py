"""
reportes.py
Caso de uso 2.3.9, analítica y reportes del administrador: ventas por periodo,
prendas más vendidas y rotación de inventario. Todo se calcula en MySQL.

- Una venta cuenta cuando el pedido quedó pagado (PAGADO, PREPARANDO, ENVIADO o
  ENTREGADO). Los pendientes y cancelados no son ingresos.
- Los montos salen de los totales históricos del pedido y de sus líneas, nunca del
  precio actual del catálogo.
- Las devoluciones se restan por el monto de sus notas crédito, en el periodo en que
  se emitieron.
- La rotación usa movimiento_inventario, que registra toda variación de existencias.
"""
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import case, func, select

from api.modelos import (
    Canal, Categoria, DetallePedido, Devolucion, EstadoDevolucion, EstadoPedido,
    MovimientoInventario, NotaCredito, Pedido, Producto, Stock, Talla, TipoMovimiento,
    Variante, db,
)

ESTADOS_VENDIDOS = (
    EstadoPedido.PAGADO, EstadoPedido.PREPARANDO, EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO,
)

# Rotación = unidades vendidas / existencias promedio del periodo.
UMBRAL_ROTACION_ALTA = Decimal("1")
UMBRAL_ROTACION_MEDIA = Decimal("0.3")


def _limites(desde, hasta):
    """El periodo incluye los dos días: [desde 00:00, hasta + 1 día 00:00)."""
    return datetime.combine(desde, time.min), datetime.combine(hasta + timedelta(days=1), time.min)


def _pesos(valor):
    return Decimal(valor or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _condiciones_venta(desde, hasta, id_sede=None, canal=None):
    inicio, fin = _limites(desde, hasta)
    condiciones = [
        Pedido.estado.in_(ESTADOS_VENDIDOS),
        Pedido.fecha_pedido >= inicio,
        Pedido.fecha_pedido < fin,
    ]
    if id_sede:
        condiciones.append(Pedido.id_sede == id_sede)
    if canal:
        condiciones.append(Pedido.canal == canal)
    return condiciones


def _periodo(desde, hasta):
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": (hasta - desde).days + 1}


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------

def ventas(desde: date, hasta: date, id_sede=None, canal: Canal | None = None):
    condiciones = _condiciones_venta(desde, hasta, id_sede, canal)

    pedidos, brutos = db.session.execute(
        select(func.count(Pedido.id_pedido), func.coalesce(func.sum(Pedido.total), 0)).where(*condiciones)
    ).one()
    unidades = db.session.scalar(
        select(func.coalesce(func.sum(DetallePedido.cantidad), 0))
        .join(Pedido, Pedido.id_pedido == DetallePedido.id_pedido)
        .where(*condiciones)
    )

    # Devoluciones: notas crédito emitidas en el periodo sobre ventas de la misma sede y canal.
    inicio, fin = _limites(desde, hasta)
    filtro_devoluciones = [
        Devolucion.estado == EstadoDevolucion.COMPLETADA,
        NotaCredito.fecha_emision >= inicio,
        NotaCredito.fecha_emision < fin,
    ]
    if id_sede:
        filtro_devoluciones.append(Pedido.id_sede == id_sede)
    if canal:
        filtro_devoluciones.append(Pedido.canal == canal)
    devoluciones, devuelto = db.session.execute(
        select(func.count(Devolucion.id_devolucion), func.coalesce(func.sum(NotaCredito.monto), 0))
        .join(NotaCredito, NotaCredito.id_devolucion == Devolucion.id_devolucion)
        .join(Pedido, Pedido.id_pedido == Devolucion.id_pedido)
        .where(*filtro_devoluciones)
    ).one()

    filas_canal = {
        fila.canal: fila for fila in db.session.execute(
            select(Pedido.canal, func.count(Pedido.id_pedido).label("pedidos"),
                   func.coalesce(func.sum(Pedido.total), 0).label("ingresos"))
            .where(*condiciones).group_by(Pedido.canal)
        )
    }
    canales = [canal] if canal else list(Canal)
    por_canal = [
        {"canal": c.value,
         "pedidos": filas_canal[c].pedidos if c in filas_canal else 0,
         "ingresos": _pesos(filas_canal[c].ingresos if c in filas_canal else 0)}
        for c in canales
    ]

    dia = func.date(Pedido.fecha_pedido)
    por_dia = [
        {"fecha": str(fila.fecha), "pedidos": fila.pedidos, "ingresos": _pesos(fila.ingresos)}
        for fila in db.session.execute(
            select(dia.label("fecha"), func.count(Pedido.id_pedido).label("pedidos"),
                   func.sum(Pedido.total).label("ingresos"))
            .where(*condiciones).group_by(dia).order_by(dia)
        )
    ]

    brutos = _pesos(brutos)
    return {
        "periodo": _periodo(desde, hasta),
        "filtros": {"id_sede": id_sede, "canal": canal.value if canal else None},
        "resumen": {
            "total_pedidos": pedidos,
            "unidades_vendidas": int(unidades),
            "ingresos_brutos": brutos,
            "devoluciones": devoluciones,
            "monto_devuelto": _pesos(devuelto),
            "ingresos_netos": brutos - _pesos(devuelto),
            "ticket_promedio": _pesos(brutos / pedidos) if pedidos else Decimal("0"),
        },
        "por_canal": por_canal,
        "por_dia": por_dia,
    }


# ---------------------------------------------------------------------------
# Prendas más vendidas
# ---------------------------------------------------------------------------

def productos_mas_vendidos(desde: date, hasta: date, limite=5, id_sede=None):
    condiciones = _condiciones_venta(desde, hasta, id_sede)
    unidades = func.sum(DetallePedido.cantidad).label("unidades")
    ingresos = func.sum(DetallePedido.subtotal_linea).label("ingresos")
    filas = db.session.execute(
        select(Producto.id_producto, Producto.nombre, Categoria.nombre.label("categoria"), unidades, ingresos)
        .select_from(DetallePedido)
        .join(Pedido, Pedido.id_pedido == DetallePedido.id_pedido)
        .join(Variante, Variante.id_variante == DetallePedido.id_variante)
        .join(Producto, Producto.id_producto == Variante.id_producto)
        .join(Categoria, Categoria.id_categoria == Producto.id_categoria)
        .where(*condiciones)
        .group_by(Producto.id_producto, Producto.nombre, Categoria.nombre)
        .order_by(unidades.desc(), ingresos.desc(), Producto.id_producto)
        .limit(limite)
    ).all()

    # Talla más vendida de cada prenda del ranking (en empate, la de menor orden).
    tallas = {}
    if filas:
        por_talla = func.sum(DetallePedido.cantidad).label("unidades")
        for fila in db.session.execute(
            select(Variante.id_producto, Talla.valor, por_talla)
            .select_from(DetallePedido)
            .join(Pedido, Pedido.id_pedido == DetallePedido.id_pedido)
            .join(Variante, Variante.id_variante == DetallePedido.id_variante)
            .join(Talla, Talla.id_talla == Variante.id_talla)
            .where(*condiciones, Variante.id_producto.in_([f.id_producto for f in filas]))
            .group_by(Variante.id_producto, Talla.valor, Talla.orden)
            .order_by(Variante.id_producto, por_talla.desc(), Talla.orden)
        ):
            tallas.setdefault(fila.id_producto, fila.valor)

    return {
        "periodo": _periodo(desde, hasta),
        "filtros": {"id_sede": id_sede, "limite": limite},
        "items": [
            {"posicion": i, "id_producto": f.id_producto, "producto": f.nombre, "categoria": f.categoria,
             "unidades_vendidas": int(f.unidades), "ingresos": _pesos(f.ingresos),
             "talla_mas_vendida": tallas.get(f.id_producto)}
            for i, f in enumerate(filas, start=1)
        ],
    }


# ---------------------------------------------------------------------------
# Rotación de inventario
# ---------------------------------------------------------------------------

def _clasificar(vendidas, indice):
    if not vendidas:
        return "SIN_VENTAS"
    if indice is None or indice >= UMBRAL_ROTACION_ALTA:
        return "ALTA"
    if indice >= UMBRAL_ROTACION_MEDIA:
        return "MEDIA"
    return "BAJA"


def rotacion_inventario(desde: date, hasta: date, id_sede=None):
    """
    Por prenda, en el periodo:
      unidades_vendidas = salidas por VENTA (movimientos negativos)
      stock_final       = existencias actuales menos lo que se movió después de 'hasta'
      stock_inicial     = stock_final menos la variación neta dentro del periodo
      indice_rotacion   = unidades_vendidas / promedio(stock_inicial, stock_final)
      dias_inventario   = días que alcanza el stock_final al ritmo de venta del periodo
    """
    inicio, fin = _limites(desde, hasta)
    dias = (hasta - desde).days + 1
    filtro_sede = [MovimientoInventario.id_sede == id_sede] if id_sede else []

    en_periodo = (MovimientoInventario.fecha >= inicio) & (MovimientoInventario.fecha < fin)
    vendidas = func.coalesce(func.sum(case(
        (en_periodo & (MovimientoInventario.tipo == TipoMovimiento.VENTA), -MovimientoInventario.cantidad),
        else_=0)), 0)
    devueltas = func.coalesce(func.sum(case(
        (en_periodo & (MovimientoInventario.tipo == TipoMovimiento.DEVOLUCION), MovimientoInventario.cantidad),
        else_=0)), 0)
    neto_periodo = func.coalesce(func.sum(case((en_periodo, MovimientoInventario.cantidad), else_=0)), 0)
    neto_despues = func.coalesce(func.sum(case(
        (MovimientoInventario.fecha >= fin, MovimientoInventario.cantidad), else_=0)), 0)
    movimientos = {
        fila.id_producto: fila for fila in db.session.execute(
            select(Variante.id_producto, vendidas.label("vendidas"), devueltas.label("devueltas"),
                   neto_periodo.label("neto_periodo"), neto_despues.label("neto_despues"))
            .join(Variante, Variante.id_variante == MovimientoInventario.id_variante)
            .where(MovimientoInventario.fecha >= inicio, *filtro_sede)
            .group_by(Variante.id_producto)
        )
    }

    filtro_stock = [Stock.id_sede == id_sede] if id_sede else []
    existencias = {
        fila.id_producto: int(fila.cantidad) for fila in db.session.execute(
            select(Variante.id_producto, func.sum(Stock.cantidad).label("cantidad"))
            .join(Variante, Variante.id_variante == Stock.id_variante)
            .where(*filtro_stock).group_by(Variante.id_producto)
        )
    }

    ids = set(movimientos) | {i for i, c in existencias.items() if c}
    productos = {
        p.id_producto: p for p in db.session.execute(
            select(Producto.id_producto, Producto.nombre, Categoria.nombre.label("categoria"))
            .join(Categoria, Categoria.id_categoria == Producto.id_categoria)
            .where(Producto.id_producto.in_(ids))
        )
    } if ids else {}

    items = []
    for id_producto in ids:
        mov = movimientos.get(id_producto)
        actual = existencias.get(id_producto, 0)
        unidades = int(mov.vendidas) if mov else 0
        final = actual - (int(mov.neto_despues) if mov else 0)
        inicial = final - (int(mov.neto_periodo) if mov else 0)
        promedio = Decimal(inicial + final) / 2
        indice = (Decimal(unidades) / promedio).quantize(Decimal("0.01")) if promedio > 0 else None
        ritmo = Decimal(unidades) / dias
        items.append({
            "id_producto": id_producto,
            "producto": productos[id_producto].nombre,
            "categoria": productos[id_producto].categoria,
            "unidades_vendidas": unidades,
            "unidades_devueltas": int(mov.devueltas) if mov else 0,
            "stock_inicial": inicial,
            "stock_final": final,
            "stock_actual": actual,
            "indice_rotacion": indice,
            "dias_inventario": int((final / ritmo).to_integral_value(ROUND_HALF_UP)) if unidades else None,
            "clasificacion": _clasificar(unidades, indice),
        })

    # Primero lo que más rota; las prendas sin ventas al final, las de más stock antes.
    items.sort(key=lambda i: (i["unidades_vendidas"] == 0,
                              -(i["indice_rotacion"] if i["indice_rotacion"] is not None else Decimal("999999")),
                              -i["unidades_vendidas"], -i["stock_final"], i["id_producto"]))

    resumen = {c: sum(1 for i in items if i["clasificacion"] == c)
               for c in ("ALTA", "MEDIA", "BAJA", "SIN_VENTAS")}
    return {
        "periodo": _periodo(desde, hasta),
        "filtros": {"id_sede": id_sede},
        "criterio": {
            "indice_rotacion": "unidades vendidas / existencias promedio del periodo",
            "ALTA": f">= {UMBRAL_ROTACION_ALTA}",
            "MEDIA": f">= {UMBRAL_ROTACION_MEDIA} y < {UMBRAL_ROTACION_ALTA}",
            "BAJA": f"< {UMBRAL_ROTACION_MEDIA}",
            "SIN_VENTAS": "sin ventas en el periodo",
        },
        "resumen": resumen,
        "items": items,
    }
