"""
modelos.py
Modelos Flask-SQLAlchemy de Solsticio. Reflejan database/solsticio_schema.sql:
ese script crea la base, estos modelos solo la mapean.
"""
import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    true,
    false,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

TinyInt = SmallInteger().with_variant(mysql.TINYINT(), "mysql")
Dinero = Numeric(12, 2)


# =====================================================================
# ENUMS
# =====================================================================

class Genero(str, enum.Enum):
    HOMBRE = "HOMBRE"
    MUJER = "MUJER"
    UNISEX = "UNISEX"
    INFANTIL = "INFANTIL"


class TipoDocumento(str, enum.Enum):
    CC = "CC"
    CE = "CE"
    NIT = "NIT"
    PASAPORTE = "PASAPORTE"


class TipoMovimiento(str, enum.Enum):
    INGRESO = "INGRESO"
    VENTA = "VENTA"
    DEVOLUCION = "DEVOLUCION"
    TRASLADO_SALIDA = "TRASLADO_SALIDA"
    TRASLADO_ENTRADA = "TRASLADO_ENTRADA"
    AJUSTE = "AJUSTE"


class EstadoTraslado(str, enum.Enum):
    SOLICITADO = "SOLICITADO"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDO = "RECIBIDO"
    CANCELADO = "CANCELADO"


class Canal(str, enum.Enum):
    WEB = "WEB"
    TIENDA = "TIENDA"


class TipoEntrega(str, enum.Enum):
    INMEDIATA = "INMEDIATA"
    RECOGER_EN_TIENDA = "RECOGER_EN_TIENDA"
    DOMICILIO = "DOMICILIO"


class EstadoPedido(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    PREPARANDO = "PREPARANDO"
    ENVIADO = "ENVIADO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class EstadoEnvio(str, enum.Enum):
    PREPARANDO = "PREPARANDO"
    DESPACHADO = "DESPACHADO"
    ENTREGADO = "ENTREGADO"
    DEVUELTO = "DEVUELTO"


class TipoMetodoPago(str, enum.Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"


class EstadoPago(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    REVERSADO = "REVERSADO"


class EstadoDian(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    VALIDADA = "VALIDADA"
    RECHAZADA = "RECHAZADA"


class TipoDevolucion(str, enum.Enum):
    CAMBIO = "CAMBIO"
    DEVOLUCION = "DEVOLUCION"


class EstadoDevolucion(str, enum.Enum):
    SOLICITADA = "SOLICITADA"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    COMPLETADA = "COMPLETADA"


# =====================================================================
# MODULO: CATALOGO
# =====================================================================

class Categoria(db.Model):
    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true())

    productos: Mapped[list["Producto"]] = relationship(back_populates="categoria")


class Producto(db.Model):
    __tablename__ = "producto"
    __table_args__ = (CheckConstraint("precio_base > 0", name="chk_producto_precio"),)

    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_categoria: Mapped[int] = mapped_column(
        ForeignKey("categoria.id_categoria", name="fk_producto_categoria", ondelete="RESTRICT")
    )
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    precio_base: Mapped[Decimal] = mapped_column(Dinero)
    genero: Mapped[Genero] = mapped_column(
        Enum(Genero, name="genero"), server_default=Genero.UNISEX.value
    )
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true())
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    categoria: Mapped["Categoria"] = relationship(back_populates="productos")
    variantes: Mapped[list["Variante"]] = relationship(back_populates="producto")
    imagenes: Mapped[list["ImagenProducto"]] = relationship(
        back_populates="producto", order_by="ImagenProducto.orden"
    )


class Talla(db.Model):
    __tablename__ = "talla"

    id_talla: Mapped[int] = mapped_column(Integer, primary_key=True)
    valor: Mapped[str] = mapped_column(String(10), unique=True)
    orden: Mapped[int] = mapped_column(TinyInt, server_default=text("1"))


class Color(db.Model):
    __tablename__ = "color"

    id_color: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    codigo_hex: Mapped[Optional[str]] = mapped_column(CHAR(7))


class Variante(db.Model):
    """Unidad mínima inventariable (SKU). Portadora del código QR de etiqueta."""
    __tablename__ = "variante"
    __table_args__ = (
        UniqueConstraint("id_producto", "id_talla", "id_color", name="uq_variante_combinacion"),
    )

    id_variante: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto", name="fk_variante_producto", ondelete="RESTRICT")
    )
    id_talla: Mapped[int] = mapped_column(
        ForeignKey("talla.id_talla", name="fk_variante_talla", ondelete="RESTRICT")
    )
    id_color: Mapped[int] = mapped_column(
        ForeignKey("color.id_color", name="fk_variante_color", ondelete="RESTRICT")
    )
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    codigo_qr: Mapped[str] = mapped_column(String(80), unique=True)
    precio_adicional: Mapped[Decimal] = mapped_column(Dinero, server_default=text("0"))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true())

    producto: Mapped["Producto"] = relationship(back_populates="variantes")
    talla: Mapped["Talla"] = relationship()
    color: Mapped["Color"] = relationship()
    stocks: Mapped[list["Stock"]] = relationship(back_populates="variante")


class ImagenProducto(db.Model):
    __tablename__ = "imagen_producto"

    id_imagen: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto", name="fk_imagen_producto", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(String(255))
    orden: Mapped[int] = mapped_column(TinyInt, server_default=text("1"))
    es_principal: Mapped[bool] = mapped_column(Boolean, server_default=false())

    producto: Mapped["Producto"] = relationship(back_populates="imagenes")


# =====================================================================
# MODULO: SEDES Y USUARIOS
# =====================================================================

class Sede(db.Model):
    __tablename__ = "sede"

    id_sede: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    direccion: Mapped[str] = mapped_column(String(150))
    ciudad: Mapped[str] = mapped_column(String(60), server_default="Bogota")
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true())


class Rol(db.Model):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(150))


class Usuario(db.Model):
    """Personal con acceso autenticado. id_sede es nulo para el administrador global."""
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_rol: Mapped[int] = mapped_column(
        ForeignKey("rol.id_rol", name="fk_usuario_rol", ondelete="RESTRICT")
    )
    id_sede: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_usuario_sede", ondelete="RESTRICT")
    )
    documento: Mapped[str] = mapped_column(String(20), unique=True)
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    hash_password: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true())
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rol: Mapped["Rol"] = relationship()
    sede: Mapped[Optional["Sede"]] = relationship()
    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="usuario")


class Cliente(db.Model):
    """Comprador. Separado de usuario: el cliente de mostrador no necesita cuenta."""
    __tablename__ = "cliente"

    id_cliente: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id_usuario", name="fk_cliente_usuario", ondelete="RESTRICT"),
        unique=True,
    )
    tipo_documento: Mapped[TipoDocumento] = mapped_column(
        Enum(TipoDocumento, name="tipo_documento"), server_default=TipoDocumento.CC.value
    )
    numero_documento: Mapped[str] = mapped_column(String(20), unique=True)
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[Optional[str]] = mapped_column(String(80))
    email: Mapped[Optional[str]] = mapped_column(String(120))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    direccion: Mapped[Optional[str]] = mapped_column(String(150))

    usuario: Mapped[Optional["Usuario"]] = relationship(back_populates="cliente")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")


# =====================================================================
# MODULO: INVENTARIO
# =====================================================================

class Stock(db.Model):
    """Existencias por sede y variante. Nunca modificar cantidad sin su MovimientoInventario."""
    __tablename__ = "stock"
    __table_args__ = (
        CheckConstraint("cantidad >= 0", name="chk_stock_cantidad"),
        CheckConstraint("cantidad_reservada >= 0", name="chk_stock_reservada"),
    )

    id_sede: Mapped[int] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_stock_sede", ondelete="RESTRICT"), primary_key=True
    )
    id_variante: Mapped[int] = mapped_column(
        ForeignKey("variante.id_variante", name="fk_stock_variante", ondelete="RESTRICT"),
        primary_key=True,
    )
    cantidad: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cantidad_reservada: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    stock_minimo: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    sede: Mapped["Sede"] = relationship()
    variante: Mapped["Variante"] = relationship(back_populates="stocks")


class MovimientoInventario(db.Model):
    __tablename__ = "movimiento_inventario"
    __table_args__ = (
        Index("idx_movimiento_fecha", "fecha"),
        Index("idx_movimiento_variante_sede", "id_variante", "id_sede"),
    )

    id_movimiento: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_variante: Mapped[int] = mapped_column(
        ForeignKey("variante.id_variante", name="fk_movimiento_variante", ondelete="RESTRICT")
    )
    id_sede: Mapped[int] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_movimiento_sede", ondelete="RESTRICT")
    )
    tipo: Mapped[TipoMovimiento] = mapped_column(Enum(TipoMovimiento, name="tipo_movimiento"))
    cantidad: Mapped[int] = mapped_column(Integer)
    id_usuario: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id_usuario", name="fk_movimiento_usuario", ondelete="RESTRICT")
    )
    tipo_referencia: Mapped[Optional[str]] = mapped_column(String(30))
    id_referencia: Mapped[Optional[int]] = mapped_column(BigInteger)
    observacion: Mapped[Optional[str]] = mapped_column(String(200))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    variante: Mapped["Variante"] = relationship()
    sede: Mapped["Sede"] = relationship()
    usuario: Mapped[Optional["Usuario"]] = relationship()


class Traslado(db.Model):
    __tablename__ = "traslado"
    __table_args__ = (
        CheckConstraint("id_sede_origen <> id_sede_destino", name="chk_traslado_sedes"),
    )

    id_traslado: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sede_origen: Mapped[int] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_traslado_origen", ondelete="RESTRICT")
    )
    id_sede_destino: Mapped[int] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_traslado_destino", ondelete="RESTRICT")
    )
    id_usuario_solicita: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario", name="fk_traslado_solicita", ondelete="RESTRICT")
    )
    id_usuario_recibe: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id_usuario", name="fk_traslado_recibe", ondelete="RESTRICT")
    )
    estado: Mapped[EstadoTraslado] = mapped_column(
        Enum(EstadoTraslado, name="estado_traslado"),
        server_default=EstadoTraslado.SOLICITADO.value,
    )
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_recepcion: Mapped[Optional[datetime]] = mapped_column(DateTime)

    sede_origen: Mapped["Sede"] = relationship(foreign_keys=[id_sede_origen])
    sede_destino: Mapped["Sede"] = relationship(foreign_keys=[id_sede_destino])
    usuario_solicita: Mapped["Usuario"] = relationship(foreign_keys=[id_usuario_solicita])
    usuario_recibe: Mapped[Optional["Usuario"]] = relationship(foreign_keys=[id_usuario_recibe])
    detalles: Mapped[list["DetalleTraslado"]] = relationship(back_populates="traslado")


class DetalleTraslado(db.Model):
    __tablename__ = "detalle_traslado"
    __table_args__ = (CheckConstraint("cantidad > 0", name="chk_detraslado_cantidad"),)

    id_detalle_traslado: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_traslado: Mapped[int] = mapped_column(
        ForeignKey("traslado.id_traslado", name="fk_detraslado_traslado", ondelete="CASCADE")
    )
    id_variante: Mapped[int] = mapped_column(
        ForeignKey("variante.id_variante", name="fk_detraslado_variante", ondelete="RESTRICT")
    )
    cantidad: Mapped[int] = mapped_column(Integer)

    traslado: Mapped["Traslado"] = relationship(back_populates="detalles")
    variante: Mapped["Variante"] = relationship()


# =====================================================================
# MODULO: VENTAS
# =====================================================================

class Pedido(db.Model):
    """Venta unificada: canal WEB (id_usuario nulo) o TIENDA (id_cliente puede ser nulo)."""
    __tablename__ = "pedido"
    __table_args__ = (
        Index("idx_pedido_fecha", "fecha_pedido"),
        Index("idx_pedido_sede_fecha", "id_sede", "fecha_pedido"),
    )

    id_pedido: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_cliente: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cliente.id_cliente", name="fk_pedido_cliente", ondelete="RESTRICT")
    )
    id_sede: Mapped[int] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_pedido_sede", ondelete="RESTRICT")
    )
    id_usuario: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id_usuario", name="fk_pedido_usuario", ondelete="RESTRICT")
    )
    canal: Mapped[Canal] = mapped_column(Enum(Canal, name="canal"))
    tipo_entrega: Mapped[TipoEntrega] = mapped_column(
        Enum(TipoEntrega, name="tipo_entrega"), server_default=TipoEntrega.INMEDIATA.value
    )
    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido, name="estado_pedido"), server_default=EstadoPedido.PENDIENTE.value
    )
    codigo_qr: Mapped[str] = mapped_column(String(80), unique=True)
    subtotal: Mapped[Decimal] = mapped_column(Dinero, server_default=text("0"))
    impuestos: Mapped[Decimal] = mapped_column(Dinero, server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Dinero, server_default=text("0"))
    fecha_pedido: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="pedidos")
    sede: Mapped["Sede"] = relationship()
    usuario: Mapped[Optional["Usuario"]] = relationship()
    detalles: Mapped[list["DetallePedido"]] = relationship(back_populates="pedido")
    envio: Mapped[Optional["Envio"]] = relationship(back_populates="pedido")
    pagos: Mapped[list["Pago"]] = relationship(back_populates="pedido")
    factura: Mapped[Optional["Factura"]] = relationship(back_populates="pedido")
    devoluciones: Mapped[list["Devolucion"]] = relationship(back_populates="pedido")


class DetallePedido(db.Model):
    """precio_unitario es histórico: se copia al vender y nunca se recalcula."""
    __tablename__ = "detalle_pedido"
    __table_args__ = (CheckConstraint("cantidad > 0", name="chk_detpedido_cantidad"),)

    id_detalle_pedido: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido", name="fk_detpedido_pedido", ondelete="CASCADE")
    )
    id_variante: Mapped[int] = mapped_column(
        ForeignKey("variante.id_variante", name="fk_detpedido_variante", ondelete="RESTRICT")
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Dinero)
    subtotal_linea: Mapped[Decimal] = mapped_column(Dinero)

    pedido: Mapped["Pedido"] = relationship(back_populates="detalles")
    variante: Mapped["Variante"] = relationship()


class Envio(db.Model):
    __tablename__ = "envio"

    id_envio: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido", name="fk_envio_pedido", ondelete="CASCADE"), unique=True
    )
    direccion: Mapped[str] = mapped_column(String(150))
    ciudad: Mapped[str] = mapped_column(String(60))
    destinatario: Mapped[str] = mapped_column(String(120))
    telefono_contacto: Mapped[str] = mapped_column(String(20))
    transportadora: Mapped[Optional[str]] = mapped_column(String(60))
    numero_guia: Mapped[Optional[str]] = mapped_column(String(60))
    estado: Mapped[EstadoEnvio] = mapped_column(
        Enum(EstadoEnvio, name="estado_envio"), server_default=EstadoEnvio.PREPARANDO.value
    )
    fecha_despacho: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fecha_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime)

    pedido: Mapped["Pedido"] = relationship(back_populates="envio")


# =====================================================================
# MODULO: PAGOS (pasarela simulada)
# =====================================================================

class MetodoPago(db.Model):
    __tablename__ = "metodo_pago"

    id_metodo_pago: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    tipo: Mapped[TipoMetodoPago] = mapped_column(Enum(TipoMetodoPago, name="tipo_metodo_pago"))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true())


class Pago(db.Model):
    __tablename__ = "pago"
    __table_args__ = (CheckConstraint("monto > 0", name="chk_pago_monto"),)

    id_pago: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido", name="fk_pago_pedido", ondelete="RESTRICT")
    )
    id_metodo_pago: Mapped[int] = mapped_column(
        ForeignKey("metodo_pago.id_metodo_pago", name="fk_pago_metodo", ondelete="RESTRICT")
    )
    monto: Mapped[Decimal] = mapped_column(Dinero)
    estado: Mapped[EstadoPago] = mapped_column(
        Enum(EstadoPago, name="estado_pago"), server_default=EstadoPago.PENDIENTE.value
    )
    referencia_transaccion: Mapped[Optional[str]] = mapped_column(String(80), unique=True)
    fecha_pago: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pedido: Mapped["Pedido"] = relationship(back_populates="pagos")
    metodo_pago: Mapped["MetodoPago"] = relationship()


# =====================================================================
# MODULO: FACTURACION ELECTRONICA
# =====================================================================

class Factura(db.Model):
    __tablename__ = "factura"

    id_factura: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido", name="fk_factura_pedido", ondelete="RESTRICT"), unique=True
    )
    numero_factura: Mapped[str] = mapped_column(String(30), unique=True)
    prefijo: Mapped[str] = mapped_column(String(10))
    cufe: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    estado_dian: Mapped[EstadoDian] = mapped_column(
        Enum(EstadoDian, name="estado_dian"), server_default=EstadoDian.PENDIENTE.value
    )
    subtotal: Mapped[Decimal] = mapped_column(Dinero)
    iva: Mapped[Decimal] = mapped_column(Dinero)
    total: Mapped[Decimal] = mapped_column(Dinero)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_validacion: Mapped[Optional[datetime]] = mapped_column(DateTime)
    url_xml: Mapped[Optional[str]] = mapped_column(String(255))

    pedido: Mapped["Pedido"] = relationship(back_populates="factura")
    notas_credito: Mapped[list["NotaCredito"]] = relationship(back_populates="factura")


# =====================================================================
# MODULO: DEVOLUCIONES Y CAMBIOS
# =====================================================================

class Devolucion(db.Model):
    __tablename__ = "devolucion"

    id_devolucion: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido", name="fk_devolucion_pedido", ondelete="RESTRICT")
    )
    id_sede: Mapped[int] = mapped_column(
        ForeignKey("sede.id_sede", name="fk_devolucion_sede", ondelete="RESTRICT")
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario", name="fk_devolucion_usuario", ondelete="RESTRICT")
    )
    tipo: Mapped[TipoDevolucion] = mapped_column(Enum(TipoDevolucion, name="tipo_devolucion"))
    motivo: Mapped[str] = mapped_column(String(200))
    estado: Mapped[EstadoDevolucion] = mapped_column(
        Enum(EstadoDevolucion, name="estado_devolucion"),
        server_default=EstadoDevolucion.SOLICITADA.value,
    )
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pedido: Mapped["Pedido"] = relationship(back_populates="devoluciones")
    sede: Mapped["Sede"] = relationship()
    usuario: Mapped["Usuario"] = relationship()
    detalles: Mapped[list["DetalleDevolucion"]] = relationship(back_populates="devolucion")
    nota_credito: Mapped[Optional["NotaCredito"]] = relationship(back_populates="devolucion")


class DetalleDevolucion(db.Model):
    __tablename__ = "detalle_devolucion"
    __table_args__ = (CheckConstraint("cantidad > 0", name="chk_detdev_cantidad"),)

    id_detalle_devolucion: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_devolucion: Mapped[int] = mapped_column(
        ForeignKey("devolucion.id_devolucion", name="fk_detdev_devolucion", ondelete="CASCADE")
    )
    id_detalle_pedido: Mapped[int] = mapped_column(
        ForeignKey(
            "detalle_pedido.id_detalle_pedido", name="fk_detdev_detpedido", ondelete="RESTRICT"
        )
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    id_variante_cambio: Mapped[Optional[int]] = mapped_column(
        ForeignKey("variante.id_variante", name="fk_detdev_variante", ondelete="RESTRICT")
    )

    devolucion: Mapped["Devolucion"] = relationship(back_populates="detalles")
    detalle_pedido: Mapped["DetallePedido"] = relationship()
    variante_cambio: Mapped[Optional["Variante"]] = relationship()


class NotaCredito(db.Model):
    __tablename__ = "nota_credito"

    id_nota_credito: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_devolucion: Mapped[int] = mapped_column(
        ForeignKey("devolucion.id_devolucion", name="fk_nota_devolucion", ondelete="RESTRICT"),
        unique=True,
    )
    id_factura: Mapped[int] = mapped_column(
        ForeignKey("factura.id_factura", name="fk_nota_factura", ondelete="RESTRICT")
    )
    numero_nota: Mapped[str] = mapped_column(String(30), unique=True)
    cude: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    monto: Mapped[Decimal] = mapped_column(Dinero)
    estado_dian: Mapped[EstadoDian] = mapped_column(
        Enum(EstadoDian, name="estado_dian"), server_default=EstadoDian.PENDIENTE.value
    )
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    devolucion: Mapped["Devolucion"] = relationship(back_populates="nota_credito")
    factura: Mapped["Factura"] = relationship(back_populates="notas_credito")
