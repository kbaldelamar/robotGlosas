import os
import sys
import subprocess
import logging
from pathlib import Path
import urllib.request
import tempfile
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtCore import QThread, Signal, Qt

class TesseractDownloadThread(QThread):
    """Hilo para descargar e instalar Tesseract sin bloquear la UI."""
    
    progress_updated = Signal(int)
    status_updated = Signal(str)
    download_finished = Signal(bool, str)  # (exitoso, mensaje)
    
    def __init__(self, installer_path=None):
        super().__init__()
        self.installer_path = installer_path
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Ejecuta la descarga e instalación de Tesseract."""
        try:
            if self.installer_path and os.path.exists(self.installer_path):
                # Usar instalador local
                self.status_updated.emit("Ejecutando instalador local...")
                self._install_from_file(self.installer_path)
            else:
                # Descargar e instalar
                self.status_updated.emit("Descargando Tesseract OCR...")
                installer_path = self._download_tesseract()
                
                if installer_path:
                    self.status_updated.emit("Ejecutando instalador...")
                    self._install_from_file(installer_path)
                else:
                    self.download_finished.emit(False, "Error descargando Tesseract")
                    
        except Exception as e:
            self.logger.error(f"Error en instalación de Tesseract: {e}")
            self.download_finished.emit(False, f"Error: {str(e)}")
    
    def _download_tesseract(self):
        """Descarga Tesseract desde el repositorio oficial."""
        try:
            # URL del instalador de Tesseract para Windows (64-bit)
            url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
            
            # Crear archivo temporal
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "tesseract_installer.exe")
            
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    self.progress_updated.emit(percent)
            
            # Descargar archivo
            urllib.request.urlretrieve(url, installer_path, progress_hook)
            
            return installer_path
            
        except Exception as e:
            self.logger.error(f"Error descargando Tesseract: {e}")
            return None
    
    def _install_from_file(self, installer_path):
        """Ejecuta el instalador de Tesseract."""
        try:
            # Primero intentar instalación local (sin permisos admin)
            local_install_dir = os.path.join(os.getcwd(), "tesseract-local")
            
            if self._try_local_installation(installer_path, local_install_dir):
                return
            
            # Si falla, intentar instalación estándar
            self._try_standard_installation(installer_path)
                
        except Exception as e:
            self.download_finished.emit(False, f"Error en instalación: {e}")
    
    def _try_local_installation(self, installer_path, local_dir):
        """Intenta instalación local sin permisos de administrador."""
        try:
            self.status_updated.emit("Intentando instalación local (sin permisos admin)...")
            
            # Crear directorio local
            os.makedirs(local_dir, exist_ok=True)
            
            # Comando para instalación local
            cmd = [installer_path, "/S", f"/D={local_dir}"]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
            
            # Verificar si se instaló localmente
            local_tesseract = os.path.join(local_dir, "tesseract.exe")
            if os.path.exists(local_tesseract):
                # Configurar ruta local
                try:
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = local_tesseract
                    
                    # Probar que funciona
                    pytesseract.get_tesseract_version()
                    
                    self.download_finished.emit(True, f"Tesseract instalado localmente en: {local_dir}")
                    return True
                except:
                    pass
            
            return False
            
        except subprocess.CalledProcessError:
            return False
        except Exception:
            return False
    
    def _try_standard_installation(self, installer_path):
        """Intenta instalación estándar que puede requerir permisos."""
        try:
            install_dir = r"C:\Program Files\Tesseract-OCR"
            
            # Comando básico (puede requerir UAC)
            cmd = [installer_path, "/S", f"/D={install_dir}"]
            
            self.status_updated.emit("Intentando instalación estándar (puede requerir permisos de administrador)...")
            
            # Intentar ejecutar como proceso normal primero
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
                
                # Verificar instalación
                if self._verify_installation():
                    self.download_finished.emit(True, "Tesseract OCR instalado correctamente")
                    return
                    
            except subprocess.CalledProcessError as e:
                if "740" in str(e) or "elevation" in str(e).lower():
                    # Error de privilegios - intentar con PowerShell como admin
                    self.status_updated.emit("Solicitando permisos de administrador...")
                    self._install_as_admin(installer_path, install_dir)
                    return
                else:
                    raise e
            
            # Si llegamos aquí, la instalación falló
            self.download_finished.emit(False, "La instalación no se pudo verificar")
                
        except subprocess.TimeoutExpired:
            self.download_finished.emit(False, "La instalación tomó demasiado tiempo")
        except subprocess.CalledProcessError as e:
            error_msg = f"Error ejecutando instalador (código {e.returncode})"
            if "740" in str(e) or "elevation" in str(e).lower():
                error_msg += ". Se requieren permisos de administrador."
            self.download_finished.emit(False, error_msg)
        except Exception as e:
            self.download_finished.emit(False, f"Error en instalación: {e}")
    
    def _install_as_admin(self, installer_path, install_dir):
        """Intenta instalar usando PowerShell con privilegios elevados."""
        try:
            # Crear script PowerShell temporal
            ps_script = f'''
            Start-Process -FilePath "{installer_path}" -ArgumentList "/S", "/D={install_dir}" -Verb RunAs -Wait
            '''
            
            # Ejecutar con PowerShell
            cmd = ["powershell", "-Command", ps_script]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
            
            # Dar tiempo para que la instalación termine
            import time
            time.sleep(3)
            
            # Verificar instalación
            if self._verify_installation():
                self.download_finished.emit(True, "Tesseract OCR instalado correctamente (con permisos de administrador)")
            else:
                self.download_finished.emit(False, "Instalación completada pero no se puede verificar")
                
        except Exception as e:
            self.download_finished.emit(False, f"Error con permisos de administrador: {e}")
    
    def _verify_installation(self):
        """Verifica que Tesseract se haya instalado correctamente."""
        try:
            # Intentar ejecutar tesseract --version
            result = subprocess.run(["tesseract", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            # Intentar con rutas comunes
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.join(os.getcwd(), "tesseract-local", "tesseract.exe")
            ]
            
            for tesseract_path in common_paths:
                try:
                    if os.path.exists(tesseract_path):
                        result = subprocess.run([tesseract_path, "--version"], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            return True
                except:
                    continue
        return False


class TesseractManager:
    """Gestor para verificar, descargar e instalar Tesseract OCR."""
    
    def __init__(self, parent_widget=None):
        self.parent = parent_widget
        self.logger = logging.getLogger(__name__)
        
    def is_tesseract_available(self):
        """Verifica si Tesseract está disponible en el sistema."""
        try:
            import pytesseract
            # Intentar obtener la versión
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            self.logger.debug(f"Tesseract no disponible: {e}")
            return False
    
    def get_tesseract_path(self):
        """Obtiene la ruta de Tesseract si está instalado."""
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
            os.path.join(os.getcwd(), "tesseract-local", "tesseract.exe")  # Instalación local
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Intentar encontrar en PATH
        try:
            result = subprocess.run(["where", "tesseract"], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip().split('\n')[0]
        except:
            pass
            
        return None
    
    def configure_tesseract_path(self):
        """Configura la ruta de Tesseract en pytesseract."""
        tesseract_path = self.get_tesseract_path()
        if tesseract_path:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                return True
            except ImportError:
                pass
        return False
    
    def show_installation_dialog(self, installer_path=None):
        """Muestra diálogo para instalar Tesseract."""
        if installer_path and os.path.exists(installer_path):
            message = f"""
            <h3>🔍 Tesseract OCR No Encontrado</h3>
            <p>Tesseract OCR es necesario para identificar números de documento automáticamente.</p>
            
            <p><b>Se encontró un instalador:</b><br>
            <code>{os.path.basename(installer_path)}</code></p>
            
            <p><b>¿Desea instalar Tesseract automáticamente?</b></p>
            
            <ul>
            <li>✅ Instalación automática y silenciosa</li>
            <li>✅ Se configurará automáticamente</li>
            <li>✅ Permitirá identificar documentos por OCR</li>
            </ul>
            
            <p><i>Si selecciona "No", puede continuar sin OCR (archivos se nombrarán solo con número de página).</i></p>
            """
        else:
            message = """
            <h3>🔍 Tesseract OCR No Encontrado</h3>
            <p>Tesseract OCR es necesario para identificar números de documento automáticamente.</p>
            
            <p><b>¿Desea descargar e instalar Tesseract automáticamente?</b></p>
            
            <ul>
            <li>✅ Descarga desde repositorio oficial</li>
            <li>✅ Instalación automática y silenciosa</li>
            <li>✅ Se configurará automáticamente</li>
            <li>✅ Permitirá identificar documentos por OCR</li>
            </ul>
            
            <p><b>Tamaño:</b> ~60 MB</p>
            <p><i>Si selecciona "No", puede continuar sin OCR.</i></p>
            """
        
        reply = QMessageBox.question(
            self.parent,
            "Instalar Tesseract OCR",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def install_tesseract(self, installer_path=None):
        """Inicia el proceso de instalación de Tesseract."""
        # Crear diálogo de progreso
        progress_dialog = QProgressDialog(
            "Preparando instalación de Tesseract OCR...",
            "Cancelar",
            0, 100,
            self.parent
        )
        progress_dialog.setWindowTitle("Instalando Tesseract OCR")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(False)
        progress_dialog.setAutoReset(False)
        progress_dialog.show()
        
        # Crear hilo de descarga/instalación
        self.download_thread = TesseractDownloadThread(installer_path)
        
        # Conectar señales
        self.download_thread.progress_updated.connect(progress_dialog.setValue)
        self.download_thread.status_updated.connect(progress_dialog.setLabelText)
        self.download_thread.download_finished.connect(
            lambda success, msg: self._on_installation_finished(success, msg, progress_dialog)
        )
        
        # Manejar cancelación
        progress_dialog.canceled.connect(self.download_thread.terminate)
        
        # Iniciar descarga/instalación
        self.download_thread.start()
        
        return progress_dialog
    
    def _on_installation_finished(self, success, message, progress_dialog):
        """Maneja la finalización de la instalación."""
        progress_dialog.close()
        
        if success:
            QMessageBox.information(
                self.parent,
                "Instalación Completada",
                f"""
                <h3>✅ Tesseract OCR Instalado</h3>
                <p>{message}</p>
                
                <p><b>Pasos siguientes:</b></p>
                <ul>
                <li>La aplicación configurará automáticamente Tesseract</li>
                <li>Ahora puede usar OCR para identificar documentos</li>
                <li>Reinicie la operación de separación de PDF</li>
                </ul>
                """
            )
            
            # Configurar ruta automáticamente
            self.configure_tesseract_path()
            
        else:
            # Crear mensaje de error más detallado con opciones
            error_msg = f"""
            <h3>❌ Error en Instalación</h3>
            <p>{message}</p>
            
            <p><b>Opciones disponibles:</b></p>
            <ul>
            <li><b>Opción 1 (Recomendada):</b> Ejecutar VS Code/aplicación como Administrador y volver a intentar</li>
            <li><b>Opción 2:</b> Descargar manualmente desde: 
            <a href="https://github.com/UB-Mannheim/tesseract/wiki">GitHub</a> e instalar</li>
            <li><b>Opción 3:</b> Usar script helper: <code>descargar_tesseract.bat</code></li>
            <li><b>Opción 4:</b> Continuar sin OCR (solo numeración de páginas)</li>
            </ul>
            
            <p><b>Para Opción 1:</b></p>
            <ol>
            <li>Cerrar esta aplicación</li>
            <li>Hacer clic derecho en VS Code → "Ejecutar como administrador"</li>
            <li>Abrir el proyecto y volver a intentar</li>
            </ol>
            """
            
            reply = QMessageBox.critical(
                self.parent,
                "Error de Instalación",
                error_msg,
                QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Ignore
            )
            
            if reply == QMessageBox.StandardButton.Retry:
                # Intentar nuevamente
                self.show_retry_options()
    
    def show_retry_options(self):
        """Muestra opciones para reintentar la instalación."""
        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Opciones de Instalación")
        msg.setText("¿Cómo desea proceder?")
        msg.setInformativeText("""
        Seleccione una opción para instalar Tesseract OCR:
        """)
        
        # Botones personalizados
        admin_btn = msg.addButton("🔧 Intentar como Admin", QMessageBox.ButtonRole.ActionRole)
        manual_btn = msg.addButton("📁 Abrir descarga manual", QMessageBox.ButtonRole.ActionRole)
        script_btn = msg.addButton("⚡ Usar script helper", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("❌ Cancelar", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == admin_btn:
            self.try_admin_installation()
        elif msg.clickedButton() == manual_btn:
            self.open_manual_download()
        elif msg.clickedButton() == script_btn:
            self.run_helper_script()
    
    def try_admin_installation(self):
        """Intenta la instalación con permisos de administrador."""
        QMessageBox.information(
            self.parent,
            "Instalación como Administrador",
            """
            <h3>🔧 Instalación con Permisos Elevados</h3>
            
            <p><b>Pasos a seguir:</b></p>
            <ol>
            <li>Cerrar esta aplicación completamente</li>
            <li>Hacer clic derecho en VS Code</li>
            <li>Seleccionar "Ejecutar como administrador"</li>
            <li>Abrir el proyecto nuevamente</li>
            <li>Volver a intentar el Separador de PDF</li>
            </ol>
            
            <p><b>Nota:</b> Windows le pedirá confirmación UAC.</p>
            """
        )
    
    def open_manual_download(self):
        """Abre la página de descarga manual."""
        import webbrowser
        webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")
        
        QMessageBox.information(
            self.parent,
            "Descarga Manual",
            """
            <h3>📁 Descarga Manual de Tesseract</h3>
            
            <p>Se abrió la página de descarga oficial.</p>
            
            <p><b>Instrucciones:</b></p>
            <ol>
            <li>Descargar el archivo .exe para Windows 64-bit</li>
            <li>Ejecutar el instalador manualmente</li>
            <li>Asegurarse de que se agregue al PATH</li>
            <li>Reiniciar la aplicación</li>
            </ol>
            
            <p><b>Archivo recomendado:</b><br>
            <code>tesseract-ocr-w64-setup-*.exe</code></p>
            """
        )
    
    def run_helper_script(self):
        """Ejecuta el script helper para descargar Tesseract."""
        import os
        script_path = os.path.join(os.getcwd(), "descargar_tesseract.bat")
        
        if os.path.exists(script_path):
            try:
                os.startfile(script_path)
                QMessageBox.information(
                    self.parent,
                    "Script Helper",
                    """
                    <h3>⚡ Script Helper Ejecutado</h3>
                    
                    <p>Se ejecutó el script <code>descargar_tesseract.bat</code></p>
                    
                    <p><b>El script le permitirá:</b></p>
                    <ul>
                    <li>Descargar Tesseract automáticamente</li>
                    <li>Verificar instalación existente</li>
                    <li>Obtener enlaces de descarga manual</li>
                    </ul>
                    
                    <p>Una vez completado, reinicie la aplicación.</p>
                    """
                )
            except Exception as e:
                QMessageBox.warning(
                    self.parent,
                    "Error",
                    f"No se pudo ejecutar el script: {e}"
                )
        else:
            QMessageBox.warning(
                self.parent,
                "Script No Encontrado",
                f"No se encontró el archivo: {script_path}"
            )
    
    def find_local_installer(self, search_paths=None):
        """Busca instaladores de Tesseract en rutas locales."""
        if search_paths is None:
            search_paths = [
                os.getcwd(),  # Directorio actual
                os.path.join(os.getcwd(), "installers"),
                os.path.join(os.getcwd(), "utils"),
                os.path.expanduser("~/Downloads"),
                os.path.expanduser("~/Desktop")
            ]
        
        installer_patterns = [
            "tesseract*.exe",
            "Tesseract*.exe",
            "*tesseract*.exe"
        ]
        
        import glob
        
        for path in search_paths:
            if os.path.exists(path):
                for pattern in installer_patterns:
                    full_pattern = os.path.join(path, pattern)
                    matches = glob.glob(full_pattern)
                    if matches:
                        # Devolver el más reciente
                        return max(matches, key=os.path.getmtime)
        
        return None


def check_and_install_tesseract(parent_widget=None):
    """
    Función helper para verificar e instalar Tesseract si es necesario.
    
    Returns:
        bool: True si Tesseract está disponible, False si no
    """
    manager = TesseractManager(parent_widget)
    
    # Verificar si ya está disponible
    if manager.is_tesseract_available():
        return True
    
    # Configurar ruta si está instalado pero no configurado
    if manager.configure_tesseract_path():
        if manager.is_tesseract_available():
            return True
    
    # Buscar instalador local
    local_installer = manager.find_local_installer()
    
    # Mostrar diálogo de instalación
    if manager.show_installation_dialog(local_installer):
        # Usuario quiere instalar
        progress_dialog = manager.install_tesseract(local_installer)
        
        # Esperar a que termine (esto bloquea hasta que el usuario cierre el diálogo)
        if progress_dialog:
            # El diálogo se maneja en el hilo, retornar False por ahora
            # La aplicación debería verificar nuevamente después
            return False
    
    return False