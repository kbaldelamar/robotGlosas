import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QMenuBar, QStatusBar, QStackedWidget, QPushButton,
                            QSplitter, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from ui.glosas_widget import GlosasWidget  # *** MANTENER NOMBRE ORIGINAL ***
from ui.components.client_table import ClientTable
from database.db_manager import DatabaseManager

# *** NUEVO: Importar gestor de base de datos de glosas ***
from database.db_manager_glosas import DatabaseManagerGlosas
from ui.glosas_en_pausa_widget import GlosasEnPausaWidget
from database.models import Cliente
from config.settings import Settings

class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.
    Coordina todos los componentes y proporciona la interfaz principal.
    *** ACTUALIZADO: Ahora incluye soporte para base de datos de glosas ***
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()
        
        # *** NUEVO: Inicializar base de datos de glosas ***
        try:
            self.db_manager_glosas = DatabaseManagerGlosas()
            self.db_manager_glosas.create_glosas_tables()
            self.logger.info("Base de datos de glosas inicializada correctamente")
        except Exception as e:
            self.logger.error(f"Error inicializando base de datos de glosas: {e}")
            self.db_manager_glosas = None
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.load_initial_data()
        
        # Establecer vista inicial después de configurar todo
        self.switch_to_view(0)
        
    def setup_ui(self):
        """Configura la interfaz principal."""
        # Configurar ventana
        self.setWindowTitle(Settings.WINDOW_TITLE)
        self.setGeometry(100, 100, Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal (sin botones de navegación)
        main_layout = QVBoxLayout(central_widget)
        
        # Crear splitter principal
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Stack widget para diferentes vistas
        self.stacked_widget = QStackedWidget()
        
        # Crear y agregar widgets (MANTENER NOMBRES ORIGINALES)
        self.glosas_widget = GlosasWidget()  # *** NOMBRE ORIGINAL ***
        self.stacked_widget.addWidget(self.glosas_widget)
        
        self.glosas_en_pausa_widget = GlosasEnPausaWidget()
        self.stacked_widget.addWidget(self.glosas_en_pausa_widget)
        
        # Widget de placeholder para reportes (futuro)
        self.reports_widget = self.create_placeholder_widget("Módulo de Reportes")
        self.stacked_widget.addWidget(self.reports_widget)
        
        main_splitter.addWidget(self.stacked_widget)
        
        # Tabla de clientes en la parte inferior
        client_group = QGroupBox("Clientes Registrados")
        client_layout = QVBoxLayout(client_group)
        
        self.client_table = ClientTable()
        client_layout.addWidget(self.client_table)
        
        main_splitter.addWidget(client_group)
        
        # Configurar proporciones del splitter
        main_splitter.setSizes([500, 300])
        main_layout.addWidget(main_splitter)
        
        # Conectar señales
        self.connect_signals()
        
    def create_placeholder_widget(self, title: str) -> QWidget:
        """Crea un widget placeholder para módulos futuros."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Mensaje de placeholder
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt
        
        label = QLabel(f"🚧 {title}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #666666;
                padding: 50px;
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
            }
        """)
        
        layout.addWidget(label)
        
        # Botón para volver a gestión
        back_button = QPushButton("Volver a Gestión")
        back_button.clicked.connect(lambda: self.switch_to_view(0))
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                max-width: 200px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return widget
    
    def setup_menu(self):
        """Configura la barra de menú con nueva estructura."""
        menubar = self.menuBar()
        
        # ===================================
        # MENÚ MÓDULOS
        # ===================================
        modules_menu = menubar.addMenu('Módulos')
        
        # Submenu Gestión (lo que antes era "Gestión de Glosas")
        gestion_action = QAction('Gestión de Glosas', self)
        gestion_action.setShortcut(QKeySequence('Ctrl+G'))
        gestion_action.setStatusTip('Abrir módulo de gestión de glosas')
        gestion_action.triggered.connect(lambda: self.switch_to_view(0))
        modules_menu.addAction(gestion_action)


        en_pausa_action = QAction('🔄 Glosas en Pausa', self)
        en_pausa_action.setShortcut(QKeySequence('Ctrl+P'))
        en_pausa_action.setStatusTip('Reprocesar glosas fallidas y en proceso')
        en_pausa_action.triggered.connect(lambda: self.switch_to_view(1))
        modules_menu.addAction(en_pausa_action)
        
        # Separador
        modules_menu.addSeparator()
        
        # Submenu Reportes
        reports_action = QAction('Reportes', self)
        reports_action.setShortcut(QKeySequence('Ctrl+R'))
        reports_action.setStatusTip('Abrir módulo de reportes')
        reports_action.triggered.connect(lambda: self.switch_to_view(1))
        reports_action.setEnabled(True)  # Habilitado para mostrar placeholder
        modules_menu.addAction(reports_action)
        
        # Submenu Auditoría (ejemplo futuro)
        audit_action = QAction('Auditoría', self)
        audit_action.setShortcut(QKeySequence('Ctrl+A'))
        audit_action.setStatusTip('Módulo de auditoría de glosas')
        audit_action.setEnabled(False)  # Por implementar
        modules_menu.addAction(audit_action)
        
        # ===================================
        # MENÚ CONFIGURACIÓN
        # ===================================
        config_menu = menubar.addMenu('Configuración')
        
        # Submenu Base de Datos (movido desde antes)
        db_submenu = config_menu.addMenu('Base de Datos')
        
        # Refrescar clientes
        refresh_action = QAction('Refrescar Clientes', self)
        refresh_action.setShortcut(QKeySequence('F5'))
        refresh_action.setStatusTip('Actualizar lista de clientes')
        refresh_action.triggered.connect(self.refresh_clients)
        db_submenu.addAction(refresh_action)
        
        # *** NUEVO: Refrescar datos de glosas ***
        refresh_glosas_action = QAction('Refrescar Datos de Glosas', self)
        refresh_glosas_action.setShortcut(QKeySequence('Ctrl+F5'))
        refresh_glosas_action.setStatusTip('Actualizar datos de glosas')
        refresh_glosas_action.triggered.connect(self.refresh_glosas_data)
        db_submenu.addAction(refresh_glosas_action)
        
        # Agregar cliente (funcionalidad futura)
        add_client_action = QAction('Agregar Cliente', self)
        add_client_action.setShortcut(QKeySequence('Ctrl+N'))
        add_client_action.setStatusTip('Agregar nuevo cliente')
        add_client_action.setEnabled(False)  # Por implementar
        db_submenu.addAction(add_client_action)
        
        # Separador en base de datos
        db_submenu.addSeparator()
        
        # Exportar/Importar
        export_action = QAction('Exportar Clientes', self)
        export_action.setStatusTip('Exportar clientes a Excel')
        export_action.setEnabled(False)  # Por implementar
        db_submenu.addAction(export_action)
        
        import_action = QAction('Importar Clientes', self)
        import_action.setStatusTip('Importar clientes desde Excel')
        import_action.setEnabled(False)  # Por implementar
        db_submenu.addAction(import_action)
        
        # Separador principal en configuración
        config_menu.addSeparator()
        
        # Submenu Automatización
        automation_submenu = config_menu.addMenu('Automatización')
        
        # Configurar URLs
        urls_action = QAction('URLs del Sistema', self)
        urls_action.setStatusTip('Configurar URLs de login y glosas')
        urls_action.triggered.connect(self.show_url_config)
        automation_submenu.addAction(urls_action)
        
        # Configurar selectores CSS
        selectors_action = QAction('Selectores CSS', self)
        selectors_action.setStatusTip('Configurar selectores para automatización')
        selectors_action.setEnabled(False)  # Por implementar
        automation_submenu.addAction(selectors_action)
        
        # Configurar credenciales por defecto
        credentials_action = QAction('Credenciales por Defecto', self)
        credentials_action.setStatusTip('Configurar credenciales predeterminadas')
        credentials_action.triggered.connect(self.show_credentials_config)
        automation_submenu.addAction(credentials_action)
        
        # Separador en configuración
        config_menu.addSeparator()
        
        # Submenu Aplicación
        app_submenu = config_menu.addMenu('Aplicación')
        
        # Configuración general
        general_action = QAction('Configuración General', self)
        general_action.setStatusTip('Configuración general de la aplicación')
        general_action.setEnabled(False)  # Por implementar
        app_submenu.addAction(general_action)
        
        # Ver logs
        logs_action = QAction('Ver Archivos de Log', self)
        logs_action.setStatusTip('Abrir carpeta de archivos de log')
        logs_action.triggered.connect(self.open_logs_folder)
        app_submenu.addAction(logs_action)
        
        # ===================================
        # MENÚ ARCHIVO
        # ===================================
        file_menu = menubar.addMenu('Archivo')
        
        # Nuevo (placeholder)
        new_action = QAction('Nuevo', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setEnabled(False)  # Por implementar
        file_menu.addAction(new_action)
        
        # Separador
        file_menu.addSeparator()
        
        # Salir
        exit_action = QAction('Salir', self)
        exit_action.setShortcut(QKeySequence('Ctrl+Q'))
        exit_action.setStatusTip('Cerrar la aplicación')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ===================================
        # MENÚ AYUDA
        # ===================================
        help_menu = menubar.addMenu('Ayuda')
        
        # Manual de usuario
        manual_action = QAction('Manual de Usuario', self)
        manual_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        manual_action.setEnabled(False)  # Por implementar
        help_menu.addAction(manual_action)
        
        # Separador
        help_menu.addSeparator()
        
        # Acerca de
        about_action = QAction('Acerca de BootGestor', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Acerca de Qt
        about_qt_action = QAction('Acerca de Qt', self)
        about_qt_action.triggered.connect(lambda: QMessageBox.aboutQt(self, "Acerca de Qt"))
        help_menu.addAction(about_qt_action)
        
    def setup_status_bar(self):
        """Configura la barra de estado."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # *** INDICAR QUE ES LA VERSIÓN MEJORADA ***
        self.status_bar.showMessage("BootGestor v2.0 - Módulo: Gestión de Glosas (Mejorado)")
        
        # Timer para actualizar estado periódicamente
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Actualizar cada 5 segundos
        
    def connect_signals(self):
        """Conecta las señales de los componentes."""
        # Tabla de clientes
        self.client_table.client_selected.connect(self.on_client_selected)
        self.client_table.client_delete_requested.connect(self.delete_client)
        
    def switch_to_view(self, index: int):
        """
        Cambia a una vista específica.

        Args:
            index (int): Índice de la vista en el stack widget
        """
        self.stacked_widget.setCurrentIndex(index)

        view_names = {
            0: "Gestión de Glosas",
            1: "🔄 Glosas en Pausa",  # NUEVO
            2: "Reportes",
            3: "Configuración"
        }

        view_name = view_names.get(index, "Desconocido")

        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.showMessage(f"BootGestor v2.1 - Módulo: {view_name}")

        self.logger.info(f"Cambiado a módulo: {view_name}")
    def refresh_en_pausa_data(self):
        """Actualiza los datos de glosas EN PAUSA."""
        try:
            if hasattr(self.glosas_en_pausa_widget, 'refresh_data'):
                self.glosas_en_pausa_widget.refresh_data()
                QMessageBox.information(
                    self,
                    "Datos EN PAUSA Actualizados",
                    "Los datos de glosas EN PAUSA se han actualizado correctamente."
                )
            else:
                QMessageBox.information(
                    self,
                    "Función No Disponible",
                    "La función de actualización EN PAUSA aún no está disponible."
                )
            self.logger.info("🔄 Datos de glosas EN PAUSA actualizados")

        except Exception as e:
            self.logger.error(f"Error actualizando datos EN PAUSA: {e}")
            QMessageBox.critical(
                self,
                "Error de Base de Datos",
                f"No se pudieron actualizar los datos EN PAUSA: {str(e)}"
            )

    # En el método setup_menu(), AGREGAR en la sección de configuración:

    def show_url_config(self):
        """Muestra diálogo de configuración de URLs."""
        QMessageBox.information(
            self,
            "Configuración de URLs",
            f"""
            <h3>URLs Actuales del Sistema</h3>
            <p><b>URL de Login:</b><br>{Settings.LOGIN_URL}</p>
            <p><b>URL de Glosas:</b><br>{Settings.GLOSAS_URL}</p>
            <hr>
            <p><i>Para cambiar estas URLs, edita el archivo config/settings.py</i></p>
            """
        )
    
    def show_credentials_config(self):
        """Muestra información sobre configuración de credenciales."""
        username_status = "✅ Configurado" if Settings.DEFAULT_USERNAME else "❌ No configurado"
        password_status = "✅ Configurado" if Settings.DEFAULT_PASSWORD else "❌ No configurado"
        
        QMessageBox.information(
            self,
            "Configuración de Credenciales",
            f"""
            <h3>Estado de Credenciales por Defecto</h3>
            <p><b>Usuario:</b> {username_status}</p>
            <p><b>Contraseña:</b> {password_status}</p>
            <hr>
            <p><i>Para configurar credenciales por defecto:</i></p>
            <ul>
            <li>Edita config/settings.py, o</li>
            <li>Crea archivo .env con las variables, o</li>
            <li>Configura variables de entorno del sistema</li>
            </ul>
            """
        )
    
    def open_logs_folder(self):
        """Abre la carpeta de archivos de log."""
        import os
        import subprocess
        import platform
        
        try:
            log_folder = os.getcwd()
            
            if platform.system() == "Windows":
                os.startfile(log_folder)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", log_folder])
            else:  # Linux
                subprocess.run(["xdg-open", log_folder])
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo abrir la carpeta de logs: {str(e)}"
            )
    
    def load_initial_data(self):
        """Carga los datos iniciales de la aplicación."""
        self.refresh_clients()
        self.logger.info("Datos iniciales cargados")
        
    def refresh_clients(self):
        """Actualiza la lista de clientes desde la base de datos."""
        try:
            clients = self.db_manager.get_all_clients()
            self.client_table.load_clients(clients)
            
            # Actualizar mensaje de estado
            current_view = self.stacked_widget.currentIndex()
            view_names = {0: "Gestión de Glosas (v2.0)", 1: "Reportes"}
            view_name = view_names.get(current_view, "Módulo Actual")
            
            self.status_bar.showMessage(
                f"BootGestor v2.0 - {view_name} | Clientes: {len(clients)}"
            )
            
            self.logger.info(f"Lista de clientes actualizada: {len(clients)} registros")
            
        except Exception as e:
            self.logger.error(f"Error actualizando clientes: {e}")
            QMessageBox.critical(
                self,
                "Error de Base de Datos",
                f"No se pudieron cargar los clientes: {str(e)}"
            )
    
    def refresh_glosas_data(self):
        """*** NUEVO: Actualiza los datos de glosas ***"""
        try:
            if hasattr(self.glosas_widget, 'refresh_data'):
                self.glosas_widget.refresh_data()
                QMessageBox.information(
                    self,
                    "Datos Actualizados",
                    "Los datos de glosas se han actualizado correctamente."
                )
            else:
                QMessageBox.information(
                    self,
                    "Función No Disponible",
                    "La función de actualización de glosas aún no está disponible."
                )
            self.logger.info("Datos de glosas actualizados")
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de glosas: {e}")
            QMessageBox.critical(
                self,
                "Error de Base de Datos",
                f"No se pudieron actualizar los datos de glosas: {str(e)}"
            )
    
    def on_client_selected(self, client: Cliente):
        """
        Maneja la selección de un cliente.
        
        Args:
            client (Cliente): Cliente seleccionado
        """
        current_view = self.stacked_widget.currentIndex()
        view_names = {0: "Gestión de Glosas (v2.0)", 1: "Reportes"}
        view_name = view_names.get(current_view, "Módulo Actual")
        
        self.status_bar.showMessage(
            f"BootGestor v2.0 - {view_name} | Cliente: {client.nombre}"
        )
        
        self.logger.info(f"Cliente seleccionado: {client.nombre} (ID: {client.id})")
    
    def delete_client(self, client_id: int):
        """
        Elimina un cliente de la base de datos.
        
        Args:
            client_id (int): ID del cliente a eliminar
        """
        try:
            success = self.db_manager.delete_client(client_id)
            if success:
                self.refresh_clients()
                QMessageBox.information(
                    self,
                    "Cliente Eliminado",
                    "El cliente fue eliminado correctamente."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo eliminar el cliente."
                )
                
        except Exception as e:
            self.logger.error(f"Error eliminando cliente: {e}")
            QMessageBox.critical(
                self,
                "Error de Base de Datos",
                f"Error eliminando cliente: {str(e)}"
            )
    
    def update_status(self):
        """Actualiza la información de la barra de estado."""
        try:
            client_count = len(self.db_manager.get_all_clients())
            current_view = self.stacked_widget.currentIndex()
            view_names = {0: "Gestión de Glosas (v2.0)", 1: "Reportes"}
            view_name = view_names.get(current_view, "Módulo Actual")
            
            self.status_bar.showMessage(
                f"BootGestor v2.0 - {view_name} | Clientes: {client_count}"
            )
        except Exception as e:
            self.logger.error(f"Error actualizando estado: {e}")
    
    def show_about(self):
        """Muestra el diálogo Acerca de."""
        QMessageBox.about(
            self,
            "Acerca de BootGestor",
            """
            <h3>BootGestor v2.1 (Con Glosas en Pausa)</h3>
            <p>Sistema de automatización para gestión de glosas</p>
            
            <h4>Módulos Disponibles:</h4>
            <ul>
            <li>✅ Gestión de Glosas (Procesamiento principal)</li>
            <li>✅ 🔄 Glosas en Pausa (Reprocesamiento) - <b>NUEVO</b></li>
            <li>🚧 Reportes (En desarrollo)</li>
            </ul>
            
            <h4>Nuevas Funcionalidades v2.1:</h4>
            <ul>
            <li>✅ <b>Módulo Glosas en Pausa independiente</b></li>
            <li>✅ Navegación específica a sección "En Pausa"</li>
            <li>✅ Control de reintentos automático (máximo 5)</li>
            <li>✅ Filtrado específico de cuentas fallidas</li>
            <li>✅ Estadísticas de recuperación en tiempo real</li>
            <li>✅ Arquitectura completamente separada</li>
            </ul>
            
            <h4>Características Técnicas:</h4>
            <ul>
            <li>✅ Reutilización inteligente de componentes</li>
            <li>✅ Base de datos con control de intentos</li>
            <li>✅ Signals para actualización en tiempo real</li>
            <li>✅ Separación completa de lógicas</li>
            <li>✅ Navegación específica por módulo</li>
            </ul>
            
            <h4>Desarrollado con:</h4>
            <ul>
            <li>Python 3.x</li>
            <li>PySide6</li>
            <li>Playwright</li>
            <li>SQLite</li>
            </ul>
            
            <p>© 2025 - Todos los derechos reservados</p>
            """
        )
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de la aplicación."""
        reply = QMessageBox.question(
            self,
            "Confirmar Salida",
            "¿Está seguro de que desea salir de BootGestor?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info("Cerrando aplicación BootGestor v2.0")
            event.accept()
        else:
            event.ignore()