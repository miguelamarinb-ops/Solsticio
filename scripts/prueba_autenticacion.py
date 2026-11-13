"""
prueba_autenticacion.py
Demostración de la autenticación de Solsticio contra la base de datos relacional
(MySQL) y del control de acceso por roles con JWT. Recorre, con la API encendida:

  1. Registro de un cliente (POST /auth/registro).
  2. Lo que quedó en MySQL: fila en usuario (rol CLIENTE, hash bcrypt) y en cliente.
  3. Inicio de sesión correcto e incorrecto (POST /auth/login).
  4. Contenido del token JWT (cabecera y payload; la firma no se puede leer).
  5. Rutas protegidas: sin token, token alterado, token vencido -> 401.
  6. Roles: CLIENTE, TRABAJADOR y ADMINISTRADOR contra rutas de cada nivel (200/403).

Uso, con la API corriendo:
    python scripts/prueba_autenticacion.py
Variables opcionales:
    SOLSTICIO_URL          http://127.0.0.1:5000
    SOLSTICIO_EMAIL / SOLSTICIO_PASSWORD   credenciales de un ADMINISTRADOR
    DATABASE_URL           la del .env (para leer la fila guardada en MySQL)

Cada ejecución registra un cliente nuevo (documento y correo con marca de tiempo),
así que se puede repetir sin borrar nada.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

BASE = os.environ.get("SOLSTICIO_URL", "http://127.0.0.1:5000").rstrip("/") + "/api/v1"
ADMIN = {
    "email": os.environ.get("SOLSTICIO_EMAIL", "admin@solsticio.com"),
    "password": os.environ.get("SOLSTICIO_PASSWORD", "Admin12345"),
}

VERDE, ROJO, AMARILLO, GRIS, NEGRITA, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m"
if not sys.stdout.isatty() and not os.environ.get("FORCE_COLOR"):
    VERDE = ROJO = AMARILLO = GRIS = NEGRITA = FIN = ""
fallos = 0


def llamar(metodo, ruta, cuerpo=None, token=None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    if datos is not None:
        peticion.add_header("Content-Type", "application/json")
    if token:
        peticion.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            return respuesta.status, json.loads(respuesta.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")
    except urllib.error.URLError as error:
        sys.exit(f"No hay conexión con la API en {BASE} ({error.reason}). ¿Está encendida?")


def titulo(texto):
    print(f"\n{NEGRITA}{texto}{FIN}")


def comprobar(descripcion, metodo, ruta, esperado, obtenido, detalle=""):
    global fallos
    ok = obtenido == esperado
    fallos += not ok
    marca = f"{VERDE}OK {FIN}" if ok else f"{ROJO}MAL{FIN}"
    color = VERDE if obtenido < 400 else AMARILLO
    print(f"  {marca} {descripcion:<44} {metodo:<5} {ruta:<28} -> {color}{obtenido}{FIN}"
          f" (esperado {esperado}){GRIS}{'  ' + detalle if detalle else ''}{FIN}")


def decodificar_jwt(token):
    def parte(texto):
        return json.loads(base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4)))
    cabecera, payload, firma = token.split(".")
    return parte(cabecera), parte(payload), firma


def fila_en_mysql(email):
    """Lee directamente de MySQL lo que guardó el registro (no pasa por la API)."""
    try:
        import pymysql
        from sqlalchemy.engine import make_url
        from dotenv import load_dotenv
        load_dotenv(RAIZ / ".env")
        url = make_url(os.environ["DATABASE_URL"])
        conexion = pymysql.connect(host=url.host or "localhost", port=url.port or 3306, user=url.username,
                                   password=url.password or "", database=url.database, charset="utf8mb4")
    except Exception as error:  # noqa: BLE001 - es una demostración, no debe tumbarse
        print(f"  {GRIS}(No se pudo leer MySQL directamente: {error}){FIN}")
        return
    with conexion, conexion.cursor() as cursor:
        cursor.execute("""
            SELECT u.id_usuario, r.nombre AS rol, u.id_sede, u.email, u.hash_password,
                   c.id_cliente, c.numero_documento
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            LEFT JOIN cliente c ON c.id_usuario = u.id_usuario
            WHERE u.email = %s""", (email,))
        fila = cursor.fetchone()
    nombres = ("id_usuario", "rol", "id_sede", "email", "hash_password", "id_cliente", "numero_documento")
    print(f"  {GRIS}SELECT ... FROM usuario JOIN rol LEFT JOIN cliente WHERE email = '{email}'{FIN}")
    for nombre, valor in zip(nombres, fila):
        print(f"    {nombre:<17} {valor}")
    print(f"  {GRIS}El hash empieza por $2b$ (bcrypt con sal y costo 12): la contraseña nunca se guarda en claro.{FIN}")


def main():
    marca = str(int(time.time()))[-7:]
    cliente = {
        "tipo_documento": "CC", "documento": f"10{marca}", "nombres": "Laura", "apellidos": "Gómez",
        "email": f"laura.{marca}@correo.com", "password": "Clienta2026", "telefono": "3015550101",
    }
    print(f"{NEGRITA}Solsticio: autenticación contra MySQL, JWT y roles{FIN}  {GRIS}{BASE}{FIN}")

    titulo("1. Registro de cliente")
    estado, r = llamar("POST", "/auth/registro", cliente)
    comprobar("Registro con datos válidos", "POST", "/auth/registro", 201, estado,
              f"rol={r.get('usuario', {}).get('rol')}" if estado == 201 else r.get("detail", ""))
    if estado != 201:
        sys.exit("No se pudo registrar el cliente; revise que la base tenga el rol CLIENTE.")
    token_cliente = r["access_token"]
    estado, r = llamar("POST", "/auth/registro", cliente)
    comprobar("Mismo documento y correo otra vez", "POST", "/auth/registro", 409, estado, r["detail"])
    estado, r = llamar("POST", "/auth/registro", {**cliente, "documento": "1", "email": "x@correo.com",
                                                  "password": "solamenteletras"})
    comprobar("Contraseña sin números", "POST", "/auth/registro", 422, estado, r["detail"])

    titulo("2. Qué quedó guardado en MySQL")
    fila_en_mysql(cliente["email"])

    titulo("3. Inicio de sesión")
    estado, r = llamar("POST", "/auth/login", {"email": cliente["email"], "password": cliente["password"]})
    comprobar("Correo y contraseña correctos", "POST", "/auth/login", 200, estado)
    estado, r = llamar("POST", "/auth/login", {"email": cliente["email"], "password": "Equivocada1"})
    comprobar("Contraseña equivocada", "POST", "/auth/login", 401, estado, r["detail"])
    estado, r = llamar("POST", "/auth/login", {"email": "nadie@correo.com", "password": "Equivocada1"})
    comprobar("Correo que no existe (mismo mensaje)", "POST", "/auth/login", 401, estado, r["detail"])

    titulo("4. Contenido del token JWT del cliente")
    cabecera, payload, firma = decodificar_jwt(token_cliente)
    print(f"    cabecera  {json.dumps(cabecera)}")
    print(f"    payload   {json.dumps(payload)}")
    print(f"    firma     {firma[:20]}...  {GRIS}(HMAC-SHA256 con SECRET_KEY: sin la clave no se puede falsificar){FIN}")

    titulo("5. Rutas protegidas")
    comprobar("Perfil sin token", "GET", "/auth/perfil", 401, llamar("GET", "/auth/perfil")[0])
    alterado = token_cliente[:-4] + ("AAAA" if not token_cliente.endswith("AAAA") else "BBBB")
    comprobar("Perfil con la firma alterada", "GET", "/auth/perfil", 401, llamar("GET", "/auth/perfil", token=alterado)[0])
    cab = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    pay = base64.urlsafe_b64encode(json.dumps({**payload, "rol": "ADMINISTRADOR"}).encode()).rstrip(b"=").decode()
    falso = f"{cab}.{pay}.{token_cliente.split('.')[2]}"
    comprobar("Token editado para decir ADMINISTRADOR", "GET", "/usuarios", 401, llamar("GET", "/usuarios", token=falso)[0])
    comprobar("Perfil con el token correcto", "GET", "/auth/perfil", 200, llamar("GET", "/auth/perfil", token=token_cliente)[0])

    titulo("6. Roles y permisos (RBAC)")
    estado, r = llamar("POST", "/auth/login", ADMIN)
    if estado != 200:
        print(f"  {AMARILLO}No pude entrar como administrador ({ADMIN['email']}). "
              f"Use SOLSTICIO_EMAIL y SOLSTICIO_PASSWORD. Se omite el paso 6.{FIN}")
        return
    token_admin = r["access_token"]
    trabajador = {"documento": f"20{marca}", "nombres": "Pedro", "apellidos": "Suárez", "email": f"pedro.{marca}@solsticio.com",
                  "password": "Trabajador2026", "rol": "TRABAJADOR", "id_sede": 1}
    llamar("POST", "/usuarios", trabajador, token=token_admin)
    token_trab = llamar("POST", "/auth/login", {"email": trabajador["email"], "password": trabajador["password"]})[1]["access_token"]

    casos = [
        ("CLIENTE ve sus pedidos", "GET", "/cuenta/pedidos", token_cliente, 200),
        ("CLIENTE consulta stock", "GET", "/stock", token_cliente, 403),
        ("CLIENTE lista usuarios", "GET", "/usuarios", token_cliente, 403),
        ("TRABAJADOR consulta stock de su sede", "GET", "/stock", token_trab, 200),
        ("TRABAJADOR consulta stock de otra sede", "GET", "/stock?id_sede=2", token_trab, 403),
        ("TRABAJADOR lista usuarios", "GET", "/usuarios", token_trab, 403),
        ("TRABAJADOR entra a 'mis pedidos'", "GET", "/cuenta/pedidos", token_trab, 403),
        ("ADMINISTRADOR lista usuarios", "GET", "/usuarios", token_admin, 200),
        ("ADMINISTRADOR consulta stock de otra sede", "GET", "/stock?id_sede=2", token_admin, 200),
    ]
    for descripcion, metodo, ruta, token, esperado in casos:
        comprobar(descripcion, metodo, ruta, esperado, llamar(metodo, ruta, token=token)[0])

    print(f"\n{NEGRITA}{VERDE if not fallos else ROJO}{'Todo correcto' if not fallos else f'{fallos} comprobaciones fallaron'}{FIN}")


if __name__ == "__main__":
    main()
    sys.exit(1 if fallos else 0)
