import logging
import sys
from datetime import datetime
from config.settings import Settings

class CustomFormatter(logging.Formatter):
    """Formateador personalizado para logs con colores y compatible con Windows."""
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + Settings.LOG_FORMAT + reset,
        logging.INFO: grey + Settings.LOG_FORMAT + reset,
        logging.WARNING: yellow + Settings.LOG_FORMAT + reset,
        logging.ERROR: red + Settings.LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + Settings.LOG_FORMAT + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logger() -> logging.Logger:
    """
    Configura el sistema de logging de la aplicación con codificación UTF-8.
    
    Returns:
        logging.Logger: Logger principal configurado
    """
    # Crear logger principal
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, Settings.LOG_LEVEL))
    
    # Limpiar handlers existentes
    logger.handlers.clear()
    
    # Handler para consola con codificación UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())
    
    # Configurar codificación UTF-8 para Windows (soluciona errores Unicode)
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(encoding='utf-8')
        except:
            pass  # Si falla, continuar sin reconfigurar
    
    # Handler para archivo con codificación UTF-8
    file_handler = logging.FileHandler(
        f'bootgestor_{datetime.now().strftime("%Y%m%d")}.log',
        encoding='utf-8'  # Importante para caracteres especiales y emojis
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(Settings.LOG_FORMAT)
    )
    
    # Agregar handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger