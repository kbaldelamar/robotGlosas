@echo off
echo ================================================================
echo         INSTALACION DE DEPENDENCIAS SEPARADOR PDF
echo ================================================================
echo.

echo [1/4] Instalando PyPDF2...
pip install PyPDF2==3.0.1

echo.
echo [2/4] Instalando Pillow (PIL)...
pip install Pillow==10.1.0

echo.
echo [3/4] Instalando PyMuPDF...
pip install PyMuPDF==1.23.14

echo.
echo [4/4] Instalando pytesseract...
pip install pytesseract==0.3.10

echo.
echo ================================================================
echo         INSTALACION COMPLETADA
echo ================================================================
echo.
echo ATENCION: Para usar OCR, tambien necesita instalar Tesseract:
echo 1. Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
echo 2. Instalar en C:\Program Files\Tesseract-OCR\
echo 3. Agregar al PATH de Windows
echo 4. Ver TESSERACT_SETUP.md para instrucciones detalladas
echo.
echo Presione cualquier tecla para continuar...
pause >nul