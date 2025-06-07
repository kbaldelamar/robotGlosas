import os

class Settings:
    """
    Configuración global de la aplicación.
    Centraliza todas las constantes y configuraciones.
    """
    
    # Base de datos
    DATABASE_NAME = "bootgestor.db"
    DATABASE_PATH = os.path.join(os.getcwd(), DATABASE_NAME)
    
    # Configuración de logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configuración de Playwright
    BROWSER_HEADLESS = False
    BROWSER_TIMEOUT = 30000  # 30 segundos
    
    # URLs de la aplicación web (modificar según tu sitio)
    LOGIN_URL = "https://vco.ctamedicas.com/app/"
    GLOSAS_URL = "https://vco.ctamedicas.com/app/"  # Mismo por ahora
    
    # Credenciales (en producción usar variables de entorno)
    DEFAULT_USERNAME = os.getenv('BOOTGESTOR_USERNAME', '50011648301')  # Usuario específico
    DEFAULT_PASSWORD = os.getenv('BOOTGESTOR_PASSWORD', 'Uh8Ai0Hg1Sr1')             
    
    # Interfaz
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    WINDOW_TITLE = "BootGestor - Automatización de Glosas"