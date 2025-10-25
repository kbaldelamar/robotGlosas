import logging
import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QProgressBar, QTextEdit,
                             QGroupBox, QGridLayout, QSpinBox, QCheckBox,
                             QMessageBox, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap
from utils.tesseract_installer import check_and_install_tesseract, TesseractManager

class PDFSeparatorThread(QThread):
    """Hilo para procesar la separación de PDF sin bloquear la UI."""
    
    # Señales para comunicación con la UI
    progress_updated = Signal(int)
    status_updated = Signal(str)
    page_processed = Signal(str, str)  # (numero_pagina, numero_documento)
    error_occurred = Signal(str)
    finished_processing = Signal(bool, str)  # (exitoso, mensaje)
    
    def __init__(self, pdf_path, output_folder, use_ocr=True, start_page=1, end_page=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_folder = output_folder
        self.use_ocr = use_ocr
        self.start_page = start_page
        self.end_page = end_page
        self.logger = logging.getLogger(__name__)
        self._stop_processing = False
        
    def run(self):
        """Ejecuta el proceso de separación de PDF."""
        try:
            from PyPDF2 import PdfReader, PdfWriter
            import pytesseract
            from PIL import Image
            import fitz  # PyMuPDF para convertir PDF a imagen
            import re
            
            self.status_updated.emit("Iniciando separación de PDF...")
            
            # Leer el PDF
            reader = PdfReader(self.pdf_path)
            total_pages = len(reader.pages)
            
            # Determinar rango de páginas
            start = max(1, self.start_page) - 1  # Convertir a índice base 0
            end = min(total_pages, self.end_page or total_pages)
            
            self.status_updated.emit(f"Procesando páginas {start + 1} a {end} de {total_pages}")
            
            pages_processed = 0
            successful_extractions = 0
            
            for page_num in range(start, end):
                if self._stop_processing:
                    break
                    
                current_page = page_num + 1  # Para mostrar número humano
                self.status_updated.emit(f"Procesando página {current_page}...")
                
                try:
                    # Extraer la página
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_num])
                    
                    # Nombre temporal para la página
                    temp_page_name = f"pagina_{current_page:03d}.pdf"
                    temp_page_path = os.path.join(self.output_folder, temp_page_name)
                    
                    # Guardar página individual
                    with open(temp_page_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    documento_numero = "SIN_IDENTIFICAR"
                    
                    # Si está habilitado OCR, intentar extraer número de documento
                    if self.use_ocr:
                        try:
                            # Configurar Tesseract si es necesario
                            try:
                                import pytesseract
                                # Intentar configurar ruta automáticamente
                                from utils.tesseract_installer import TesseractManager
                                manager = TesseractManager()
                                manager.configure_tesseract_path()
                            except ImportError:
                                pass
                            
                            # Convertir página PDF a imagen usando PyMuPDF
                            pdf_doc = fitz.open(temp_page_path)
                            page = pdf_doc[0]
                            
                            # Renderizar como imagen
                            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Escala 2x para mejor calidad
                            img_data = pix.tobytes("png")
                            
                            # Convertir a PIL Image
                            from io import BytesIO
                            img = Image.open(BytesIO(img_data))
                            
                            # Ejecutar OCR
                            ocr_text = pytesseract.image_to_string(img, config='--psm 6 -c tessedit_char_whitelist=0123456789')
                            
                            # Buscar números de documento (8-11 dígitos típicamente)
                            numeros_encontrados = re.findall(r'\b\d{8,11}\b', ocr_text)
                            
                            if numeros_encontrados:
                                # Tomar el primer número encontrado que parece una cédula
                                documento_numero = numeros_encontrados[0]
                                self.logger.info(f"Página {current_page}: Documento encontrado - {documento_numero}")
                            else:
                                self.logger.warning(f"Página {current_page}: No se encontró número de documento válido")
                                # Buscar cualquier secuencia de números como respaldo
                                numeros_backup = re.findall(r'\d+', ocr_text)
                                if numeros_backup:
                                    # Filtrar números que podrían ser documentos
                                    posibles_docs = [n for n in numeros_backup if len(n) >= 7 and len(n) <= 12]
                                    if posibles_docs:
                                        documento_numero = posibles_docs[0]
                                        self.logger.info(f"Página {current_page}: Documento encontrado (backup) - {documento_numero}")
                            
                            pdf_doc.close()
                            
                        except Exception as e:
                            self.logger.error(f"Error en OCR para página {current_page}: {e}")
                            documento_numero = f"ERROR_OCR_P{current_page}"
                    
                    # Renombrar archivo con número de documento
                    final_name = f"documento_{documento_numero}_pagina_{current_page:03d}.pdf"
                    final_path = os.path.join(self.output_folder, final_name)
                    
                    # Renombrar archivo
                    os.rename(temp_page_path, final_path)
                    
                    # Emitir señal de progreso
                    self.page_processed.emit(str(current_page), documento_numero)
                    
                    pages_processed += 1
                    if documento_numero != "SIN_IDENTIFICAR" and not documento_numero.startswith("ERROR_"):
                        successful_extractions += 1
                    
                    # Actualizar progreso
                    progress = int((pages_processed / (end - start)) * 100)
                    self.progress_updated.emit(progress)
                    
                except Exception as e:
                    self.logger.error(f"Error procesando página {current_page}: {e}")
                    self.error_occurred.emit(f"Error en página {current_page}: {str(e)}")
            
            # Resultado final
            if self._stop_processing:
                self.finished_processing.emit(False, "Proceso cancelado por el usuario")
            else:
                mensaje = f"""
                ✅ Separación completada exitosamente!
                
                📊 Resumen:
                • Páginas procesadas: {pages_processed}
                • Documentos identificados: {successful_extractions}
                • Archivos generados en: {self.output_folder}
                
                📁 Los archivos se nombraron como:
                documento_[NUMERO]_pagina_[XXX].pdf
                """
                self.finished_processing.emit(True, mensaje)
                
        except Exception as e:
            self.logger.error(f"Error general en separación de PDF: {e}")
            self.error_occurred.emit(f"Error general: {str(e)}")
            self.finished_processing.emit(False, f"Error: {str(e)}")
    
    def stop(self):
        """Detiene el procesamiento."""
        self._stop_processing = True


class PDFSeparatorWidget(QWidget):
    """Widget para separar PDF en páginas individuales con OCR."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.pdf_path = ""
        self.output_folder = ""
        self.separator_thread = None
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configura la interfaz del separador de PDF."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Título principal
        title_label = QLabel("📄 Separador de PDF")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel("""
        Este módulo permite dividir un PDF con múltiples páginas en archivos PDF individuales.
        Utiliza OCR para identificar números de documento en cada página y nombrar los archivos automáticamente.
        """)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: #34495e;
                padding: 10px;
                background-color: #e8f4fd;
                border-left: 4px solid #3498db;
                border-radius: 4px;
            }
        """)
        layout.addWidget(desc_label)
        
        # Grupo de selección de archivos
        file_group = QGroupBox("📁 Selección de Archivos")
        file_layout = QGridLayout(file_group)
        
        # Selección de PDF
        self.pdf_label = QLabel("Archivo PDF:")
        self.pdf_path_label = QLabel("No seleccionado")
        self.pdf_path_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        self.pdf_browse_btn = QPushButton("Seleccionar PDF")
        self.pdf_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        file_layout.addWidget(self.pdf_label, 0, 0)
        file_layout.addWidget(self.pdf_path_label, 0, 1)
        file_layout.addWidget(self.pdf_browse_btn, 0, 2)
        
        # Selección de carpeta de salida
        self.output_label = QLabel("Carpeta de salida:")
        self.output_path_label = QLabel("No seleccionada")
        self.output_path_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        self.output_browse_btn = QPushButton("Seleccionar Carpeta")
        self.output_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        file_layout.addWidget(self.output_label, 1, 0)
        file_layout.addWidget(self.output_path_label, 1, 1)
        file_layout.addWidget(self.output_browse_btn, 1, 2)
        
        layout.addWidget(file_group)
        
        # Grupo de configuración
        config_group = QGroupBox("⚙️ Configuración")
        config_layout = QGridLayout(config_group)
        
        # OCR habilitado
        self.ocr_checkbox = QCheckBox("Usar OCR para identificar números de documento")
        self.ocr_checkbox.setChecked(True)
        self.ocr_checkbox.setStyleSheet("font-weight: bold; color: #2c3e50;")
        config_layout.addWidget(self.ocr_checkbox, 0, 0, 1, 2)
        
        # Rango de páginas
        config_layout.addWidget(QLabel("Página inicial:"), 1, 0)
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setMinimum(1)
        self.start_page_spin.setMaximum(9999)
        self.start_page_spin.setValue(1)
        config_layout.addWidget(self.start_page_spin, 1, 1)
        
        config_layout.addWidget(QLabel("Página final:"), 2, 0)
        self.end_page_spin = QSpinBox()
        self.end_page_spin.setMinimum(1)
        self.end_page_spin.setMaximum(9999)
        self.end_page_spin.setValue(999)
        self.end_page_spin.setSpecialValueText("Hasta el final")
        config_layout.addWidget(self.end_page_spin, 2, 1)
        
        layout.addWidget(config_group)
        
        # Botones de control
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Iniciar Separación")
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Estado actual
        self.status_label = QLabel("Listo para procesar")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Log de resultados
        log_group = QGroupBox("📋 Registro de Procesamiento")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Espaciado al final
        layout.addStretch()
        
    def setup_connections(self):
        """Configura las conexiones de señales."""
        self.pdf_browse_btn.clicked.connect(self.browse_pdf)
        self.output_browse_btn.clicked.connect(self.browse_output_folder)
        self.start_btn.clicked.connect(self.start_separation)
        self.stop_btn.clicked.connect(self.stop_separation)
        
    def browse_pdf(self):
        """Abre diálogo para seleccionar archivo PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo PDF",
            "",
            "Archivos PDF (*.pdf);;Todos los archivos (*.*)"
        )
        
        if file_path:
            self.pdf_path = file_path
            self.pdf_path_label.setText(os.path.basename(file_path))
            self.pdf_path_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.log_message(f"📁 PDF seleccionado: {file_path}")
            self.check_ready_to_start()
            
    def browse_output_folder(self):
        """Abre diálogo para seleccionar carpeta de salida."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de salida",
            ""
        )
        
        if folder_path:
            self.output_folder = folder_path
            self.output_path_label.setText(folder_path)
            self.output_path_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.log_message(f"📂 Carpeta de salida: {folder_path}")
            self.check_ready_to_start()
            
    def check_ready_to_start(self):
        """Verifica si todo está listo para iniciar."""
        ready = bool(self.pdf_path and self.output_folder and os.path.exists(self.pdf_path))
        self.start_btn.setEnabled(ready)
        
        if ready:
            self.status_label.setText("✅ Listo para iniciar separación")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-weight: bold;
                    padding: 8px;
                    background-color: #e8f5e8;
                    border-radius: 4px;
                }
            """)
        
    def start_separation(self):
        """Inicia el proceso de separación."""
        if not self.pdf_path or not self.output_folder:
            QMessageBox.warning(self, "Error", "Debe seleccionar el archivo PDF y la carpeta de salida.")
            return
            
        # Verificar OCR si está habilitado
        if self.ocr_checkbox.isChecked():
            tesseract_manager = TesseractManager(self)
            
            if not tesseract_manager.is_tesseract_available():
                # Intentar configurar la ruta primero
                if not tesseract_manager.configure_tesseract_path():
                    # Buscar instalador local
                    local_installer = tesseract_manager.find_local_installer()
                    
                    if tesseract_manager.show_installation_dialog(local_installer):
                        # Usuario quiere instalar Tesseract
                        progress_dialog = tesseract_manager.install_tesseract(local_installer)
                        # La instalación se maneja de forma asíncrona
                        # El usuario puede intentar nuevamente después
                        QMessageBox.information(
                            self,
                            "Instalación en Proceso",
                            "La instalación de Tesseract está en proceso.\n"
                            "Una vez completada, puede intentar la separación nuevamente."
                        )
                        return
                    else:
                        # Usuario eligió continuar sin OCR
                        reply = QMessageBox.question(
                            self,
                            "Continuar sin OCR",
                            "¿Desea continuar sin OCR?\n"
                            "Los archivos se nombrarán solo con el número de página.",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.No:
                            return
                        self.ocr_checkbox.setChecked(False)
        
        # Configurar UI para procesamiento
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        # Configurar hilo de procesamiento
        end_page = self.end_page_spin.value() if self.end_page_spin.value() < 999 else None
        
        self.separator_thread = PDFSeparatorThread(
            pdf_path=self.pdf_path,
            output_folder=self.output_folder,
            use_ocr=self.ocr_checkbox.isChecked(),
            start_page=self.start_page_spin.value(),
            end_page=end_page
        )
        
        # Conectar señales
        self.separator_thread.progress_updated.connect(self.progress_bar.setValue)
        self.separator_thread.status_updated.connect(self.update_status)
        self.separator_thread.page_processed.connect(self.on_page_processed)
        self.separator_thread.error_occurred.connect(self.on_error_occurred)
        self.separator_thread.finished_processing.connect(self.on_finished_processing)
        
        # Iniciar procesamiento
        self.separator_thread.start()
        self.log_message("🚀 Iniciando separación de PDF...")
        
    def stop_separation(self):
        """Detiene el proceso de separación."""
        if self.separator_thread:
            self.separator_thread.stop()
            self.log_message("⏹️ Deteniendo procesamiento...")
            self.status_label.setText("Deteniendo...")
            
    def update_status(self, message):
        """Actualiza el estado actual."""
        self.status_label.setText(message)
        self.log_message(f"ℹ️ {message}")
        
    def on_page_processed(self, page_num, document_num):
        """Maneja el procesamiento de una página."""
        if document_num == "SIN_IDENTIFICAR":
            self.log_message(f"📄 Página {page_num}: ⚠️  No se pudo identificar documento")
        elif document_num.startswith("ERROR_"):
            self.log_message(f"📄 Página {page_num}: ❌ Error en OCR")
        else:
            self.log_message(f"📄 Página {page_num}: ✅ Documento {document_num}")
            
    def on_error_occurred(self, error_message):
        """Maneja errores durante el procesamiento."""
        self.log_message(f"❌ ERROR: {error_message}")
        
    def on_finished_processing(self, success, message):
        """Maneja la finalización del procesamiento."""
        # Restaurar UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText("✅ Separación completada")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-weight: bold;
                    padding: 8px;
                    background-color: #e8f5e8;
                    border-radius: 4px;
                }
            """)
            QMessageBox.information(self, "Proceso Completado", message)
        else:
            self.status_label.setText("❌ Error en separación")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-weight: bold;
                    padding: 8px;
                    background-color: #fdf2f2;
                    border-radius: 4px;
                }
            """)
            QMessageBox.critical(self, "Error en Procesamiento", message)
            
        self.log_message("=" * 50)
        self.log_message("🏁 Proceso finalizado")
        
    def log_message(self, message):
        """Agrega mensaje al log."""
        self.log_text.append(message)
        self.log_text.ensureCursorVisible()