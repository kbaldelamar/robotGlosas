from typing import List
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                            QAbstractItemView, QMenu, QMessageBox)
from PySide6.QtCore import Qt, Signal as pyqtSignal
from PySide6.QtGui import QAction
from database.models import Cliente

class ClientTable(QTableWidget):
    """
    Tabla para mostrar y gestionar clientes.
    Proporciona funcionalidad CRUD básica para clientes.
    """
    
    # Señales personalizadas
    client_selected = pyqtSignal(Cliente)
    client_edit_requested = pyqtSignal(Cliente)
    client_delete_requested = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.clients: List[Cliente] = []
        self.setup_ui()
        self.setup_context_menu()
        
    def setup_ui(self):
        """Configura la interfaz de la tabla."""
        # Configurar columnas
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(['ID', 'Nombre', 'NIT', 'Correo', 'Teléfono'])
        
        # Configurar comportamiento
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Configurar redimensionamiento de columnas
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nombre
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # NIT
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Correo
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Teléfono
        
        # Establecer anchos específicos
        self.setColumnWidth(0, 50)   # ID
        self.setColumnWidth(2, 120)  # NIT
        self.setColumnWidth(4, 120)  # Teléfono
        
        # Conectar señales
        self.itemSelectionChanged.connect(self.on_selection_changed)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
    def setup_context_menu(self):
        """Configura el menú contextual."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def show_context_menu(self, position):
        """Muestra el menú contextual."""
        if self.itemAt(position) is None:
            return
            
        menu = QMenu(self)
        
        edit_action = QAction("Editar", self)
        edit_action.triggered.connect(self.edit_selected_client)
        menu.addAction(edit_action)
        
        delete_action = QAction("Eliminar", self)
        delete_action.triggered.connect(self.delete_selected_client)
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(position))
        
    def load_clients(self, clients: List[Cliente]):
        """
        Carga los clientes en la tabla.
        
        Args:
            clients (List[Cliente]): Lista de clientes a mostrar
        """
        self.clients = clients
        self.setRowCount(len(clients))
        
        for row, client in enumerate(clients):
            self.setItem(row, 0, QTableWidgetItem(str(client.id)))
            self.setItem(row, 1, QTableWidgetItem(client.nombre))
            self.setItem(row, 2, QTableWidgetItem(client.nit))
            self.setItem(row, 3, QTableWidgetItem(client.correo))
            self.setItem(row, 4, QTableWidgetItem(client.telefono))
            
            # Hacer que el ID no sea editable
            id_item = self.item(row, 0)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    
    def get_selected_client(self) -> Cliente:
        """
        Obtiene el cliente seleccionado.
        
        Returns:
            Cliente: Cliente seleccionado o None si no hay selección
        """
        current_row = self.currentRow()
        if current_row >= 0 and current_row < len(self.clients):
            return self.clients[current_row]
        return None
    
    def on_selection_changed(self):
        """Maneja el cambio de selección."""
        client = self.get_selected_client()
        if client:
            self.client_selected.emit(client)
    
    def on_item_double_clicked(self, item):
        """Maneja el doble clic en un elemento."""
        client = self.get_selected_client()
        if client:
            self.client_edit_requested.emit(client)
    
    def edit_selected_client(self):
        """Edita el cliente seleccionado."""
        client = self.get_selected_client()
        if client:
            self.client_edit_requested.emit(client)
    
    def delete_selected_client(self):
        """Elimina el cliente seleccionado."""
        client = self.get_selected_client()
        if client:
            reply = QMessageBox.question(
                self, 
                "Confirmar Eliminación",
                f"¿Está seguro de eliminar el cliente '{client.nombre}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.client_delete_requested.emit(client.id)