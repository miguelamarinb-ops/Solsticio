"""
documentacion.py
Documentación técnica de la API en formato OpenAPI 3.0, servida en
/api/openapi.json y visible con Swagger UI en /api/docs.

Las rutas y sus métodos se leen del propio Flask (url_map) y los permisos de
cada una salen de los decoradores de api/seguridad.py, así que la documentación
no puede quedar desfasada del código: tests/test_documentacion.py falla si se
agrega una ruta sin describirla aquí.
"""
import re

from flask import Blueprint, current_app, jsonify

from api.seguridad import ADMINISTRADOR, CLIENTE, ROLES, TRABAJADOR

bp = Blueprint("documentacion", __name__)

# ---------------------------------------------------------------------
# Descripción de cada endpoint (clave: nombre interno de Flask)
#   r = resumen, d = descripción, q = parámetros de consulta, b = cuerpo de ejemplo,
#   e = códigos de error propios del endpoint (además de 401/403 que se agregan solos)
# ---------------------------------------------------------------------
PAGINA = [("page", "integer", "Página (desde 1)"), ("size", "integer", "Tamaño de página (máx. 100)")]
PERIODO = [("desde", "string", "AAAA-MM-DD (por defecto, hace 29 días)"),
           ("hasta", "string", "AAAA-MM-DD, incluido (por defecto, hoy)")]

ENDPOINTS = {
    # Autenticación ---------------------------------------------------
    "auth.registro": dict(
        t="Autenticación", r="Registrar cliente",
        d="Registro público de la tienda web. Crea un usuario con rol CLIENTE (contraseña con bcrypt) "
          "y su ficha en la tabla cliente, y devuelve el token JWT. Si el documento ya tenía compras "
          "sin cuenta y el correo coincide, la cuenta se enlaza a ese historial.",
        b={"tipo_documento": "CC", "documento": "1032456789", "nombres": "Laura", "apellidos": "Gómez",
           "email": "laura.gomez@correo.com", "password": "Clienta2026", "telefono": "3015550101"},
        e={201: "Cuenta creada, devuelve la sesión", 409: "Documento o correo ya registrados",
           422: "Datos inválidos o contraseña débil (mín. 8, letras y números)"}),
    "auth.login": dict(
        t="Autenticación", r="Iniciar sesión",
        d="Valida el correo y la contraseña contra la tabla usuario de MySQL (bcrypt) y devuelve "
          "un JWT HS256 que vence en ACCESS_TOKEN_EXPIRE_MINUTES. Sirve para los tres roles.",
        b={"email": "admin@solsticio.com", "password": "Admin12345"},
        e={401: "Credenciales incorrectas (mismo mensaje si el correo no existe)"}),
    "auth.perfil": dict(t="Autenticación", r="Perfil del usuario autenticado"),
    "actividad.perfil_con_actividad": dict(
        t="Autenticación", r="Perfil con su actividad reciente",
        d="Combina el usuario (MySQL) con sus últimas acciones registradas en la bitácora (MongoDB).",
        q=[("limite", "integer", "Cantidad de eventos")]),

    # Cuenta del cliente ----------------------------------------------
    "cuenta.mis_pedidos": dict(
        t="Cuenta del cliente", r="Mis pedidos",
        d="Pedidos web enlazados a la ficha del cliente autenticado, del más reciente al más antiguo.",
        q=PAGINA),
    "cuenta.mi_pedido": dict(
        t="Cuenta del cliente", r="Detalle de mi pedido",
        d="Seguimiento de un pedido propio. Un pedido ajeno responde 404 para no revelar que existe.",
        e={404: "El pedido no existe o no es del cliente"}),

    "cuenta.solicitar_devolucion": dict(
        t="Cuenta del cliente", r="Solicitar devolución o cambio",
        d="El cliente pide devolver o cambiar prendas de un pedido suyo. Queda SOLICITADA: el stock "
          "y la nota crédito se mueven cuando la sede recibe las prendas.",
        b={"tipo": "CAMBIO", "motivo": "La talla M me queda ajustada",
           "items": [{"id_detalle_pedido": 12, "cantidad": 1, "id_variante_cambio": 22}]},
        e={201: "Solicitud registrada", 409: "Unidades ya devueltas o pedido sin pagar",
           422: "Datos inválidos (el cambio debe ser de la misma prenda)"}),
    "cuenta.mis_devoluciones": dict(t="Cuenta del cliente", r="Mis devoluciones y su estado"),

    # Devoluciones ----------------------------------------------------
    "devoluciones.registrar_devolucion": dict(
        t="Devoluciones y cambios", r="Registrar devolución o cambio",
        d="El personal recibe las prendas en su sede (puede ser distinta a la que vendió). Reintegra el "
          "stock con un movimiento DEVOLUCION; en un CAMBIO entrega la prenda nueva con un movimiento "
          "VENTA; emite la nota crédito sobre la factura y la valida ante la DIAN (simulada).",
        b={"id_pedido": 1058, "id_sede": 1, "tipo": "CAMBIO", "motivo": "La talla M le queda ajustada",
           "items": [{"id_detalle_pedido": 2411, "cantidad": 1, "id_variante_cambio": 22}]},
        e={201: "Devolución COMPLETADA con movimientos y nota crédito",
           409: "Unidades ya devueltas, pedido sin pagar o sin existencias para el cambio",
           422: "Datos inválidos"}),
    "devoluciones.listar_devoluciones": dict(
        t="Devoluciones y cambios", r="Listar devoluciones",
        q=[("estado", "string", "SOLICITADA, APROBADA, RECHAZADA o COMPLETADA"),
           ("tipo", "string", "CAMBIO o DEVOLUCION"), ("id_pedido", "integer", "Pedido"),
           ("id_sede", "integer", "Sede (solo administrador)")] + PAGINA),
    "devoluciones.obtener_devolucion": dict(t="Devoluciones y cambios", r="Detalle de devolución"),
    "devoluciones.procesar_solicitud": dict(
        t="Devoluciones y cambios", r="Completar o rechazar una solicitud",
        b={"accion": "COMPLETAR"}, e={409: "La devolución ya no está pendiente"}),
    "devoluciones.buscar_pedido_para_devolucion": dict(
        t="Devoluciones y cambios", r="Buscar el pedido a devolver",
        d="Por el código del comprobante o el id. Cualquier sede puede recibir la devolución, así que "
          "no se limita por sede. Cada ítem trae 'devolvible': unidades que aún se pueden devolver.",
        q=[("codigo", "string", "Código QR del pedido (SOL-P-...)"), ("id_pedido", "integer", "Pedido")]),
    "reportes.reporte_ventas": dict(
        t="Reportes de ventas e inventario", r="Reporte: ventas por periodo",
        d="Cuenta los pedidos pagados (PAGADO, PREPARANDO, ENVIADO, ENTREGADO). Los ingresos netos restan "
          "las notas crédito emitidas en el periodo.",
        q=PERIODO + [("id_sede", "integer", "Sede"), ("canal", "string", "WEB o TIENDA")]),
    "reportes.reporte_productos_mas_vendidos": dict(
        t="Reportes de ventas e inventario", r="Reporte: prendas más vendidas",
        q=PERIODO + [("limite", "integer", "Cantidad (máx. 50, por defecto 5)"), ("id_sede", "integer", "Sede")]),
    "reportes.reporte_rotacion_inventario": dict(
        t="Reportes de ventas e inventario", r="Reporte: rotación de inventario",
        d="Por prenda: unidades vendidas / existencias promedio del periodo, días de inventario y "
          "clasificación ALTA, MEDIA, BAJA o SIN_VENTAS.",
        q=PERIODO + [("id_sede", "integer", "Sede")]),

    # Catálogo --------------------------------------------------------
    "catalogo.listar_categorias": dict(t="Catálogo", r="Listar categorías"),
    "catalogo.listar_sedes": dict(t="Catálogo", r="Listar sedes"),
    "catalogo.listar_tallas": dict(t="Catálogo", r="Listar tallas"),
    "catalogo.listar_colores": dict(t="Catálogo", r="Listar colores"),
    "catalogo.listar_productos": dict(
        t="Catálogo", r="Buscar productos",
        d="Catálogo paginado con filtros. Con token de ADMINISTRADOR y inactivos=true incluye los desactivados.",
        q=[("q", "string", "Texto a buscar"), ("categoria", "integer", "id_categoria"),
           ("genero", "string", "HOMBRE, MUJER o UNISEX"), ("sede", "integer", "Solo con stock en la sede"),
           ("inactivos", "boolean", "Solo administrador")] + PAGINA),
    "catalogo.obtener_producto": dict(
        t="Catálogo", r="Detalle de producto",
        d="Producto con variantes y disponibilidad desglosada por sede.", e={404: "Producto no encontrado"}),
    "catalogo.resolver_qr_variante": dict(
        t="Catálogo", r="Resolver QR de etiqueta",
        d="Devuelve la variante (producto + talla + color) del código QR y registra el escaneo en MongoDB.",
        e={404: "QR desconocido"}),
    "catalogo.disponibilidad_variante": dict(t="Catálogo", r="Disponibilidad de una variante por sede"),

    # Inventario ------------------------------------------------------
    "inventario.consultar_stock": dict(
        t="Inventario", r="Consultar stock",
        d="El TRABAJADOR solo ve su sede; pedir otra responde 403.",
        q=[("id_sede", "integer", "Sede"), ("id_variante", "integer", "Variante"),
           ("id_producto", "integer", "Producto"), ("bajo_minimo", "boolean", "Solo bajo el mínimo")]),
    "inventario.registrar_ingreso": dict(
        t="Inventario", r="Registrar ingreso de mercancía",
        b={"id_sede": 1, "observacion": "Remisión TEXTIL-4471",
           "items": [{"id_variante": 1, "cantidad": 20}, {"id_variante": 2, "cantidad": 15}]},
        e={201: "Ingreso registrado con su movimiento de inventario"}),
    "inventario.registrar_ajuste": dict(
        t="Inventario", r="Ajuste por conteo físico",
        b={"id_sede": 1, "observacion": "Conteo físico", "items": [{"id_variante": 2, "cantidad_contada": 13}]},
        e={201: "Ajuste registrado"}),
    "inventario.listar_movimientos": dict(
        t="Inventario", r="Movimientos de inventario (trazabilidad)",
        q=[("id_sede", "integer", "Sede"), ("id_variante", "integer", "Variante"),
           ("tipo", "string", "INGRESO, VENTA, TRASLADO_SALIDA, ..."), ("desde", "string", "AAAA-MM-DD"),
           ("hasta", "string", "AAAA-MM-DD")] + PAGINA),
    "inventario.crear_traslado": dict(
        t="Traslados", r="Solicitar traslado entre sedes",
        b={"id_sede_origen": 2, "id_sede_destino": 1, "items": [{"id_variante": 1, "cantidad": 4}]},
        e={201: "Traslado SOLICITADO", 409: "Existencias insuficientes en el origen"}),
    "inventario.listar_traslados": dict(
        t="Traslados", r="Listar traslados",
        q=[("estado", "string", "SOLICITADO, EN_TRANSITO, RECIBIDO"), ("id_sede", "integer", "Sede")] + PAGINA),
    "inventario.obtener_traslado": dict(t="Traslados", r="Detalle de traslado"),
    "inventario.despachar_traslado": dict(
        t="Traslados", r="Despachar traslado", d="Genera el movimiento TRASLADO_SALIDA en el origen.",
        e={409: "Estado no permite despachar"}),
    "inventario.recibir_traslado": dict(
        t="Traslados", r="Recibir traslado", d="Genera el movimiento TRASLADO_ENTRADA en el destino.",
        e={409: "Estado no permite recibir"}),

    # Pedidos y pagos ---------------------------------------------------
    "pedidos.crear_pedido": dict(
        t="Pedidos y ventas", r="Crear pedido (web o tienda)",
        d="Canal WEB: público; con token de CLIENTE el comprador sale de su cuenta y no hace falta 'cliente'. "
          "Canal TIENDA: solo personal (TRABAJADOR en su sede o ADMINISTRADOR). Reserva las unidades.",
        b={"canal": "WEB", "id_sede": 1, "tipo_entrega": "RECOGER_EN_TIENDA",
           "cliente": {"tipo_documento": "CC", "numero_documento": "1020304050", "nombres": "Andrés",
                       "email": "andres@correo.com"},
           "items": [{"id_variante": 1, "cantidad": 2}]},
        e={201: "Pedido PENDIENTE", 409: "Existencias insuficientes (incluye sedes alternativas)"}),
    "pedidos.listar_pedidos": dict(
        t="Pedidos y ventas", r="Listar pedidos",
        q=[("id_sede", "integer", "Sede"), ("estado", "string", "Estado"), ("canal", "string", "WEB o TIENDA")] + PAGINA),
    "pedidos.obtener_pedido": dict(t="Pedidos y ventas", r="Detalle de pedido"),
    "pedidos.resolver_qr_pedido": dict(t="Pedidos y ventas", r="Resolver QR de comprobante"),
    "pedidos.cambiar_estado_pedido": dict(
        t="Pedidos y ventas", r="Cambiar estado de pedido",
        b={"estado": "ENVIADO", "transportadora": "Servientrega", "numero_guia": "SV123"},
        e={409: "Transición de estado no permitida"}),
    "pedidos.listar_metodos_pago": dict(t="Pagos y facturación", r="Métodos de pago"),
    "pedidos.registrar_pago": dict(
        t="Pagos y facturación", r="Registrar pago (pasarela simulada)",
        d="Pedidos WEB: público. Pedidos TIENDA: solo personal. Si se aprueba descuenta el stock "
          "y emite la factura. 'simular_rechazo': true prueba el rechazo.",
        b={"id_metodo_pago": 4, "monto": 159800},
        e={201: "Pago aprobado", 402: "Pago rechazado, se liberan las unidades", 409: "El pedido no admite pagos"}),
    "pedidos.generar_factura": dict(
        t="Pagos y facturación", r="Emitir factura electrónica (DIAN simulada)",
        e={201: "Factura validada", 502: "La DIAN no respondió; factura PENDIENTE"}),
    "pedidos.obtener_factura": dict(t="Pagos y facturación", r="Consultar factura"),

    # Administración ----------------------------------------------------
    "admin.crear_categoria": dict(t="Administración", r="Crear categoría",
                                  b={"nombre": "Camisas", "descripcion": "Camisas y camisetas"}),
    "admin.crear_sede": dict(t="Administración", r="Crear sede",
                             b={"nombre": "Solsticio Usaquén", "direccion": "Calle 119 # 6-15", "telefono": "6013009900"}),
    "admin.listar_usuarios": dict(
        t="Administración", r="Listar usuarios",
        q=[("rol", "string", "ADMINISTRADOR, TRABAJADOR o CLIENTE"), ("activo", "boolean", "true o false")]),
    "admin.crear_usuario": dict(
        t="Administración", r="Crear usuario del personal",
        d="Solo roles ADMINISTRADOR y TRABAJADOR; los clientes se registran en /auth/registro.",
        b={"documento": "1000000002", "nombres": "Carlos", "apellidos": "Méndez", "email": "carlos@solsticio.com",
           "password": "Trabajador123", "rol": "TRABAJADOR", "id_sede": 1},
        e={201: "Usuario creado", 409: "Documento o correo repetido", 422: "Rol o datos inválidos"}),
    "admin.cambiar_estado_usuario": dict(
        t="Administración", r="Activar o desactivar usuario",
        d="No hay borrado físico. Un usuario desactivado pierde el acceso aunque su token no haya vencido.",
        b={"activo": False}),
    "admin.crear_producto": dict(
        t="Administración", r="Crear producto",
        b={"id_categoria": 1, "nombre": "Camiseta oversize algodón", "precio_base": 79900, "genero": "UNISEX"}),
    "admin.actualizar_producto": dict(
        t="Administración", r="Actualizar producto",
        b={"id_categoria": 1, "nombre": "Camiseta oversize algodón", "precio_base": 84900, "genero": "UNISEX"}),
    "admin.desactivar_producto": dict(t="Administración", r="Desactivar producto"),
    "admin.crear_variantes": dict(
        t="Administración", r="Crear variantes (talla y color)",
        b={"combinaciones": [{"id_talla": 3, "id_color": 1}, {"id_talla": 4, "id_color": 1}]}),

    # MongoDB -------------------------------------------------------------
    "fichas.obtener_ficha": dict(t="Fichas técnicas (MongoDB)", r="Ver ficha técnica"),
    "fichas.guardar_ficha": dict(
        t="Fichas técnicas (MongoDB)", r="Guardar ficha técnica",
        b={"atributos": {"material": "Algodón", "gramaje_gsm": 220, "fit": "oversize"},
           "cuidados": ["Lavar a máquina en frío"], "etiquetas": ["Verano"]}),
    "fichas.eliminar_ficha": dict(t="Fichas técnicas (MongoDB)", r="Eliminar ficha técnica"),
    "fichas.producto_completo": dict(t="Fichas técnicas (MongoDB)", r="Producto completo (MySQL + MongoDB)"),
    "fichas.buscar_por_atributos": dict(
        t="Fichas técnicas (MongoDB)", r="Buscar por atributos de la ficha",
        q=[("atributos.material", "string", "Cualquier atributo con prefijo atributos."),
           ("etiqueta", "string", "Etiqueta")]),
    "resenas.listar_resenas": dict(
        t="Reseñas (MongoDB)", r="Reseñas de un producto",
        q=[("orden", "string", "recientes o mejores")] + PAGINA),
    "resenas.crear_resena": dict(
        t="Reseñas (MongoDB)", r="Publicar reseña",
        b={"nombre": "Andrés Rivera", "email": "andres@correo.com", "calificacion": 5,
           "titulo": "Excelente calidad", "comentario": "La tela es gruesa."}),
    "resenas.obtener_resena": dict(t="Reseñas (MongoDB)", r="Ver reseña"),
    "resenas.marcar_util": dict(t="Reseñas (MongoDB)", r="Marcar reseña como útil"),
    "resenas.listar_resenas_moderacion": dict(
        t="Reseñas (MongoDB)", r="Bandeja de moderación",
        q=[("estado", "string", "PUBLICADA u OCULTA"), ("id_producto", "integer", "Producto"),
           ("calificacion", "integer", "1 a 5")] + PAGINA),
    "resenas.moderar_resena": dict(t="Reseñas (MongoDB)", r="Moderar o responder reseña",
                                   b={"respuesta": "¡Gracias por tu compra!", "estado": "PUBLICADA"}),
    "resenas.eliminar_resena": dict(t="Reseñas (MongoDB)", r="Eliminar reseña"),
    "actividad.listar_actividad": dict(
        t="Bitácora y reportes (MongoDB)", r="Bitácora de actividad",
        q=[("accion", "string", "INICIO_SESION, VENTA_REGISTRADA, ..."), ("id_usuario", "integer", "Usuario"),
           ("exito", "boolean", "Solo peticiones exitosas o fallidas")] + PAGINA),
    "actividad.actividad_de_usuario": dict(t="Bitácora y reportes (MongoDB)", r="Actividad de un usuario"),
    "actividad.qr_mas_escaneados": dict(
        t="Bitácora y reportes (MongoDB)", r="Reporte: QR más escaneados",
        q=[("dias", "integer", "Ventana en días"), ("limite", "integer", "Cantidad")]),
    "inicio": dict(t="General", r="Información de la API"),
}

ETIQUETAS = [
    ("Autenticación", "Registro, inicio de sesión (JWT) y perfil."),
    ("Cuenta del cliente", "Rutas exclusivas del rol CLIENTE."),
    ("Catálogo", "Consulta pública del catálogo y la disponibilidad por sede."),
    ("Inventario", "Existencias por sede y su trazabilidad."),
    ("Traslados", "Movimiento de mercancía entre sedes."),
    ("Pedidos y ventas", "Venta web y en tienda."),
    ("Pagos y facturación", "Pasarela y DIAN simuladas."),
    ("Devoluciones y cambios", "Reintegro de stock y nota crédito ante la DIAN."),
    ("Reportes de ventas e inventario", "Caso de uso 2.3.9: ventas, prendas más vendidas y rotación (MySQL)."),
    ("Administración", "Maestros y usuarios del personal."),
    ("Fichas técnicas (MongoDB)", "Atributos variables por producto."),
    ("Reseñas (MongoDB)", "Opiniones de los compradores."),
    ("Bitácora y reportes (MongoDB)", "Actividad de los usuarios y escaneos de QR."),
    ("General", ""),
]

DESCRIPCION = f"""
API REST del sistema multisede de inventario y ventas **Solsticio** (Flask + MySQL + MongoDB).

## Autenticación
1. `POST /api/v1/auth/login` (o `/auth/registro` para clientes) devuelve `access_token`.
2. Enviar el token en cada petición protegida: `Authorization: Bearer <token>`.
3. El token es un JWT HS256 firmado con `SECRET_KEY`; vence en `ACCESS_TOKEN_EXPIRE_MINUTES`.
   El rol se lee de MySQL en cada petición, así que desactivar un usuario corta su acceso al instante.

## Roles (RBAC)
| Rol | Alcance |
|---|---|
| `{ADMINISTRADOR}` | Control total, todas las sedes. |
| `{TRABAJADOR}` | Ventas, inventario y traslados **solo de su sede**. |
| `{CLIENTE}` | Compra en la tienda web y consulta **solo sus pedidos**. |

Cada operación indica en **Roles** quién puede usarla. Sin token: `401`. Con un rol no permitido: `403`.

## Errores
Cuerpo `{{"detail": "mensaje"}}`, a veces con llaves extra (por ejemplo `conflictos` en un `409` de existencias).
"""


def _ruta_openapi(regla):
    return re.sub(r"<(?:[a-z]+:)?([a-z_]+)>", r"{\1}", regla)


def _parametros_ruta(regla):
    parametros = []
    for convertidor, nombre in re.findall(r"<(?:([a-z]+):)?([a-z_]+)>", regla):
        parametros.append({
            "name": nombre, "in": "path", "required": True,
            "schema": {"type": "integer" if convertidor == "int" else "string"},
        })
    return parametros


def _operacion(endpoint, vista, metodo, regla):
    info = ENDPOINTS.get(endpoint, {})
    roles = getattr(vista, "roles_permitidos", None)
    opcional = getattr(vista, "auth_opcional", False)
    if roles:
        acceso = "Requiere token. Roles: " + ", ".join(roles) + "."
    elif opcional:
        acceso = "Público. Si llega un token, la respuesta se adapta al rol."
    else:
        acceso = "Público, sin token."

    operacion = {
        "tags": [info.get("t", "General")],
        "summary": info.get("r", endpoint),
        "description": (info.get("d", "") + "\n\n**Acceso:** " + acceso).strip(),
        "operationId": endpoint.replace(".", "_") + "_" + metodo.lower(),
        "x-roles": list(roles) if roles else [],
        "parameters": _parametros_ruta(regla) + [
            {"name": n, "in": "query", "required": False, "schema": {"type": tipo}, "description": desc}
            for n, tipo, desc in info.get("q", []) if metodo == "GET"
        ],
        "responses": {},
    }
    if roles:
        operacion["security"] = [{"bearerAuth": []}]
    elif opcional:
        operacion["security"] = [{}, {"bearerAuth": []}]

    if "b" in info and metodo in ("POST", "PUT", "PATCH"):
        operacion["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": {"type": "object"}, "example": info["b"]}},
        }

    errores = dict(info.get("e", {}))
    exito = next((c for c in errores if 200 <= c < 300), 201 if metodo == "POST" else 200)
    respuestas = {str(exito): {"description": errores.pop(exito, "Operación exitosa")}}
    if roles:
        errores.setdefault(401, "Falta el token, es inválido o venció")
        if set(roles) != set(ROLES):
            errores.setdefault(403, "El rol del usuario no tiene permiso")
    if regla.count("<"):
        errores.setdefault(404, "Recurso no encontrado")
    for codigo, texto in sorted(errores.items()):
        respuestas[str(codigo)] = {"description": texto, "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
    operacion["responses"] = respuestas
    return operacion


def generar_especificacion(app):
    rutas = {}
    for regla in app.url_map.iter_rules():
        if not regla.rule.startswith("/api/v1"):
            continue
        vista = app.view_functions[regla.endpoint]
        for metodo in sorted(regla.methods - {"HEAD", "OPTIONS"}):
            rutas.setdefault(_ruta_openapi(regla.rule), {})[metodo.lower()] = \
                _operacion(regla.endpoint, vista, metodo, regla.rule)

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Solsticio API",
            "version": "3.0.0",
            "description": DESCRIPCION,
            "contact": {"name": "Miguel Ángel Marín Baracaldo · Joan Sebastian Lara Fuenmayor"},
        },
        "servers": [{"url": "/", "description": "Servidor actual"}],
        "tags": [{"name": n, "description": d} for n, d in ETIQUETAS],
        "paths": dict(sorted(rutas.items())),
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                               "description": "Token de POST /api/v1/auth/login o /auth/registro"},
            },
            "schemas": {
                "Error": {"type": "object", "required": ["detail"],
                          "properties": {"detail": {"type": "string", "example": "No tiene permisos para esta operación"}}},
            },
        },
    }


@bp.get("/api/openapi.json")
def especificacion():
    return jsonify(generar_especificacion(current_app))


@bp.get("/api/docs")
def swagger_ui():
    # Swagger UI desde CDN con versión fija; solo la usa esta página de documentación.
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Solsticio API | Documentación</title>
  <link rel="icon" href="/recursos/img/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
  <style>body { margin: 0; background: #fff; } .topbar { display: none; }</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js" crossorigin></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: "/api/openapi.json", dom_id: "#swagger-ui", deepLinking: true,
      persistAuthorization: true, docExpansion: "none", tagsSorter: "alpha",
    });
  </script>
</body>
</html>"""
