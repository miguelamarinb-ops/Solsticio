"""
app.py
Backend Flask para Solsticio: API RESTful para productos, inventario multisede,
pedidos y facturación electrónica simulada (DIAN).
Preparado para desarrollo local (SQLite) y despliegue en Render (PostgreSQL + Gunicorn).
"""
import base64
import io
import os
import random
import string
from datetime import datetime

import qrcode
from flask import Flask, jsonify, request, send_from_directory

from models import db, Sede, Categoria, Producto, Inventario, Pedido, DetallePedido, Factura, Usuario

app = Flask(__name__)

# --- Configuración de base de datos ---
# En local: usa SQLite automáticamente (no requiere configurar nada).
# En Render: lee la variable de entorno DATABASE_URL que Render inyecta
# al conectar la base de datos PostgreSQL desde el dashboard.
database_url = os.environ.get("DATABASE_URL", "sqlite:///solsticio.db")

# Render entrega la URL con el prefijo "postgres://", pero SQLAlchemy 2.x
# requiere el prefijo "postgresql://". Se corrige automáticamente aquí.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_AS_ASCII"] = False  # para que tildes/ñ se vean bien en las respuestas

db.init_app(app)


# =========================================================
#  UTILIDADES
# =========================================================
def generar_cufe():
    """Simula el Código Único de Facturación Electrónica que asignaría la DIAN."""
    partes = "".join(random.choices(string.hexdigits.lower(), k=64))
    return f"CUFE-{partes[:40]}"


def error(msg, code=400):
    return jsonify({"error": msg}), code


# =========================================================
#  SEED DE DATOS (solo si la BD está vacía) — sedes y categorías base
# =========================================================
def seed_inicial():
    if Sede.query.first():
        return
    sedes = [
        Sede(nombre="Solsticio Chapinero", ciudad="Bogotá", direccion="Cra 13 #56-20"),
        Sede(nombre="Solsticio Usaquén", ciudad="Bogotá", direccion="Cl 119 #6-15"),
        Sede(nombre="Solsticio Centro Mayor", ciudad="Bogotá", direccion="Av. Boyacá #21-45"),
    ]
    categorias = [Categoria(nombre="Camisetas"), Categoria(nombre="Pantalones"),
                  Categoria(nombre="Chaquetas"), Categoria(nombre="Accesorios")]
    db.session.add_all(sedes + categorias)
    db.session.commit()


def inicializar_base_de_datos():
    """Crea las tablas y siembra datos base. Se llama tanto en local como en Render."""
    with app.app_context():
        db.create_all()
        seed_inicial()


# =========================================================
#  RUTAS - PRODUCTOS (CRUD)  /api/productos
# =========================================================
@app.route("/api/productos", methods=["GET"])
def listar_productos():
    """Lista el catálogo. Filtros opcionales: ?categoria_id=  ?sede_id= (solo activos con stock>0 en esa sede)."""
    query = Producto.query.filter_by(activo=True)

    categoria_id = request.args.get("categoria_id", type=int)
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)

    productos = query.all()
    sede_id = request.args.get("sede_id", type=int)

    resultado = []
    for p in productos:
        data = p.to_dict(incluir_stock=True)
        if sede_id:
            stock_sede = next((s["cantidad"] for s in data["stock_por_sede"] if s["sede_id"] == sede_id), 0)
            data["stock_en_sede_consultada"] = stock_sede
        resultado.append(data)

    return jsonify(resultado)


@app.route("/api/productos/<int:producto_id>", methods=["GET"])
def obtener_producto(producto_id):
    producto = Producto.query.get(producto_id)
    if not producto:
        return error("Producto no encontrado", 404)
    return jsonify(producto.to_dict(incluir_stock=True))


@app.route("/api/productos", methods=["POST"])
def crear_producto():
    """
    Crea un producto y (opcionalmente) su stock inicial por sede.
    Body esperado:
    {
      "sku": "CAM-001", "nombre": "Camiseta Oversize", "precio": 79900,
      "categoria_id": 1, "descripcion": "...", "talla": "M", "color": "Negro",
      "imagen_url": "https://...",
      "stock_inicial": [{"sede_id": 1, "cantidad": 20}, {"sede_id": 2, "cantidad": 10}]
    }
    """
    body = request.get_json(silent=True)
    if not body:
        return error("JSON body requerido")

    campos_obligatorios = ["sku", "nombre", "precio", "categoria_id"]
    faltantes = [c for c in campos_obligatorios if c not in body]
    if faltantes:
        return error(f"Faltan campos obligatorios: {faltantes}")

    if Producto.query.filter_by(sku=body["sku"]).first():
        return error("Ya existe un producto con ese SKU", 409)

    producto = Producto(
        sku=body["sku"],
        nombre=body["nombre"],
        descripcion=body.get("descripcion", ""),
        talla=body.get("talla", "U"),
        color=body.get("color", ""),
        precio=float(body["precio"]),
        categoria_id=body["categoria_id"],
        imagen_url=body.get("imagen_url", ""),
        qr_payload=f"SOLSTICIO-SKU-{body['sku']}",
    )
    db.session.add(producto)
    db.session.flush()  # obtiene producto.id sin hacer commit todavía

    for item in body.get("stock_inicial", []):
        db.session.add(Inventario(producto_id=producto.id, sede_id=item["sede_id"], cantidad=item.get("cantidad", 0)))

    db.session.commit()
    return jsonify(producto.to_dict(incluir_stock=True)), 201


@app.route("/api/productos/<int:producto_id>", methods=["PUT"])
def actualizar_producto(producto_id):
    """Reemplazo completo del recurso (todos los campos deben enviarse)."""
    producto = Producto.query.get(producto_id)
    if not producto:
        return error("Producto no encontrado", 404)

    body = request.get_json(silent=True)
    if not body:
        return error("JSON body requerido")

    for campo in ["sku", "nombre", "descripcion", "talla", "color", "precio", "categoria_id", "imagen_url"]:
        if campo not in body:
            return error(f"PUT requiere todos los campos. Falta: {campo}")
        setattr(producto, campo, body[campo])

    db.session.commit()
    return jsonify(producto.to_dict(incluir_stock=True))


@app.route("/api/productos/<int:producto_id>", methods=["PATCH"])
def modificar_parcial_producto(producto_id):
    """Actualización parcial: solo se envían los campos que cambian."""
    producto = Producto.query.get(producto_id)
    if not producto:
        return error("Producto no encontrado", 404)

    body = request.get_json(silent=True) or {}
    campos_permitidos = ["nombre", "descripcion", "talla", "color", "precio", "categoria_id", "imagen_url", "activo"]
    for campo, valor in body.items():
        if campo in campos_permitidos:
            setattr(producto, campo, valor)

    db.session.commit()
    return jsonify(producto.to_dict(incluir_stock=True))


@app.route("/api/productos/<int:producto_id>", methods=["DELETE"])
def eliminar_producto(producto_id):
    """Borrado lógico (soft delete) para no perder trazabilidad de ventas/inventario históricas."""
    producto = Producto.query.get(producto_id)
    if not producto:
        return error("Producto no encontrado", 404)

    producto.activo = False
    db.session.commit()
    return jsonify({"mensaje": f"Producto {producto_id} desactivado correctamente"})


# =========================================================
#  RUTAS - INVENTARIO MULTISEDE  /api/inventario
# =========================================================
@app.route("/api/inventario", methods=["GET"])
def consultar_inventario():
    """
    Consulta general de stock. Filtros: ?producto_id=  ?sede_id=
    Es la ruta clave para que el trabajador vea stock en otras sedes.
    """
    query = Inventario.query
    producto_id = request.args.get("producto_id", type=int)
    sede_id = request.args.get("sede_id", type=int)

    if producto_id:
        query = query.filter_by(producto_id=producto_id)
    if sede_id:
        query = query.filter_by(sede_id=sede_id)

    registros = query.all()
    return jsonify([
        {
            "producto_id": r.producto_id,
            "producto": r.producto.nombre,
            "sede_id": r.sede_id,
            "sede": r.sede.nombre,
            "cantidad": r.cantidad,
        }
        for r in registros
    ])


@app.route("/api/inventario/<int:producto_id>/<int:sede_id>", methods=["PATCH"])
def ajustar_inventario(producto_id, sede_id):
    """
    Ajusta el stock de un producto en una sede específica.
    Body: {"delta": -1}  para descontar, {"delta": 5} para reponer,
          o {"cantidad": 30} para fijar un valor absoluto (ej. tras un conteo físico).
    Este endpoint es la solución directa al descuadre de inventario:
    todas las sedes leen y escriben sobre la MISMA fila, en tiempo real.
    """
    inventario = Inventario.query.filter_by(producto_id=producto_id, sede_id=sede_id).first()
    if not inventario:
        inventario = Inventario(producto_id=producto_id, sede_id=sede_id, cantidad=0)
        db.session.add(inventario)

    body = request.get_json(silent=True) or {}
    if "cantidad" in body:
        inventario.cantidad = int(body["cantidad"])
    elif "delta" in body:
        nueva_cantidad = inventario.cantidad + int(body["delta"])
        if nueva_cantidad < 0:
            return error("Stock insuficiente para esta operación", 409)
        inventario.cantidad = nueva_cantidad
    else:
        return error("Se requiere 'delta' o 'cantidad' en el body")

    db.session.commit()
    return jsonify(inventario.to_dict())


# =========================================================
#  RUTAS - SEDES Y CATEGORÍAS (soporte para el admin)
# =========================================================
@app.route("/api/sedes", methods=["GET"])
def listar_sedes():
    return jsonify([s.to_dict() for s in Sede.query.all()])


@app.route("/api/sedes", methods=["POST"])
def crear_sede():
    body = request.get_json(silent=True) or {}
    if not all(k in body for k in ["nombre", "ciudad", "direccion"]):
        return error("nombre, ciudad y direccion son obligatorios")
    sede = Sede(**body)
    db.session.add(sede)
    db.session.commit()
    return jsonify(sede.to_dict()), 201


@app.route("/api/categorias", methods=["GET"])
def listar_categorias():
    return jsonify([c.to_dict() for c in Categoria.query.all()])


@app.route("/api/categorias", methods=["POST"])
def crear_categoria():
    body = request.get_json(silent=True) or {}
    if "nombre" not in body:
        return error("nombre es obligatorio")
    categoria = Categoria(nombre=body["nombre"])
    db.session.add(categoria)
    db.session.commit()
    return jsonify(categoria.to_dict()), 201


@app.route("/api/categorias/<int:categoria_id>", methods=["DELETE"])
def eliminar_categoria(categoria_id):
    categoria = Categoria.query.get(categoria_id)
    if not categoria:
        return error("Categoría no encontrada", 404)
    db.session.delete(categoria)
    db.session.commit()
    return jsonify({"mensaje": "Categoría eliminada"})


# =========================================================
#  RUTAS - PEDIDOS  /api/pedidos  (cliente virtual + trabajador mostrador)
# =========================================================
@app.route("/api/pedidos", methods=["GET"])
def listar_pedidos():
    query = Pedido.query
    sede_id = request.args.get("sede_id", type=int)
    estado = request.args.get("estado")
    if sede_id:
        query = query.filter_by(sede_id=sede_id)
    if estado:
        query = query.filter_by(estado=estado)
    pedidos = query.order_by(Pedido.creado_en.desc()).all()
    return jsonify([p.to_dict() for p in pedidos])


@app.route("/api/pedidos/<int:pedido_id>", methods=["GET"])
def obtener_pedido(pedido_id):
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return error("Pedido no encontrado", 404)
    return jsonify(pedido.to_dict())


@app.route("/api/pedidos", methods=["POST"])
def crear_pedido():
    """
    Crea un pedido (virtual desde el cliente, o mostrador desde el trabajador)
    y descuenta el inventario de la sede correspondiente de forma atómica.
    Body:
    {
      "cliente_nombre": "Juan Pérez", "cliente_documento": "123",
      "canal": "virtual", "sede_id": 1,
      "items": [{"producto_id": 3, "cantidad": 2}]
    }
    """
    body = request.get_json(silent=True) or {}
    campos_obligatorios = ["cliente_nombre", "sede_id", "items"]
    if not all(c in body for c in campos_obligatorios) or not body["items"]:
        return error("cliente_nombre, sede_id e items (no vacío) son obligatorios")

    pedido = Pedido(
        cliente_nombre=body["cliente_nombre"],
        cliente_documento=body.get("cliente_documento", ""),
        canal=body.get("canal", "virtual"),
        sede_id=body["sede_id"],
        estado="pendiente",
    )
    db.session.add(pedido)
    db.session.flush()

    total = 0.0
    for item in body["items"]:
        producto = Producto.query.get(item["producto_id"])
        if not producto:
            db.session.rollback()
            return error(f"Producto {item['producto_id']} no existe", 404)

        inventario = Inventario.query.filter_by(producto_id=producto.id, sede_id=body["sede_id"]).first()
        cantidad_pedida = int(item["cantidad"])
        if not inventario or inventario.cantidad < cantidad_pedida:
            db.session.rollback()
            return error(f"Stock insuficiente de '{producto.nombre}' en la sede seleccionada", 409)

        inventario.cantidad -= cantidad_pedida  # descuadre resuelto: descuento inmediato y centralizado
        subtotal = producto.precio * cantidad_pedida
        total += subtotal

        db.session.add(DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto.id,
            cantidad=cantidad_pedida,
            precio_unitario=producto.precio,
        ))

    pedido.total = round(total, 2)
    db.session.commit()
    return jsonify(pedido.to_dict()), 201


@app.route("/api/pedidos/<int:pedido_id>", methods=["PATCH"])
def actualizar_estado_pedido(pedido_id):
    """Cambia el estado del pedido: pendiente -> pagado -> entregado, o cancelado."""
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return error("Pedido no encontrado", 404)

    body = request.get_json(silent=True) or {}
    nuevo_estado = body.get("estado")
    if nuevo_estado not in ["pendiente", "pagado", "entregado", "cancelado"]:
        return error("Estado inválido")

    if nuevo_estado == "cancelado" and pedido.estado != "cancelado":
        # devolver el stock a la sede
        for detalle in pedido.detalles:
            inventario = Inventario.query.filter_by(producto_id=detalle.producto_id, sede_id=pedido.sede_id).first()
            if inventario:
                inventario.cantidad += detalle.cantidad

    pedido.estado = nuevo_estado
    db.session.commit()
    return jsonify(pedido.to_dict())


@app.route("/api/pedidos/<int:pedido_id>", methods=["DELETE"])
def eliminar_pedido(pedido_id):
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return error("Pedido no encontrado", 404)
    db.session.delete(pedido)
    db.session.commit()
    return jsonify({"mensaje": f"Pedido {pedido_id} eliminado"})


# =========================================================
#  FACTURACIÓN ELECTRÓNICA + SERVICIO SIMULADO DIAN
# =========================================================
@app.route("/api/pedidos/<int:pedido_id>/factura", methods=["POST"])
def generar_factura(pedido_id):
    """
    Genera la factura del pedido y la envía al servicio simulado de la DIAN
    para su 'validación'. En un entorno real esto sería una llamada SOAP/REST
    al webservice de la DIAN con firma digital y XML en formato UBL 2.1.
    """
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return error("Pedido no encontrado", 404)
    if pedido.factura:
        return error("Este pedido ya tiene una factura generada", 409)
    if pedido.estado == "cancelado":
        return error("No se puede facturar un pedido cancelado", 409)

    xml_simulado = (
        f"<Factura><NumeroPedido>{pedido.id}</NumeroPedido>"
        f"<Cliente>{pedido.cliente_nombre}</Cliente>"
        f"<Total>{pedido.total}</Total>"
        f"<Sede>{pedido.sede.nombre}</Sede></Factura>"
    )

    factura = Factura(
        pedido_id=pedido.id,
        cufe=generar_cufe(),
        estado_dian="pendiente",
        xml_simulado=xml_simulado,
    )
    db.session.add(factura)
    db.session.commit()

    # Llamada interna al "servicio externo" de la DIAN para validar
    resultado_dian = _servicio_dian_validar(factura)

    return jsonify({"factura": factura.to_dict(), "respuesta_dian": resultado_dian}), 201


def _servicio_dian_validar(factura: Factura):
    """
    Simula el actor externo DIAN. En producción esto sería una petición HTTP
    a la infraestructura de la DIAN (Facturación Electrónica - Resolución 000165).
    Aquí simplemente 'validamos' de forma determinística y guardamos el resultado.
    """
    factura.estado_dian = "validada"
    factura.fecha_validacion = datetime.utcnow()
    db.session.commit()
    return {
        "cufe": factura.cufe,
        "estado": factura.estado_dian,
        "mensaje": "Factura validada exitosamente por la DIAN (simulado)",
        "fecha_validacion": factura.fecha_validacion.isoformat(),
    }


@app.route("/api/dian/validar", methods=["POST"])
def endpoint_dian_validar():
    """
    Endpoint independiente que representa al actor externo DIAN recibiendo
    una factura directamente (útil para pruebas manuales o reintentos de validación).
    Body: {"cufe": "..."}
    """
    body = request.get_json(silent=True) or {}
    cufe = body.get("cufe")
    factura = Factura.query.filter_by(cufe=cufe).first()
    if not factura:
        return error("CUFE no encontrado", 404)
    return jsonify(_servicio_dian_validar(factura))


@app.route("/api/facturas/<int:pedido_id>", methods=["GET"])
def consultar_factura(pedido_id):
    factura = Factura.query.filter_by(pedido_id=pedido_id).first()
    if not factura:
        return error("Este pedido no tiene factura generada", 404)
    return jsonify(factura.to_dict())


# =========================================================
#  CÓDIGOS QR
# =========================================================
@app.route("/api/qr/producto/<int:producto_id>", methods=["GET"])
def generar_qr_producto(producto_id):
    """Genera el QR de una prenda como imagen PNG codificada en base64."""
    producto = Producto.query.get(producto_id)
    if not producto:
        return error("Producto no encontrado", 404)

    img = qrcode.make(producto.qr_payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({
        "producto_id": producto.id,
        "payload": producto.qr_payload,
        "qr_base64": f"data:image/png;base64,{qr_base64}",
    })


@app.route("/api/qr/pedido/<int:pedido_id>", methods=["GET"])
def generar_qr_pedido(pedido_id):
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return error("Pedido no encontrado", 404)

    payload = f"SOLSTICIO-PEDIDO-{pedido.id}"
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({"pedido_id": pedido.id, "payload": payload, "qr_base64": f"data:image/png;base64,{qr_base64}"})


@app.route("/api/qr/leer", methods=["POST"])
def leer_qr():
    """
    Simula la lectura de un QR escaneado por el trabajador.
    En el frontend real, una librería JS (ej. html5-qrcode) decodifica la imagen
    de la cámara y envía aquí SOLO el texto plano resultante (el 'payload').
    Body: {"payload": "SOLSTICIO-SKU-CAM-001"}  o {"payload": "SOLSTICIO-PEDIDO-7"}
    """
    body = request.get_json(silent=True) or {}
    payload = body.get("payload", "")

    if payload.startswith("SOLSTICIO-SKU-"):
        sku = payload.replace("SOLSTICIO-SKU-", "")
        producto = Producto.query.filter_by(sku=sku).first()
        if not producto:
            return error("QR válido pero producto no encontrado", 404)
        return jsonify({"tipo": "producto", "data": producto.to_dict(incluir_stock=True)})

    if payload.startswith("SOLSTICIO-PEDIDO-"):
        pedido_id = payload.replace("SOLSTICIO-PEDIDO-", "")
        pedido = Pedido.query.get(int(pedido_id)) if pedido_id.isdigit() else None
        if not pedido:
            return error("QR válido pero pedido no encontrado", 404)
        return jsonify({"tipo": "pedido", "data": pedido.to_dict()})

    return error("Formato de QR no reconocido", 400)


# =========================================================
#  SERVIR LOS FRONTENDS ESTÁTICOS
# =========================================================
@app.route("/")
@app.route("/cliente")
def frontend_cliente():
    return send_from_directory("cliente", "catalogo.html")


@app.route("/trabajador")
def frontend_trabajador():
    return send_from_directory("trabajador", "mostrador.html")


@app.route("/admin")
def frontend_admin():
    return send_from_directory("admin", "dashboard.html")


# =========================================================
#  INICIALIZACIÓN
# =========================================================
# Se ejecuta SIEMPRE al importar el módulo, tanto si lo corres con
# "python app.py" (local) como si Gunicorn hace "from app import app" (Render).
inicializar_base_de_datos()

if __name__ == "__main__":
    # Este bloque solo corre en local. En Render, Gunicorn nunca lo ejecuta
    # porque importa la app en vez de correr este archivo directamente.
    app.run(debug=True, port=5000)