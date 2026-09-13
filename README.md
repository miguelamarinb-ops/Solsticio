# Solsticio API

API REST del sistema multisede de inventario y ventas **Solsticio**, una tienda de ropa con varias sedes en Bogotá. Es un proyecto académico de la asignatura Nuevas Tecnologías de Desarrollo.

El sistema centraliza las existencias por sede, registra las ventas web y en tienda, y deja trazabilidad de cada movimiento de mercancía. También cubre los traslados entre sedes, los pagos y la facturación electrónica ante la DIAN (estos dos últimos, simulados).

## Contenido

- [Tecnologías](#tecnologías)
- [Requisitos previos](#requisitos-previos)
- [Instalación de las herramientas (Windows)](#instalación-de-las-herramientas-windows)
- [Cómo correr el proyecto](#cómo-correr-el-proyecto)
- [Uso diario](#uso-diario)
- [Problemas frecuentes](#problemas-frecuentes)
- [Pruebas con Postman](#pruebas-con-postman)
- [Evidencias de pruebas](#evidencias-de-pruebas)
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
| Base de datos | MySQL 8.0 (driver PyMySQL) |
| Autenticación | JWT (PyJWT) + bcrypt |
| Servidor de producción | Gunicorn |
| Pruebas de endpoints | Postman |

## Requisitos previos

| Programa | Para qué | Cómo comprobar que ya está |
|---|---|---|
| **Python 3.12 o superior** | Ejecutar la API | `python --version` |
| **MySQL Server 8.0** | Base de datos | `mysql --version`, o ver el servicio `MySQL80` en ejecución |
| **MySQL Workbench** | Ver la base y ejecutar el script SQL con interfaz gráfica | Buscarlo en el menú Inicio |
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
```

| Variable | Qué es |
|---|---|
| `DATABASE_URL` | Conexión a MySQL. Cambia `TU_CLAVE` por la contraseña de `root` que pusiste al instalar MySQL. |
| `SECRET_KEY` | Clave con la que se firman los tokens JWT. Puede ser cualquier texto largo. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Minutos de validez del token. |
| `DIAN_SIMULACION` / `PASARELA_SIMULACION` | En `true`, la DIAN y la pasarela de pagos se simulan. |

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

### 6. Crear el primer administrador

```bash
flask --app app crear-admin
```

El comando pide email, documento, nombres, apellidos y contraseña (dos veces). Con ese email y contraseña se inicia sesión en Postman.

### 7. Levantar el servidor

```bash
python app.py
```

La API queda disponible en **http://127.0.0.1:5000**. Para comprobarlo, abre esa dirección en el navegador. Debe responder:

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

MySQL tiene que estar encendido.

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
| PowerShell no deja ejecutar `Activate.ps1` | Ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| `401` en Postman | Falta hacer login o el token venció. Vuelve a ejecutar **POST /api/v1/auth/login**. |

## Pruebas con Postman

1. Importar `postman/Solsticio.postman_collection.json`.
2. Confirmar que la variable de colección `base_url` vale `http://127.0.0.1:5000`.
3. Ejecutar **POST /api/v1/auth/login** con el administrador creado en el paso 6. El token se guarda solo en la variable `{{token}}`.
4. Las demás peticiones envían `Authorization: Bearer {{token}}` automáticamente.

Flujo sugerido: login → crear categoría → crear producto → crear variantes → ingreso de inventario → crear pedido → pagar → consultar factura → traslado (crear, despachar, recibir).

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

"Trabajador" incluye también al administrador. Los errores responden `{"detail": "mensaje"}` con el código HTTP correspondiente (400, 401, 402, 403, 404, 409, 422).

## Estructura del proyecto

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
docs/
  imagenes/                # capturas de las pruebas en Postman
  diagramas/               # diagramas de casos de uso
  Solsticio_Modelo_Datos.md, solsticio_dbdiagram.dbml
postman/
  Solsticio.postman_collection.json
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

## Pendiente

- Devoluciones y cambios (`/api/v1/devoluciones`) con nota crédito.
- Reportes (`/api/v1/reportes/...`).
- Registro público de clientes (`/api/v1/auth/registro`).
- Nuevos frontends sobre `/api/v1` (los del prototipo están en `legacy/prototipo/`).

## Autores

Miguel Angel Marin Baracaldo · Joan Sebastian Lara Fuenmayor
