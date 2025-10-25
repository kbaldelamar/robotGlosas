@echo off
echo ================================================================
echo     INSTALACION PORTABLE DE TESSERACT OCR (SIN ADMIN)
echo ================================================================
echo.
echo Este script instala Tesseract de forma portable sin necesidad
echo de permisos de administrador.
echo.

set "INSTALL_DIR=%~dp0tesseract-portable"
set "DOWNLOAD_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

echo [Paso 1] Creando directorio portable...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo [Paso 2] Descargando Tesseract OCR...
powershell -Command "try { Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile 'tesseract_temp.exe' -UseBasicParsing; Write-Host 'Descarga completada' } catch { Write-Host 'Error descargando:', $_.Exception.Message; exit 1 }"

if not exist "tesseract_temp.exe" (
    echo ERROR: No se pudo descargar Tesseract
    echo.
    echo Alternativas:
    echo 1. Verificar conexion a internet
    echo 2. Descargar manualmente desde: https://github.com/UB-Mannheim/tesseract/wiki
    echo 3. Ejecutar aplicacion como administrador
    pause
    exit /b 1
)

echo [Paso 3] Extrayendo archivos (modo portable)...
echo IMPORTANTE: Se abrira el instalador.
echo - Cuando aparezca, seleccione una carpeta DENTRO del proyecto
echo - Sugerencia: %INSTALL_DIR%
echo - NO use Program Files (requiere permisos admin)
echo.
echo Presione cualquier tecla para continuar con la instalacion...
pause >nul

start /wait tesseract_temp.exe

echo [Paso 4] Limpiando archivos temporales...
del tesseract_temp.exe 2>nul

echo [Paso 5] Verificando instalacion...
if exist "%INSTALL_DIR%\tesseract.exe" (
    echo ✅ Tesseract instalado correctamente en modo portable
    echo Ubicacion: %INSTALL_DIR%
    echo.
    echo La aplicacion detectara automaticamente esta instalacion.
) else (
    echo ⚠️  Verificando otras ubicaciones...
    
    REM Buscar en subdirectorios comunes
    for /d %%i in (tesseract*) do (
        if exist "%%i\tesseract.exe" (
            echo ✅ Tesseract encontrado en: %%i
            goto found
        )
    )
    
    echo ❌ No se encontro tesseract.exe
    echo.
    echo Posibles causas:
    echo - La instalacion fue cancelada
    echo - Se instalo en otra ubicacion
    echo - Se requieren permisos de administrador
    echo.
    echo Solucion: Ejecutar la aplicacion principal y volver a intentar
)

:found
echo.
echo ================================================================
echo                    INSTALACION COMPLETADA
echo ================================================================
echo.
echo Pasos siguientes:
echo 1. Reiniciar la aplicacion BootGestor
echo 2. Ir al Separador de PDF
echo 3. El OCR deberia funcionar automaticamente
echo.
echo Si aun no funciona:
echo - Verificar que tesseract.exe existe en alguna subcarpeta
echo - Usar la opcion "Continuar sin OCR" temporalmente
echo.
pause