#!/usr/bin/env python3
"""
Script FINAL que incluye el navegador Chromium en el ejecutable.
🎯 SOLUCIONA: Executable doesn't exist - playwright install

CAMBIOS CRÍTICOS:
- Incluye navegador Chromium completo
- Configura paths correctos para Playwright
- Crea ejecutable completamente autocontenido
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil
import platform

def verificar_sistema():
    """Verifica el sistema."""
    print("🔍 Verificando sistema...")
    
    print(f"   Python: {sys.version}")
    print(f"   PyInstaller: ", end="")
    try:
        import PyInstaller
        print(f"{PyInstaller.__version__}")
    except ImportError:
        print("❌ No encontrado")
        return False
    
    print(f"   Playwright: ", end="")
    try:
        import playwright
        # Algunas versiones no tienen __version__
        try:
            version = playwright.__version__
        except AttributeError:
            version = "instalado (versión no disponible)"
        print(f"{version}")
    except ImportError:
        print("❌ No encontrado")
        return False
    
    return True

def instalar_navegador_playwright():
    """Instala el navegador Chromium para incluirlo en el ejecutable."""
    print("🎭 Instalando navegador Chromium...")
    
    try:
        # Instalar Chromium
        resultado = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Chromium instalado correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando Chromium: {e}")
        print(f"Salida: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def encontrar_chromium_path():
    """Encuentra la ubicación del navegador Chromium instalado."""
    print("🔍 Buscando ubicación de Chromium...")
    
    # Ubicaciones comunes de Playwright
    posibles_ubicaciones = [
        Path.home() / "AppData" / "Local" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
        Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")),
    ]
    
    for ubicacion in posibles_ubicaciones:
        if ubicacion.exists():
            # Buscar carpeta chromium
            chromium_dirs = list(ubicacion.glob("chromium-*"))
            if chromium_dirs:
                chromium_path = chromium_dirs[0]
                print(f"✅ Chromium encontrado en: {chromium_path}")
                return chromium_path
    
    print("❌ No se encontró Chromium instalado")
    return None

def limpiar_builds():
    """Limpia builds anteriores."""
    print("🗑️ Limpiando builds anteriores...")
    
    for dir_name in ["build", "dist", "__pycache__"]:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"   Eliminado: {dir_name}")
    
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"   Eliminado: {spec_file}")

def crear_config_playwright():
    """Crea configuración especial de Playwright para el ejecutable."""
    print("🔧 Creando configuración de Playwright...")
    
    # Verificar que existe la carpeta config
    config_dir = Path("config")
    if not config_dir.exists():
        config_dir.mkdir()
        print("📁 Carpeta config creada")
    
    # Crear archivo de configuración mejorado
    config_content = '''"""
Configuración de Playwright para ejecutable con navegador incluido.
🎯 UBICACIÓN: config/playwright_exe_config.py
"""

import os
import sys
from pathlib import Path

def setup_for_exe():
    """Configura Playwright para ejecutable con navegador incluido."""
    if getattr(sys, 'frozen', False):
        # Estamos en un ejecutable PyInstaller
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller onefile
            bundle_dir = Path(sys._MEIPASS)
        else:
            # PyInstaller onedir
            bundle_dir = Path(sys.executable).parent
        
        # Configurar ruta de navegadores de Playwright
        playwright_browsers = bundle_dir / "playwright_browsers"
        
        if playwright_browsers.exists():
            # Configurar variables de entorno
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(playwright_browsers)
            os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
            
            print(f"✅ Playwright configurado con navegador embebido: {playwright_browsers}")
        else:
            print(f"⚠️ Navegadores no encontrados en: {playwright_browsers}")
            # Fallback: intentar usar navegador del sistema
            print("🔄 Intentando usar navegador del sistema...")
    else:
        # Modo desarrollo - usar configuración normal
        print("🔧 Modo desarrollo - usando configuración estándar de Playwright")

def verificar_playwright():
    """Verifica que Playwright esté funcionando."""
    try:
        import playwright
        try:
            version = playwright.__version__
        except AttributeError:
            version = "versión desconocida"
        print(f"✅ Playwright {version} importado correctamente")
        return True
    except ImportError as e:
        print(f"❌ Error importando Playwright: {e}")
        return False
'''
    
    config_file = config_dir / "playwright_exe_config.py"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"✅ Configuración creada: {config_file}")
    return config_file

def crear_ejecutable_con_navegador():
    """Crea ejecutable incluyendo el navegador Chromium."""
    print("🏗️ Creando ejecutable CON NAVEGADOR...")
    
    # Encontrar Chromium
    chromium_path = encontrar_chromium_path()
    if not chromium_path:
        return False
    
    # Comando de PyInstaller con navegador incluido
    comando = [
        sys.executable, "-m", "PyInstaller",
        
        # Configuración básica
        "--onefile",
        "--windowed", 
        "--clean",
        "--noconfirm",
        "--noupx",
        
        # ✅ INCLUIR NAVEGADOR CHROMIUM:
        f"--add-data={chromium_path};playwright_browsers/chromium-{chromium_path.name.split('-')[1]}",
        
        # Incluir archivos de proyecto
        "--add-data=config;config",
        *(["--add-data=contrato.pdf;."] if Path("contrato.pdf").exists() else []),
        
        # Importaciones críticas
        "--hidden-import=playwright",
        "--hidden-import=playwright.sync_api",
        "--hidden-import=playwright.async_api",
        "--hidden-import=playwright._impl._api_structures",
        "--hidden-import=playwright._impl._transport",
        "--hidden-import=playwright._impl._browser_type",
        
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        
        "--hidden-import=sqlite3",
        "--hidden-import=_sqlite3", 
        "--hidden-import=asyncio",
        "--hidden-import=logging",
        "--hidden-import=json",
        "--hidden-import=datetime",
        "--hidden-import=pathlib",
        "--hidden-import=dataclasses",
        "--hidden-import=enum",
        "--hidden-import=typing",
        
        # Exclusiones
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=tkinter",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        
        "--name=BootGestor",
        "main.py"
    ]
    
    print("📦 Ejecutando PyInstaller con navegador incluido...")
    print("⏳ ADVERTENCIA: Esto tardará MUCHO tiempo (navegador es ~200MB)")
    
    try:
        resultado = subprocess.run(comando, check=True)
        print("✅ Ejecutable con navegador creado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creando ejecutable: {e}")
        return False

def verificar_ejecutable():
    """Verifica el ejecutable creado."""
    exe_path = Path("dist/BootGestor.exe")
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Ejecutable creado: {exe_path}")
        print(f"📏 Tamaño: {size_mb:.1f} MB")
        
        if size_mb < 100:
            print("⚠️ Tamaño sospechosamente pequeño - el navegador podría no estar incluido")
        else:
            print("✅ Tamaño correcto - navegador probablemente incluido")
        
        crear_script_prueba()
        return True
    else:
        print("❌ Ejecutable no encontrado")
        return False

def crear_script_prueba():
    """Crea script de prueba mejorado."""
    test_content = '''@echo off
echo 🧪 PROBANDO BOOTGESTOR CON NAVEGADOR
echo =====================================
echo.

if not exist "BootGestor.exe" (
    echo ❌ BootGestor.exe no encontrado
    pause
    exit /b 1
)

echo ✅ Ejecutable encontrado
echo.

echo 📋 Información del ejecutable:
for %%I in (BootGestor.exe) do echo    Tamaño: %%~zI bytes

echo.
echo 🚀 Iniciando BootGestor...
echo 💡 Si es la primera vez, puede tardar 15-30 segundos
echo.

BootGestor.exe

if errorlevel 1 (
    echo.
    echo ❌ BootGestor falló
    echo.
    echo 💡 SOLUCIONES COMUNES:
    echo 1. Instalar Visual C++ Redistributables
    echo 2. Ejecutar como Administrador
    echo 3. Desactivar antivirus temporalmente
    echo 4. Verificar conexión a internet
    echo.
) else (
    echo.
    echo ✅ BootGestor ejecutado correctamente
)

echo.
pause
'''
    
    with open("dist/Probar_BootGestor.bat", 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("✅ Script de prueba creado")

def mostrar_resultado():
    """Muestra resultado final."""
    print("\n" + "="*70)
    print("🎉 EJECUTABLE CON NAVEGADOR CREADO")
    print("="*70)
    print()
    print("📁 ARCHIVOS:")
    print("   • dist/BootGestor.exe (incluye navegador Chromium)")
    print("   • dist/Probar_BootGestor.bat")
    print()
    print("📦 CARACTERÍSTICAS:")
    print("   ✅ Navegador Chromium embebido")
    print("   ✅ No requiere 'playwright install' en cliente")
    print("   ✅ Completamente autocontenido")
    print("   ⚠️ Tamaño grande (~300-400MB)")
    print()
    print("🚀 DISTRIBUCIÓN:")
    print("   • Envía solo BootGestor.exe")
    print("   • Funciona sin instalaciones adicionales")
    print("   • Primera ejecución puede tardar 30 segundos")
    print()

def main():
    """Función principal."""
    print("🚀 CREADOR DE EJECUTABLE CON NAVEGADOR")
    print("🎯 INCLUYE CHROMIUM COMPLETO")
    print("="*60)
    print()
    
    if not verificar_sistema():
        input("Presiona Enter para salir...")
        return False
    
    # Instalar navegador si no existe
    if not instalar_navegador_playwright():
        input("Presiona Enter para salir...")
        return False
    
    # Crear configuración
    crear_config_playwright()
    
    # Limpiar builds
    limpiar_builds()
    
    # Crear ejecutable
    if not crear_ejecutable_con_navegador():
        print("\n❌ Error creando ejecutable con navegador")
        input("Presiona Enter para salir...")
        return False
    
    # Verificar resultado
    if not verificar_ejecutable():
        print("\n❌ Ejecutable no válido")
        input("Presiona Enter para salir...")
        return False
    
    mostrar_resultado()
    
    # Preguntar si probar
    print()
    respuesta = input("¿Probar el ejecutable? (s/n): ").lower()
    if respuesta in ['s', 'si', 'y', 'yes']:
        try:
            print("🚀 Iniciando BootGestor...")
            subprocess.Popen([str(Path("dist/BootGestor.exe"))])
            print("✅ BootGestor iniciado (puede tardar en aparecer)")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Cancelado por usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        input("Presiona Enter para salir...")