# 3. MODELO DE DATOS RELACIONAL

## 3.1 Consideraciones de diseño

El modelo relacional del sistema multisede Solsticio se construyó a partir de los casos de uso descritos en la sección 2, bajo las siguientes decisiones de diseño:

**Separación Producto / Variante.** Un producto representa el diseño comercial (por ejemplo, "Camiseta oversize algodón"), mientras que una variante representa la combinación específica de producto, talla y color que efectivamente se vende y se inventaría. Esta separación es necesaria para cumplir la Tercera Forma Normal: si la talla y el color fueran columnas de `producto`, un mismo diseño en cinco tallas exigiría cinco filas duplicando nombre, descripción, categoría y precio.

**Trazabilidad por referencia.** El código QR se asocia a la variante (SKU), no a la unidad física individual. Todas las prendas de un mismo producto, talla y color comparten código QR. Esta decisión mantiene el modelo manejable y satisface el caso de uso 2.3.2, en el cual el cliente escanea una etiqueta para consultar características y disponibilidad.

**Inventario distribuido.** La existencia de mercancía no es un atributo del producto ni de la variante, sino una relación entre sede y variante. La tabla `stock` implementa esta relación N:M con atributo mediante llave primaria compuesta, permitiendo que el catálogo web muestre la disponibilidad desglosada por sede.

**Pedido unificado por canal.** Las ventas web y las ventas en mostrador comparten una única tabla `pedido`, diferenciada por el atributo `canal`. Modelar dos tablas con estructura casi idéntica introduciría redundancia estructural y duplicaría la lógica de facturación.

**Precio histórico en el detalle.** La tabla `detalle_pedido` almacena `precio_unitario` aunque el precio también exista en `producto`. Esto no constituye una violación de la normalización: el precio del catálogo es un dato vigente y modificable, mientras que el precio del detalle es un dato histórico inmutable. Si el precio de catálogo cambia, las facturas ya emitidas deben conservar el valor con el que fueron generadas.

**Movimientos de inventario.** Toda variación de existencias queda registrada en `movimiento_inventario`, lo que permite auditar por qué cambió el stock en cualquier momento. Esta tabla es la respuesta directa a la problemática planteada en la sección 1: los descuadres de inventario provienen de transacciones no documentadas.

---

## 3.2 Diagrama Entidad-Relación

> El diagrama se genera a partir del archivo `solsticio_dbdiagram.dbml` en [dbdiagram.io](https://dbdiagram.io). Exportar como PNG e insertar aquí.

### Relaciones principales

| Relación | Cardinalidad | Descripción |
|---|---|---|
| categoria — producto | 1:N | Una categoría agrupa varios productos |
| producto — variante | 1:N | Un producto se despliega en varias variantes (SKU) |
| talla — variante | 1:N | Una talla aplica a muchas variantes |
| color — variante | 1:N | Un color aplica a muchas variantes |
| producto — imagen_producto | 1:N | Un producto tiene varias fotografías |
| sede — variante | N:M | Resuelta por `stock`, con atributo cantidad |
| rol — usuario | 1:N | Un rol se asigna a varios usuarios |
| sede — usuario | 1:N | Un usuario operativo pertenece a una sede |
| usuario — cliente | 1:1 opcional | Un cliente puede o no tener cuenta registrada |
| cliente — pedido | 1:N | Un cliente realiza varios pedidos |
| sede — pedido | 1:N | Todo pedido se atiende desde una sede |
| pedido — detalle_pedido | 1:N | Un pedido contiene varias líneas |
| variante — detalle_pedido | 1:N | Una variante aparece en muchas líneas |
| pedido — envio | 1:1 opcional | Solo pedidos web con despacho a domicilio |
| pedido — pago | 1:N | Un pedido admite pagos parciales o reintentos |
| pedido — factura | 1:1 | Todo pedido confirmado genera una factura |
| pedido — devolucion | 1:N | Un pedido puede originar varias devoluciones |
| devolucion — nota_credito | 1:1 | Toda devolución aprobada genera nota crédito |
| traslado — detalle_traslado | 1:N | Un traslado mueve varias variantes |
| sede — traslado | 1:N (doble) | Sede origen y sede destino |

---

## 3.3 Diccionario de Datos

### Módulo: Catálogo

#### `categoria`
Clasificación de las prendas comercializadas.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_categoria | INT | PK, AUTO_INCREMENT | Identificador de la categoría |
| nombre | VARCHAR(60) | NOT NULL, UNIQUE | Nombre de la categoría (Camisas, Pantalones) |
| descripcion | VARCHAR(200) | NULL | Descripción ampliada |
| activo | BOOLEAN | NOT NULL, DEFAULT TRUE | Permite ocultar sin eliminar |

#### `producto`
Diseño comercial ofrecido por la tienda.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_producto | INT | PK, AUTO_INCREMENT | Identificador del producto |
| id_categoria | INT | FK → categoria | Categoría a la que pertenece |
| nombre | VARCHAR(120) | NOT NULL | Nombre comercial |
| descripcion | TEXT | NULL | Descripción para el catálogo web |
| precio_base | DECIMAL(12,2) | NOT NULL, CHECK > 0 | Precio de venta antes de IVA |
| genero | ENUM | NOT NULL | HOMBRE, MUJER, UNISEX, INFANTIL |
| activo | BOOLEAN | NOT NULL, DEFAULT TRUE | Visibilidad en catálogo |
| fecha_creacion | DATETIME | NOT NULL, DEFAULT NOW | Fecha de alta |

#### `talla`
Catálogo de tallas disponibles.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_talla | INT | PK, AUTO_INCREMENT | Identificador de la talla |
| valor | VARCHAR(10) | NOT NULL, UNIQUE | XS, S, M, L, XL, 28, 30 |
| orden | TINYINT | NOT NULL | Orden de presentación en el catálogo |

#### `color`
Catálogo de colores disponibles.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_color | INT | PK, AUTO_INCREMENT | Identificador del color |
| nombre | VARCHAR(40) | NOT NULL, UNIQUE | Nombre del color |
| codigo_hex | CHAR(7) | NULL | Código hexadecimal para la web |

#### `variante`
Unidad mínima inventariable (SKU). Portadora del código QR.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_variante | INT | PK, AUTO_INCREMENT | Identificador de la variante |
| id_producto | INT | FK → producto | Producto al que pertenece |
| id_talla | INT | FK → talla | Talla de la variante |
| id_color | INT | FK → color | Color de la variante |
| sku | VARCHAR(40) | NOT NULL, UNIQUE | Código interno de referencia |
| codigo_qr | VARCHAR(80) | NOT NULL, UNIQUE | Cadena codificada en el QR de la etiqueta |
| precio_adicional | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | Sobrecosto por talla especial |
| activo | BOOLEAN | NOT NULL, DEFAULT TRUE | Disponibilidad comercial |

*Restricción adicional:* UNIQUE (id_producto, id_talla, id_color) — impide duplicar la misma combinación.

#### `imagen_producto`
Fotografías asociadas al catálogo.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_imagen | INT | PK, AUTO_INCREMENT | Identificador de la imagen |
| id_producto | INT | FK → producto | Producto ilustrado |
| url | VARCHAR(255) | NOT NULL | Ruta del archivo |
| orden | TINYINT | NOT NULL, DEFAULT 1 | Orden de galería |
| es_principal | BOOLEAN | NOT NULL, DEFAULT FALSE | Imagen destacada del catálogo |

---

### Módulo: Sedes y Usuarios

#### `sede`
Locales físicos de la cadena.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_sede | INT | PK, AUTO_INCREMENT | Identificador de la sede |
| nombre | VARCHAR(80) | NOT NULL, UNIQUE | Nombre del local |
| direccion | VARCHAR(150) | NOT NULL | Dirección física |
| ciudad | VARCHAR(60) | NOT NULL, DEFAULT 'Bogotá' | Ciudad |
| telefono | VARCHAR(20) | NULL | Teléfono de contacto |
| activo | BOOLEAN | NOT NULL, DEFAULT TRUE | Sede en operación |

#### `rol`
Perfiles de acceso al sistema.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_rol | INT | PK, AUTO_INCREMENT | Identificador del rol |
| nombre | VARCHAR(40) | NOT NULL, UNIQUE | ADMINISTRADOR, TRABAJADOR |
| descripcion | VARCHAR(150) | NULL | Alcance de privilegios |

#### `usuario`
Personal con acceso autenticado al sistema.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_usuario | INT | PK, AUTO_INCREMENT | Identificador del usuario |
| id_rol | INT | FK → rol | Rol asignado |
| id_sede | INT | FK → sede, NULL | Sede asignada; nulo para administrador global |
| documento | VARCHAR(20) | NOT NULL, UNIQUE | Documento de identidad |
| nombres | VARCHAR(80) | NOT NULL | Nombres |
| apellidos | VARCHAR(80) | NOT NULL | Apellidos |
| email | VARCHAR(120) | NOT NULL, UNIQUE | Correo de acceso |
| hash_password | VARCHAR(255) | NOT NULL | Contraseña cifrada |
| activo | BOOLEAN | NOT NULL, DEFAULT TRUE | Cuenta habilitada |
| fecha_registro | DATETIME | NOT NULL, DEFAULT NOW | Fecha de creación |

#### `cliente`
Compradores. Se separa de `usuario` porque un cliente de mostrador requiere datos para facturación sin tener cuenta.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_cliente | INT | PK, AUTO_INCREMENT | Identificador del cliente |
| id_usuario | INT | FK → usuario, NULL, UNIQUE | Cuenta web, si está registrado |
| tipo_documento | ENUM | NOT NULL | CC, CE, NIT, PASAPORTE |
| numero_documento | VARCHAR(20) | NOT NULL, UNIQUE | Número de documento |
| nombres | VARCHAR(80) | NOT NULL | Nombres o razón social |
| apellidos | VARCHAR(80) | NULL | Apellidos |
| email | VARCHAR(120) | NULL | Correo para factura electrónica |
| telefono | VARCHAR(20) | NULL | Teléfono |
| direccion | VARCHAR(150) | NULL | Dirección de residencia |

---

### Módulo: Inventario

#### `stock`
Existencias por sede y variante. Resuelve la relación N:M.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_sede | INT | PK, FK → sede | Sede donde reposa la mercancía |
| id_variante | INT | PK, FK → variante | Variante inventariada |
| cantidad | INT | NOT NULL, DEFAULT 0, CHECK >= 0 | Unidades disponibles |
| cantidad_reservada | INT | NOT NULL, DEFAULT 0 | Unidades comprometidas en pedidos pendientes |
| stock_minimo | INT | NOT NULL, DEFAULT 0 | Umbral de alerta de reposición |

#### `movimiento_inventario`
Bitácora de toda variación de existencias.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_movimiento | BIGINT | PK, AUTO_INCREMENT | Identificador del movimiento |
| id_variante | INT | FK → variante | Variante afectada |
| id_sede | INT | FK → sede | Sede afectada |
| tipo | ENUM | NOT NULL | INGRESO, VENTA, DEVOLUCION, TRASLADO_SALIDA, TRASLADO_ENTRADA, AJUSTE |
| cantidad | INT | NOT NULL | Positiva o negativa según el tipo |
| id_usuario | INT | FK → usuario, NULL | Responsable del movimiento |
| tipo_referencia | VARCHAR(30) | NULL | Entidad que originó el movimiento |
| id_referencia | BIGINT | NULL | Identificador de esa entidad |
| observacion | VARCHAR(200) | NULL | Nota del responsable |
| fecha | DATETIME | NOT NULL, DEFAULT NOW | Momento del movimiento |

#### `traslado`
Movimiento de mercancía entre sedes.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_traslado | INT | PK, AUTO_INCREMENT | Identificador del traslado |
| id_sede_origen | INT | FK → sede | Sede que envía |
| id_sede_destino | INT | FK → sede | Sede que recibe |
| id_usuario_solicita | INT | FK → usuario | Quien solicita el traslado |
| id_usuario_recibe | INT | FK → usuario, NULL | Quien confirma la recepción |
| estado | ENUM | NOT NULL, DEFAULT 'SOLICITADO' | SOLICITADO, EN_TRANSITO, RECIBIDO, CANCELADO |
| fecha_solicitud | DATETIME | NOT NULL, DEFAULT NOW | Fecha de solicitud |
| fecha_recepcion | DATETIME | NULL | Fecha de confirmación |

*Restricción adicional:* CHECK (id_sede_origen <> id_sede_destino).

#### `detalle_traslado`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_detalle_traslado | INT | PK, AUTO_INCREMENT | Identificador de la línea |
| id_traslado | INT | FK → traslado | Traslado al que pertenece |
| id_variante | INT | FK → variante | Variante trasladada |
| cantidad | INT | NOT NULL, CHECK > 0 | Unidades movidas |

---

### Módulo: Ventas

#### `pedido`
Transacción de venta, unificada por canal.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_pedido | BIGINT | PK, AUTO_INCREMENT | Identificador del pedido |
| id_cliente | INT | FK → cliente, NULL | Comprador |
| id_sede | INT | FK → sede | Sede que atiende o despacha |
| id_usuario | INT | FK → usuario, NULL | Empleado que registra; nulo en canal WEB |
| canal | ENUM | NOT NULL | WEB, TIENDA |
| tipo_entrega | ENUM | NOT NULL | INMEDIATA, RECOGER_EN_TIENDA, DOMICILIO |
| estado | ENUM | NOT NULL, DEFAULT 'PENDIENTE' | PENDIENTE, PAGADO, PREPARANDO, ENVIADO, ENTREGADO, CANCELADO |
| codigo_qr | VARCHAR(80) | NOT NULL, UNIQUE | QR del comprobante, distinto del QR de prenda |
| subtotal | DECIMAL(12,2) | NOT NULL | Suma de líneas antes de IVA |
| impuestos | DECIMAL(12,2) | NOT NULL | IVA calculado |
| total | DECIMAL(12,2) | NOT NULL | Total a pagar |
| fecha_pedido | DATETIME | NOT NULL, DEFAULT NOW | Fecha de registro |

#### `detalle_pedido`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_detalle_pedido | BIGINT | PK, AUTO_INCREMENT | Identificador de la línea |
| id_pedido | BIGINT | FK → pedido | Pedido al que pertenece |
| id_variante | INT | FK → variante | Variante vendida |
| cantidad | INT | NOT NULL, CHECK > 0 | Unidades vendidas |
| precio_unitario | DECIMAL(12,2) | NOT NULL | Precio histórico al momento de la venta |
| subtotal_linea | DECIMAL(12,2) | NOT NULL | cantidad × precio_unitario |

#### `envio`
Datos de despacho. Solo para pedidos con entrega a domicilio.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_envio | BIGINT | PK, AUTO_INCREMENT | Identificador del envío |
| id_pedido | BIGINT | FK → pedido, UNIQUE | Pedido despachado |
| direccion | VARCHAR(150) | NOT NULL | Dirección de entrega |
| ciudad | VARCHAR(60) | NOT NULL | Ciudad de entrega |
| destinatario | VARCHAR(120) | NOT NULL | Nombre de quien recibe |
| telefono_contacto | VARCHAR(20) | NOT NULL | Teléfono del destinatario |
| transportadora | VARCHAR(60) | NULL | Empresa de mensajería |
| numero_guia | VARCHAR(60) | NULL | Número de rastreo |
| estado | ENUM | NOT NULL, DEFAULT 'PREPARANDO' | PREPARANDO, DESPACHADO, ENTREGADO, DEVUELTO |
| fecha_despacho | DATETIME | NULL | Fecha de salida |
| fecha_entrega | DATETIME | NULL | Fecha de entrega efectiva |

---

### Módulo: Pagos (pasarela simulada)

#### `metodo_pago`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_metodo_pago | INT | PK, AUTO_INCREMENT | Identificador del método |
| nombre | VARCHAR(50) | NOT NULL, UNIQUE | Efectivo, Tarjeta débito, PSE |
| tipo | ENUM | NOT NULL | EFECTIVO, TARJETA, TRANSFERENCIA |
| activo | BOOLEAN | NOT NULL, DEFAULT TRUE | Método habilitado |

#### `pago`
Registro de transacciones. La pasarela se simula mediante el campo `referencia_transaccion`.

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_pago | BIGINT | PK, AUTO_INCREMENT | Identificador del pago |
| id_pedido | BIGINT | FK → pedido | Pedido pagado |
| id_metodo_pago | INT | FK → metodo_pago | Medio utilizado |
| monto | DECIMAL(12,2) | NOT NULL, CHECK > 0 | Valor abonado |
| estado | ENUM | NOT NULL, DEFAULT 'PENDIENTE' | PENDIENTE, APROBADO, RECHAZADO, REVERSADO |
| referencia_transaccion | VARCHAR(80) | NULL, UNIQUE | Identificador devuelto por la pasarela |
| fecha_pago | DATETIME | NOT NULL, DEFAULT NOW | Fecha de la transacción |

---

### Módulo: Facturación electrónica

#### `factura`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_factura | BIGINT | PK, AUTO_INCREMENT | Identificador de la factura |
| id_pedido | BIGINT | FK → pedido, UNIQUE | Pedido facturado |
| numero_factura | VARCHAR(30) | NOT NULL, UNIQUE | Consecutivo autorizado |
| prefijo | VARCHAR(10) | NOT NULL | Prefijo de resolución DIAN |
| cufe | VARCHAR(100) | NULL, UNIQUE | Código Único de Facturación Electrónica |
| estado_dian | ENUM | NOT NULL, DEFAULT 'PENDIENTE' | PENDIENTE, VALIDADA, RECHAZADA |
| subtotal | DECIMAL(12,2) | NOT NULL | Base gravable |
| iva | DECIMAL(12,2) | NOT NULL | Impuesto liquidado |
| total | DECIMAL(12,2) | NOT NULL | Total facturado |
| fecha_emision | DATETIME | NOT NULL, DEFAULT NOW | Fecha de emisión |
| fecha_validacion | DATETIME | NULL | Fecha de respuesta de la DIAN |
| url_xml | VARCHAR(255) | NULL | Ruta del XML firmado |

---

### Módulo: Devoluciones y cambios

#### `devolucion`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_devolucion | BIGINT | PK, AUTO_INCREMENT | Identificador de la devolución |
| id_pedido | BIGINT | FK → pedido | Pedido de origen |
| id_sede | INT | FK → sede | Sede donde se recibe |
| id_usuario | INT | FK → usuario | Empleado que gestiona |
| tipo | ENUM | NOT NULL | CAMBIO, DEVOLUCION |
| motivo | VARCHAR(200) | NOT NULL | Razón declarada |
| estado | ENUM | NOT NULL, DEFAULT 'SOLICITADA' | SOLICITADA, APROBADA, RECHAZADA, COMPLETADA |
| fecha_solicitud | DATETIME | NOT NULL, DEFAULT NOW | Fecha de solicitud |

#### `detalle_devolucion`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_detalle_devolucion | BIGINT | PK, AUTO_INCREMENT | Identificador de la línea |
| id_devolucion | BIGINT | FK → devolucion | Devolución a la que pertenece |
| id_detalle_pedido | BIGINT | FK → detalle_pedido | Línea original devuelta |
| cantidad | INT | NOT NULL, CHECK > 0 | Unidades devueltas |
| id_variante_cambio | INT | FK → variante, NULL | Variante entregada a cambio |

#### `nota_credito`

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| id_nota_credito | BIGINT | PK, AUTO_INCREMENT | Identificador de la nota |
| id_devolucion | BIGINT | FK → devolucion, UNIQUE | Devolución que la origina |
| id_factura | BIGINT | FK → factura | Factura afectada |
| numero_nota | VARCHAR(30) | NOT NULL, UNIQUE | Consecutivo |
| cude | VARCHAR(100) | NULL, UNIQUE | Código único de nota crédito |
| monto | DECIMAL(12,2) | NOT NULL | Valor acreditado |
| estado_dian | ENUM | NOT NULL, DEFAULT 'PENDIENTE' | PENDIENTE, VALIDADA, RECHAZADA |
| fecha_emision | DATETIME | NOT NULL, DEFAULT NOW | Fecha de emisión |

---

## 3.4 Verificación de Formas Normales

**Primera Forma Normal.** Todos los atributos son atómicos. No existen campos multivaluados: las tallas y colores se resuelven en `variante`, las imágenes en `imagen_producto` y las líneas de venta en `detalle_pedido`.

**Segunda Forma Normal.** La única llave compuesta del modelo es la de `stock` (id_sede, id_variante). Sus atributos no clave (`cantidad`, `cantidad_reservada`, `stock_minimo`) dependen de la llave completa: la cantidad no tiene sentido conociendo solo la sede o solo la variante.

**Tercera Forma Normal.** No existen dependencias transitivas. El nombre de la categoría no se replica en `producto`, sino que se referencia por `id_categoria`; el nombre de la sede no se replica en `stock` ni en `pedido`; los datos del cliente no se replican en `factura`. Los totales de `pedido` y `factura` son valores derivados almacenados deliberadamente como dato histórico inmutable, criterio también aplicado a `precio_unitario` en `detalle_pedido`.
