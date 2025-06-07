import asyncio
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QGroupBox, QLineEdit, QLabel, QProgressBar,
                            QSplitter, QMessageBox, QTableWidget, QTableWidgetItem,
                            QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal
from ui.components.log_widget import LogWidget

# *** CAMBIO: Importar el nuevo automatizador de glosas ***
from automation.web_scraper_glosas import WebScraperGlosas
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import CuentaGlosasPrincipal, EstadoCuenta
from config.settings import Settings

class AutomationWorker(QThread):
    """
    Worker thread para ejecutar automatización de glosas sin bloquear la UI.
    *** ACTUALIZADO: Ahora usa el nuevo sistema de glosas ***
    """
    
    # Señales para comunicación con la UI
    automation_finished = pyqtSignal(bool)
    progress_updated = pyqtSignal(int)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Ejecuta la automatización de glosas en el hilo de trabajo."""
        try:
            self.logger.info("Iniciando worker de automatización de glosas")
            
            # *** CAMBIO: Usar el nuevo automatizador de glosas ***
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            scraper = WebScraperGlosas()  # ✅ NUEVO
            success = loop.run_until_complete(
                scraper.start_glosas_automation(self.username, self.password)  # ✅ NUEVO
            )
            
            loop.close()
            
            self.automation_finished.emit(success)
            
        except Exception as e:
            self.logger.error(f"Error en worker de automatización de glosas: {e}")
            self.automation_finished.emit(False)

class GlosasStatsTable(QTableWidget):
    """
    *** NUEVA CLASE: Tabla para mostrar estadísticas de cuentas de glosas ***
    """
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManagerGlosas()
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Configura la interfaz de la tabla."""
        # Configurar columnas
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            'ID Cuenta', 'Proveedor', 'Estado', 'Glosas Encontradas', 
            'Glosas Procesadas', 'Último Intento', 'Motivo Fallo'
        ])
        
        # Configurar comportamiento
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Configurar redimensionamiento de columnas
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)      # ID Cuenta
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)    # Proveedor
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)      # Estado
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)      # Glosas Encontradas
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)      # Glosas Procesadas
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)      # Último Intento
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)    # Motivo Fallo
        
        # Establecer anchos específicos
        self.setColumnWidth(0, 80)   # ID Cuenta
        self.setColumnWidth(2, 100)  # Estado
        self.setColumnWidth(3, 120)  # Glosas Encontradas
        self.setColumnWidth(4, 120)  # Glosas Procesadas
        self.setColumnWidth(5, 130)  # Último Intento
        
    def load_data(self):
        """Carga los datos de cuentas desde la base de datos."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT idcuenta, proveedor, estado, glosas_encontradas, 
                           glosas_procesadas, fecha_inicio, motivo_fallo
                    FROM cuenta_glosas_principal 
                    ORDER BY fecha_inicio DESC
                """)
                
                rows = cursor.fetchall()
                self.setRowCount(len(rows))
                
                for row_idx, row in enumerate(rows):
                    self.setItem(row_idx, 0, QTableWidgetItem(str(row['idcuenta'])))
                    self.setItem(row_idx, 1, QTableWidgetItem(row['proveedor'] or ''))
                    
                    # Colorear estado según valor
                    estado_item = QTableWidgetItem(row['estado'])
                    if row['estado'] == 'COMPLETADO':
                        estado_item.setBackground(Qt.GlobalColor.green)
                    elif row['estado'] == 'FALLIDO':
                        estado_item.setBackground(Qt.GlobalColor.red)
                    elif row['estado'] == 'EN_PROCESO':
                        estado_item.setBackground(Qt.GlobalColor.yellow)
                    
                    self.setItem(row_idx, 2, estado_item)
                    self.setItem(row_idx, 3, QTableWidgetItem(str(row['glosas_encontradas'])))
                    self.setItem(row_idx, 4, QTableWidgetItem(str(row['glosas_procesadas'])))
                    self.setItem(row_idx, 5, QTableWidgetItem(row['fecha_inicio'] or ''))
                    self.setItem(row_idx, 6, QTableWidgetItem(row['motivo_fallo'] or ''))
                    
        except Exception as e:
            logging.getLogger(__name__).error(f"Error cargando datos de tabla: {e}")

class GlosasWidget(QWidget):
    """
    Widget principal para la gestión de glosas.
    *** ACTUALIZADO: Ahora incluye el nuevo sistema de base de datos y estadísticas ***
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.automation_worker = None
        
        # *** NUEVO: Inicializar base de datos de glosas ***
        self.db_manager = DatabaseManagerGlosas()
        self.db_manager.create_glosas_tables()
        
        self.setup_ui()
        self.connect_signals()
        
        # *** NUEVO: Actualizar estadísticas al iniciar ***
        self.update_stats()
        
    def setup_ui(self):
        """Configura la interfaz del widget."""
        layout = QVBoxLayout(self)
        
        # Grupo de configuración
        config_group = self.create_config_group()
        layout.addWidget(config_group)
        
        # Grupo de control
        control_group = self.create_control_group()
        layout.addWidget(control_group)
        
        # *** NUEVO: Grupo de estadísticas ***
        stats_group = self.create_stats_group()
        layout.addWidget(stats_group)
        
        # Splitter para logs y tabla de cuentas
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Widget de logs
        log_group = QGroupBox("Log de Automatización")
        log_layout = QVBoxLayout(log_group)
        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)
        splitter.addWidget(log_group)
        
        # *** NUEVO: Tabla de cuentas procesadas ***
        table_group = QGroupBox("Cuentas de Glosas")
        table_layout = QVBoxLayout(table_group)
        self.stats_table = GlosasStatsTable()
        table_layout.addWidget(self.stats_table)
        splitter.addWidget(table_group)
        
        # Widget de progreso
        progress_group = self.create_progress_group()
        splitter.addWidget(progress_group)
        
        # Configurar proporciones del splitter
        splitter.setSizes([300, 200, 100])
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
        group = QGroupBox("Control de Automatización de Glosas")  # *** TÍTULO ACTUALIZADO ***
        layout = QHBoxLayout(group)
        
        # Botón de inicio
        self.start_button = QPushButton("Iniciar Automatización de Glosas")  # *** TÍTULO ACTUALIZADO ***
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
        
        # *** NUEVO: Botón de actualizar estadísticas ***
        self.refresh_button = QPushButton("Actualizar Datos")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(self.refresh_button)
        
        return group
    
    def create_stats_group(self) -> QGroupBox:
        """*** NUEVO: Crea el grupo de estadísticas ***"""
        group = QGroupBox("Estadísticas de Procesamiento")
        layout = QHBoxLayout(group)
        
        # Etiquetas de estadísticas
        self.stats_labels = {
            'pendientes': QLabel("Pendientes: 0"),
            'en_proceso': QLabel("En Proceso: 0"),
            'completadas': QLabel("Completadas: 0"),
            'fallidas': QLabel("Fallidas: 0"),
            'glosas_procesadas': QLabel("Glosas Procesadas: 0")
        }
        
        for label in self.stats_labels.values():
            label.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px;")
            layout.addWidget(label)
        
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
        self.status_label = QLabel("Listo para iniciar automatización de glosas")  # *** TEXTO ACTUALIZADO ***
        layout.addWidget(self.status_label)
        
        return group
    
    def connect_signals(self):
        """Conecta las señales de los widgets."""
        self.start_button.clicked.connect(self.start_automation)
        self.stop_button.clicked.connect(self.stop_automation)
        self.clear_button.clicked.connect(self.log_widget.clear_logs)
        
        # *** NUEVO: Conectar botón de actualizar ***
        self.refresh_button.clicked.connect(self.refresh_data)
        
    def start_automation(self):
        """Inicia el proceso de automatización de glosas."""
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
        
        self.logger.info("Iniciando proceso de automatización de glosas desde UI")
        
        # Actualizar estado de la UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        self.status_label.setText("Ejecutando automatización de glosas...")
        
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
            self.logger.info("Automatización de glosas detenida por el usuario")
            
        self.reset_ui_state()
        
    def on_automation_finished(self, success: bool):
        """Maneja la finalización de la automatización."""
        self.reset_ui_state()
        
        if success:
            self.status_label.setText("Automatización de glosas completada exitosamente")
            QMessageBox.information(
                self,
                "Automatización Exitosa",
                "El proceso de automatización de glosas se completó correctamente."
            )
        else:
            self.status_label.setText("Error en automatización de glosas")
            QMessageBox.critical(
                self,
                "Error en Automatización",
                "El proceso de automatización de glosas falló. Revise los logs para más detalles."
            )
        
        # *** NUEVO: Actualizar datos después de la automatización ***
        self.refresh_data()
    
    def on_progress_updated(self, value: int):
        """Actualiza la barra de progreso."""
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        
    def reset_ui_state(self):
        """Resetea el estado de la interfaz después de la automatización."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.automation_worker = None
    
    def refresh_data(self):
        """*** NUEVO: Actualiza los datos de la interfaz ***"""
        self.update_stats()
        self.stats_table.load_data()
        self.logger.info("Datos de interfaz actualizados")
    
    def update_stats(self):
        """*** NUEVO: Actualiza las estadísticas mostradas ***"""
        try:
            with self.db_manager.get_connection() as conn:
                # Obtener estadísticas por estado
                cursor = conn.execute("""
                    SELECT estado, COUNT(*) as count 
                    FROM cuenta_glosas_principal 
                    GROUP BY estado
                """)
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row['estado'].lower()] = row['count']
                
                # Obtener total de glosas procesadas
                cursor = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM glosa_items_detalle 
                    WHERE fue_procesado = 1
                """)
                
                glosas_row = cursor.fetchone()
                glosas_procesadas = glosas_row['count'] if glosas_row else 0
                
                # Actualizar etiquetas
                self.stats_labels['pendientes'].setText(f"Pendientes: {stats.get('pendiente', 0)}")
                self.stats_labels['en_proceso'].setText(f"En Proceso: {stats.get('en_proceso', 0)}")
                self.stats_labels['completadas'].setText(f"Completadas: {stats.get('completado', 0)}")
                self.stats_labels['fallidas'].setText(f"Fallidas: {stats.get('fallido', 0)}")
                self.stats_labels['glosas_procesadas'].setText(f"Glosas Procesadas: {glosas_procesadas}")
                
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas: {e}")
            # Si hay error, mostrar valores por defecto
            for label in self.stats_labels.values():
                if ":" not in label.text():
                    continue
                prefix = label.text().split(":")[0]
                label.setText(f"{prefix}: 0")