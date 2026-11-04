# Solsticio API

API REST del sistema multisede de inventario y ventas **Solsticio**, una tienda de ropa con varias sedes en Bogotá. Es un proyecto académico de la asignatura Nuevas Tecnologías de Desarrollo.

El sistema centraliza las existencias por sede, registra las ventas web y en tienda, y deja trazabilidad de cada movimiento de mercancía. También cubre los traslados entre sedes, los pagos y la facturación electrónica ante la DIAN (estos dos últimos, simulados).

Desde la **Entrega 2** la API usa **persistencia políglota**: MySQL para los datos estructurados y transaccionales, y **MongoDB** para la bitácora de actividad, los escaneos de códigos QR, las reseñas de productos y las fichas técnicas con atributos variables. Ver [Integración NoSQL (MongoDB)](#integración-nosql-mongodb). La justificación del modelo documental está en [`docs/Entrega2_NoSQL_Solsticio.pdf`](docs/Entrega2_NoSQL_Solsticio.pdf).

## Contenido

- [Tecnologías](#tecnologías)
- [Requisitos previos](#requisitos-previos)
- [Instalación de las herramientas (Windows)](#instalación-de-las-herramientas-windows)
- [Cómo correr el proyecto](#cómo-correr-el-proyecto)
- [Uso diario](#uso-diario)
- [Problemas frecuentes](#problemas-frecuentes)
- [Pruebas con Postman](#pruebas-con-postman)
- [Pruebas automáticas (pytest)](#pruebas-automáticas-pytest)
- [Evidencias de pruebas](#evidencias-de-pruebas)
- [Integración NoSQL (MongoDB)](#integración-nosql-mongodb)
- [Tienda web](#tienda-web)
- [Endpoints](#endpoints)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Reglas de negocio implementadas](#reglas-de-negocio-implementadas)
- [Pendiente](#pendiente)

## Tecnologías

| Componente | Herramienta |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Flask 3.0 |
| ORM | Flask-SQLAlchemy 3.1 / SQLAlchemy 2.0 |
| Base de datos relacional | MySQL 8.0 (driver PyMySQL) |
| Base de datos documental (NoSQL) | MongoDB 7 (driver PyMongo 4.10) |
| Autenticación | JWT (PyJWT) + bcrypt |
| Servidor de producción | Gunicorn |
| Pruebas de endpoints | Postman |

## Requisitos previos

| Programa | Para qué | Cómo comprobar que ya está |
|---|---|---|
| **Python 3.12 o superior** | Ejecutar la API | `python --version` |
| **MySQL Server 8.0** | Base de datos | `mysql --version`, o ver el servicio `MySQL80` en ejecución |
| **MySQL Workbench** | Ver la base y ejecutar el script SQL con interfaz gráfica | Buscarlo en el menú Inicio |
| **MongoDB Community Server 7** | Base documental (NoSQL) | Ver el servicio `MongoDB` en ejecución, o `mongod --version` |
| **MongoDB Compass** (opcional) | Ver las colecciones y documentos con interfaz gráfica | Buscarlo en el menú Inicio |
| **Git** | Descargar el repositorio | `git --version` |
| **Postman** | Probar los endpoints | Buscarlo en el menú Inicio |

Si ya tienes todo, salta a [Cómo correr el proyecto](#cómo-correr-el-proyecto). Si no, sigue la guía de abajo.

## Instalación de las herramientas (Windows)

Esta guía es para quien nunca ha instalado estas herramientas. Si algo ya lo tienes, sáltate esa parte.

### Python

1. Descargar el instalador desde https://www.python.org/downloads/.
2. En la primera pantalla, **marcar la casilla `Add python.exe to PATH`** antes de pulsar *Install Now*. Si no se marca, la terminal no reconocerá el comando `python`.
3. Cerrar y volver a abrir la terminal, y comprobar con `python --version`.

> Si `python` abre la Microsoft Store en lugar de responder con la versión, desactiva los alias en *Configuración → Aplicaciones → Configuración avanzada de aplicaciones → Alias de ejecución de aplicaciones* (apagar `python.exe` y `python3.exe`).

### MySQL Server y MySQL Workbench

MySQL no viene instalado en Windows. Tener solo Workbench no basta: Workbench es el cliente gráfico, pero la base de datos la guarda **MySQL Server**, que se instala aparte.

1. Descargar **MySQL Installer for Windows** desde https://dev.mysql.com/downloads/installer/. Elige el archivo más grande (`mysql-installer-community-8.0.x.msi`). La página pide iniciar sesión, pero abajo tiene el enlace **"No thanks, just start my download"**.
2. Ejecutar el instalador. En **Choosing a Setup Type** elegir **Custom** y agregar a la lista de productos:
   - `MySQL Server 8.0.x`
   - `MySQL Workbench 8.0.x`
3. Pulsar *Next* y luego *Execute* para descargar e instalar. Esperar a que todo quede con el check verde.
4. Después viene la **configuración del servidor**. Estas pantallas son las que confunden:

   | Pantalla | Qué elegir |
   |---|---|
   | **Type and Networking** | *Config Type:* `Development Computer`. Dejar marcado `TCP/IP` con el puerto **3306**. |
   | **Authentication Method** | `Use Strong Password Encryption` (la opción recomendada). |
   | **Accounts and Roles** | Escribir la **contraseña del usuario `root`** dos veces. **Anótala**: la vas a necesitar en Workbench y en el archivo `.env`. |
   | **Windows Service** | Dejar marcado `Configure MySQL Server as a Windows Service`, con el nombre `MySQL80` y `Start the MySQL Server at System Startup`. Así MySQL arranca solo al encender el PC. |
   | **Server File Permissions** | Dejar la opción por defecto. |
   | **Apply Configuration** | Pulsar *Execute* y esperar a que todos los pasos queden en verde. Luego *Finish*. |

5. **Comprobar que funciona:** abrir MySQL Workbench. En la pantalla de inicio debe aparecer una conexión `Local instance MySQL80` (`root@localhost:3306`). Al abrirla pide la contraseña de `root`. Si conecta, el servidor está bien.

> Si la conexión no aparece, créala con el botón **+**: *Hostname* `127.0.0.1`, *Port* `3306`, *Username* `root`.

#### Usar `mysql` desde la terminal (opcional)

El instalador no agrega MySQL al `PATH`, así que `mysql` no se reconoce en la terminal. No hace falta si usas Workbench. Si lo quieres:

1. Buscar en el menú Inicio **"Editar las variables de entorno del sistema"** → botón **Variables de entorno**.
2. En *Variables del sistema* seleccionar `Path` → **Editar** → **Nuevo** y pegar `C:\Program Files\MySQL\MySQL Server 8.0\bin`.
3. Aceptar todo, **cerrar y volver a abrir la terminal** y comprobar con `mysql --version`.

#### Encender MySQL si está apagado

Si aparece `Can't connect to MySQL server`, el servicio puede estar detenido:

- Pulsar `Win + R`, escribir `services.msc`, buscar **MySQL80** → clic derecho → **Iniciar**.
- O en una terminal **abierta como administrador**: `net start MySQL80`.

### MongoDB Community Server y Compass

1. Descargar el instalador `.msi` desde https://www.mongodb.com/try/download/community (versión 7.0 o superior, plataforma Windows).
2. Elegir **Complete** y dejar marcado **Install MongoD as a Service** (nombre `MongoDB`). Así arranca solo con el PC y escucha en `localhost:27017`.
3. Dejar marcado **Install MongoDB Compass** para tener el cliente gráfico.
4. **Comprobar:** abrir Compass y conectar a `mongodb://localhost:27017`. Si conecta, el servidor está bien.

No hay que crear la base ni las colecciones: la API crea la base `solsticio`, sus colecciones e índices la primera vez que arranca.

> **Alternativa sin instalar nada:** crear un clúster gratuito M0 en [MongoDB Atlas](https://www.mongodb.com/atlas) y usar su cadena de conexión `mongodb+srv://...` en `MONGO_URI`. Con Docker: `docker run -d --name mongo -p 27017:27017 mongo:7`.

Si el servicio está detenido: `Win + R` → `services.msc` → **MongoDB** → **Iniciar**.

### Git

1. Descargar desde https://git-scm.com/download/win e instalar con las opciones por defecto. Esto también instala **Git Bash**.
2. Comprobar con `git --version`.

### Postman

Descargar desde https://www.postman.com/downloads/ e instalar. Pide crear una cuenta, que es gratuita.

### Descargar el repositorio

```bash
git clone https://github.com/miguelamarinb-ops/Solsticio.git
cd Solsticio
```

## Cómo correr el proyecto

Todos los comandos se ejecutan **dentro de la carpeta `Solsticio/`**, la que contiene `app.py`. En VS Code se puede abrir esa carpeta y usar la terminal integrada (`Ctrl + ñ`).

### 1. Crear la base de datos

El script `database/solsticio_schema.sql` crea la base `solsticio`, sus tablas y los datos iniciales: roles, tallas, colores, métodos de pago y sedes.

> **Cuidado:** el script empieza con `DROP DATABASE IF EXISTS solsticio`, así que borra todo lo que haya. Ejecútalo solo la primera vez o cuando quieras empezar de cero.

Elige una de estas formas:

| Dónde | Comando |
|---|---|
| **MySQL Workbench** (recomendado) | Ver los pasos de abajo. |
| **cmd** o **Git Bash** | `mysql -u root -p < database/solsticio_schema.sql` |
| **PowerShell** | `Get-Content database/solsticio_schema.sql -Raw \| mysql -u root -p` |

Con **MySQL Workbench**:

1. Abrir la conexión `Local instance MySQL80` e ingresar la contraseña de `root`.
2. Menú **File → Open SQL Script…** y elegir `database/solsticio_schema.sql`.
3. Pulsar el **rayo** ⚡ de la barra del editor, el primero, que ejecuta todo el script. No uses el rayo con cursor, porque ese ejecuta solo una sentencia.
4. En el panel izquierdo (*Schemas*), pulsar el botón de refrescar. Debe aparecer la base `solsticio` con sus tablas.

Los comandos de terminal piden la contraseña de `root`. Si dicen `mysql: command not found`, usa Workbench o agrega MySQL al `PATH` como se explica en [Usar `mysql` desde la terminal](#usar-mysql-desde-la-terminal-opcional).

### 2. Crear y activar el entorno virtual

```bash
python -m venv .venv
```

La activación depende de la terminal:

| Terminal | Comando para activar |
|---|---|
| PowerShell | `.venv\Scripts\Activate.ps1` |
| cmd | `.venv\Scripts\activate.bat` |
| Git Bash (Windows) | `source .venv/Scripts/activate` |
| Linux / macOS / WSL | `source .venv/bin/activate` |

Sabrás que quedó activo porque la línea de la terminal empieza con `(.venv)`.

### 3. Instalar las dependencias

Con el entorno activo:

```bash
pip install -r requirements.txt
```

> Gunicorn se instala también en Windows, pero allí no se ejecuta. Es normal: solo se usa al desplegar.

### 4. Configurar las variables de entorno

Copia la plantilla y edítala:

```bash
cp .env.example .env        # Git Bash / Linux / macOS
copy .env.example .env      # cmd / PowerShell
```

Contenido de `.env`:

```
DATABASE_URL=mysql+pymysql://root:TU_CLAVE@localhost:3306/solsticio
SECRET_KEY=una-clave-larga-y-aleatoria
ACCESS_TOKEN_EXPIRE_MINUTES=60
DIAN_SIMULACION=true
PASARELA_SIMULACION=true
MONGO_URI=mongodb://localhost:27017
MONGO_DB=solsticio
MONGO_TIMEOUT_MS=2000
```

| Variable | Qué es |
|---|---|
| `DATABASE_URL` | Conexión a MySQL. Cambia `TU_CLAVE` por la contraseña de `root` que pusiste al instalar MySQL. |
| `SECRET_KEY` | Clave con la que se firman los tokens JWT. Puede ser cualquier texto largo. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Minutos de validez del token. |
| `DIAN_SIMULACION` / `PASARELA_SIMULACION` | En `true`, la DIAN y la pasarela de pagos se simulan. |
| `MONGO_URI` | Conexión a MongoDB. En local `mongodb://localhost:27017`; en Atlas, la cadena `mongodb+srv://usuario:clave@cluster.../`. |
| `MONGO_DB` | Nombre de la base documental. |
| `MONGO_TIMEOUT_MS` | Milisegundos que la API espera a MongoDB antes de darlo por caído. |

La URL tiene la forma `mysql+pymysql://USUARIO:CONTRASEÑA@SERVIDOR:PUERTO/BASE`. Por ejemplo, con la contraseña `Clave123`:

```
DATABASE_URL=mysql+pymysql://root:Clave123@localhost:3306/solsticio
```

> **Contraseñas con símbolos:** si la contraseña tiene `@`, `:`, `/`, `#`, `?` o `%`, la URL se rompe. Hay que reemplazar cada símbolo por su código: `@` → `%40`, `:` → `%3A`, `/` → `%2F`, `#` → `%23`, `?` → `%3F`, `%` → `%25`. Por ejemplo, `Mi@Clave#1` se escribe `Mi%40Clave%231`.

El archivo `.env` no se sube al repositorio: cada integrante crea el suyo con su propia contraseña.

### 5. Verificar la conexión a la base de datos

```bash
flask --app app verificar-bd
```

Respuesta esperada:

```
Conexión correcta. Tablas en la base de datos: 23
```

Y la de MongoDB (crea los índices si no existen):

```bash
flask --app app verificar-mongo
```

```
Conexión correcta a MongoDB 7.0.x, base 'solsticio'.
  actividad_usuario: 0 documentos
  escaneos_qr: 0 documentos
  resenas_producto: 0 documentos
  fichas_producto: 0 documentos
```

### 6. Crear el primer administrador

```bash
flask --app app crear-admin
```

El comando pide email, documento, nombres, apellidos y contraseña (dos veces). Con ese email y contraseña se inicia sesión en Postman y en el [panel del personal](#panel-del-personal-panel).

### 6.1 Cargar el catálogo de ejemplo (opcional)

Para ver la tienda con prendas, existencias, fichas técnicas y opiniones:

```bash
flask --app app sembrar-demo
```

Crea 6 categorías y 12 prendas con ilustración, sus tallas y colores, existencias repartidas en las sedes (cada una con su movimiento de ingreso), fichas técnicas y opiniones en MongoDB. Se puede ejecutar varias veces: no duplica nada.

### 7. Levantar el servidor

```bash
python app.py
```

Abre **http://127.0.0.1:5000** en el navegador: ahí está la [tienda web](#tienda-web). La API vive en **http://127.0.0.1:5000/api/v1**, que debe responder:

```json
{"api": "Solsticio", "version": "v1", "base": "/api/v1"}
```

Para detener el servidor, pulsa `Ctrl + C`.

## Uso diario

Una vez hecha la instalación, cada vez que vuelvas a trabajar solo necesitas:

```bash
cd Solsticio
source .venv/Scripts/activate    # o el comando de tu terminal (paso 2)
python app.py
```

MySQL y MongoDB tienen que estar encendidos. Si MongoDB está apagado la API arranca igual: lo que depende de MySQL sigue funcionando, los endpoints de reseñas y fichas responden 503 y la bitácora deja de registrarse (con un aviso en la consola).

### Producción (Render)

En el servidor se usa Gunicorn en lugar de `python app.py`:

```bash
gunicorn app:app
```

Las variables del paso 4 se definen en el panel del servicio en lugar de en un `.env`. Gunicorn no corre de forma nativa en Windows; para probarlo en local usa WSL.

## Problemas frecuentes

| Error | Causa y solución |
|---|---|
| `python` no se reconoce o abre la Microsoft Store | Python no quedó en el `PATH`. Reinstálalo marcando `Add python.exe to PATH` y desactiva los alias de la Store (ver [Python](#python)). |
| `flask: command not found` | El entorno virtual no está activo. Actívalo (paso 2). |
| `Error: No such command 'verificar-bd'` | Flask no pudo cargar `app.py`, casi siempre por falta de dependencias (por ejemplo `No module named 'bcrypt'`). Activa el entorno y ejecuta `pip install -r requirements.txt`. |
| `RuntimeError: Falta DATABASE_URL` / `Falta SECRET_KEY` | No existe `.env` o le falta esa variable (paso 4). |
| `Access denied for user 'root'` | Usuario o contraseña incorrectos en `DATABASE_URL`. Si la contraseña tiene símbolos, revisa la nota del paso 4. |
| `Can't connect to MySQL server` | MySQL no está encendido o no escucha en el puerto 3306. Inícialo como se explica en [Encender MySQL](#encender-mysql-si-está-apagado). |
| `'cryptography' package is required for sha256_password or caching_sha2_password` | Falta la librería `cryptography`, que MySQL 8 necesita para su método de autenticación. Ejecuta `pip install -r requirements.txt` con el entorno activo. |
| `mysql: command not found` | MySQL no está en el `PATH`. Usa Workbench o [agrégalo al PATH](#usar-mysql-desde-la-terminal-opcional). |
| `Unknown database 'solsticio'` | Falta ejecutar el script de la base de datos (paso 1). |
| `No se pudo conectar a MongoDB` / respuestas `503` en reseñas o fichas | MongoDB no está encendido o `MONGO_URI` está mal. Inicia el servicio `MongoDB` o revisa la variable. |
| `No module named 'pymongo'` | Faltan dependencias: `pip install -r requirements.txt`. |
| PowerShell no deja ejecutar `Activate.ps1` | Ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| `401` en Postman | Falta hacer login o el token venció. Vuelve a ejecutar **POST /api/v1/auth/login**. |

## Pruebas con Postman

1. Importar `postman/Solsticio.postman_collection.json`.
2. Confirmar que la variable de colección `base_url` vale `http://127.0.0.1:5000`.
3. Ejecutar **POST /api/v1/auth/login** con el administrador creado en el paso 6. El token se guarda solo en la variable `{{token}}`.
4. Las demás peticiones envían `Authorization: Bearer {{token}}` automáticamente.

Flujo sugerido: login → crear categoría → crear producto → crear variantes → ingreso de inventario → crear pedido → pagar → consultar factura → traslado (crear, despachar, recibir).

Para la parte NoSQL: crear ficha técnica → crear reseña (con el `codigo_qr` del pedido pagado como `codigo_pedido`) → listar reseñas → escanear QR de variantes → `GET /auth/perfil/actividad` → `GET /productos/1/completo` → `GET /reportes/qr-mas-escaneados`. Las carpetas **Fichas técnicas (MongoDB)**, **Reseñas (MongoDB)** y **Combinados SQL + NoSQL** de la colección traen estas peticiones; el id de la reseña creada se guarda solo en `{{id_resena}}`.

También se puede recorrer todo el flujo con un script, con la API corriendo y las bases vacías:

```bash
python scripts/flujo_demo_nosql.py
```

Por defecto inicia sesión como `admin@solsticio.com` / `Admin12345`. Si tu administrador tiene otros datos, defínelos antes (PowerShell):

```powershell
$env:SOLSTICIO_EMAIL = "tu@correo.com"; $env:SOLSTICIO_PASSWORD = "tu-clave"
python scripts/flujo_demo_nosql.py
```

## Pruebas automáticas (pytest)

47 pruebas de integración contra **MySQL y MongoDB reales**. Usan bases aparte llamadas `solsticio_test`, que se crean y se vacían solas, así que **no tocan tus datos de desarrollo**. Toman el usuario, la clave y el puerto de MySQL del `.env`.

```bash
pip install -r requirements-dev.txt
pytest
```

No hace falta que la API esté corriendo, pero MySQL y MongoDB sí deben estar encendidos. Si alguno no responde, las pruebas se marcan como omitidas (`skipped`) en vez de fallar.

| Archivo | Qué comprueba |
|---|---|
| `test_fichas.py` | CRUD de fichas técnicas, versión, atributos distintos por prenda, bloqueo de claves `$`/`.`, búsqueda por atributos sin tildes con stock de MySQL |
| `test_resenas.py` | CRUD de reseñas, compra verificada contra MySQL, una reseña por email, validaciones, resumen con `$facet`, moderación y permisos |
| `test_combinados.py` | Perfil (MySQL) + últimas 10 actividades (MongoDB), bitácora con errores y parámetros, escaneos QR, ranking de QR con stock, producto completo |
| `test_degradacion.py` | Con MongoDB caído la API arranca, MySQL sigue respondiendo, `/completo` devuelve `nosql_disponible: false` y los endpoints NoSQL responden 503 |
| `test_web.py` | La tienda se sirve en `/`, sus CSS y JS cargan, y `/productos?sede=` cuenta el stock de una sola sede |
| `test_panel_api.py` | Listados para el panel (traslados, usuarios, opiniones para moderar, prendas desactivadas), activar y desactivar usuarios, y las páginas `/escanear`, `/carrito` y `/panel` |

Resultado esperado:

```
47 passed
```

## Evidencias de pruebas

Capturas de la colección ejecutada en Postman contra la API en local. Las imágenes están en `docs/imagenes/`.

Algunas respuestas son **409 Conflict** a propósito: las peticiones se ejecutaron sobre datos que ya existían y la API aplicó correctamente sus validaciones de negocio (nombres duplicados, stock insuficiente, transiciones de estado no permitidas).

### Autenticación

| Petición | Resultado |
|---|---|
| POST `/api/v1/auth/login` | 200 OK: devuelve `access_token` y datos del usuario |
| GET `/api/v1/auth/perfil` | 200 OK: perfil del administrador autenticado |

![Login](docs/imagenes/01-auth-login.png)
![Perfil](docs/imagenes/02-auth-perfil.png)

### Catálogo

| Petición | Resultado |
|---|---|
| GET `/api/v1/categorias` | 200 OK |
| GET `/api/v1/sedes` | 200 OK: 4 sedes |
| GET `/api/v1/productos?categoria=1&genero=UNISEX&page=1&size=20` | 200 OK: listado paginado con filtros |
| GET `/api/v1/productos/1` | 200 OK: detalle con imágenes y variantes |
| GET `/api/v1/variantes/qr/SOL-V-000001` | 200 OK: variante encontrada por código QR |
| GET `/api/v1/variantes/1/disponibilidad` | 200 OK: stock por sede |
| GET `/api/v1/tallas` | 200 OK |

![Categorías](docs/imagenes/03-catalogo-categorias.png)
![Sedes](docs/imagenes/04-catalogo-sedes.png)
![Productos con filtros](docs/imagenes/05-catalogo-productos-filtros.png)
![Detalle de producto](docs/imagenes/06-catalogo-producto-detalle.png)
![Variante por QR](docs/imagenes/07-catalogo-variante-qr.png)
![Disponibilidad de variante](docs/imagenes/08-catalogo-variante-disponibilidad.png)
![Tallas](docs/imagenes/09-catalogo-tallas.png)

### Inventario

| Petición | Resultado |
|---|---|
| GET `/api/v1/stock` | 200 OK: existencias por sede y variante |
| POST `/api/v1/inventario/ingresos` | 201 Created: dos movimientos INGRESO con stock anterior y actual |
| POST `/api/v1/inventario/ajustes` | 201 Created: movimiento AJUSTE por conteo físico |
| GET `/api/v1/inventario/movimientos` | 200 OK: historial de movimientos |

![Stock](docs/imagenes/10-inventario-stock.png)
![Ingreso de inventario](docs/imagenes/11-inventario-ingreso.png)
![Ajuste de inventario](docs/imagenes/12-inventario-ajuste.png)
![Movimientos de inventario](docs/imagenes/13-inventario-movimientos.png)

### Traslados

| Petición | Resultado |
|---|---|
| POST `/api/v1/traslados` | 409 Conflict: la sede de origen no tiene existencias suficientes; la respuesta sugiere otra sede con stock |
| PATCH `/api/v1/traslados/1/despachar` | 409 Conflict: el traslado 1 ya estaba RECIBIDO |
| PATCH `/api/v1/traslados/1/recibir` | 409 Conflict: el traslado 1 ya estaba RECIBIDO |

![Crear traslado](docs/imagenes/14-traslado-crear-409.png)
![Despachar traslado](docs/imagenes/15-traslado-despachar-409.png)
![Recibir traslado](docs/imagenes/16-traslado-recibir-409.png)

### Pedidos y ventas

| Petición | Resultado |
|---|---|
| POST `/api/v1/pedidos` | 201 Created: pedido WEB con cliente, envío, subtotal, IVA y total |
| GET `/api/v1/pedidos` | 200 OK: listado paginado |
| GET `/api/v1/pedidos/1` | 200 OK: detalle con pagos y factura |
| GET `/api/v1/pedidos/qr/SOL-P-00000001` | 200 OK: pedido por QR con acción sugerida |
| PATCH `/api/v1/pedidos/1/estado` | 409 Conflict: transición ENVIADO → ENVIADO no permitida; indica los estados válidos |

![Crear pedido](docs/imagenes/17-pedido-crear.png)
![Listar pedidos](docs/imagenes/18-pedido-listar.png)
![Detalle de pedido](docs/imagenes/19-pedido-detalle.png)
![Pedido por QR](docs/imagenes/20-pedido-qr.png)
![Cambiar estado de pedido](docs/imagenes/21-pedido-estado-409.png)

### Pagos y facturación

| Petición | Resultado |
|---|---|
| GET `/api/v1/metodos-pago` | 200 OK |
| POST `/api/v1/pedidos/1/factura` | 409 Conflict: el pedido ya tiene una factura validada por la DIAN |
| GET `/api/v1/facturas/1` | 200 OK: factura con CUFE y estado VALIDADA |

![Métodos de pago](docs/imagenes/22-pagos-metodos.png)
![Emitir factura](docs/imagenes/23-factura-emitir-409.png)
![Consultar factura](docs/imagenes/24-factura-consultar.png)

### Administración

| Petición | Resultado |
|---|---|
| POST `/api/v1/productos` | 201 Created |
| PUT `/api/v1/productos/1` | 200 OK |
| DELETE `/api/v1/productos/1` | 204 No Content: desactivación lógica |
| POST `/api/v1/productos/1/variantes` | 409 Conflict: las combinaciones talla/color ya existían |
| POST `/api/v1/categorias` | 409 Conflict: ya existe una categoría con ese nombre |
| POST `/api/v1/sedes` | 409 Conflict: ya existe una sede con ese nombre |
| POST `/api/v1/usuarios` | 409 Conflict: ya existe un usuario con ese documento o email |

![Crear producto](docs/imagenes/25-admin-producto-crear.png)
![Actualizar producto](docs/imagenes/26-admin-producto-actualizar.png)
![Desactivar producto](docs/imagenes/27-admin-producto-desactivar.png)
![Crear variantes](docs/imagenes/28-admin-variantes-409.png)
![Crear categoría](docs/imagenes/29-admin-categoria-409.png)
![Crear sede](docs/imagenes/30-admin-sede-409.png)
![Crear usuario](docs/imagenes/31-admin-usuario-409.png)

## Integración NoSQL (MongoDB)

### Qué va en cada base

| Dato | Base | Por qué |
|---|---|---|
| Productos, variantes, precios, stock, pedidos, pagos, facturas, usuarios | **MySQL** | Necesitan transacciones ACID, llaves foráneas y consistencia fuerte (no se puede vender stock que no existe). |
| Bitácora de actividad de los usuarios (`actividad_usuario`) | **MongoDB** | Se escribe en **cada** petición autenticada (alta frecuencia), cada evento trae campos distintos y solo interesa por un tiempo (se borra sola a los 180 días con un índice TTL). |
| Escaneos de códigos QR (`escaneos_qr`) | **MongoDB** | Un evento por cada lectura del QR de una prenda, en tienda o desde la web. Volumen alto, solo inserciones y consultas agregadas. TTL de 365 días. |
| Reseñas de productos (`resenas_producto`) | **MongoDB** | Texto libre, atributos opcionales que cambian por prenda, fotos y respuestas de la tienda **embebidas** en el mismo documento. |
| Ficha técnica (`fichas_producto`) | **MongoDB** | Un jean, una camiseta y unos tenis no comparten atributos (tiro, gramaje, suela...). En MySQL serían columnas casi siempre vacías o un modelo EAV. |

Los documentos se enlazan con MySQL por identificador (`id_usuario`, `id_producto`, `id_variante`); el `_id` de la ficha técnica **es** el `id_producto`. La explicación completa, con la estructura de cada colección y sus índices, está en [`docs/Entrega2_NoSQL_Solsticio.pdf`](docs/Entrega2_NoSQL_Solsticio.pdf).

### Ejemplos de documentos

Ficha técnica (los `atributos` cambian por tipo de prenda):

```json
{
  "_id": 1,
  "producto": "Camiseta oversize algodón",
  "categoria": "Camisetas",
  "atributos": {
    "material": "Algodón",
    "composicion": [{ "fibra": "algodón peinado", "porcentaje": 100 }],
    "gramaje_gsm": 240, "cuello": "redondo", "fit": "oversize",
    "certificaciones": ["OEKO-TEX Standard 100"]
  },
  "cuidados": ["Lavar a máquina en frío", "No usar blanqueador"],
  "etiquetas": ["verano", "básicos", "unisex"],
  "version": 2,
  "actualizado_por": 1,
  "fecha_actualizacion": "2026-11-04T13:17:04Z"
}
```

Evento de la bitácora (se guarda solo en `after_request`, sin código extra en cada endpoint):

```json
{
  "id_usuario": 1, "rol": "ADMINISTRADOR", "id_sede": null,
  "accion": "FICHA_GUARDADA", "metodo": "PUT", "ruta": "/api/v1/productos/1/ficha",
  "estado_http": 200, "exito": true, "parametros": { "id_producto": 1 },
  "ip": "127.0.0.1", "user_agent": "PostmanRuntime/7.43.0",
  "fecha": "2026-11-04T13:17:04Z"
}
```

### Cómo funciona

1. `api/nosql.py` crea el `MongoClient` al arrancar la app (`iniciar_mongo`) y los índices de cada colección. Si MongoDB no responde, la API arranca igual y lo reintenta en cada uso.
2. `app.after_request(registrar_peticion)` guarda en `actividad_usuario` cada petición hecha con token: acción, ruta, código HTTP, parámetros, filtros y, si falló, el mensaje de error. Un fallo de MongoDB aquí solo deja un aviso en el log.
3. `GET /variantes/qr/{codigo_qr}` guarda cada lectura en `escaneos_qr` (también las de códigos inexistentes), con el canal (`WEB` sin token, `TIENDA` con token) y la sede.
4. Reseñas y fichas tienen CRUD completo. Antes de escribir se valida en MySQL que el producto exista y, si la reseña trae `codigo_pedido`, que el pedido esté pagado e incluya el producto.
5. Las claves que empiezan por `$` o contienen `.` se rechazan, para que nadie pueda inyectar operadores de MongoDB en los atributos libres.

### Endpoints que combinan SQL y NoSQL

| Endpoint | De MySQL | De MongoDB |
|---|---|---|
| `GET /api/v1/auth/perfil/actividad` | Datos del usuario, rol y sede | Últimas 10 actividades (`?limite=` hasta 50) y conteo por acción (agregación `$group`) |
| `GET /api/v1/usuarios/{id}/actividad` | Igual, para cualquier usuario (admin) | Igual |
| `GET /api/v1/productos/{id}/completo` | Producto, imágenes, variantes, precio y stock por sede | Ficha técnica, resumen de reseñas (`$facet`), 5 reseñas recientes, escaneos de 30 días |
| `GET /api/v1/productos/buscar-atributos?atributos.material=algodon&etiqueta=verano` | Precio, tallas y stock vigentes de los productos encontrados | Búsqueda por atributos dinámicos, sin distinguir tildes ni mayúsculas (collation `es`) |
| `GET /api/v1/reportes/qr-mas-escaneados?dias=30` | Descripción, precio y stock de cada variante | Ranking de escaneos por variante y canal (agregación) |

Si MongoDB está caído, `/productos/{id}/completo` responde igual con la parte de MySQL y `"nosql_disponible": false`.

### Evidencias de ejecución (Entrega 2)

Capturas generadas al ejecutar `scripts/flujo_demo_nosql.py` contra la API en local (MySQL 8.0 + MongoDB 7.0), sobre bases recién creadas. Cada imagen muestra la petición enviada y la respuesta real de la API. Las imágenes están en `docs/imagenes/nosql/`.

**Conexión y datos guardados en MongoDB**

![verificar-mongo](docs/imagenes/nosql/50-verificar-mongo.png)
![Documentos en mongosh](docs/imagenes/nosql/51-mongosh-documentos.png)

**Endpoints combinados SQL + NoSQL**

| Petición | Resultado |
|---|---|
| GET `/api/v1/auth/perfil/actividad` | 200 OK: usuario de MySQL + últimas 10 actividades y resumen de MongoDB |
| GET `/api/v1/productos/1/completo` | 200 OK: stock por sede (MySQL) + ficha, reseñas y escaneos (MongoDB) |
| GET `/api/v1/productos/buscar-atributos?atributos.material=algodon&etiqueta=verano` | 200 OK: `algodon` encuentra `Algodón`; precio y stock desde MySQL |
| GET `/api/v1/reportes/qr-mas-escaneados?dias=30&limite=5` | 200 OK: ranking de MongoDB con descripción y stock de MySQL |
| GET `/api/v1/actividad?accion=FICHA_GUARDADA&size=5` | 200 OK: bitácora filtrada |

![Perfil con actividad](docs/imagenes/nosql/45-combinado-perfil-actividad.png)
![Producto completo](docs/imagenes/nosql/46-combinado-producto-completo.png)
![Buscar por atributos](docs/imagenes/nosql/47-combinado-buscar-atributos.png)
![QR más escaneados](docs/imagenes/nosql/48-combinado-qr-ranking.png)
![Bitácora](docs/imagenes/nosql/49-bitacora-admin.png)

**CRUD de fichas técnicas**

| Petición | Resultado |
|---|---|
| PUT `/api/v1/productos/2/ficha` | 200 OK: ficha creada (upsert), `version` 1 |
| GET `/api/v1/productos/1/ficha` | 200 OK |
| PUT `/api/v1/productos/1/ficha` | 200 OK: ficha reemplazada, `version` 2, nuevo atributo `certificaciones` |
| DELETE `/api/v1/productos/2/ficha` | 204 No Content |

![Crear ficha](docs/imagenes/nosql/32-ficha-crear.png)
![Consultar ficha](docs/imagenes/nosql/33-ficha-consultar.png)
![Actualizar ficha](docs/imagenes/nosql/34-ficha-actualizar.png)
![Eliminar ficha](docs/imagenes/nosql/35-ficha-eliminar.png)

**CRUD de reseñas**

| Petición | Resultado |
|---|---|
| POST `/api/v1/productos/1/resenas` | 201 Created: `compra_verificada: true` tras validar el pedido en MySQL |
| POST `/api/v1/productos/1/resenas` | 201 Created: otra reseña con atributos y fotos distintos |
| POST `/api/v1/productos/1/resenas` | 409 Conflict: el mismo email ya reseñó el producto |
| POST `/api/v1/productos/2/resenas` | 422: el pedido indicado no incluye ese producto |
| GET `/api/v1/productos/1/resenas?orden=mejores` | 200 OK: listado + resumen (promedio, estrellas, ajuste de talla) |
| POST `/api/v1/resenas/{id}/util` | 200 OK: `util` incrementado con `$inc` |
| PATCH `/api/v1/resenas/{id}` | 200 OK: respuesta de la tienda agregada con `$push` |
| PATCH `/api/v1/resenas/{id}` | 200 OK: reseña ocultada |
| DELETE `/api/v1/resenas/{id}` | 204 No Content |

![Crear reseña verificada](docs/imagenes/nosql/36-resena-crear-verificada.png)
![Crear reseña con atributos](docs/imagenes/nosql/37-resena-crear-atributos.png)
![Reseña duplicada](docs/imagenes/nosql/38-resena-duplicada-409.png)
![Compra no verificable](docs/imagenes/nosql/39-resena-compra-422.png)
![Listar reseñas](docs/imagenes/nosql/40-resenas-listar-resumen.png)
![Marcar útil](docs/imagenes/nosql/41-resena-util.png)
![Responder reseña](docs/imagenes/nosql/42-resena-responder.png)
![Ocultar reseña](docs/imagenes/nosql/43-resena-ocultar.png)
![Eliminar reseña](docs/imagenes/nosql/44-resena-eliminar.png)

## Tienda web

La carpeta `web/` tiene toda la interfaz: páginas HTML, CSS y JavaScript que Flask sirve tal cual y que consumen `/api/v1` con `fetch`. No hay que instalar Node ni compilar nada; se abre con la API corriendo. Hay dos partes: la **tienda** para los clientes y el **panel** para el personal.

### Tienda (clientes)

| Página | Qué hace | Endpoints que usa |
|---|---|---|
| `/` | Catálogo con búsqueda, filtros y "solo lo que hay en mi sede"; el título cambia con la sede ("Lo que hay hoy en Chapinero") | `GET /sedes`, `/categorias`, `/productos?sede=` |
| `/producto?id=N` | Precio, tallas y colores, disponibilidad por sede, agregar al carrito, ficha técnica como etiqueta de ropa y opiniones (ver, ordenar, votar y escribir) | `GET /productos/{id}/completo` (MySQL + MongoDB), `GET`/`POST /productos/{id}/resenas`, `POST /resenas/{id}/util` |
| `/escanear` | Lee el QR de la etiqueta con la cámara (navegadores con `BarcodeDetector`, como Chrome en Android) o con el código escrito; cada lectura queda en `escaneos_qr` | `GET /variantes/qr/{codigo}?sede=` |
| `/carrito` | Carrito, datos del cliente, recoger en tienda o domicilio, pago con la pasarela simulada (también se puede simular un rechazo) y tiquete con el QR del pedido y la factura | `GET /metodos-pago`, `POST /pedidos` (canal WEB), `POST /pedidos/{id}/pagos` |

- La sede elegida y el carrito se recuerdan en el navegador. El pedido web sale de la sede elegida, así que solo deja agregar lo que hay allí; si algo se agotó, la API responde 409 y la página dice en qué otras sedes hay.
- Si MongoDB no responde, el detalle sigue mostrando precio y disponibilidad, y avisa que las opiniones no están disponibles.
- El texto que escriben los clientes se inserta con `textContent`, nunca como HTML.

### Panel del personal (`/panel`)

Se entra con el correo y la contraseña de un usuario del sistema. El menú cambia según el rol: el **trabajador** opera su sede y la **administración** ve todo.

| Sección | Qué hace | Rol |
|---|---|---|
| Inicio | Pedidos por cobrar y por preparar, traslados en camino, referencias agotadas, últimos pedidos; para administración también la actividad reciente (MongoDB) y lo más escaneado | Ambos |
| Mostrador | Venta en tienda: agregar prendas por código QR o nombre (muestra existencias de la sede), cliente opcional para la factura, cobro y recibo con factura y QR | Ambos |
| Pedidos | Lista con filtros y búsqueda por código; detalle con prendas, cliente, envío, pagos y factura; cobrar, preparar, enviar (transportadora y guía), entregar, cancelar y emitir factura | Ambos |
| Inventario | Existencias por sede (disponibles y reservadas), registrar ingresos; ajustes por conteo físico e historial de movimientos | Ambos / Administración |
| Traslados | Lista, detalle con avance, despachar (sede de origen) y recibir (sede de destino); crear traslados | Ambos / Administración |
| Prendas | Crear y editar, desactivar y reactivar; tallas y colores; **editor de ficha técnica** (MongoDB) con vista previa de la etiqueta; **etiquetas QR para imprimir** y colgar en las prendas | Administración |
| Categorías y sedes | Listar y crear | Administración |
| Opiniones | Moderación: responder como tienda, ocultar o publicar, eliminar | Administración |
| Usuarios | Crear, activar o desactivar el acceso, ver la actividad de cada uno | Administración |
| Bitácora | Actividad de todos los usuarios (MongoDB) con filtros por usuario, acción, resultado y fechas | Administración |
| Reportes | Prendas más escaneadas por periodo, con existencias de MySQL | Administración |
| Mi perfil | Datos del usuario (MySQL) y sus últimas acciones (MongoDB): el endpoint combinado `/auth/perfil/actividad` | Ambos |

El token se guarda en `sessionStorage`: la sesión se cierra al cerrar la pestaña o cuando vence el token, y entonces el panel vuelve a pedir el inicio de sesión. Las etiquetas QR codifican la dirección `/escanear?codigo=SOL-V-…`, así que cualquier celular las abre con la cámara normal.

### Diseño

Índigo denim, papel frío y un solo acento amarillo, reservado para el precio (que va en una etiqueta colgante) y para lo que pide atención en el panel. La tipografía es [Archivo](https://fonts.google.com/specimen/Archivo), usando su eje de ancho: expandida para la marca y los títulos, condensada para la etiqueta de la ficha técnica. Las prendas de ejemplo tienen ilustraciones SVG propias (`web/recursos/img/prendas/`). Los QR se generan en el navegador con [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) (MIT), incluida en `web/recursos/vendor/` para que funcione sin internet.

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
| Administración | GET | `/api/v1/usuarios` | Administrador |
| Administración | PATCH | `/api/v1/usuarios/{id_usuario}` (activar o desactivar) | Administrador |
| Administración | GET | `/api/v1/productos?inactivos=true` y `/api/v1/productos/{id}` desactivados | Administrador |
| Inventario | GET | `/api/v1/traslados` | Trabajador |
| Reseñas (MongoDB) | GET | `/api/v1/resenas` (moderación, incluye ocultas) | Administrador |
| Fichas (MongoDB) | GET | `/api/v1/productos/{id_producto}/ficha` | Público |
| Fichas (MongoDB) | PUT | `/api/v1/productos/{id_producto}/ficha` | Administrador |
| Fichas (MongoDB) | DELETE | `/api/v1/productos/{id_producto}/ficha` | Administrador |
| Reseñas (MongoDB) | GET | `/api/v1/productos/{id_producto}/resenas` | Público |
| Reseñas (MongoDB) | POST | `/api/v1/productos/{id_producto}/resenas` | Público |
| Reseñas (MongoDB) | GET | `/api/v1/resenas/{id_resena}` | Público |
| Reseñas (MongoDB) | POST | `/api/v1/resenas/{id_resena}/util` | Público |
| Reseñas (MongoDB) | PATCH | `/api/v1/resenas/{id_resena}` | Administrador |
| Reseñas (MongoDB) | DELETE | `/api/v1/resenas/{id_resena}` | Administrador |
| Actividad (MongoDB) | GET | `/api/v1/actividad` | Administrador |
| **SQL + NoSQL** | GET | `/api/v1/auth/perfil/actividad` | Autenticado |
| **SQL + NoSQL** | GET | `/api/v1/usuarios/{id_usuario}/actividad` | Administrador |
| **SQL + NoSQL** | GET | `/api/v1/productos/{id_producto}/completo` | Público |
| **SQL + NoSQL** | GET | `/api/v1/productos/buscar-atributos` | Público |
| **SQL + NoSQL** | GET | `/api/v1/reportes/qr-mas-escaneados` | Administrador |

"Trabajador" incluye también al administrador. Los errores responden `{"detail": "mensaje"}` con el código HTTP correspondiente (400, 401, 402, 403, 404, 409, 422, y 503 si una base no está disponible). `GET /api/v1/variantes/qr/{codigo_qr}` ahora también registra cada escaneo en MongoDB.

## Estructura del proyecto

```
app.py                     # punto de entrada: python app.py / gunicorn app:app
requirements.txt
requirements-dev.txt       # dependencias de desarrollo (pytest)
pytest.ini
.env.example               # plantilla de variables de entorno (.env no se versiona)
api/
  __init__.py              # crear_app(): configuración, base de datos, rutas, errores
  config.py                # lectura de variables de entorno
  nosql.py                 # conexión a MongoDB, colecciones e índices
  demo.py                  # catálogo de ejemplo (flask sembrar-demo)
  modelos.py               # modelos Flask-SQLAlchemy (reflejan database/solsticio_schema.sql)
  seguridad.py             # JWT, bcrypt y control de roles y sedes
  validacion.py            # validación de datos de entrada
  serializadores.py        # conversión de modelos a JSON
  errores.py               # ErrorApi y manejadores -> {"detail": "..."}
  comandos.py              # flask verificar-bd / verificar-mongo / crear-admin / sembrar-demo
  rutas/                   # capa HTTP: un blueprint por módulo, bajo /api/v1
    auth.py  catalogo.py  inventario.py  pedidos.py  admin.py      # MySQL
    actividad.py  resenas.py  fichas.py                            # MongoDB y combinados
    web.py                                                         # sirve la tienda (web/)
  servicios/               # lógica de negocio y transacciones
    comun.py  inventario.py  traslados.py  pedidos.py  facturacion.py  catalogo.py  usuarios.py
    actividad.py  resenas.py  fichas.py                            # MongoDB
database/
  solsticio_schema.sql     # script de creación de la base de datos (23 tablas)
docs/
  Entrega2_NoSQL_Solsticio.pdf   # documento de la Entrega 2 (estructura NoSQL y justificación)
  imagenes/                # capturas de las pruebas en Postman
    nosql/                 # evidencias de la Entrega 2 (MongoDB)
  diagramas/               # diagramas de casos de uso
  Solsticio_Modelo_Datos.md, solsticio_dbdiagram.dbml
postman/
  Solsticio.postman_collection.json
scripts/
  flujo_demo_nosql.py      # recorre todos los endpoints NoSQL y combinados
tests/                     # pruebas automáticas con pytest (MySQL + MongoDB reales)
  conftest.py  test_fichas.py  test_resenas.py  test_combinados.py  test_degradacion.py  test_web.py  test_panel_api.py
web/                       # interfaz (HTML + CSS + JS) servida por Flask
  index.html  producto.html  escanear.html  carrito.html  panel.html
  recursos/css/            # estilos.css (tienda y base), panel.css
  recursos/js/             # comun.js, etiqueta.js, catalogo.js, producto.js, escanear.js, carrito.js
  recursos/js/panel/       # app.js (sesión y rutas), ui.js (componentes) y una sección por archivo
  recursos/img/            # favicon e ilustraciones de las prendas de ejemplo
  recursos/vendor/         # qrcode-generator (MIT)
legacy/prototipo/          # primer prototipo (SQLite + frontends HTML), ya no se usa
```

Flujo de una petición: **ruta** (valida permisos y datos) → **servicio** (reglas de negocio y transacción) → **modelo** (base de datos) → **serializador** (JSON de respuesta).

## Reglas de negocio implementadas

- Toda variación de existencias genera una fila en `movimiento_inventario` (INGRESO, VENTA, TRASLADO_SALIDA, TRASLADO_ENTRADA, AJUSTE).
- Un pedido descuenta stock solo de su sede. Si no hay existencias, responde 409 con las sedes alternativas.
- Al crear el pedido las unidades quedan reservadas y se descuentan cuando el pago se aprueba. Si el pago se rechaza, la reserva se libera.
- El precio unitario del pedido es histórico: cambiar el precio del catálogo no altera ventas anteriores.
- Un traslado genera dos movimientos: salida al despachar y entrada al recibir. Origen y destino no pueden ser la misma sede.
- Un trabajador solo opera sobre su sede; el administrador es global.
- Si la DIAN (simulada) falla, la factura queda PENDIENTE sin bloquear la venta.
- No hay borrado físico: los productos se desactivan.
- Una reseña con `codigo_pedido` solo se acepta si ese pedido (MySQL) está pagado e incluye el producto; queda marcada como compra verificada.
- Un mismo email solo puede publicar una reseña por producto (índice único en MongoDB).
- MongoDB nunca guarda precios ni existencias: esos datos siempre se leen de MySQL.
- Si MongoDB falla, ninguna operación de MySQL se cancela por ello.

## Pendiente

- Devoluciones y cambios (`/api/v1/devoluciones`) con nota crédito.
- Más reportes (`/api/v1/reportes/...`); ya existe `qr-mas-escaneados`.
- Registro público de clientes (`/api/v1/auth/registro`).
- Seguimiento público del pedido para el cliente (hoy solo el personal consulta un pedido por su código).

## Autores

Miguel Angel Marin Baracaldo · Joan Sebastian Lara Fuenmayor
