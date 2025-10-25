# ui/glosas_en_pausa_widget.py
import asyncio
import logging
from typing import List, Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QGroupBox, QLineEdit, QLabel, QProgressBar,
                            QSplitter, QMessageBox, QTableWidget, QTableWidgetItem,
                            QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, QThread, QTimer, Signal as pyqtSignal
from ui.components.log_widget import LogWidget
from automation.web_scraper_glosas_en_pausa import WebScraperGlosasEnPausa
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import CuentaGlosasPrincipal, EstadoCuenta
from automation.web_scraper_glosas_en_pausa_actualizado import WebScraperGlosasEnPausaActualizado

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
    mensaje_usuario = pyqtSignal(str)
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Ejecuta la automatización de glosas EN PAUSA en el hilo de trabajo."""
        try:
            self.logger.info("Iniciando worker de automatización de glosas EN PAUSA con HERENCIA")
            
            # Ejecutar automatización de glosas en pausa
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # ✅ CAMBIO: Usar la versión actualizada con herencia
            scraper = WebScraperGlosasEnPausaActualizado(worker_thread=self)  # <-- CAMBIO AQUÍ
            success = loop.run_until_complete(
                scraper.start_glosas_en_pausa_automation(self.username, self.password)
            )
            
            loop.close()
            
            self.automation_finished.emit(success)
            
        except Exception as e:
            self.logger.error(f"Error en worker de automatización de glosas EN PAUSA con herencia: {e}")
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
    
    def emit_mensaje_usuario(self, mensaje: str):
        """Emite mensaje informativo al usuario."""
        self.mensaje_usuario.emit(mensaje)

class GlosasEnPausaStatsTable(QTableWidget):
    """
    Tabla para mostrar estadísticas de cuentas EN PAUSA.
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
                    
                    # ✅ CORRECCIÓN: Colorear intentos según cantidad SIN setStyleSheet()
                    intentos_item = QTableWidgetItem(str(row['intentos']))
                    if row['intentos'] >= 5:
                        # ✅ USAR setBackground() y setForeground() en lugar de setStyleSheet()
                        intentos_item.setBackground(Qt.GlobalColor.darkRed)
                        intentos_item.setForeground(Qt.GlobalColor.white)  # Color del texto
                        
                        # ✅ USAR setFont() para hacer el texto bold
                        from PySide6.QtGui import QFont
                        bold_font = QFont()
                        bold_font.setBold(True)
                        intentos_item.setFont(bold_font)
                        
                    elif row['intentos'] >= 3:
                        intentos_item.setBackground(Qt.GlobalColor.yellow)
                    
                    self.setItem(row_idx, 6, intentos_item)
                    self.setItem(row_idx, 7, QTableWidgetItem(row['motivo_fallo'] or ''))
                    
        except Exception as e:
            logging.getLogger(__name__).error(f"Error cargando datos de tabla EN PAUSA: {e}")
    
class GlosasEnPausaWidget(QWidget):
    """
    Widget para gestión de glosas EN PAUSA (FALLIDAS y EN_PROCESO).
    Completamente separado del widget principal.
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
        group = QGroupBox("Configuración de Acceso (Reprocesamiento)")
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
        group = QGroupBox("🔄 Reprocesamiento de Glosas EN PAUSA")
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
            'fallidas': QLabel("❌ Fallidas: 0"),
            'en_proceso': QLabel("🔄 En Proceso: 0"),
            'total_en_pausa': QLabel("⏳ Total EN PAUSA: 0"),
            'intentos_1_2': QLabel("🟡 Intentos 1-2: 0"),
            'intentos_3_4': QLabel("🟠 Intentos 3-4: 0"),
            'intentos_5_mas': QLabel("🔴 Intentos 5+: 0")
        }
        
        for key, label in self.stats_labels.items():
            label.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px;")
            # Colores específicos por tipo
            if key == 'fallidas':
                label.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px; color: #d32f2f;")
            elif key == 'en_proceso':
                label.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px; color: #f57c00;")
            elif key == 'intentos_5_mas':
                label.setStyleSheet("font-weight: bold; padding: 5px; margin: 2px; color: #8b0000;")
            
            layout.addWidget(label)
        
        return group
    
    def create_progress_group(self) -> QGroupBox:
        """Crea el grupo de indicadores de progreso."""
        group = QGroupBox("Estado del Reprocesamiento")
        layout = QVBoxLayout(group)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = QLabel("✅ Listo para reprocesar glosas EN PAUSA")
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
        
        # ✅ VERIFICAR: Configuraciones de respuesta automática
        if not self._verificar_configuraciones_respuesta():
            return  # Cancelar si no hay configuraciones
        
        self.logger.info("🔄 Iniciando reprocesamiento EN PAUSA")
        
        # Actualizar estado de la UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        self.status_label.setText("🔄 Ejecutando reprocesamiento EN PAUSA...")
        
        # Crear y iniciar worker
        self.automation_worker = GlosasEnPausaAutomationWorker(username, password)
        
        # Conectar signals
        self.automation_worker.automation_finished.connect(self.on_automation_finished)
        self.automation_worker.progress_updated.connect(self.on_progress_updated)
        self.automation_worker.data_imported.connect(self.on_data_imported)
        self.automation_worker.cuenta_processed.connect(self.on_cuenta_processed)
        self.automation_worker.tabla_refresh_needed.connect(self.on_tabla_refresh_needed)
        self.automation_worker.mensaje_usuario.connect(self.on_mensaje_usuario)
        
        self.automation_worker.start()
        
    def on_data_imported(self, cantidad: int):
        """Se ejecuta cuando se importan datos."""
        self.logger.info(f"📊 Signal recibido: Identificadas {cantidad} cuentas EN PAUSA para reprocesar")
        self.update_stats()
        self.stats_table.load_data()
        self.status_label.setText(f"✅ Identificadas {cantidad} cuentas EN PAUSA - Iniciando reprocesamiento...")
    
    def on_cuenta_processed(self, idcuenta: str, estado: str):
        """Se ejecuta cuando se procesa una cuenta EN PAUSA."""
        emoji_map = {
            "COMPLETADO": "✅",
            "FALLIDO": "❌", 
            "EN_PROCESO": "🔄"
        }
        emoji = emoji_map.get(estado, "❓")
        
        self.logger.info(f"📊 Signal recibido: {emoji} Cuenta {idcuenta} -> {estado}")
        
        self.update_stats()
        
        # Actualizar mensaje de estado con progreso
        total_recuperadas = self.get_total_recuperadas()
        total_en_pausa = self.get_total_en_pausa()
        
        self.status_label.setText(f"🔄 Reprocesando... (✅{total_recuperadas} recuperadas, ⏳{total_en_pausa} EN PAUSA)")
    
    def on_tabla_refresh_needed(self):
        """Se ejecuta cuando se necesita refrescar la tabla."""
        self.logger.info("📊 Signal recibido: Refrescando interfaz EN PAUSA completa")
        self.stats_table.load_data()
        self.update_stats()
    
    def on_mensaje_usuario(self, mensaje: str):
        """Muestra mensaje informativo al usuario."""
        from PySide6.QtWidgets import QMessageBox
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle("Información - Reprocesamiento EN PAUSA")
        msgBox.setText(mensaje)
        msgBox.setDetailedText("Para más detalles, revise los logs de la aplicación.")
        msgBox.exec()
        self.logger.info(f"💬 Mensaje mostrado al usuario: {mensaje}")
        
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
        
        total_recuperadas = self.get_total_recuperadas()
        total_en_pausa = self.get_total_en_pausa()
        
        if success:
            self.status_label.setText(f"✅ Reprocesamiento completado - {total_recuperadas} recuperadas")
            QMessageBox.information(
                self,
                "Reprocesamiento Exitoso",
                f"El reprocesamiento de glosas EN PAUSA se completó.\n\n"
                f"✅ Recuperadas: {total_recuperadas}\n"
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
                cursor = conn.execute("""
                    SELECT 
                        SUM(CASE WHEN estado = 'FALLIDO' THEN 1 ELSE 0 END) as fallidas,
                        SUM(CASE WHEN estado = 'EN_PROCESO' THEN 1 ELSE 0 END) as en_proceso,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') THEN 1 ELSE 0 END) as total_en_pausa,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND COALESCE(intentos, 0) BETWEEN 1 AND 2 THEN 1 ELSE 0 END) as intentos_1_2,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND COALESCE(intentos, 0) BETWEEN 3 AND 4 THEN 1 ELSE 0 END) as intentos_3_4,
                        SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND COALESCE(intentos, 0) >= 5 THEN 1 ELSE 0 END) as intentos_5_mas
                    FROM cuenta_glosas_principal
                """)
                
                row = cursor.fetchone()
                
                # Actualizar labels
                self.stats_labels['fallidas'].setText(f"❌ Fallidas: {row['fallidas'] or 0}")
                self.stats_labels['en_proceso'].setText(f"🔄 En Proceso: {row['en_proceso'] or 0}")
                self.stats_labels['total_en_pausa'].setText(f"⏳ Total EN PAUSA: {row['total_en_pausa'] or 0}")
                self.stats_labels['intentos_1_2'].setText(f"🟡 Intentos 1-2: {row['intentos_1_2'] or 0}")
                self.stats_labels['intentos_3_4'].setText(f"🟠 Intentos 3-4: {row['intentos_3_4'] or 0}")
                self.stats_labels['intentos_5_mas'].setText(f"🔴 Intentos 5+: {row['intentos_5_mas'] or 0}")
                
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas EN PAUSA: {e}")
    
    def get_total_recuperadas(self) -> int:
        """Obtiene total de cuentas recuperadas (COMPLETADAS) desde BD."""
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
    
    def _verificar_configuraciones_respuesta(self) -> bool:
        """
        Verifica si existen configuraciones de respuesta automática activas.
        
        Returns:
            bool: True si existen configuraciones, False si no hay configuraciones
        """
        try:
            db_manager = DatabaseManagerGlosas()
            
            # Obtener configuraciones activas
            count_activas = db_manager.get_configuraciones_respuesta_count()
            
            if count_activas > 0:
                self.logger.info(f"✅ Se encontraron {count_activas} configuraciones de respuesta activas")
                return True
            
            # No hay configuraciones activas - verificar si existen pero están inactivas
            configuraciones_detalle = db_manager.get_configuraciones_respuesta_detalle()
            total_configs = len(configuraciones_detalle)
            
            if total_configs > 0:
                # Hay configuraciones pero están inactivas
                self._mostrar_modal_configuraciones_inactivas(configuraciones_detalle)
            else:
                # No hay configuraciones en absoluto
                self._mostrar_modal_sin_configuraciones()
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando configuraciones: {e}")
            QMessageBox.critical(
                self,
                "Error de Sistema",
                f"Error verificando configuraciones de respuesta:\n{e}"
            )
            return False
    
    def _mostrar_modal_sin_configuraciones(self):
        """Muestra modal con opción para crear configuraciones de respuesta."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Configuraciones de Respuesta Requeridas")
        msg.setText("⚠️ No hay configuraciones de respuesta automática")
        
        mensaje_detallado = """
<b>RAZÓN:</b> Sin configuraciones no se pueden responder glosas automáticamente.

<b>¿QUÉ HACER?</b>
1. Haga clic en "Gestionar Configuraciones" para crear sus configuraciones personalizadas
2. O haga clic en "Crear Ejemplos" para comenzar con configuraciones básicas
3. Personalice las respuestas según las necesidades de su organización

<b>NOTA:</b> Cada cliente debe crear sus propias configuraciones personalizadas.
        """
        
        msg.setDetailedText(mensaje_detallado)
        
        # Botones personalizados
        gestionar_btn = msg.addButton("🔧 Gestionar Configuraciones", QMessageBox.ActionRole)
        cancelar_btn = msg.addButton("❌ Cancelar", QMessageBox.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == gestionar_btn:
            self._abrir_gestor_configuraciones()
    
    def _mostrar_modal_configuraciones_inactivas(self, configuraciones: List[Dict]):
        """Muestra modal cuando hay configuraciones pero están inactivas."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Configuraciones Inactivas")
        msg.setText("⚠️ Hay configuraciones pero están inactivas")
        
        activas = [c for c in configuraciones if c['activo']]
        inactivas = [c for c in configuraciones if not c['activo']]
        
        mensaje_detallado = f"""
<b>RESUMEN:</b>
• Total configuraciones: {len(configuraciones)}
• Activas: {len(activas)}
• Inactivas: {len(inactivas)}

<b>CONFIGURACIONES INACTIVAS:</b>
"""
        
        for config in inactivas:
            mensaje_detallado += f"• {config['tipo']} - {config['justificacion_patron']}\n"
        
        mensaje_detallado += """
<b>SOLUCIÓN:</b>
• Use el gestor de configuraciones para activar las que necesite
• O elimine las configuraciones que no necesite

<b>NOTA:</b> Solo las configuraciones activas se usarán para responder glosas.
        """
        
        msg.setDetailedText(mensaje_detallado)
        
        # Botones personalizados
        gestionar_btn = msg.addButton("🔧 Gestionar Configuraciones", QMessageBox.ActionRole)
        cancelar_btn = msg.addButton("❌ Cancelar", QMessageBox.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == gestionar_btn:
            self._abrir_gestor_configuraciones()
    
    def _abrir_gestor_configuraciones(self):
        """Abre el dialog para gestionar configuraciones de respuesta."""
        try:
            from ui.components.configuraciones_respuesta_dialog import ConfiguracionesRespuestaDialog
            
            dialog = ConfiguracionesRespuestaDialog(self)
            
            # Conectar señal para actualizar cuando se guarden configuraciones
            dialog.configuraciones_actualizadas.connect(self._on_configuraciones_actualizadas)
            
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Error abriendo gestor de configuraciones: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error abriendo gestor de configuraciones:\n{e}"
            )
    
    def _on_configuraciones_actualizadas(self):
        """Se ejecuta cuando se actualizan las configuraciones."""
        self.logger.info("✅ Configuraciones de respuesta actualizadas")
        
        # Opcional: Mostrar mensaje de éxito
        QMessageBox.information(
            self,
            "Configuraciones Actualizadas",
            "✅ Las configuraciones de respuesta han sido actualizadas.\n\n"
            "Ahora puede ejecutar el reprocesamiento de glosas EN PAUSA."
        )