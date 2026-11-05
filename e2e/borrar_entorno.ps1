# Apaga la API de pruebas (puerto 5001) y borra las bases solsticio_e2e de MySQL y MongoDB.
# No toca la base de desarrollo "solsticio".
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "comun.ps1")
Set-Location $Proyecto

Stop-ServidorE2E
Invoke-MySql "DROP DATABASE IF EXISTS $BaseE2E;"
& (Join-Path $Proyecto ".venv\Scripts\python.exe") -c "from api.config import Config; from pymongo import MongoClient; MongoClient(Config.MONGO_URI).drop_database('$BaseE2E')"
Write-Host "Entorno de pruebas borrado: servidor detenido y bases $BaseE2E eliminadas."
