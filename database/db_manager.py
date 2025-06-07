import sqlite3
import logging
from typing import List, Optional
from config.settings import Settings
from database.models import Cliente

class DatabaseManager:
    """
    Gestor de base de datos SQLite.
    Maneja todas las operaciones CRUD para las tablas de la aplicación.
    """
    
    def __init__(self):
        """Inicializa el gestor de base de datos."""
        self.db_path = Settings.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        
    def get_connection(self) -> sqlite3.Connection:
        """
        Obtiene una conexión a la base de datos.
        
        Returns:
            sqlite3.Connection: Conexión a la base de datos
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
        return conn
    
    def create_tables(self) -> None:
        """Crea las tablas necesarias en la base de datos."""
        try:
            with self.get_connection() as conn:
                # Tabla clientes
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cliente (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        nit TEXT UNIQUE NOT NULL,
                        correo TEXT,
                        telefono TEXT
                    )
                """)
                
                # Tabla para logs de automatización (opcional)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS automation_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        action TEXT NOT NULL,
                        status TEXT NOT NULL,
                        details TEXT
                    )
                """)
                
                conn.commit()
                self.logger.info("Tablas creadas correctamente")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error creando tablas: {e}")
            raise
    
    def insert_client(self, cliente: Cliente) -> int:
        """
        Inserta un nuevo cliente en la base de datos.
        
        Args:
            cliente (Cliente): Objeto cliente a insertar
            
        Returns:
            int: ID del cliente insertado
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO cliente (nombre, nit, correo, telefono)
                    VALUES (?, ?, ?, ?)
                """, (cliente.nombre, cliente.nit, cliente.correo, cliente.telefono))
                
                conn.commit()
                self.logger.info(f"Cliente insertado: {cliente.nombre}")
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            self.logger.error(f"Error insertando cliente: {e}")
            raise
    
    def get_all_clients(self) -> List[Cliente]:
        """
        Obtiene todos los clientes de la base de datos.
        
        Returns:
            List[Cliente]: Lista de todos los clientes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, nombre, nit, correo, telefono
                    FROM cliente
                    ORDER BY nombre
                """)
                
                rows = cursor.fetchall()
                clients = [
                    Cliente(
                        id=row['id'],
                        nombre=row['nombre'],
                        nit=row['nit'],
                        correo=row['correo'],
                        telefono=row['telefono']
                    )
                    for row in rows
                ]
                
                self.logger.info(f"Obtenidos {len(clients)} clientes")
                return clients
                
        except sqlite3.Error as e:
            self.logger.error(f"Error obteniendo clientes: {e}")
            return []
    
    def update_client(self, cliente: Cliente) -> bool:
        """
        Actualiza un cliente existente.
        
        Args:
            cliente (Cliente): Cliente con datos actualizados
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE cliente 
                    SET nombre=?, nit=?, correo=?, telefono=?
                    WHERE id=?
                """, (cliente.nombre, cliente.nit, cliente.correo, 
                     cliente.telefono, cliente.id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Cliente actualizado: {cliente.nombre}")
                    return True
                else:
                    self.logger.warning(f"No se encontró cliente con ID: {cliente.id}")
                    return False
                    
        except sqlite3.Error as e:
            self.logger.error(f"Error actualizando cliente: {e}")
            return False
    
    def delete_client(self, client_id: int) -> bool:
        """
        Elimina un cliente por su ID.
        
        Args:
            client_id (int): ID del cliente a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("DELETE FROM cliente WHERE id=?", (client_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Cliente eliminado con ID: {client_id}")
                    return True
                else:
                    self.logger.warning(f"No se encontró cliente con ID: {client_id}")
                    return False
                    
        except sqlite3.Error as e:
            self.logger.error(f"Error eliminando cliente: {e}")
            return False