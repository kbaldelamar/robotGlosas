"""
Runtime hook para corregir problema de Python DLL.
Este archivo se ejecuta ANTES que tu aplicación.
"""
import os
import sys
from pathlib import Path

def fix_dll_paths():
    """Corrige las rutas de DLLs para PyInstaller onefile."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Estamos en PyInstaller onefile
        bundle_dir = Path(sys._MEIPASS)
        
        # Agregar directorio bundle al PATH
        if str(bundle_dir) not in os.environ.get('PATH', ''):
            os.environ['PATH'] = str(bundle_dir) + os.pathsep + os.environ.get('PATH', '')
        
        # Configurar Playwright específicamente
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundle_dir)
        os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
        
        print(f"🔧 DLL paths corregidos: {bundle_dir}")

# Ejecutar corrección automáticamente
fix_dll_paths()
