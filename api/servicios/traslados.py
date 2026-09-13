"""
traslados.py
Movimiento de mercancía entre sedes. Genera dos movimientos de inventario:
TRASLADO_SALIDA al despachar y TRASLADO_ENTRADA al recibir.
"""
from datetime import datetime

from api.errores import ErrorApi
from api.modelos import DetalleTraslado, EstadoTraslado, TipoMovimiento, Traslado, db
from api.seguridad import verificar_sede
from api.servicios.comun import obtener_sede_activa, obtener_variante_activa
from api.servicios.inventario import (
    conflicto_existencias, disponible, obtener_stock, registrar_movimiento,
)
from api.validacion import a_entero, consolidar_items, exigir, lista_items


def crear_traslado(datos, usuario):
    exigir(datos, "id_sede_origen", "id_sede_destino")
    origen = obtener_sede_activa(a_entero(datos["id_sede_origen"], "id_sede_origen", 1))
    destino = obtener_sede_activa(a_entero(datos["id_sede_destino"], "id_sede_destino", 1))
    if origen.id_sede == destino.id_sede:
        raise ErrorApi(422, "La sede de origen y la de destino no pueden ser la misma")

    cantidades = consolidar_items(lista_items(datos))
    disponibles, conflictos = {}, []
    for id_variante, cantidad in cantidades.items():
        variante = obtener_variante_activa(id_variante)
        libre = disponible(obtener_stock(origen.id_sede, id_variante))
        disponibles[id_variante] = libre
        if libre < cantidad:
            conflictos.append(conflicto_existencias(variante, origen.id_sede, cantidad, libre))
    if conflictos:
        raise ErrorApi(409, "Existencias insuficientes en la sede de origen", conflictos=conflictos)

    traslado = Traslado(id_sede_origen=origen.id_sede, id_sede_destino=destino.id_sede,
                        id_usuario_solicita=usuario.id_usuario, estado=EstadoTraslado.SOLICITADO)
    db.session.add(traslado)
    db.session.flush()
    for id_variante, cantidad in cantidades.items():
        db.session.add(DetalleTraslado(id_traslado=traslado.id_traslado,
                                       id_variante=id_variante, cantidad=cantidad))
    db.session.commit()
    return traslado, disponibles


def despachar_traslado(traslado, usuario):
    if traslado.estado != EstadoTraslado.SOLICITADO:
        raise ErrorApi(409, f"Solo se despachan traslados SOLICITADOS (estado actual: {traslado.estado.value})")
    verificar_sede(usuario, traslado.id_sede_origen)
    for detalle in traslado.detalles:
        libre = disponible(obtener_stock(traslado.id_sede_origen, detalle.id_variante))
        if libre < detalle.cantidad:
            raise ErrorApi(409, "Existencias insuficientes en la sede de origen", conflictos=[
                conflicto_existencias(detalle.variante, traslado.id_sede_origen, detalle.cantidad, libre)])
    resultados = [
        registrar_movimiento(
            id_sede=traslado.id_sede_origen, variante=d.variante,
            tipo=TipoMovimiento.TRASLADO_SALIDA, cantidad=-d.cantidad, usuario=usuario,
            tipo_referencia="TRASLADO", id_referencia=traslado.id_traslado,
        )
        for d in traslado.detalles
    ]
    traslado.estado = EstadoTraslado.EN_TRANSITO
    db.session.commit()
    return resultados


def recibir_traslado(traslado, usuario):
    if traslado.estado != EstadoTraslado.EN_TRANSITO:
        raise ErrorApi(409, f"Solo se reciben traslados EN_TRANSITO (estado actual: {traslado.estado.value})")
    verificar_sede(usuario, traslado.id_sede_destino)
    resultados = [
        registrar_movimiento(
            id_sede=traslado.id_sede_destino, variante=d.variante,
            tipo=TipoMovimiento.TRASLADO_ENTRADA, cantidad=d.cantidad, usuario=usuario,
            tipo_referencia="TRASLADO", id_referencia=traslado.id_traslado,
        )
        for d in traslado.detalles
    ]
    traslado.estado = EstadoTraslado.RECIBIDO
    traslado.id_usuario_recibe = usuario.id_usuario
    traslado.fecha_recepcion = datetime.now().replace(microsecond=0)
    db.session.commit()
    return resultados
