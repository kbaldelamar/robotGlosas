import logging
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Signal as pyqtSignal, QObject
from PySide6.QtGui import QTextCursor, QColor

class LogSignalEmitter(QObject):
    """Emisor de señales para logs thread-safe."""
    log_signal = pyqtSignal(str, str)  # mensaje, nivel

class LogHandler(logging.Handler):
    """Handler personalizado para mostrar logs en la interfaz."""
    
    def __init__(self, signal_emitter: LogSignalEmitter):
        super().__init__()
        self.signal_emitter = signal_emitter
    
    def emit(self, record):
        """Emite el log hacia la interfaz."""
        log_entry = self.format(record)
        level = record.levelname
        self.signal_emitter.log_signal.emit(log_entry, level)

class LogWidget(QTextEdit):
    """
    Widget que muestra logs en tiempo real.
    Proporciona una consola visual para el seguimiento de operaciones.
    """
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_logging()
        
    def setup_ui(self):
        """Configura la interfaz del widget."""
        self.setReadOnly(True)
        
        # Configurar límite de líneas (alternativa compatible)
        try:
            self.setMaximumBlockCount(1000)  # Limitar líneas para rendimiento
        except AttributeError:
            # Alternativa si setMaximumBlockCount no está disponible
            self.max_lines = 1000
            
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
            }
        """)
        
    def setup_logging(self):
        """Configura el sistema de logging para este widget."""
        self.signal_emitter = LogSignalEmitter()
        self.signal_emitter.log_signal.connect(self.append_log)
        
        # Crear handler personalizado
        self.log_handler = LogHandler(self.signal_emitter)
        self.log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Agregar handler al logger principal
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
    
    def append_log(self, message: str, level: str):
        """
        Agrega un mensaje de log al widget.
        
        Args:
            message (str): Mensaje a mostrar
            level (str): Nivel del log (INFO, ERROR, etc.)
        """
        # Configurar color según nivel
        color_map = {
            'DEBUG': '#888888',
            'INFO': '#ffffff',
            'WARNING': '#ffaa00',
            'ERROR': '#ff4444',
            'CRITICAL': '#ff0000'
        }
        
        color = color_map.get(level, '#ffffff')
        
        # Agregar mensaje con color
        self.setTextColor(QColor(color))
        self.append(message)
        
        # Limitar líneas manualmente si es necesario
        if hasattr(self, 'max_lines'):
            self._limit_lines()
        
        # Scroll automático al final
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
    
    def _limit_lines(self):
        """Limita el número de líneas en el widget manualmente."""
        try:
            document = self.document()
            if document.blockCount() > self.max_lines:
                # Obtener el cursor al inicio del documento
                cursor = QTextCursor(document)
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                
                # Seleccionar y eliminar líneas excedentes
                lines_to_remove = document.blockCount() - self.max_lines
                for _ in range(lines_to_remove):
                    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deleteChar()  # Eliminar el salto de línea
        except Exception:
            # Si hay algún error, no hacer nada crítico
            pass
    
    def clear_logs(self):
        """Limpia todos los logs del widget."""
        self.clear()