# Solsticio API

API REST del sistema multisede de inventario y ventas **Solsticio**, una tienda de ropa con varias sedes en Bogotá. Es un proyecto académico de la asignatura Nuevas Tecnologías de Desarrollo.

El sistema centraliza las existencias por sede, registra las ventas web y en tienda, y deja trazabilidad de cada movimiento de mercancía. También cubre los traslados entre sedes, los pagos y la facturación electrónica ante la DIAN (estos dos últimos, simulados).

## Tecnologías

| Componente | Herramienta |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Flask 3.0 |
| ORM | Flask-SQLAlchemy 3.1 / SQLAlchemy 2.0 |
| Base de datos | MySQL 8.0 (driver PyMySQL) |
| Autenticación | JWT (PyJWT) + bcrypt |
| Servidor de producción | Gunicorn |
| Pruebas de endpoints | Postman |

## Estructura

```
app.py                     # punto de entrada: python app.py / gunicorn app:app
requirements.txt
.env.example               # plantilla de variables de entorno (.env no se versiona)
api/
  __init__.py              # crear_app(): configuración, base de datos, rutas, errores
  config.py                # lectura de variables de entorno
  modelos.py               # modelos Flask-SQLAlchemy (reflejan database/solsticio_schema.sql)
  seguridad.py             # JWT, bcrypt y control de roles y sedes
  validacion.py            # validación de datos de entrada
  serializadores.py        # conversión de modelos a JSON
  errores.py               # ErrorApi y manejadores -> {"detail": "..."}
  comandos.py              # flask verificar-bd / crear-admin
  rutas/                   # capa HTTP: un blueprint por módulo, bajo /api/v1
    auth.py  catalogo.py  inventario.py  pedidos.py  admin.py
  servicios/               # lógica de negocio y transacciones
    comun.py  inventario.py  traslados.py  pedidos.py  facturacion.py  catalogo.py  usuarios.py
database/
  solsticio_schema.sql     # script de creación de la base de datos (23 tablas)
docs/                      # modelo de datos, diagrama DBML y diagramas de casos de uso
postman/
  Solsticio.postman_collection.json
legacy/prototipo/          # primer prototipo (SQLite + frontends HTML), ya no se usa
```

Flujo de una petición: **ruta** (valida permisos y datos) → **servicio** (reglas de negocio y transacción) → **modelo** (base de datos) → **serializador** (JSON de respuesta).

## Instalación

1. Crear la base de datos ejecutando el script completo en MySQL:
   ```bash
   mysql -u root -p < database/solsticio_schema.sql
   ```
2. Crear el entorno virtual e instalar dependencias:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   source .venv/bin/activate       # Linux / macOS
   pip install -r requirements.txt
   ```
3. Configurar las variables de entorno: copiar `.env.example` a `.env` y completarlo.
   ```
   DATABASE_URL=mysql+pymysql://root:CLAVE@localhost:3306/solsticio
   SECRET_KEY=una-clave-larga-y-aleatoria
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   DIAN_SIMULACION=true
   PASARELA_SIMULACION=true
   ```
4. Verificar la conexión y crear el primer administrador:
   ```bash
   flask --app app verificar-bd
   flask --app app crear-admin
   ```

## Ejecución

```bash
python app.py                 # desarrollo: http://127.0.0.1:5000
gunicorn app:app              # producción (Linux / Render)
```

> Gunicorn no corre de forma nativa en Windows. En local se usa `python app.py` o WSL.

## Pruebas con Postman

1. Importar `postman/Solsticio.postman_collection.json`.
2. Ejecutar **POST /api/v1/auth/login**. El token se guarda solo en la variable `{{token}}` de la colección.
3. Las demás peticiones envían `Authorization: Bearer {{token}}` automáticamente.

Flujo sugerido: login → crear categoría → crear producto → crear variantes → ingreso de inventario → crear pedido → pagar → consultar factura → traslado (crear, despachar, recibir).

## Endpoints

| Módulo | Método | Ruta | Acceso |
|---|---|---|---|
| Autenticación | POST | `/api/v1/auth/login` | Público |
| Autenticación | GET | `/api/v1/auth/perfil` | Autenticado |
| Catálogo | GET | `/api/v1/categorias` | Público |
| Catálogo | GET | `/api/v1/sedes` | Público |
| Catálogo | GET | `/api/v1/productos` | Público |
| Catálogo | GET | `/api/v1/productos/{id_producto}` | Público |
| Catálogo | GET | `/api/v1/variantes/qr/{codigo_qr}` | Público |
| Catálogo | GET | `/api/v1/variantes/{id_variante}/disponibilidad` | Público |
| Catálogo | GET | `/api/v1/tallas`, `/api/v1/colores` | Público |
| Inventario | GET | `/api/v1/stock` | Trabajador |
| Inventario | POST | `/api/v1/inventario/ingresos` | Trabajador |
| Inventario | POST | `/api/v1/inventario/ajustes` | Administrador |
| Inventario | GET | `/api/v1/inventario/movimientos` | Administrador |
| Inventario | POST | `/api/v1/traslados` | Administrador |
| Inventario | GET | `/api/v1/traslados/{id_traslado}` | Trabajador |
| Inventario | PATCH | `/api/v1/traslados/{id_traslado}/despachar` | Trabajador |
| Inventario | PATCH | `/api/v1/traslados/{id_traslado}/recibir` | Trabajador |
| Pedidos | POST | `/api/v1/pedidos` | Público (WEB) / Trabajador (TIENDA) |
| Pedidos | GET | `/api/v1/pedidos` | Trabajador |
| Pedidos | GET | `/api/v1/pedidos/{id_pedido}` | Trabajador |
| Pedidos | GET | `/api/v1/pedidos/qr/{codigo_qr}` | Trabajador |
| Pedidos | PATCH | `/api/v1/pedidos/{id_pedido}/estado` | Trabajador |
| Pagos | GET | `/api/v1/metodos-pago` | Público |
| Pagos | POST | `/api/v1/pedidos/{id_pedido}/pagos` | Público / Trabajador |
| Facturación | POST | `/api/v1/pedidos/{id_pedido}/factura` | Trabajador |
| Facturación | GET | `/api/v1/facturas/{id_factura}` | Trabajador |
| Administración | POST | `/api/v1/productos` | Administrador |
| Administración | PUT | `/api/v1/productos/{id_producto}` | Administrador |
| Administración | DELETE | `/api/v1/productos/{id_producto}` | Administrador |
| Administración | POST | `/api/v1/productos/{id_producto}/variantes` | Administrador |
| Administración | POST | `/api/v1/categorias` | Administrador |
| Administración | POST | `/api/v1/sedes` | Administrador |
| Administración | POST | `/api/v1/usuarios` | Administrador |

Los errores responden `{"detail": "mensaje"}` con el código HTTP correspondiente (400, 401, 402, 403, 404, 409, 422).

## Reglas de negocio implementadas

- Toda variación de existencias genera una fila en `movimiento_inventario` (INGRESO, VENTA, TRASLADO_SALIDA, TRASLADO_ENTRADA, AJUSTE).
- Un pedido descuenta stock solo de su sede. Si no hay existencias, responde 409 con las sedes alternativas.
- Al crear el pedido las unidades quedan reservadas y se descuentan cuando el pago se aprueba. Si el pago se rechaza, la reserva se libera.
- El precio unitario del pedido es histórico: cambiar el precio del catálogo no altera ventas anteriores.
- Un traslado genera dos movimientos: salida al despachar y entrada al recibir. Origen y destino no pueden ser la misma sede.
- Un trabajador solo opera sobre su sede; el administrador es global.
- Si la DIAN (simulada) falla, la factura queda PENDIENTE sin bloquear la venta.
- No hay borrado físico: los productos se desactivan.

## Pendiente

- Devoluciones y cambios (`/api/v1/devoluciones`) con nota crédito.
- Reportes (`/api/v1/reportes/...`).
- Registro público de clientes (`/api/v1/auth/registro`).
- Nuevos frontends sobre `/api/v1` (los del prototipo están en `legacy/prototipo/`).

## Autores

Miguel Angel Marin Baracaldo · Joan Sebastian Lara Fuenmayor
