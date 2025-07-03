import os
import sys

class Settings:
    """
    Configuración global de la aplicación.
    Centraliza todas las constantes y configuraciones.
    """
    
    # ✅ RUTA FIJA PARA LA BASE DE DATOS
    @staticmethod
    def get_database_path():
        """Obtiene la ruta FIJA donde debe estar la BD."""
        
        # RUTA FIJA: C:\robotGlosas\data\
        db_dir = r"C:\robotGlosas\data"
        
        # Crear el directorio si no existe
        try:
            os.makedirs(db_dir, exist_ok=True)
            print(f"✅ Directorio de BD verificado: {db_dir}")
        except Exception as e:
            print(f"❌ Error creando directorio {db_dir}: {e}")
            # Fallback: usar directorio actual
            db_dir = os.getcwd()
        
        db_path = os.path.join(db_dir, "bootgestor.db")
        print(f"📂 Ruta de BD: {db_path}")
        return db_path
    
    # Base de datos - USAR RUTA FIJA
    DATABASE_NAME = "bootgestor.db"
    DATABASE_PATH = get_database_path.__func__()
    
    # Configuración de logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configuración de Playwright
    BROWSER_HEADLESS = False
    BROWSER_TIMEOUT = 30000  # 30 segundos
    
    # URLs de la aplicación web
    LOGIN_URL = "https://vco.ctamedicas.com/app/"
    GLOSAS_URL = "https://vco.ctamedicas.com/app/"
    
    # Credenciales (en producción usar variables de entorno)
    DEFAULT_USERNAME = os.getenv('BOOTGESTOR_USERNAME', '50011648301')
    DEFAULT_PASSWORD = os.getenv('BOOTGESTOR_PASSWORD', 'Uh8Ai0Hg1Sr1')

    #DEFAULT_USERNAME = os.getenv('BOOTGESTOR_USERNAME', '230790043001')
    #DEFAULT_PASSWORD = os.getenv('BOOTGESTOR_PASSWORD', 'Tw2Vm2Hr4Yu9')
    
    # Interfaz
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    WINDOW_TITLE = "BootGestor - Automatización de Glosas"