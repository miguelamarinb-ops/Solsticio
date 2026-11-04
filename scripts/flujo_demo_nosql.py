"""
flujo_demo_nosql.py
Carga datos de ejemplo y recorre todos los endpoints de MongoDB y los combinados SQL + NoSQL.
Requiere la API corriendo (python app.py), las bases vacías y un usuario ADMINISTRADOR.

    python scripts/flujo_demo_nosql.py [archivo_salida.json]

Credenciales del administrador: variables de entorno SOLSTICIO_EMAIL y SOLSTICIO_PASSWORD
(por defecto admin@solsticio.com / Admin12345). En PowerShell:

    $env:SOLSTICIO_EMAIL = "tu@correo.com"; $env:SOLSTICIO_PASSWORD = "tu-clave"

Guarda cada petición y su respuesta en el JSON indicado (por defecto evidencias.json).
"""
import json, os, sys, urllib.request

BASE = "http://127.0.0.1:5000"
TOKEN = None
LOG = []

def call(nombre, metodo, ruta, cuerpo=None, token=True, guardar=True):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "solsticio-flujo-demo/1.0")
    if token and TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    try:
        with urllib.request.urlopen(req) as r:
            codigo, texto = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        codigo, texto = e.code, e.read().decode()
    resp = json.loads(texto) if texto else None
    print(f"{codigo} {metodo} {ruta}")
    if guardar:
        LOG.append({"nombre": nombre, "metodo": metodo, "ruta": ruta, "cuerpo": cuerpo, "codigo": codigo, "respuesta": resp})
    return codigo, resp

# --- Datos base en MySQL (flujo existente) ---
credenciales = {
    "email": os.environ.get("SOLSTICIO_EMAIL", "admin@solsticio.com"),
    "password": os.environ.get("SOLSTICIO_PASSWORD", "Admin12345"),
}
c, r = call("login", "POST", "/api/v1/auth/login", credenciales, token=False, guardar=False)
if c != 200:
    sys.exit(f"No se pudo iniciar sesión como {credenciales['email']}: {r}. "
             "Defina SOLSTICIO_EMAIL y SOLSTICIO_PASSWORD con un usuario ADMINISTRADOR.")
TOKEN = r["access_token"]
call("cat", "POST", "/api/v1/categorias", {"nombre": "Camisetas", "descripcion": "Camisetas y polos"}, guardar=False)
call("cat2", "POST", "/api/v1/categorias", {"nombre": "Jeans", "descripcion": "Pantalones de denim"}, guardar=False)
call("p1", "POST", "/api/v1/productos", {"id_categoria": 1, "nombre": "Camiseta oversize algodón", "descripcion": "Camiseta de corte amplio en algodón 100%", "precio_base": 79900, "genero": "UNISEX", "imagenes": [{"url": "/media/productos/frente.jpg", "orden": 1, "es_principal": True}]}, guardar=False)
call("p2", "POST", "/api/v1/productos", {"id_categoria": 2, "nombre": "Jean slim tiro alto", "descripcion": "Denim con elastano", "precio_base": 149900, "genero": "MUJER"}, guardar=False)
call("v1", "POST", "/api/v1/productos/1/variantes", {"combinaciones": [{"id_talla": 3, "id_color": 1, "precio_adicional": 0}, {"id_talla": 4, "id_color": 1, "precio_adicional": 0}]}, guardar=False)
call("v2", "POST", "/api/v1/productos/2/variantes", {"combinaciones": [{"id_talla": 2, "id_color": 2, "precio_adicional": 0}, {"id_talla": 3, "id_color": 2, "precio_adicional": 5000}]}, guardar=False)
call("ing", "POST", "/api/v1/inventario/ingresos", {"id_sede": 1, "observacion": "Remisión TEXTIL-4471", "items": [{"id_variante": 1, "cantidad": 20}, {"id_variante": 2, "cantidad": 15}, {"id_variante": 3, "cantidad": 10}, {"id_variante": 4, "cantidad": 8}]}, guardar=False)
c, ped = call("ped", "POST", "/api/v1/pedidos", {"canal": "WEB", "id_sede": 1, "tipo_entrega": "DOMICILIO", "cliente": {"tipo_documento": "CC", "numero_documento": "1020304050", "nombres": "Andrés", "apellidos": "Rivera", "email": "andres@correo.com", "telefono": "3001234567"}, "envio": {"direccion": "Carrera 15 # 82-30", "ciudad": "Bogotá", "destinatario": "Andrés Rivera", "telefono_contacto": "3001234567"}, "items": [{"id_variante": 1, "cantidad": 2}]}, guardar=False)
call("pago", "POST", f"/api/v1/pedidos/{ped['id_pedido']}/pagos", {"id_metodo_pago": 4, "monto": ped["total"]}, guardar=False)
codigo_pedido = ped["codigo_qr"]
_, var = call("var", "GET", "/api/v1/productos/1", guardar=False)
qr1 = var["variantes"][0]["codigo_qr"]; qr2 = var["variantes"][1]["codigo_qr"]
_, var2 = call("var2", "GET", "/api/v1/productos/2", guardar=False)
qr3 = var2["variantes"][0]["codigo_qr"]

# --- MongoDB: fichas técnicas (CRUD) ---
call("Crear ficha técnica (camiseta)", "PUT", "/api/v1/productos/1/ficha", {
    "atributos": {"material": "Algodón", "composicion": [{"fibra": "algodón peinado", "porcentaje": 100}],
                  "gramaje_gsm": 220, "cuello": "redondo", "manga": "corta", "fit": "oversize", "pais_origen": "Colombia"},
    "cuidados": ["Lavar a máquina en frío", "No usar blanqueador", "Planchar a temperatura media"],
    "etiquetas": ["Verano", "Básicos", "Unisex"]})
call("Crear ficha técnica (jean)", "PUT", "/api/v1/productos/2/ficha", {
    "atributos": {"material": "Denim", "composicion": [{"fibra": "algodón", "porcentaje": 98}, {"fibra": "elastano", "porcentaje": 2}],
                  "tiro": "alto", "elasticidad": "media", "lavado": "stone wash", "bolsillos": 5, "cierre": "cremallera YKK"},
    "cuidados": ["Lavar al revés", "No secar en secadora"], "etiquetas": ["Denim", "Todo el año"]})
call("Consultar ficha técnica", "GET", "/api/v1/productos/1/ficha", token=False)
call("Actualizar ficha técnica (versión 2)", "PUT", "/api/v1/productos/1/ficha", {
    "atributos": {"material": "Algodón", "composicion": [{"fibra": "algodón peinado", "porcentaje": 100}],
                  "gramaje_gsm": 240, "cuello": "redondo", "manga": "corta", "fit": "oversize", "pais_origen": "Colombia",
                  "certificaciones": ["OEKO-TEX Standard 100"]},
    "cuidados": ["Lavar a máquina en frío", "No usar blanqueador", "Planchar a temperatura media"],
    "etiquetas": ["Verano", "Básicos", "Unisex"]})

# --- MongoDB: reseñas (CRUD) ---
_, res1 = call("Crear reseña con compra verificada", "POST", "/api/v1/productos/1/resenas", {
    "nombre": "Andrés Rivera", "email": "andres@correo.com", "calificacion": 5, "titulo": "Excelente calidad",
    "comentario": "La tela es gruesa y no se transparenta. Después de 5 lavadas sigue igual.",
    "id_variante": 1, "ajuste_talla": "GRANDE", "codigo_pedido": codigo_pedido,
    "atributos": {"calidad_tela": 5, "encoge": False, "igual_a_la_foto": True}}, token=False)
call("Crear reseña sin compra", "POST", "/api/v1/productos/1/resenas", {
    "nombre": "Valentina Ruiz", "email": "vale@correo.com", "calificacion": 4,
    "comentario": "Muy cómoda, pero el color es un poco más claro que en la foto.", "ajuste_talla": "EXACTA",
    "atributos": {"igual_a_la_foto": False}, "fotos": ["https://cdn.solsticio.co/resenas/vale-1.jpg"]}, token=False)
call("seed3", "POST", "/api/v1/productos/1/resenas", {"nombre": "Camilo P.", "email": "camilo@correo.com", "calificacion": 3, "comentario": "Buena, pero la talla M me quedó grande.", "ajuste_talla": "GRANDE"}, token=False, guardar=False)
call("Reseña duplicada (409)", "POST", "/api/v1/productos/1/resenas", {"nombre": "Andrés Rivera", "email": "andres@correo.com", "calificacion": 1, "comentario": "Otra vez"}, token=False)
call("Compra no verificable (422)", "POST", "/api/v1/productos/2/resenas", {"nombre": "Andrés Rivera", "email": "andres@correo.com", "calificacion": 4, "comentario": "Lindo jean", "codigo_pedido": codigo_pedido}, token=False)
call("Marcar reseña como útil", "POST", f"/api/v1/resenas/{res1['id']}/util", token=False)
call("Listar reseñas con resumen", "GET", "/api/v1/productos/1/resenas?orden=mejores", token=False)
call("Responder reseña (admin)", "PATCH", f"/api/v1/resenas/{res1['id']}", {"respuesta": "¡Gracias Andrés! Nos alegra que te haya gustado."})
_, res_mala = call("tmp", "POST", "/api/v1/productos/1/resenas", {"nombre": "Spam", "email": "spam@x.com", "calificacion": 1, "comentario": "Compra seguidores en www.spam.example"}, token=False, guardar=False)
call("Ocultar reseña (admin)", "PATCH", f"/api/v1/resenas/{res_mala['id']}", {"estado": "OCULTA"})
call("Eliminar reseña (admin)", "DELETE", f"/api/v1/resenas/{res_mala['id']}")
call("Reseña eliminada (404)", "GET", f"/api/v1/resenas/{res_mala['id']}", token=False)

# --- MongoDB: escaneos QR (alta frecuencia) ---
for _ in range(6): call("qr", "GET", f"/api/v1/variantes/qr/{qr1}?sede=1", token=False, guardar=False)
for _ in range(3): call("qr", "GET", f"/api/v1/variantes/qr/{qr2}", guardar=False)
for _ in range(4): call("qr", "GET", f"/api/v1/variantes/qr/{qr3}?sede=2", token=False, guardar=False)
call("qr", "GET", "/api/v1/variantes/qr/SOL-V-NOEXISTE", token=False, guardar=False)

# --- Endpoints combinados SQL + NoSQL ---
call("Perfil + últimas 10 actividades", "GET", "/api/v1/auth/perfil/actividad")
call("Producto completo (SQL + NoSQL)", "GET", "/api/v1/productos/1/completo", token=False)
call("Buscar por atributos dinámicos", "GET", "/api/v1/productos/buscar-atributos?atributos.material=algodon&etiqueta=verano", token=False)
call("Ranking de QR más escaneados", "GET", "/api/v1/reportes/qr-mas-escaneados?dias=30&limite=5")
call("Bitácora filtrada (admin)", "GET", "/api/v1/actividad?accion=FICHA_GUARDADA&size=5")
call("Eliminar ficha técnica", "DELETE", "/api/v1/productos/2/ficha")

json.dump(LOG, open(sys.argv[1] if len(sys.argv) > 1 else "evidencias.json", "w"), ensure_ascii=False, indent=2, default=str)
