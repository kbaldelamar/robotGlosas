@echo off
echo ================================================================
echo       DESCARGA DE TESSERACT OCR PARA BOOTGESTOR
echo ================================================================
echo.
echo Este script le ayudara a descargar Tesseract OCR para usar
echo con el Separador de PDF.
echo.
echo Opciones disponibles:
echo.
echo [1] Abrir pagina de descarga oficial (Manual)
echo [2] Descargar automaticamente (Python)
echo [3] Verificar si ya esta instalado
echo [4] Salir
echo.
set /p choice="Seleccione una opcion (1-4): "

if "%choice%"=="1" goto manual
if "%choice%"=="2" goto automatic
if "%choice%"=="3" goto verify
if "%choice%"=="4" goto end

:manual
echo.
echo Abriendo pagina de descarga oficial...
start https://github.com/UB-Mannheim/tesseract/wiki
echo.
echo Instrucciones:
echo 1. Descargue el archivo .exe para Windows 64-bit
echo 2. Guarde el archivo en la carpeta 'installers' del proyecto
echo 3. La aplicacion lo detectara automaticamente
echo.
goto end

:automatic
echo.
echo Descargando Tesseract OCR automaticamente...
python -c "
import urllib.request
import os
print('Descargando Tesseract OCR...')
url = 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe'
filename = 'installers/tesseract-ocr-w64-setup-5.3.3.20231005.exe'
os.makedirs('installers', exist_ok=True)
urllib.request.urlretrieve(url, filename)
print(f'Descarga completada: {filename}')
print('El instalador esta listo para usar en la aplicacion.')
"
echo.
goto end

:verify
echo.
echo Verificando instalacion de Tesseract...
tesseract --version 2>nul
if %errorlevel%==0 (
    echo ✅ Tesseract esta instalado y funcionando
) else (
    echo ❌ Tesseract no esta instalado o no esta en el PATH
    echo.
    echo Para instalarlo:
    echo 1. Use la opcion 1 o 2 de este menu
    echo 2. O use el Separador de PDF que lo instalara automaticamente
)
echo.
goto end

:end
echo.
echo Presione cualquier tecla para salir...
pause >nul