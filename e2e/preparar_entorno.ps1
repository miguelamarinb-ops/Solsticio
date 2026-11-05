# Prepara el entorno para el recorrido de la interfaz:
#   1. crea las bases solsticio_e2e en MySQL y MongoDB (las borra antes si ya existían),
#   2. carga el catálogo de ejemplo y un administrador de prueba,
#   3. levanta la API en el puerto 5001 apuntando a esas bases.
# Nunca toca la base de desarrollo "solsticio".
#
# Uso, desde la carpeta del proyecto:
#   .\e2e\preparar_entorno.ps1
#   python e2e\recorrido_interfaz.py
#   .\e2e\borrar_entorno.ps1
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "comun.ps1")
Set-Location $Proyecto
Stop-ServidorE2E

# MySQL: el mismo script del proyecto, con otro nombre de base
$sql = [IO.File]::ReadAllText((Join-Path $Proyecto "database\solsticio_schema.sql"))
$sql = $sql.Replace("DROP DATABASE IF EXISTS solsticio;", "DROP DATABASE IF EXISTS $BaseE2E;").
            Replace("CREATE DATABASE solsticio", "CREATE DATABASE $BaseE2E").
            Replace("USE solsticio;", "USE $BaseE2E;")
if (-not $sql.Contains("USE $BaseE2E;")) { throw "El script SQL cambió: no pude redirigirlo a $BaseE2E." }
Invoke-MySql $sql

# Variables para los comandos siguientes y para el servidor (tienen prioridad sobre el .env)
$c = Get-ConexionMySql
$env:DATABASE_URL = "mysql+pymysql://$($c.Usuario):$($c.Clave)@$($c.Servidor):$($c.Puerto)/$BaseE2E"
$env:MONGO_DB = $BaseE2E
$env:PYTHONIOENCODING = "utf-8"
$python = Join-Path $Proyecto ".venv\Scripts\python.exe"
& $python -c "from api.config import Config; from pymongo import MongoClient; MongoClient(Config.MONGO_URI).drop_database('$BaseE2E')"
& $python -m flask --app app verificar-bd
& $python -m flask --app app sembrar-demo
& $python -m flask --app app crear-admin --email admin.e2e@solsticio.com --documento 8000000001 --nombres Admin --apellidos E2E --password AdminE2E12345

# API de pruebas en un proceso aparte (hereda las variables de arriba)
Start-Process -FilePath $python -ArgumentList "-m", "flask", "--app", "app", "run", "--port", "$PuertoE2E" -WorkingDirectory $Proyecto -WindowStyle Hidden
foreach ($i in 1..20) {
    try { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$PuertoE2E/api/v1" -TimeoutSec 2 | Out-Null; break }
    catch { Start-Sleep -Milliseconds 500 }
}
Write-Host "API de pruebas lista en http://127.0.0.1:$PuertoE2E (bases $BaseE2E)."
