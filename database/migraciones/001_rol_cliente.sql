-- =====================================================================
-- Migración 001 (Entrega 3): rol CLIENTE para el registro público.
--
-- Solo hace falta en una base creada ANTES de la Entrega 3. Una base nueva
-- creada con database/solsticio_schema.sql ya trae el rol.
-- Es segura de repetir y no borra datos:
--     mysql -u root -p solsticio < database/migraciones/001_rol_cliente.sql
-- =====================================================================
USE solsticio;

INSERT INTO rol (nombre, descripcion)
SELECT 'CLIENTE', 'Comprador registrado en la tienda web'
WHERE NOT EXISTS (SELECT 1 FROM rol WHERE nombre = 'CLIENTE');

SELECT id_rol, nombre, descripcion FROM rol ORDER BY id_rol;
