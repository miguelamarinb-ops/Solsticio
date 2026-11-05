# Funciones compartidas por preparar_entorno.ps1 y borrar_entorno.ps1.
# Leen la conexión a MySQL del .env del proyecto y ubican mysql.exe.

$script:Proyecto = Split-Path -Parent $PSScriptRoot
$script:BaseE2E = "solsticio_e2e"
$script:PuertoE2E = 5001

function Get-ConexionMySql {
    $linea = Get-Content (Join-Path $script:Proyecto ".env") | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
    if (-not $linea) { throw "No encontré DATABASE_URL en el .env del proyecto." }
    $m = [regex]::Match($linea, '^DATABASE_URL=mysql\+pymysql://([^:]+):([^@]*)@([^:/]+):(\d+)/')
    if (-not $m.Success) { throw "DATABASE_URL no tiene la forma mysql+pymysql://usuario:clave@servidor:puerto/base" }
    [pscustomobject]@{
        Usuario  = $m.Groups[1].Value
        Clave    = $m.Groups[2].Value          # tal como está en la URL (puede venir codificada)
        Servidor = $m.Groups[3].Value
        Puerto   = $m.Groups[4].Value
    }
}

function Get-MySqlExe {
    $enPath = Get-Command mysql.exe -ErrorAction SilentlyContinue
    if ($enPath) { return $enPath.Source }
    $instalado = Get-ChildItem "C:\Program Files\MySQL\MySQL Server *\bin\mysql.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($instalado) { return $instalado.FullName }
    throw "No encontré mysql.exe. Agrega la carpeta bin de MySQL Server al PATH."
}

function Invoke-MySql([string]$sql) {
    $c = Get-ConexionMySql
    $env:MYSQL_PWD = [uri]::UnescapeDataString($c.Clave)
    try {
        $sql | & (Get-MySqlExe) --default-character-set=utf8mb4 -u $c.Usuario -h $c.Servidor -P $c.Puerto
        if ($LASTEXITCODE -ne 0) { throw "mysql terminó con código $LASTEXITCODE" }
    } finally {
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    }
}

function Stop-ServidorE2E {
    Get-NetTCPConnection -LocalPort $script:PuertoE2E -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -Confirm:$false -ErrorAction SilentlyContinue }
}
