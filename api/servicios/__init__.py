"""
Capa de servicios: lógica de negocio y transacciones. Las rutas validan permisos
y delegan aquí toda operación que escriba en la base de datos.
Regla: stock.cantidad solo cambia a través de inventario.registrar_movimiento().
"""
