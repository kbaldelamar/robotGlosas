# ui/components/configuraciones_respuesta_dialog.py
"""
Dialog para gestionar configuraciones de respuesta automática de glosas.
Permite crear, editar, activar/desactivar y eliminar configuraciones.
"""

import logging
from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QGroupBox, QLineEdit, QLabel,
    QComboBox, QTextEdit, QCheckBox, QMessageBox, QSplitter,
    QFileDialog, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal as pyqtSignal
from database.db_manager_glosas import DatabaseManagerGlosas


class ConfiguracionesRespuestaDialog(QDialog):
    """
    Dialog para gestionar configuraciones de respuesta automática.
    """
    
    # Señal emitida cuando se guardan configuraciones
    configuraciones_actualizadas = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManagerGlosas()
        
        self.setWindowTitle("Gestión de Configuraciones de Respuesta Automática")
        self.resize(1000, 700)
        self.setModal(True)
        
        self.init_ui()
        self.load_configuraciones()
        
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        layout = QVBoxLayout(self)
        
        # Título y descripción
        title_label = QLabel("🔧 Configuraciones de Respuesta Automática")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin: 10px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "Configure respuestas automáticas para diferentes tipos de glosas. "
            "Cada configuración define cómo responder automáticamente cuando se encuentra "
            "una justificación específica en las glosas."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #34495e; margin: 5px 10px 15px 10px;")
        layout.addWidget(desc_label)
        
        # Splitter principal horizontal
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Panel izquierdo: Configuraciones existentes
        self.create_table_panel(main_splitter)
        
        # Splitter vertical para el lado derecho
        right_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(right_splitter)
        
        # Panel superior derecho: Formulario de edición
        self.create_form_panel(right_splitter)
        
        # Panel inferior derecho: Justificaciones sin configuración
        self.create_sin_configuracion_panel(right_splitter)
        
        # Ajustar tamaños del splitter principal
        main_splitter.setSizes([600, 400])
        
        # Ajustar tamaños del splitter vertical derecho
        right_splitter.setSizes([300, 200])
        
        # Botones de acción
        self.create_action_buttons(layout)
        
    def create_table_panel(self, parent):
        """Crea el panel con la tabla de configuraciones."""
        table_widget = QGroupBox("📋 Configuraciones Existentes")
        table_layout = QVBoxLayout(table_widget)
        
        # Botones superiores de la tabla
        table_buttons = QHBoxLayout()
        
        self.refresh_button = QPushButton("🔄 Actualizar")
        self.refresh_button.clicked.connect(self.load_configuraciones)
        table_buttons.addWidget(self.refresh_button)
        
        self.delete_button = QPushButton("🗑️ Eliminar")
        self.delete_button.clicked.connect(self.delete_configuracion)
        self.delete_button.setEnabled(False)
        table_buttons.addWidget(self.delete_button)
        
        table_buttons.addStretch()
        table_layout.addLayout(table_buttons)
        
        # Tabla de configuraciones
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        
        # Configurar columnas
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Tipo", "Justificación", "Respuesta", "PDF", "Activo"
        ])
        
        # Ajustar tamaños de columnas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Justificación
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Respuesta
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # PDF
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Activo
        
        # Conectar señales
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(self.edit_configuracion)
        
        table_layout.addWidget(self.table)
        parent.addWidget(table_widget)
        
    def create_form_panel(self, parent):
        """Crea el panel del formulario de edición."""
        form_widget = QGroupBox("✏️ Crear/Editar Configuración")
        form_layout = QVBoxLayout(form_widget)
        
        # Campo Tipo
        tipo_layout = QHBoxLayout()
        tipo_layout.addWidget(QLabel("Tipo:"))
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["TARIFAS", "GENERALES", "AUTORIZACIONES", "DOCUMENTACION", "OTRO"])
        self.tipo_combo.setEditable(True)
        tipo_layout.addWidget(self.tipo_combo)
        form_layout.addLayout(tipo_layout)
        
        # Campo Justificación Patrón
        form_layout.addWidget(QLabel("Justificación (Patrón):"))
        self.justificacion_input = QLineEdit()
        self.justificacion_input.setPlaceholderText("Ej: VALOR NO CUBIERTO, CODIGO INEXISTENTE, etc.")
        form_layout.addWidget(self.justificacion_input)
        
        # Campo Respuesta Automática
        form_layout.addWidget(QLabel("Respuesta Automática:"))
        self.respuesta_text = QTextEdit()
        self.respuesta_text.setMaximumHeight(100)
        self.respuesta_text.setPlaceholderText("Escriba la respuesta automática que se enviará...")
        form_layout.addWidget(self.respuesta_text)
        
        # Campo URL PDF
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(QLabel("URL PDF (Opcional):"))
        self.pdf_input = QLineEdit()
        self.pdf_input.setPlaceholderText("https://ejemplo.com/archivo.pdf")
        pdf_layout.addWidget(self.pdf_input)
        
        self.browse_pdf_button = QPushButton("📁 Examinar")
        self.browse_pdf_button.clicked.connect(self.browse_pdf_file)
        pdf_layout.addWidget(self.browse_pdf_button)
        form_layout.addLayout(pdf_layout)
        
        # Campo Activo
        self.activo_checkbox = QCheckBox("Configuración activa")
        self.activo_checkbox.setChecked(True)
        form_layout.addWidget(self.activo_checkbox)
        
        # Botones del formulario
        form_buttons = QHBoxLayout()
        
        self.save_button = QPushButton("💾 Guardar")
        self.save_button.clicked.connect(self.save_configuracion)
        form_buttons.addWidget(self.save_button)
        
        self.clear_button = QPushButton("🗑️ Limpiar")
        self.clear_button.clicked.connect(self.clear_form)
        form_buttons.addWidget(self.clear_button)
        
        form_buttons.addStretch()
        form_layout.addLayout(form_buttons)
        
        form_layout.addStretch()
        parent.addWidget(form_widget)
        
    def create_action_buttons(self, layout):
        """Crea los botones de acción del dialog."""
        buttons_layout = QHBoxLayout()
        
        # Botón para crear configuraciones de ejemplo
        self.ejemplo_button = QPushButton("📋 Crear Ejemplos")
        self.ejemplo_button.clicked.connect(self.crear_configuraciones_ejemplo)
        buttons_layout.addWidget(self.ejemplo_button)
        
        buttons_layout.addStretch()
        
        # Botones de cerrar
        self.close_button = QPushButton("✅ Cerrar")
        self.close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)
        
    def load_configuraciones(self):
        """Carga las configuraciones desde la base de datos."""
        try:
            configuraciones = self.db_manager.get_configuraciones_respuesta_detalle()
            
            self.table.setRowCount(len(configuraciones))
            
            for row, config in enumerate(configuraciones):
                # Tipo
                self.table.setItem(row, 0, QTableWidgetItem(config['tipo']))
                
                # Justificación (truncada si es muy larga)
                justificacion = config['justificacion_patron']
                if len(justificacion) > 30:
                    justificacion = justificacion[:27] + "..."
                self.table.setItem(row, 1, QTableWidgetItem(justificacion))
                
                # Respuesta (truncada si es muy larga)
                respuesta = config['respuesta_automatica']
                if len(respuesta) > 40:
                    respuesta = respuesta[:37] + "..."
                self.table.setItem(row, 2, QTableWidgetItem(respuesta))
                
                # PDF
                pdf_text = "Sí" if config['url_pdf'] else "No"
                self.table.setItem(row, 3, QTableWidgetItem(pdf_text))
                
                # Activo
                activo_text = "✅" if config['activo'] else "❌"
                self.table.setItem(row, 4, QTableWidgetItem(activo_text))
                
                # Guardar datos completos en el item para referencia
                self.table.item(row, 0).setData(Qt.UserRole, config)
                
            self.logger.info(f"Cargadas {len(configuraciones)} configuraciones")
            
        except Exception as e:
            self.logger.error(f"Error cargando configuraciones: {e}")
            QMessageBox.critical(self, "Error", f"Error cargando configuraciones:\n{e}")
            
    def on_selection_changed(self):
        """Maneja el cambio de selección en la tabla."""
        selected_items = self.table.selectedItems()
        self.delete_button.setEnabled(len(selected_items) > 0)
        
    def edit_configuracion(self):
        """Edita la configuración seleccionada."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
            
        # Obtener datos de la configuración
        config_item = self.table.item(current_row, 0)
        if not config_item:
            return
            
        config = config_item.data(Qt.UserRole)
        if not config:
            return
            
        # Cargar datos en el formulario
        self.tipo_combo.setCurrentText(config['tipo'])
        self.justificacion_input.setText(config['justificacion_patron'])
        self.respuesta_text.setPlainText(config['respuesta_automatica'])
        self.pdf_input.setText(config['url_pdf'] or "")
        self.activo_checkbox.setChecked(config['activo'])
        
    def save_configuracion(self):
        """Guarda la configuración actual."""
        # Validar campos
        tipo = self.tipo_combo.currentText().strip()
        justificacion = self.justificacion_input.text().strip()
        respuesta = self.respuesta_text.toPlainText().strip()
        
        if not tipo or not justificacion or not respuesta:
            QMessageBox.warning(
                self, 
                "Campos Requeridos",
                "Tipo, Justificación y Respuesta son campos obligatorios."
            )
            return
            
        try:
            with self.db_manager.get_connection() as conn:
                # Verificar si ya existe
                cursor = conn.execute("""
                    SELECT id FROM glosas_respuestas_config 
                    WHERE tipo = ? AND justificacion_patron = ?
                """, (tipo, justificacion))
                
                existing = cursor.fetchone()
                
                pdf_url = self.pdf_input.text().strip() or None
                activo = 1 if self.activo_checkbox.isChecked() else 0
                
                if existing:
                    # Actualizar existente
                    conn.execute("""
                        UPDATE glosas_respuestas_config 
                        SET respuesta_automatica = ?, url_pdf = ?, activo = ?,
                            fecha_actualizacion = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (respuesta, pdf_url, activo, existing['id']))
                    
                    self.logger.info(f"Configuración actualizada: {tipo} - {justificacion}")
                    QMessageBox.information(self, "Éxito", "Configuración actualizada correctamente.")
                    
                else:
                    # Crear nueva
                    conn.execute("""
                        INSERT INTO glosas_respuestas_config 
                        (tipo, justificacion_patron, respuesta_automatica, url_pdf, activo)
                        VALUES (?, ?, ?, ?, ?)
                    """, (tipo, justificacion, respuesta, pdf_url, activo))
                    
                    self.logger.info(f"Nueva configuración creada: {tipo} - {justificacion}")
                    QMessageBox.information(self, "Éxito", "Nueva configuración creada correctamente.")
                
                conn.commit()
                
                # Recargar tabla y limpiar formulario
                self.load_configuraciones()
                self.clear_form()
                
                # Emitir señal de actualización
                self.configuraciones_actualizadas.emit()
                
        except Exception as e:
            self.logger.error(f"Error guardando configuración: {e}")
            QMessageBox.critical(self, "Error", f"Error guardando configuración:\n{e}")
            
    def delete_configuracion(self):
        """Elimina la configuración seleccionada."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
            
        config_item = self.table.item(current_row, 0)
        if not config_item:
            return
            
        config = config_item.data(Qt.UserRole)
        if not config:
            return
            
        # Confirmar eliminación
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar la configuración?\n\n"
            f"Tipo: {config['tipo']}\n"
            f"Justificación: {config['justificacion_patron']}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    DELETE FROM glosas_respuestas_config 
                    WHERE tipo = ? AND justificacion_patron = ?
                """, (config['tipo'], config['justificacion_patron']))
                conn.commit()
                
            self.logger.info(f"Configuración eliminada: {config['tipo']} - {config['justificacion_patron']}")
            QMessageBox.information(self, "Éxito", "Configuración eliminada correctamente.")
            
            # Recargar tabla
            self.load_configuraciones()
            
            # Emitir señal de actualización
            self.configuraciones_actualizadas.emit()
            
        except Exception as e:
            self.logger.error(f"Error eliminando configuración: {e}")
            QMessageBox.critical(self, "Error", f"Error eliminando configuración:\n{e}")
            
    def clear_form(self):
        """Limpia el formulario."""
        self.tipo_combo.setCurrentIndex(0)
        self.justificacion_input.clear()
        self.respuesta_text.clear()
        self.pdf_input.clear()
        self.activo_checkbox.setChecked(True)
        
    def browse_pdf_file(self):
        """Examina archivos PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo PDF",
            "",
            "Archivos PDF (*.pdf);;Todos los archivos (*)"
        )
        
        if file_path:
            self.pdf_input.setText(file_path)
            
    def crear_configuraciones_ejemplo(self):
        """Crea configuraciones de ejemplo."""
        reply = QMessageBox.question(
            self,
            "Crear Configuraciones de Ejemplo",
            "¿Desea crear configuraciones de ejemplo?\n\n"
            "Se crearán 5 configuraciones básicas para comenzar.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
            
        configuraciones_ejemplo = [
            {
                'tipo': 'TARIFAS',
                'justificacion_patron': 'VALOR NO CUBIERTO',
                'respuesta_automatica': 'Respuesta automática para valor no cubierto en tarifas',
                'url_pdf': None,
                'activo': 1
            },
            {
                'tipo': 'TARIFAS',
                'justificacion_patron': 'CODIGO INEXISTENTE',
                'respuesta_automatica': 'Respuesta automática para código inexistente',
                'url_pdf': None,
                'activo': 1
            },
            {
                'tipo': 'TARIFAS',
                'justificacion_patron': 'VALOR SUPERIOR',
                'respuesta_automatica': 'Respuesta automática para valor superior al autorizado',
                'url_pdf': None,
                'activo': 1
            },
            {
                'tipo': 'GENERALES',
                'justificacion_patron': 'DOCUMENTACION FALTANTE',
                'respuesta_automatica': 'Respuesta automática para documentación faltante',
                'url_pdf': None,
                'activo': 1
            },
            {
                'tipo': 'GENERALES',
                'justificacion_patron': 'AUTORIZACION REQUERIDA',
                'respuesta_automatica': 'Respuesta automática para autorización requerida',
                'url_pdf': None,
                'activo': 1
            }
        ]
        
        try:
            created_count = 0
            with self.db_manager.get_connection() as conn:
                for config in configuraciones_ejemplo:
                    # Verificar si ya existe
                    cursor = conn.execute("""
                        SELECT id FROM glosas_respuestas_config 
                        WHERE tipo = ? AND justificacion_patron = ?
                    """, (config['tipo'], config['justificacion_patron']))
                    
                    if not cursor.fetchone():
                        # Crear si no existe
                        conn.execute("""
                            INSERT INTO glosas_respuestas_config 
                            (tipo, justificacion_patron, respuesta_automatica, url_pdf, activo)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            config['tipo'],
                            config['justificacion_patron'],
                            config['respuesta_automatica'],
                            config['url_pdf'],
                            config['activo']
                        ))
                        created_count += 1
                
                conn.commit()
            
            self.logger.info(f"Creadas {created_count} configuraciones de ejemplo")
            QMessageBox.information(
                self, 
                "Éxito", 
                f"Se crearon {created_count} configuraciones de ejemplo.\n"
                f"Puede editarlas según sus necesidades."
            )
            
            # Recargar tabla
            self.load_configuraciones()
            
            # Emitir señal de actualización
            self.configuraciones_actualizadas.emit()
            
        except Exception as e:
            self.logger.error(f"Error creando configuraciones de ejemplo: {e}")
            QMessageBox.critical(self, "Error", f"Error creando configuraciones de ejemplo:\n{e}")
            
    def create_sin_configuracion_panel(self, parent):
        """Crea el panel que muestra las justificaciones sin configuración."""
        sin_config_widget = QGroupBox("⚠️ Justificaciones sin Configuración")
        sin_config_layout = QVBoxLayout(sin_config_widget)
        
        # Descripción y estadísticas
        self.stats_label = QLabel("Cargando estadísticas...")
        self.stats_label.setStyleSheet("color: #7f8c8d; font-size: 11px; margin: 5px;")
        sin_config_layout.addWidget(self.stats_label)
        
        # Botones de control
        control_layout = QHBoxLayout()
        
        self.refresh_sin_config_button = QPushButton("🔄 Actualizar")
        self.refresh_sin_config_button.clicked.connect(self.load_justificaciones_sin_configuracion)
        control_layout.addWidget(self.refresh_sin_config_button)
        
        self.auto_crear_button = QPushButton("⚡ Crear Configuración")
        self.auto_crear_button.clicked.connect(self.auto_crear_configuracion_desde_justificacion)
        self.auto_crear_button.setEnabled(False)
        control_layout.addWidget(self.auto_crear_button)
        
        control_layout.addStretch()
        sin_config_layout.addLayout(control_layout)
        
        # Tabla de justificaciones sin configuración
        self.sin_config_table = QTableWidget()
        self.sin_config_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sin_config_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sin_config_table.setAlternatingRowColors(True)
        
        # Configurar columnas
        self.sin_config_table.setColumnCount(4)
        self.sin_config_table.setHorizontalHeaderLabels([
            "Tipo", "Justificación", "Cantidad", "Última Ocurrencia"
        ])
        
        # Ajustar tamaños de columnas
        header = self.sin_config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Justificación
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Cantidad
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Fecha
        
        # Conectar selección para habilitar botón
        self.sin_config_table.selectionModel().selectionChanged.connect(
            self.on_sin_config_selection_changed
        )
        
        sin_config_layout.addWidget(self.sin_config_table)
        
        parent.addWidget(sin_config_widget)
    
    def on_sin_config_selection_changed(self):
        """Maneja el cambio de selección en la tabla de justificaciones sin configuración."""
        has_selection = self.sin_config_table.selectionModel().hasSelection()
        self.auto_crear_button.setEnabled(has_selection)
    
    def auto_crear_configuracion_desde_justificacion(self):
        """Crea automáticamente una configuración basada en la justificación seleccionada."""
        current_row = self.sin_config_table.currentRow()
        if current_row < 0:
            return
        
        # Obtener datos de la fila seleccionada
        tipo = self.sin_config_table.item(current_row, 0).text()
        justificacion = self.sin_config_table.item(current_row, 1).text()
        cantidad = self.sin_config_table.item(current_row, 2).text()
        
        # Confirmar creación
        respuesta = QMessageBox.question(
            self,
            "Crear Configuración Automática",
            f"¿Desea crear una configuración para:\n\n"
            f"Tipo: {tipo}\n"
            f"Justificación: {justificacion}\n"
            f"Casos encontrados: {cantidad}\n\n"
            f"Podrá editar los detalles después de crearla.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            # Limpiar formulario y pre-llenar
            self.clear_form()
            self.tipo_combo.setCurrentText(tipo)
            
            # Crear un patrón sugerido (primeras palabras de la justificación)
            palabras = justificacion.split()[:3]  # Primeras 3 palabras
            patron_sugerido = " ".join(palabras).upper()
            self.patron_input.setText(patron_sugerido)
            
            # Sugerir una respuesta básica
            respuesta_sugerida = f"Respuesta automática para {tipo.lower()} - {patron_sugerido}"
            self.respuesta_text.setText(respuesta_sugerida)
            
            # Mensaje informativo
            QMessageBox.information(
                self,
                "Configuración Pre-llenada",
                f"Se ha pre-llenado una configuración para '{tipo}'.\n\n"
                f"Por favor, revise y ajuste:\n"
                f"• El patrón de búsqueda\n"
                f"• La respuesta automática\n"
                f"• El archivo PDF si es necesario\n\n"
                f"Luego haga clic en 'Guardar' para confirmar."
            )
    
    def load_justificaciones_sin_configuracion(self):
        """Carga las justificaciones sin configuración desde la base de datos."""
        try:
            # Obtener estadísticas
            stats = self.db_manager.obtener_estadisticas_configuraciones()
            stats_text = (
                f"📊 Total procesadas: {stats['total_procesadas']} | "
                f"Sin configuración: {stats['sin_configuracion']} "
                f"({stats['porcentaje_sin_config']:.1f}%) | "
                f"Con configuración: {stats['con_configuracion']}"
            )
            self.stats_label.setText(stats_text)
            
            # Obtener justificaciones sin configuración
            justificaciones = self.db_manager.obtener_justificaciones_sin_configuracion()
            
            # Actualizar tabla
            self.sin_config_table.setRowCount(len(justificaciones))
            
            for row, justif in enumerate(justificaciones):
                # Tipo
                tipo_item = QTableWidgetItem(justif['tipo'] or 'N/A')
                self.sin_config_table.setItem(row, 0, tipo_item)
                
                # Justificación (truncada si es muy larga)
                justificacion_texto = justif['justificacion']
                if len(justificacion_texto) > 100:
                    justificacion_texto = justificacion_texto[:97] + "..."
                justif_item = QTableWidgetItem(justificacion_texto)
                justif_item.setToolTip(justif['justificacion'])  # Tooltip con texto completo
                self.sin_config_table.setItem(row, 1, justif_item)
                
                # Cantidad
                cantidad_item = QTableWidgetItem(str(justif['cantidad']))
                cantidad_item.setTextAlignment(Qt.AlignCenter)
                self.sin_config_table.setItem(row, 2, cantidad_item)
                
                # Última ocurrencia
                fecha_item = QTableWidgetItem(justif['ultima_ocurrencia'][:16] if justif['ultima_ocurrencia'] else 'N/A')
                fecha_item.setTextAlignment(Qt.AlignCenter)
                self.sin_config_table.setItem(row, 3, fecha_item)
                
                # Colores según cantidad
                if justif['cantidad'] >= 10:
                    # Rojo para muchas ocurrencias
                    for col in range(4):
                        self.sin_config_table.item(row, col).setBackground(QTableWidgetItem().background().color().darker(110))
                elif justif['cantidad'] >= 5:
                    # Amarillo para ocurrencias medias
                    for col in range(4):
                        self.sin_config_table.item(row, col).setBackground(QTableWidgetItem().background().color().lighter(120))
            
            self.logger.info(f"Cargadas {len(justificaciones)} justificaciones sin configuración")
            
        except Exception as e:
            self.logger.error(f"Error cargando justificaciones sin configuración: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Error al cargar justificaciones sin configuración:\n{str(e)}"
            )
