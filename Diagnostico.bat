@echo off
echo.
echo 🔍 DIAGNOSTICO BOOTGESTOR
echo =========================
echo.

echo Verificando sistema...
echo.

REM Verificar versión de Windows
echo 💻 SISTEMA OPERATIVO:
systeminfo | findstr /B /C:"Nombre del sistema operativo"
systeminfo | findstr /B /C:"Tipo de sistema"

echo.
echo 📋 VERIFICANDO DEPENDENCIAS:

REM Verificar Visual C++ Redistributables
echo.
echo Buscando Visual C++ Redistributables...
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if errorlevel 1 (
    echo ❌ Visual C++ Redistributable x64 NO encontrado
    echo 💡 Descargar de: https://aka.ms/vs/17/release/vc_redist.x64.exe
) else (
    echo ✅ Visual C++ Redistributable x64 encontrado
)

reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x86" >nul 2>&1
if errorlevel 1 (
    echo ❌ Visual C++ Redistributable x86 NO encontrado  
    echo 💡 Descargar de: https://aka.ms/vs/17/release/vc_redist.x86.exe
) else (
    echo ✅ Visual C++ Redistributable x86 encontrado
)

echo.
echo 📁 VERIFICANDO ARCHIVOS:
if exist "BootGestor.exe" (
    echo ✅ BootGestor.exe encontrado
) else (
    echo ❌ BootGestor.exe NO encontrado
)

if exist "_internal\python*.dll" (
    echo ✅ Python DLL encontrada
    dir /b "_internal\python*.dll"
) else (
    echo ❌ Python DLL NO encontrada
)

echo.
echo 🚀 INTENTANDO EJECUTAR:
echo Si aparece error, anota el mensaje exacto...
echo.
pause

BootGestor.exe

echo.
echo 📋 Si BootGestor no funcionó:
echo 1. Instala Visual C++ Redistributables (links arriba)
echo 2. Reinicia el PC
echo 3. Ejecuta este diagnóstico nuevamente
echo 4. Envía los resultados al soporte técnico
echo.
pause
