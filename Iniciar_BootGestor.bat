@echo off
echo.
echo 🚀 BootGestor - Automatización de Glosas
echo ==========================================
echo.
echo Iniciando aplicación...
echo.

if not exist "BootGestor.exe" (
    echo ❌ Error: BootGestor.exe no encontrado
    echo Asegurate de estar en la carpeta correcta
    pause
    exit /b 1
)

echo ⏳ Cargando... (puede tardar unos segundos la primera vez)
BootGestor.exe

if errorlevel 1 (
    echo.
    echo ❌ La aplicación se cerró inesperadamente
    echo Si el problema persiste, revisa los logs
    pause
)
