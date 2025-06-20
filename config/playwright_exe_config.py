"""
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
