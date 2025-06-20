# ui/glosas_en_pausa_widget.py
import asyncio
import logging
from typing import List, Dict  # ✅ AGREGAR ESTA LÍNEA
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QGroupBox, QLineEdit, QLabel, QProgressBar,
                            QSplitter, QMessageBox, QTableWidget, QTableWidgetItem,
                            QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, QThread, QTimer, Signal as pyqtSignal
from ui.components.log_widget import LogWidget
from automation.web_scraper_glosas_en_pausa import WebScraperGlosasEnPausa
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import CuentaGlosasPrincipal, EstadoCuenta
from config.settings import Settings

class GlosasEnPausaAutomationWorker(QThread):
    """
    Worker thread para ejecutar automatización de glosas EN PAUSA sin bloquear la UI.
    """
    
    # Señales para comunicación con la UI
    automation_finished = pyqtSignal(bool)
    progress_updated = pyqtSignal(int)
    stats_updated = pyqtSignal(dict)
    
    # Señales para tiempo real
    data_imported = pyqtSignal(int)
    cuenta_processed = pyqtSignal(str, str)
    tabla_refresh_needed = pyqtSignal()
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Ejecuta la automatización de glosas EN PAUSA en el hilo de trabajo."""
        try:
            self.logger.info("Iniciando worker de automatización de glosas EN PAUSA")
            
            # Ejecutar automatización de glosas en pausa
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            scraper = WebScraperGlosasEnPausa(worker_thread=self)
            success = loop.run_until_complete(
                scraper.start_glosas_en_pausa_automation(self.username, self.password)
            )
            
            loop.close()
            
            self.automation_finished.emit(success)
            
        except Exception as e:
            self.logger.error(f"Error en worker de automatización de glosas EN PAUSA: {e}")
            self.automation_finished.emit(False)
    
    # Métodos para emitir signals
    def emit_data_imported(self, cantidad: int):
        """Emite signal cuando se importan datos."""
        self.data_imported.emit(cantidad)
    
    def emit_cuenta_processed(self, idcuenta: str, estado: str):
        """Emite signal cuando se procesa una cuenta."""
        self.cuenta_processed.emit(idcuenta, estado)
    
    def emit_tabla_refresh(self):
        """Emite signal para refrescar tabla."""
        self.tabla_refresh_needed.emit()

class GlosasEnPausaStatsTable(QTableWidget):
    """
    Tabla para mostrar estadísticas de cuentas EN PAUSA (FALLIDAS y EN_PROCESO).
    """
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManagerGlosas()
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Configura la interfaz de la tabla."""
        # Configurar columnas
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels([
            'ID Cuenta', 'Proveedor', 'Estado', 'Glosas Encontradas', 
            'Glosas Procesadas', 'Último Intento', 'Intentos', 'Motivo Fallo'
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
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)      # Intentos
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)    # Motivo Fallo
        
        # Establecer anchos específicos
        self.setColumnWidth(0, 80)   # ID Cuenta
        self.setColumnWidth(2, 100)  # Estado
        self.setColumnWidth(3, 120)  # Glosas Encontradas
        self.setColumnWidth(4, 120)  # Glosas Procesadas
        self.setColumnWidth(5, 130)  # Último Intento
        self.setColumnWidth(6, 70)   # Intentos
        
    def load_data(self):
        """Carga SOLO las cuentas EN PAUSA (FALLIDAS y EN_PROCESO)."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT idcuenta, proveedor, estado, glosas_encontradas, 
                           glosas_procesadas, fecha_inicio, intentos, motivo_fallo
                    FROM cuenta_glosas_principal 
                    WHERE estado IN ('FALLIDO', 'EN_PROCESO')
                    ORDER BY intentos DESC, fecha_inicio DESC
                """)
                
                rows = cursor.fetchall()
                self.setRowCount(len(rows))
                
                for row_idx, row in enumerate(rows):
                    self.setItem(row_idx, 0, QTableWidgetItem(str(row['idcuenta'])))
                    self.setItem(row_idx, 1, QTableWidgetItem(row['proveedor'] or ''))
                    
                    # Colorear estado según valor
                    estado_item = QTableWidgetItem(row['estado'])
                    if row['estado'] == 'FALLIDO':
                        estado_item.setBackground(Qt.GlobalColor.red)
                    elif row['estado'] == 'EN_PROCESO':
                        estado_item.setBackground(Qt.GlobalColor.yellow)
                    
                    self.setItem(row_idx, 2, estado_item)
                    self.setItem(row_idx, 3, QTableWidgetItem(str(row['glosas_encontradas'])))
                    self.setItem(row_idx, 4, QTableWidgetItem(str(row['glosas_procesadas'])))
                    self.setItem(row_idx, 5, QTableWidgetItem(row['fecha_inicio'] or ''))
                    self.setItem(row_idx, 6, QTableWidgetItem(str(row['intentos'])))
                    self.setItem(row_idx, 7, QTableWidgetItem(row['motivo_fallo'] or ''))
                    
        except Exception as e:
            logging.getLogger(__name__).error(f"Error cargando datos de tabla EN PAUSA: {e}")

class GlosasEnPausaWidget(QWidget):
    """
    Widget para gestión de glosas EN PAUSA (FALLIDAS y EN_PROCESO).
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.automation_worker = None
        self.db_manager = DatabaseManagerGlosas()
        
        self.setup_ui()
        self.connect_signals()
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
        
        # Grupo de estadísticas
        stats_group = self.create_stats_group()
        layout.addWidget(stats_group)
        
        # Splitter para logs y tabla de cuentas
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Widget de logs
        log_group = QGroupBox("Log de Reprocesamiento EN PAUSA")
        log_layout = QVBoxLayout(log_group)
        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)
        splitter.addWidget(log_group)
        
        # Tabla de cuentas EN PAUSA
        table_group = QGroupBox("Cuentas EN PAUSA (Fallidas y En Proceso)")
        table_layout = QVBoxLayout(table_group)
        self.stats_table = GlosasEnPausaStatsTable()
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
        group = QGroupBox("Reprocesamiento de Glosas EN PAUSA")
        layout = QHBoxLayout(group)
        
        # Botón de inicio
        self.start_button = QPushButton("🔄 Reprocesar Glosas EN PAUSA")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E55A2B;
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
        
        # Botón de actualizar estadísticas
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
        """Crea el grupo de estadísticas EN PAUSA."""
        group = QGroupBox("Estadísticas de Cuentas EN PAUSA")
        layout = QHBoxLayout(group)
        
        # Etiquetas de estadísticas específicas para EN PAUSA
        self.stats_labels = {
            'fallidas': QLabel("Fallidas: 0"),
            'en_proceso': QLabel("En Proceso: 0"),
            'total_en_pausa': QLabel("Total EN PAUSA: 0"),
            'con_reintentos': QLabel("Con Reintentos: 0"),
            'listas_reprocesar': QLabel("Listas para Reprocesar: 0")
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
        self.status_label = QLabel("Listo para reprocesar glosas EN PAUSA")
        layout.addWidget(self.status_label)
        
        return group
    
    def connect_signals(self):
        """Conecta las señales de los widgets."""
        self.start_button.clicked.connect(self.start_automation)
        self.stop_button.clicked.connect(self.stop_automation)
        self.clear_button.clicked.connect(self.log_widget.clear_logs)
        self.refresh_button.clicked.connect(self.refresh_data)
        
    def start_automation(self):
        """Inicia el proceso de reprocesamiento de glosas EN PAUSA."""
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
        
        self.logger.info("🔄 Iniciando reprocesamiento de glosas EN PAUSA")
        
        # Actualizar estado de la UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        self.status_label.setText("🔄 Ejecutando reprocesamiento EN PAUSA...")
        
        # Crear y iniciar worker CON SIGNALS
        self.automation_worker = GlosasEnPausaAutomationWorker(username, password)
        
        # Conectar signals
        self.automation_worker.automation_finished.connect(self.on_automation_finished)
        self.automation_worker.progress_updated.connect(self.on_progress_updated)
        self.automation_worker.data_imported.connect(self.on_data_imported)
        self.automation_worker.cuenta_processed.connect(self.on_cuenta_processed)
        self.automation_worker.tabla_refresh_needed.connect(self.on_tabla_refresh_needed)
        
        self.automation_worker.start()
        
    def on_data_imported(self, cantidad: int):
        """Se ejecuta cuando se importan datos - ACTUALIZACIÓN INMEDIATA."""
        self.logger.info(f"📊 Signal recibido: Importadas {cantidad} cuentas EN PAUSA")
        self.update_stats()
        self.stats_table.load_data()
        self.status_label.setText(f"✅ Identificadas {cantidad} cuentas EN PAUSA - Iniciando reprocesamiento...")
    
    def on_cuenta_processed(self, idcuenta: str, estado: str):
        """Se ejecuta cuando se procesa una cuenta EN PAUSA."""
        emoji = "✅" if estado == "COMPLETADO" else "❌"
        self.logger.info(f"📊 Signal recibido: {emoji} Cuenta {idcuenta} -> {estado}")
        
        self.update_stats()
        
        # Actualizar mensaje de estado con progreso
        total_procesadas = self.get_total_procesadas()
        total_en_pausa = self.get_total_en_pausa()
        
        self.status_label.setText(f"🔄 Reprocesando... (✅{total_procesadas} completadas, ⏳{total_en_pausa} EN PAUSA)")
    
    def on_tabla_refresh_needed(self):
        """Se ejecuta cuando necesita refrescar toda la interfaz."""
        self.logger.info("📊 Signal recibido: Refrescando interfaz EN PAUSA")
        self.stats_table.load_data()
        self.update_stats()
        
    def stop_automation(self):
        """Detiene el proceso de automatización."""
        if self.automation_worker and self.automation_worker.isRunning():
            self.automation_worker.terminate()
            self.automation_worker.wait()
            self.logger.info("🔄 Reprocesamiento EN PAUSA detenido por el usuario")
            
        self.reset_ui_state()
        
    def on_automation_finished(self, success: bool):
        """Maneja la finalización del reprocesamiento."""
        self.reset_ui_state()
        
        total_completadas = self.get_total_procesadas()
        total_en_pausa = self.get_total_en_pausa()
        
        if success:
            self.status_label.setText(f"✅ Reprocesamiento completado - {total_completadas} cuentas procesadas")
            QMessageBox.information(
                self,
                "Reprocesamiento Exitoso",
                f"El reprocesamiento de glosas EN PAUSA se completó.\n\n"
                f"✅ Completadas: {total_completadas}\n"
                f"⏳ Aún EN PAUSA: {total_en_pausa}"
            )
        else:
            self.status_label.setText("❌ Error en reprocesamiento EN PAUSA")
            QMessageBox.critical(
                self,
                "Error en Reprocesamiento",
                "El proceso de reprocesamiento falló. Revise los logs para más detalles."
            )
        
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
        """Actualiza los datos de la interfaz."""
        self.update_stats()
        self.stats_table.load_data()
        self.logger.info("🔄 Datos de interfaz EN PAUSA actualizados")
    
    def update_stats(self):
        """Actualiza las estadísticas mostradas para cuentas EN PAUSA."""
        try:
            with self.db_manager.get_connection() as conn:
                # Estadísticas específicas para EN PAUSA
                cursor = conn.execute("""
                    SELECT 
                        SUM(CASE WHEN estado = 'FALLIDO' THEN 1 ELSE 0 END) as fallidas,
                        SUM(CASE WHEN estado = 'EN_PROCESO' THEN 1 ELSE 0 END) as en_proceso,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') THEN 1 ELSE 0 END) as total_en_pausa,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos > 0 THEN 1 ELSE 0 END) as con_reintentos,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos < 3 THEN 1 ELSE 0 END) as listas_reprocesar
                    FROM cuenta_glosas_principal
                """)
                
                row = cursor.fetchone()
                
                # Actualizar labels
                self.stats_labels['fallidas'].setText(f"Fallidas: {row['fallidas'] or 0}")
                self.stats_labels['en_proceso'].setText(f"En Proceso: {row['en_proceso'] or 0}")
                self.stats_labels['total_en_pausa'].setText(f"Total EN PAUSA: {row['total_en_pausa'] or 0}")
                self.stats_labels['con_reintentos'].setText(f"Con Reintentos: {row['con_reintentos'] or 0}")
                self.stats_labels['listas_reprocesar'].setText(f"Listas para Reprocesar: {row['listas_reprocesar'] or 0}")
                
                # Efecto visual de actualización
                for label in self.stats_labels.values():
                    label.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px; background-color: #ffe8e8;")
                    QTimer.singleShot(1000, lambda l=label: l.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px;"))
                
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas EN PAUSA: {e}")
    
    def get_total_procesadas(self) -> int:
        """Obtiene total de cuentas procesadas desde BD."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM cuenta_glosas_principal 
                    WHERE estado = 'COMPLETADO'
                """)
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception:
            return 0
    
    def get_total_en_pausa(self) -> int:
        """Obtiene total de cuentas EN PAUSA desde BD."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM cuenta_glosas_principal 
                    WHERE estado IN ('FALLIDO', 'EN_PROCESO')
                """)
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception:
            return 0