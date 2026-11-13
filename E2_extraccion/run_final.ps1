# Script automatizado de consolidación, pruebas y empaquetado para el Entregable 2 (E2)
# Uso en PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\run_final.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ">>> EJECUCIÓN FINAL Y EMPAQUETADO DEL ENTREGABLE 2 (E2) <<<" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

try {
    # 1. Procesar todos los datos crudos acumulados en CSV limpios
    Write-Host "`n[Paso 1/5] Procesando datos crudos JSON hacia CSV limpios e integrados..." -ForegroundColor Yellow
    uv run python scripts/procesar_datos.py
    Write-Host "-> CSVs generados exitosamente en data/processed/" -ForegroundColor Green

    # 2. Ejecutar batería de pruebas unitarias
    Write-Host "`n[Paso 2/5] Ejecutando pruebas unitarias formales con pytest..." -ForegroundColor Yellow
    uv run pytest -v
    Write-Host "-> 100% de pruebas unitarias aprobadas." -ForegroundColor Green

    # 3. Auditoría automática de coherencia e integridad
    Write-Host "`n[Paso 3/5] Verificando coherencia e integridad referencial..." -ForegroundColor Yellow
    uv run python scripts/verificar_coherencia.py
    Write-Host "-> Auditoría de coherencia superada sin errores." -ForegroundColor Green

    # 4. Ejecutar el Notebook Jupyter y exportar a HTML autocontenido
    Write-Host "`n[Paso 4/5] Ejecutando y exportando Notebook Jupyter a formato HTML..." -ForegroundColor Yellow
    uv run python -m nbconvert --to html --execute notebooks/E2_extraccion_limpieza.ipynb
    Write-Host "-> HTML generado exitosamente en notebooks/E2_extraccion_limpieza.html" -ForegroundColor Green

    # 5. Generar archivo comprimido E2_entrega.zip
    Write-Host "`n[Paso 5/5] Empaquetando entregable en E2_entrega.zip..." -ForegroundColor Yellow
    $zipPath = "E2_entrega.zip"
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }

    $archivosParaZip = @(
        "notebooks\E2_extraccion_limpieza.html",
        "notebooks\E2_extraccion_limpieza.ipynb",
        "modelo\vocab.ttl",
        "modelo\modelo_tentativo.md",
        "modelo\mapeo_campos.csv",
        "data\processed\citybikes_estaciones.csv",
        "data\processed\citybikes_estado.csv",
        "data\processed\citybikes_operadores.csv",
        "data\processed\openmeteo_celdas.csv",
        "data\processed\openmeteo_observaciones.csv",
        "data\processed\enlace_estacion_celda.csv",
        "data\processed\enlace_estado_observacion.csv",
        "data\processed\incidencias_calidad.csv",
        "data\processed\procedencia.csv",
        "pyproject.toml",
        "requirements.txt"
    )

    Compress-Archive -Path $archivosParaZip -DestinationPath $zipPath
    Write-Host "-> Paquete generado exitosamente: $zipPath" -ForegroundColor Green

    Write-Host "`n==========================================================" -ForegroundColor Cyan
    Write-Host ">>> ENTREGABLE 2 LISTO PARA SUBIR A CANVAS CON ÉXITO <<<" -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "Archivo principal generado: notebooks/E2_extraccion_limpieza.html" -ForegroundColor White
    Write-Host "Archivo ZIP empaquetado:    E2_entrega.zip" -ForegroundColor White
}
catch {
    Write-Host "`n[ERROR EN LA EJECUCIÓN] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
