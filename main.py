import sys
import asyncio
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ui.main_window import MainWindow
from database.db_manager import DatabaseManager
from utils.logger import setup_logger

def main():
    """
    Función principal de la aplicación.
    Inicializa la base de datos, configura logging y lanza la interfaz.
    """
    # Configurar logging
    logger = setup_logger()
    logger.info("Iniciando BootGestor...")
    
    # Inicializar base de datos
    db_manager = DatabaseManager()
    db_manager.create_tables()
    logger.info("Base de datos inicializada correctamente")
    
    # Crear aplicación Qt
    app = QApplication(sys.argv)
    
    # Crear y mostrar ventana principal
    window = MainWindow()
    window.resize(1200, 990)  # <-- Añade esta línea para aumentar el tamaño
    window.show()
    
    logger.info("Aplicación iniciada correctamente")
    
    # Ejecutar aplicación
    sys.exit(app.exec())

if __name__ == "__main__":
    main()