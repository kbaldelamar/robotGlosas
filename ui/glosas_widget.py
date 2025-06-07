import asyncio
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QGroupBox, QLineEdit, QLabel, QProgressBar,
                            QSplitter, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal
from ui.components.log_widget import LogWidget
from automation.web_scraper import WebScraper
from config.settings import Settings

class AutomationWorker(QThread):
    """
    Worker thread para ejecutar automatización sin bloquear la UI.
    Ejecuta el web scraping en un hilo separado.
    """
    
    # Señales para comunicación con la UI
    automation_finished = pyqtSignal(bool)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Ejecuta la automatización en el hilo de trabajo."""
        try:
            self.logger.info("Iniciando worker de automatización")
            
            # Ejecutar automatización
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            scraper = WebScraper()
            success = loop.run_until_complete(
                scraper.start_automation(self.username, self.password)
            )
            
            loop.close()
            
            self.automation_finished.emit(success)
            
        except Exception as e:
            self.logger.error(f"Error en worker de automatización: {e}")
            self.automation_finished.emit(False)

class GlosasWidget(QWidget):
    """
    Widget principal para la gestión de glosas.
    Contiene controles para automatización y visualización de logs.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.automation_worker = None
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Configura la interfaz del widget."""
        layout = QVBoxLayout(self)
        
        # Grupo de configuración
        config_group = self.create_config_group()
        layout.addWidget(config_group)
        
        # Grupo de control
        control_group = self.create_control_group()
        layout.addWidget(control_group)
        
        # Splitter para logs y progreso
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Widget de logs
        log_group = QGroupBox("Log de Automatización")
        log_layout = QVBoxLayout(log_group)
        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)
        splitter.addWidget(log_group)
        
        # Widget de progreso
        progress_group = self.create_progress_group()
        splitter.addWidget(progress_group)
        
        # Configurar proporciones del splitter
        splitter.setSizes([400, 100])
        layout.addWidget(splitter)
        
    def create_config_group(self) -> QGroupBox:
        """Crea el grupo de configuración de credenciales."""
        group = QGroupBox("Configuración de Acceso")
        layout = QVBoxLayout(group)
        
        # Layout para credenciales
        cred_layout = QHBoxLayout()
        
        # Usuario
        cred_layout.addWidget(QLabel("Usuario:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nombre de usuario")
        self.username_input.setText(Settings.DEFAULT_USERNAME)
        cred_layout.addWidget(self.username_input)
        
        # Contraseña
        cred_layout.addWidget(QLabel("Contraseña:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setText(Settings.DEFAULT_PASSWORD)
        cred_layout.addWidget(self.password_input)
        
        layout.addLayout(cred_layout)
        
        return group
    
    def create_control_group(self) -> QGroupBox:
        """Crea el grupo de controles de automatización."""
        group = QGroupBox("Control de Automatización")
        layout = QHBoxLayout(group)
        
        # Botón de inicio
        self.start_button = QPushButton("Iniciar Automatización")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.start_button)
        
        # Botón de parada
        self.stop_button = QPushButton("Detener")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.stop_button)
        
        # Botón de limpiar logs
        self.clear_button = QPushButton("Limpiar Log")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(self.clear_button)
        
        return group
    
    def create_progress_group(self) -> QGroupBox:
        """Crea el grupo de indicadores de progreso."""
        group = QGroupBox("Estado")
        layout = QVBoxLayout(group)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = QLabel("Listo para iniciar automatización")
        layout.addWidget(self.status_label)
        
        return group
    
    def connect_signals(self):
        """Conecta las señales de los widgets."""
        self.start_button.clicked.connect(self.start_automation)
        self.stop_button.clicked.connect(self.stop_automation)
        self.clear_button.clicked.connect(self.log_widget.clear_logs)
        
    def start_automation(self):
        """Inicia el proceso de automatización."""
        # Validar credenciales
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(
                self, 
                "Credenciales Requeridas",
                "Por favor ingrese usuario y contraseña."
            )
            return
        
        self.logger.info("Iniciando proceso de automatización desde UI")
        
        # Actualizar estado de la UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        self.status_label.setText("Ejecutando automatización...")
        
        # Crear y iniciar worker
        self.automation_worker = AutomationWorker(username, password)
        self.automation_worker.automation_finished.connect(self.on_automation_finished)
        self.automation_worker.progress_updated.connect(self.on_progress_updated)
        self.automation_worker.start()
        
    def stop_automation(self):
        """Detiene el proceso de automatización."""
        if self.automation_worker and self.automation_worker.isRunning():
            self.automation_worker.terminate()
            self.automation_worker.wait()
            self.logger.info("Automatización detenida por el usuario")
            
        self.reset_ui_state()
        
    def on_automation_finished(self, success: bool):
        """
        Maneja la finalización de la automatización.
        
        Args:
            success (bool): True si la automatización fue exitosa
        """
        self.reset_ui_state()
        
        if success:
            self.status_label.setText("Automatización completada exitosamente")
            QMessageBox.information(
                self,
                "Automatización Exitosa",
                "El proceso de automatización se completó correctamente."
            )
        else:
            self.status_label.setText("Error en automatización")
            QMessageBox.critical(
                self,
                "Error en Automatización",
                "El proceso de automatización falló. Revise los logs para más detalles."
            )
    
    def on_progress_updated(self, value: int):
        """
        Actualiza la barra de progreso.
        
        Args:
            value (int): Valor de progreso
        """
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        
    def reset_ui_state(self):
        """Resetea el estado de la interfaz después de la automatización."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.automation_worker = None