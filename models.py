"""
models.py
Modelos relacionales para Solsticio (multisede).
Diseñado con Flask-SQLAlchemy: funciona con SQLite (prototipo)
y es portable a MySQL/PostgreSQL cambiando solo la SQLALCHEMY_DATABASE_URI.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Sede(db.Model):
    __tablename__ = "sedes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)

    inventarios = db.relationship("Inventario", backref="sede", lazy=True)

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "ciudad": self.ciudad, "direccion": self.direccion}


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)

    productos = db.relationship("Producto", backref="categoria", lazy=True)

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre}


class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(40), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, default="")
    talla = db.Column(db.String(10), default="U")
    color = db.Column(db.String(40), default="")
    precio = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    imagen_url = db.Column(db.String(300), default="")
    qr_payload = db.Column(db.String(120), unique=True)  # contenido codificado en el QR
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    inventarios = db.relationship("Inventario", backref="producto", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, incluir_stock=False):
        data = {
            "id": self.id,
            "sku": self.sku,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "talla": self.talla,
            "color": self.color,
            "precio": self.precio,
            "categoria": self.categoria.nombre if self.categoria else None,
            "categoria_id": self.categoria_id,
            "imagen_url": self.imagen_url,
            "qr_payload": self.qr_payload,
            "activo": self.activo,
        }
        if incluir_stock:
            data["stock_por_sede"] = [
                {"sede_id": inv.sede_id, "sede": inv.sede.nombre, "cantidad": inv.cantidad}
                for inv in self.inventarios
            ]
            data["stock_total"] = sum(inv.cantidad for inv in self.inventarios)
        return data


class Inventario(db.Model):
    """Tabla puente: cuánto stock hay de un producto en una sede específica."""
    __tablename__ = "inventario"

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.UniqueConstraint("producto_id", "sede_id", name="uix_producto_sede"),)

    def to_dict(self):
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "sede_id": self.sede_id,
            "cantidad": self.cantidad,
        }


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    cliente_nombre = db.Column(db.String(150), nullable=False)
    cliente_documento = db.Column(db.String(30), default="")
    canal = db.Column(db.String(20), nullable=False, default="virtual")  # virtual | mostrador
    sede_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    estado = db.Column(db.String(20), default="pendiente")  # pendiente|pagado|entregado|cancelado
    total = db.Column(db.Float, default=0.0)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    sede = db.relationship("Sede")
    detalles = db.relationship("DetallePedido", backref="pedido", lazy=True, cascade="all, delete-orphan")
    factura = db.relationship("Factura", backref="pedido", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "cliente_nombre": self.cliente_nombre,
            "cliente_documento": self.cliente_documento,
            "canal": self.canal,
            "sede_id": self.sede_id,
            "sede": self.sede.nombre if self.sede else None,
            "estado": self.estado,
            "total": self.total,
            "creado_en": self.creado_en.isoformat(),
            "detalles": [d.to_dict() for d in self.detalles],
            "qr_pedido": f"SOLSTICIO-PEDIDO-{self.id}",
        }


class DetallePedido(db.Model):
    __tablename__ = "detalle_pedidos"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False)

    producto = db.relationship("Producto")

    def to_dict(self):
        return {
            "producto_id": self.producto_id,
            "producto": self.producto.nombre if self.producto else None,
            "cantidad": self.cantidad,
            "precio_unitario": self.precio_unitario,
            "subtotal": round(self.cantidad * self.precio_unitario, 2),
        }


class Factura(db.Model):
    """Representación simulada de la factura electrónica validada por la DIAN."""
    __tablename__ = "facturas"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False, unique=True)
    cufe = db.Column(db.String(120), unique=True, nullable=False)  # Código Único de Facturación Electrónica (simulado)
    estado_dian = db.Column(db.String(20), default="pendiente")  # pendiente|validada|rechazada
    fecha_generacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_validacion = db.Column(db.DateTime, nullable=True)
    xml_simulado = db.Column(db.Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "cufe": self.cufe,
            "estado_dian": self.estado_dian,
            "fecha_generacion": self.fecha_generacion.isoformat(),
            "fecha_validacion": self.fecha_validacion.isoformat() if self.fecha_validacion else None,
        }


class Usuario(db.Model):
    """Usuarios internos: trabajador o administrador (el cliente no requiere login para el catálogo)."""
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="trabajador")  # trabajador|administrador
    sede_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=True)

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "email": self.email, "rol": self.rol, "sede_id": self.sede_id}