-- =====================================================================
-- SOLSTICIO - Sistema Multisede de Inventario y Ventas
-- Esquema relacional (MySQL 8.0)
--
-- Proyecto: Nuevas Tecnologias de Desarrollo
-- Autores : Miguel Angel Marin Baracaldo / Joan Sebastian Lara Fuenmayor
-- =====================================================================

DROP DATABASE IF EXISTS solsticio;
CREATE DATABASE solsticio
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE solsticio;

-- =====================================================================
-- MODULO: CATALOGO
-- =====================================================================

CREATE TABLE categoria (
    id_categoria  INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(60)  NOT NULL UNIQUE,
    descripcion   VARCHAR(200),
    activo        BOOLEAN      NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE producto (
    id_producto     INT AUTO_INCREMENT PRIMARY KEY,
    id_categoria    INT            NOT NULL,
    nombre          VARCHAR(120)   NOT NULL,
    descripcion     TEXT,
    precio_base     DECIMAL(12,2)  NOT NULL,
    genero          ENUM('HOMBRE','MUJER','UNISEX','INFANTIL') NOT NULL DEFAULT 'UNISEX',
    activo          BOOLEAN        NOT NULL DEFAULT TRUE,
    fecha_creacion  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_producto_categoria FOREIGN KEY (id_categoria)
        REFERENCES categoria(id_categoria) ON DELETE RESTRICT,
    CONSTRAINT chk_producto_precio CHECK (precio_base > 0)
) ENGINE=InnoDB;

CREATE TABLE talla (
    id_talla  INT AUTO_INCREMENT PRIMARY KEY,
    valor     VARCHAR(10) NOT NULL UNIQUE,
    orden     TINYINT     NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE color (
    id_color     INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(40) NOT NULL UNIQUE,
    codigo_hex   CHAR(7)
) ENGINE=InnoDB;

-- Unidad minima inventariable (SKU). Portadora del codigo QR de etiqueta.
CREATE TABLE variante (
    id_variante       INT AUTO_INCREMENT PRIMARY KEY,
    id_producto       INT           NOT NULL,
    id_talla          INT           NOT NULL,
    id_color          INT           NOT NULL,
    sku               VARCHAR(40)   NOT NULL UNIQUE,
    codigo_qr         VARCHAR(80)   NOT NULL UNIQUE,
    precio_adicional  DECIMAL(12,2) NOT NULL DEFAULT 0,
    activo            BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_variante_producto FOREIGN KEY (id_producto)
        REFERENCES producto(id_producto) ON DELETE RESTRICT,
    CONSTRAINT fk_variante_talla FOREIGN KEY (id_talla)
        REFERENCES talla(id_talla) ON DELETE RESTRICT,
    CONSTRAINT fk_variante_color FOREIGN KEY (id_color)
        REFERENCES color(id_color) ON DELETE RESTRICT,
    CONSTRAINT uq_variante_combinacion UNIQUE (id_producto, id_talla, id_color)
) ENGINE=InnoDB;

CREATE TABLE imagen_producto (
    id_imagen     INT AUTO_INCREMENT PRIMARY KEY,
    id_producto   INT          NOT NULL,
    url           VARCHAR(255) NOT NULL,
    orden         TINYINT      NOT NULL DEFAULT 1,
    es_principal  BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_imagen_producto FOREIGN KEY (id_producto)
        REFERENCES producto(id_producto) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO: SEDES Y USUARIOS
-- =====================================================================

CREATE TABLE sede (
    id_sede    INT AUTO_INCREMENT PRIMARY KEY,
    nombre     VARCHAR(80)  NOT NULL UNIQUE,
    direccion  VARCHAR(150) NOT NULL,
    ciudad     VARCHAR(60)  NOT NULL DEFAULT 'Bogota',
    telefono   VARCHAR(20),
    activo     BOOLEAN      NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE rol (
    id_rol       INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(40)  NOT NULL UNIQUE,
    descripcion  VARCHAR(150)
) ENGINE=InnoDB;

CREATE TABLE usuario (
    id_usuario      INT AUTO_INCREMENT PRIMARY KEY,
    id_rol          INT          NOT NULL,
    id_sede         INT,                       -- NULL para administrador global
    documento       VARCHAR(20)  NOT NULL UNIQUE,
    nombres         VARCHAR(80)  NOT NULL,
    apellidos       VARCHAR(80)  NOT NULL,
    email           VARCHAR(120) NOT NULL UNIQUE,
    hash_password   VARCHAR(255) NOT NULL,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    fecha_registro  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol)
        REFERENCES rol(id_rol) ON DELETE RESTRICT,
    CONSTRAINT fk_usuario_sede FOREIGN KEY (id_sede)
        REFERENCES sede(id_sede) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Separado de usuario: el cliente de mostrador requiere datos de
-- facturacion sin necesidad de tener cuenta de acceso.
CREATE TABLE cliente (
    id_cliente        INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario        INT UNIQUE,              -- NULL si no esta registrado
    tipo_documento    ENUM('CC','CE','NIT','PASAPORTE') NOT NULL DEFAULT 'CC',
    numero_documento  VARCHAR(20)  NOT NULL UNIQUE,
    nombres           VARCHAR(80)  NOT NULL,
    apellidos         VARCHAR(80),
    email             VARCHAR(120),
    telefono          VARCHAR(20),
    direccion         VARCHAR(150),
    CONSTRAINT fk_cliente_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO: INVENTARIO
-- =====================================================================

-- Resuelve la relacion N:M entre sede y variante con atributo cantidad.
CREATE TABLE stock (
    id_sede             INT NOT NULL,
    id_variante         INT NOT NULL,
    cantidad            INT NOT NULL DEFAULT 0,
    cantidad_reservada  INT NOT NULL DEFAULT 0,
    stock_minimo        INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id_sede, id_variante),
    CONSTRAINT fk_stock_sede FOREIGN KEY (id_sede)
        REFERENCES sede(id_sede) ON DELETE RESTRICT,
    CONSTRAINT fk_stock_variante FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante) ON DELETE RESTRICT,
    CONSTRAINT chk_stock_cantidad CHECK (cantidad >= 0),
    CONSTRAINT chk_stock_reservada CHECK (cantidad_reservada >= 0)
) ENGINE=InnoDB;

-- Bitacora de toda variacion de existencias. Responde directamente a la
-- problematica: los descuadres provienen de transacciones no documentadas.
CREATE TABLE movimiento_inventario (
    id_movimiento    BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_variante      INT      NOT NULL,
    id_sede          INT      NOT NULL,
    tipo             ENUM('INGRESO','VENTA','DEVOLUCION',
                          'TRASLADO_SALIDA','TRASLADO_ENTRADA','AJUSTE') NOT NULL,
    cantidad         INT      NOT NULL,
    id_usuario       INT,
    tipo_referencia  VARCHAR(30),
    id_referencia    BIGINT,
    observacion      VARCHAR(200),
    fecha            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimiento_variante FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante) ON DELETE RESTRICT,
    CONSTRAINT fk_movimiento_sede FOREIGN KEY (id_sede)
        REFERENCES sede(id_sede) ON DELETE RESTRICT,
    CONSTRAINT fk_movimiento_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    INDEX idx_movimiento_fecha (fecha),
    INDEX idx_movimiento_variante_sede (id_variante, id_sede)
) ENGINE=InnoDB;

CREATE TABLE traslado (
    id_traslado          INT AUTO_INCREMENT PRIMARY KEY,
    id_sede_origen       INT      NOT NULL,
    id_sede_destino      INT      NOT NULL,
    id_usuario_solicita  INT      NOT NULL,
    id_usuario_recibe    INT,
    estado               ENUM('SOLICITADO','EN_TRANSITO','RECIBIDO','CANCELADO')
                         NOT NULL DEFAULT 'SOLICITADO',
    fecha_solicitud      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_recepcion      DATETIME,
    CONSTRAINT fk_traslado_origen FOREIGN KEY (id_sede_origen)
        REFERENCES sede(id_sede) ON DELETE RESTRICT,
    CONSTRAINT fk_traslado_destino FOREIGN KEY (id_sede_destino)
        REFERENCES sede(id_sede) ON DELETE RESTRICT,
    CONSTRAINT fk_traslado_solicita FOREIGN KEY (id_usuario_solicita)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT fk_traslado_recibe FOREIGN KEY (id_usuario_recibe)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_traslado_sedes CHECK (id_sede_origen <> id_sede_destino)
) ENGINE=InnoDB;

CREATE TABLE detalle_traslado (
    id_detalle_traslado INT AUTO_INCREMENT PRIMARY KEY,
    id_traslado         INT NOT NULL,
    id_variante         INT NOT NULL,
    cantidad            INT NOT NULL,
    CONSTRAINT fk_detraslado_traslado FOREIGN KEY (id_traslado)
        REFERENCES traslado(id_traslado) ON DELETE CASCADE,
    CONSTRAINT fk_detraslado_variante FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante) ON DELETE RESTRICT,
    CONSTRAINT chk_detraslado_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO: VENTAS
-- =====================================================================

-- Tabla unificada: la venta web y la venta en mostrador comparten
-- estructura y se diferencian por el atributo canal.
CREATE TABLE pedido (
    id_pedido      BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_cliente     INT,
    id_sede        INT           NOT NULL,
    id_usuario     INT,                       -- NULL cuando canal = WEB
    canal          ENUM('WEB','TIENDA') NOT NULL,
    tipo_entrega   ENUM('INMEDIATA','RECOGER_EN_TIENDA','DOMICILIO')
                   NOT NULL DEFAULT 'INMEDIATA',
    estado         ENUM('PENDIENTE','PAGADO','PREPARANDO','ENVIADO',
                        'ENTREGADO','CANCELADO') NOT NULL DEFAULT 'PENDIENTE',
    codigo_qr      VARCHAR(80)   NOT NULL UNIQUE,
    subtotal       DECIMAL(12,2) NOT NULL DEFAULT 0,
    impuestos      DECIMAL(12,2) NOT NULL DEFAULT 0,
    total          DECIMAL(12,2) NOT NULL DEFAULT 0,
    fecha_pedido   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (id_cliente)
        REFERENCES cliente(id_cliente) ON DELETE RESTRICT,
    CONSTRAINT fk_pedido_sede FOREIGN KEY (id_sede)
        REFERENCES sede(id_sede) ON DELETE RESTRICT,
    CONSTRAINT fk_pedido_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    INDEX idx_pedido_fecha (fecha_pedido),
    INDEX idx_pedido_sede_fecha (id_sede, fecha_pedido)
) ENGINE=InnoDB;

CREATE TABLE detalle_pedido (
    id_detalle_pedido BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_pedido         BIGINT        NOT NULL,
    id_variante       INT           NOT NULL,
    cantidad          INT           NOT NULL,
    -- Dato historico inmutable: no es redundancia, el precio de catalogo
    -- puede cambiar sin afectar facturas ya emitidas.
    precio_unitario   DECIMAL(12,2) NOT NULL,
    subtotal_linea    DECIMAL(12,2) NOT NULL,
    CONSTRAINT fk_detpedido_pedido FOREIGN KEY (id_pedido)
        REFERENCES pedido(id_pedido) ON DELETE CASCADE,
    CONSTRAINT fk_detpedido_variante FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante) ON DELETE RESTRICT,
    CONSTRAINT chk_detpedido_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

CREATE TABLE envio (
    id_envio           BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_pedido          BIGINT       NOT NULL UNIQUE,
    direccion          VARCHAR(150) NOT NULL,
    ciudad             VARCHAR(60)  NOT NULL,
    destinatario       VARCHAR(120) NOT NULL,
    telefono_contacto  VARCHAR(20)  NOT NULL,
    transportadora     VARCHAR(60),
    numero_guia        VARCHAR(60),
    estado             ENUM('PREPARANDO','DESPACHADO','ENTREGADO','DEVUELTO')
                       NOT NULL DEFAULT 'PREPARANDO',
    fecha_despacho     DATETIME,
    fecha_entrega      DATETIME,
    CONSTRAINT fk_envio_pedido FOREIGN KEY (id_pedido)
        REFERENCES pedido(id_pedido) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO: PAGOS (pasarela simulada)
-- =====================================================================

CREATE TABLE metodo_pago (
    id_metodo_pago INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(50) NOT NULL UNIQUE,
    tipo           ENUM('EFECTIVO','TARJETA','TRANSFERENCIA') NOT NULL,
    activo         BOOLEAN     NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE pago (
    id_pago                 BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_pedido               BIGINT        NOT NULL,
    id_metodo_pago          INT           NOT NULL,
    monto                   DECIMAL(12,2) NOT NULL,
    estado                  ENUM('PENDIENTE','APROBADO','RECHAZADO','REVERSADO')
                            NOT NULL DEFAULT 'PENDIENTE',
    referencia_transaccion  VARCHAR(80) UNIQUE,
    fecha_pago              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pago_pedido FOREIGN KEY (id_pedido)
        REFERENCES pedido(id_pedido) ON DELETE RESTRICT,
    CONSTRAINT fk_pago_metodo FOREIGN KEY (id_metodo_pago)
        REFERENCES metodo_pago(id_metodo_pago) ON DELETE RESTRICT,
    CONSTRAINT chk_pago_monto CHECK (monto > 0)
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO: FACTURACION ELECTRONICA
-- =====================================================================

CREATE TABLE factura (
    id_factura        BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_pedido         BIGINT        NOT NULL UNIQUE,
    numero_factura    VARCHAR(30)   NOT NULL UNIQUE,
    prefijo           VARCHAR(10)   NOT NULL,
    cufe              VARCHAR(100) UNIQUE,
    estado_dian       ENUM('PENDIENTE','VALIDADA','RECHAZADA')
                      NOT NULL DEFAULT 'PENDIENTE',
    subtotal          DECIMAL(12,2) NOT NULL,
    iva               DECIMAL(12,2) NOT NULL,
    total             DECIMAL(12,2) NOT NULL,
    fecha_emision     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_validacion  DATETIME,
    url_xml           VARCHAR(255),
    CONSTRAINT fk_factura_pedido FOREIGN KEY (id_pedido)
        REFERENCES pedido(id_pedido) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO: DEVOLUCIONES Y CAMBIOS
-- =====================================================================

CREATE TABLE devolucion (
    id_devolucion    BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_pedido        BIGINT       NOT NULL,
    id_sede          INT          NOT NULL,
    id_usuario       INT          NOT NULL,
    tipo             ENUM('CAMBIO','DEVOLUCION') NOT NULL,
    motivo           VARCHAR(200) NOT NULL,
    estado           ENUM('SOLICITADA','APROBADA','RECHAZADA','COMPLETADA')
                     NOT NULL DEFAULT 'SOLICITADA',
    fecha_solicitud  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_devolucion_pedido FOREIGN KEY (id_pedido)
        REFERENCES pedido(id_pedido) ON DELETE RESTRICT,
    CONSTRAINT fk_devolucion_sede FOREIGN KEY (id_sede)
        REFERENCES sede(id_sede) ON DELETE RESTRICT,
    CONSTRAINT fk_devolucion_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE detalle_devolucion (
    id_detalle_devolucion BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_devolucion         BIGINT NOT NULL,
    id_detalle_pedido     BIGINT NOT NULL,
    cantidad              INT    NOT NULL,
    id_variante_cambio    INT,             -- variante entregada a cambio
    CONSTRAINT fk_detdev_devolucion FOREIGN KEY (id_devolucion)
        REFERENCES devolucion(id_devolucion) ON DELETE CASCADE,
    CONSTRAINT fk_detdev_detpedido FOREIGN KEY (id_detalle_pedido)
        REFERENCES detalle_pedido(id_detalle_pedido) ON DELETE RESTRICT,
    CONSTRAINT fk_detdev_variante FOREIGN KEY (id_variante_cambio)
        REFERENCES variante(id_variante) ON DELETE RESTRICT,
    CONSTRAINT chk_detdev_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

CREATE TABLE nota_credito (
    id_nota_credito BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_devolucion   BIGINT        NOT NULL UNIQUE,
    id_factura      BIGINT        NOT NULL,
    numero_nota     VARCHAR(30)   NOT NULL UNIQUE,
    cude            VARCHAR(100) UNIQUE,
    monto           DECIMAL(12,2) NOT NULL,
    estado_dian     ENUM('PENDIENTE','VALIDADA','RECHAZADA')
                    NOT NULL DEFAULT 'PENDIENTE',
    fecha_emision   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_nota_devolucion FOREIGN KEY (id_devolucion)
        REFERENCES devolucion(id_devolucion) ON DELETE RESTRICT,
    CONSTRAINT fk_nota_factura FOREIGN KEY (id_factura)
        REFERENCES factura(id_factura) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =====================================================================
-- MODULO OPCIONAL: NOMINA
--
-- Este bloque NO esta respaldado por ningun caso de uso de la seccion 2
-- ni por la problematica de la seccion 1. Si se decide incluirlo, es
-- necesario agregar el actor correspondiente, sus casos de uso y sus
-- descripciones. Si se decide excluirlo, basta con eliminar este bloque:
-- ninguna otra tabla del esquema depende de el.
-- =====================================================================

/*
CREATE TABLE contrato (
    id_contrato    INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT           NOT NULL,
    tipo_contrato  ENUM('INDEFINIDO','FIJO','PRESTACION') NOT NULL,
    cargo          VARCHAR(80)   NOT NULL,
    salario_base   DECIMAL(12,2) NOT NULL,
    fecha_inicio   DATE          NOT NULL,
    fecha_fin      DATE,
    estado         ENUM('ACTIVO','TERMINADO','SUSPENDIDO') NOT NULL DEFAULT 'ACTIVO',
    CONSTRAINT fk_contrato_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_contrato_salario CHECK (salario_base > 0)
) ENGINE=InnoDB;

CREATE TABLE periodo_nomina (
    id_periodo    INT AUTO_INCREMENT PRIMARY KEY,
    anio          SMALLINT NOT NULL,
    mes           TINYINT  NOT NULL,
    quincena      TINYINT  NOT NULL,
    fecha_inicio  DATE     NOT NULL,
    fecha_fin     DATE     NOT NULL,
    estado        ENUM('ABIERTO','LIQUIDADO','PAGADO') NOT NULL DEFAULT 'ABIERTO',
    CONSTRAINT uq_periodo UNIQUE (anio, mes, quincena)
) ENGINE=InnoDB;

CREATE TABLE novedad_nomina (
    id_novedad   BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_contrato  INT           NOT NULL,
    id_periodo   INT           NOT NULL,
    tipo         ENUM('HORA_EXTRA','INCAPACIDAD','VACACIONES',
                      'BONIFICACION','DESCUENTO','COMISION') NOT NULL,
    cantidad     DECIMAL(8,2)  NOT NULL DEFAULT 0,
    valor        DECIMAL(12,2) NOT NULL DEFAULT 0,
    descripcion  VARCHAR(200),
    CONSTRAINT fk_novedad_contrato FOREIGN KEY (id_contrato)
        REFERENCES contrato(id_contrato) ON DELETE CASCADE,
    CONSTRAINT fk_novedad_periodo FOREIGN KEY (id_periodo)
        REFERENCES periodo_nomina(id_periodo) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE liquidacion_nomina (
    id_liquidacion     BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_contrato        INT           NOT NULL,
    id_periodo         INT           NOT NULL,
    salario_devengado  DECIMAL(12,2) NOT NULL,
    total_devengos     DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_deducciones  DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_pagar        DECIMAL(12,2) NOT NULL,
    fecha_pago         DATE,
    CONSTRAINT fk_liquidacion_contrato FOREIGN KEY (id_contrato)
        REFERENCES contrato(id_contrato) ON DELETE RESTRICT,
    CONSTRAINT fk_liquidacion_periodo FOREIGN KEY (id_periodo)
        REFERENCES periodo_nomina(id_periodo) ON DELETE RESTRICT,
    CONSTRAINT uq_liquidacion UNIQUE (id_contrato, id_periodo)
) ENGINE=InnoDB;
*/

-- =====================================================================
-- DATOS INICIALES
-- =====================================================================

INSERT INTO rol (nombre, descripcion) VALUES
    ('ADMINISTRADOR', 'Control total del sistema multisede'),
    ('TRABAJADOR',    'Operacion de ventas y consultas en su sede');

INSERT INTO talla (valor, orden) VALUES
    ('XS',1), ('S',2), ('M',3), ('L',4), ('XL',5), ('XXL',6);

INSERT INTO color (nombre, codigo_hex) VALUES
    ('Negro','#000000'), ('Blanco','#FFFFFF'), ('Azul','#1E3A8A'),
    ('Gris','#6B7280'),  ('Beige','#D6C7A1');

INSERT INTO metodo_pago (nombre, tipo) VALUES
    ('Efectivo','EFECTIVO'), ('Tarjeta debito','TARJETA'),
    ('Tarjeta credito','TARJETA'), ('PSE','TRANSFERENCIA');

INSERT INTO sede (nombre, direccion, telefono) VALUES
    ('Solsticio Chapinero', 'Calle 63 # 11-45',  '6013001122'),
    ('Solsticio Centro',    'Carrera 7 # 22-18', '6013004455'),
    ('Solsticio Suba',      'Calle 145 # 91-30', '6013007788');
