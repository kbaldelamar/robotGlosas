import sqlite3
import logging
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from database.db_manager import DatabaseManager
from database.models_glosas import CuentaGlosasPrincipal, GlosaItemDetalle, EstadoCuenta

class DatabaseManagerGlosas(DatabaseManager):
    """
    Extensión del DatabaseManager para manejar glosas.
    Hereda toda la funcionalidad base y agrega métodos específicos para glosas.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    def create_glosas_tables(self) -> None:
        """Crea las tablas necesarias para el manejo de glosas."""
        try:
            with self.get_connection() as conn:
                # Tabla principal de cuentas de glosas
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cuenta_glosas_principal (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        idcuenta TEXT UNIQUE NOT NULL,
                        numero_radicacion TEXT,
                        fecha_radicacion TEXT,
                        proveedor TEXT,
                        numero_factura TEXT,
                        fecha_factura TEXT,
                        valor_factura REAL DEFAULT 0.0,
                        valor_glosado REAL DEFAULT 0.0,
                        
                        estado TEXT NOT NULL DEFAULT 'PENDIENTE',
                        fecha_inicio DATETIME,
                        fecha_fin DATETIME,
                        glosas_encontradas INTEGER DEFAULT 0,
                        glosas_tarifas INTEGER DEFAULT 0,
                        glosas_procesadas INTEGER DEFAULT 0,
                        motivo_fallo TEXT,
                        intentos INTEGER DEFAULT 0,
                        
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabla de glosas individuales
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS glosa_items_detalle (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cuenta_principal_id INTEGER NOT NULL,
                        
                        id_glosa TEXT NOT NULL,
                        id_item TEXT,
                        descripcion_item TEXT,
                        tipo TEXT,
                        descripcion TEXT,
                        justificacion TEXT,
                        valor_glosado REAL DEFAULT 0.0,
                        estado_original TEXT,
                        
                        es_procesable BOOLEAN DEFAULT FALSE,
                        fue_procesado BOOLEAN DEFAULT FALSE,
                        fecha_procesamiento DATETIME,
                        respuesta_enviada TEXT,
                        archivo_subido TEXT,
                        error_procesamiento TEXT,
                        
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (cuenta_principal_id) REFERENCES cuenta_glosas_principal(id)
                    )
                """)
                
                # Índices para optimizar consultas
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cuenta_idcuenta 
                    ON cuenta_glosas_principal(idcuenta)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_glosa_cuenta_id 
                    ON glosa_items_detalle(cuenta_principal_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_glosa_id_glosa 
                    ON glosa_items_detalle(id_glosa)
                """)
                
                conn.commit()
                self.logger.info("Tablas de glosas creadas correctamente")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error creando tablas de glosas: {e}")
            raise
    
    def get_cuenta_estado(self, idcuenta: str) -> Optional[EstadoCuenta]:
        """
        Obtiene el estado actual de una cuenta.
        
        Args:
            idcuenta (str): ID de la cuenta a consultar
            
        Returns:
            Optional[EstadoCuenta]: Estado de la cuenta o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT estado FROM cuenta_glosas_principal 
                    WHERE idcuenta = ?
                """, (idcuenta,))
                
                row = cursor.fetchone()
                if row:
                    return EstadoCuenta(row['estado'])
                return None
                
        except sqlite3.Error as e:
            self.logger.error(f"Error obteniendo estado de cuenta {idcuenta}: {e}")
            return None
    
    def should_process_cuenta(self, idcuenta: str) -> bool:
        """
        Determina si una cuenta debe ser procesada basándose en su estado.
        CORREGIDO: Lógica mejorada para el flujo de importación y procesamiento.
        
        Args:
            idcuenta (str): ID de la cuenta
            
        Returns:
            bool: True si debe procesarse, False si debe saltarse
        """
        estado = self.get_cuenta_estado(idcuenta)
        
        if estado is None:
            # Primera vez, debe importarse (se creará como PENDIENTE)
            self.logger.info(f"Cuenta {idcuenta}: Primera vez, se importará como PENDIENTE")
            return True
        
        if estado == EstadoCuenta.PENDIENTE:
            # Está pendiente, debe procesarse
            self.logger.info(f"Cuenta {idcuenta}: Estado PENDIENTE, se procesará")
            return True
        
        if estado == EstadoCuenta.FALLIDO:
            # Falló anteriormente, dar otra oportunidad
            self.logger.info(f"Cuenta {idcuenta}: Estado FALLIDO, se reintentará")
            return True
        
        if estado == EstadoCuenta.EN_PROCESO:
            # Ya está en proceso, no tocar (evitar duplicados)
            self.logger.info(f"Cuenta {idcuenta}: Estado EN_PROCESO, se saltará para evitar duplicados")
            return False
        
        if estado == EstadoCuenta.COMPLETADO:
            # Ya está completada, saltar
            self.logger.info(f"Cuenta {idcuenta}: Estado COMPLETADO, se saltará")
            return False
        
        # Caso por defecto, procesar
        self.logger.info(f"Cuenta {idcuenta}: Estado desconocido ({estado}), se procesará por defecto")
        return True
    
    # EN LA CLASE DatabaseManagerGlosas (database/db_manager_glosas.py)
    # REEMPLAZAR EL MÉTODO create_or_update_cuenta POR ESTE:
    
    def create_or_update_cuenta(self, cuenta_data: dict) -> int:
        """
        Crea o actualiza una cuenta en la base de datos.
        MODIFICADO: Ahora crea/actualiza como PENDIENTE en lugar de EN_PROCESO
        
        Args:
            cuenta_data (dict): Datos de la cuenta extraídos de la tabla web
            
        Returns:
            int: ID de la cuenta en la base de datos
        """
        try:
            with self.get_connection() as conn:
                # Verificar si existe
                cursor = conn.execute("""
                    SELECT id, estado FROM cuenta_glosas_principal WHERE idcuenta = ?
                """, (cuenta_data['idcuenta'],))
                
                existing_row = cursor.fetchone()
                
                if existing_row:
                    # Actualizar existente SOLO si NO está completada
                    cuenta_id = existing_row['id']
                    estado_actual = existing_row['estado']
                    
                    if estado_actual != 'COMPLETADO':
                        conn.execute("""
                            UPDATE cuenta_glosas_principal 
                            SET numero_radicacion = ?, fecha_radicacion = ?, proveedor = ?,
                                numero_factura = ?, fecha_factura = ?, valor_factura = ?,
                                valor_glosado = ?, estado = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (
                            cuenta_data.get('numero_radicacion', ''),
                            cuenta_data.get('fecha_radicacion', ''),
                            cuenta_data.get('proveedor', ''),
                            cuenta_data.get('numero_factura', ''),
                            cuenta_data.get('fecha_factura', ''),
                            cuenta_data.get('valor_factura', 0.0),
                            cuenta_data.get('valor_glosado', 0.0),
                            EstadoCuenta.PENDIENTE.value,  # ✅ CAMBIO: PENDIENTE en lugar de EN_PROCESO
                            cuenta_id
                        ))
                        
                        self.logger.info(f"Cuenta {cuenta_data['idcuenta']} actualizada como PENDIENTE")
                    else:
                        self.logger.info(f"Cuenta {cuenta_data['idcuenta']} ya está COMPLETADA, no se actualiza")
                    
                else:
                    # Crear nueva como PENDIENTE
                    cursor = conn.execute("""
                        INSERT INTO cuenta_glosas_principal 
                        (idcuenta, numero_radicacion, fecha_radicacion, proveedor,
                         numero_factura, fecha_factura, valor_factura, valor_glosado,
                         estado, intentos)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        cuenta_data['idcuenta'],
                        cuenta_data.get('numero_radicacion', ''),
                        cuenta_data.get('fecha_radicacion', ''),
                        cuenta_data.get('proveedor', ''),
                        cuenta_data.get('numero_factura', ''),
                        cuenta_data.get('fecha_factura', ''),
                        cuenta_data.get('valor_factura', 0.0),
                        cuenta_data.get('valor_glosado', 0.0),
                        EstadoCuenta.PENDIENTE.value,  # ✅ CAMBIO: PENDIENTE en lugar de EN_PROCESO
                    ))
                    
                    cuenta_id = cursor.lastrowid
                    self.logger.info(f"Cuenta {cuenta_data['idcuenta']} creada como PENDIENTE con ID {cuenta_id}")
                
                conn.commit()
                return cuenta_id
                
        except sqlite3.Error as e:
            self.logger.error(f"Error creando/actualizando cuenta: {e}")
            raise
        
    def save_glosa_item(self, cuenta_id: int, glosa_data: dict) -> int:
        """
        Guarda un item de glosa individual.
        
        Args:
            cuenta_id (int): ID de la cuenta principal
            glosa_data (dict): Datos de la glosa extraídos de la tabla web
            
        Returns:
            int: ID del item de glosa guardado
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO glosa_items_detalle 
                    (cuenta_principal_id, id_glosa, id_item, descripcion_item,
                     tipo, descripcion, justificacion, valor_glosado, estado_original,
                     es_procesable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cuenta_id,
                    glosa_data['id_glosa'],
                    glosa_data.get('id_item', ''),
                    glosa_data.get('descripcion_item', ''),
                    glosa_data.get('tipo', ''),
                    glosa_data.get('descripcion', ''),
                    glosa_data.get('justificacion', ''),
                    glosa_data.get('valor_glosado', 0.0),
                    glosa_data.get('estado_original', ''),
                    glosa_data.get('es_procesable', False)
                ))
                
                glosa_item_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"Glosa {glosa_data['id_glosa']} guardada con ID {glosa_item_id}")
                return glosa_item_id
                
        except sqlite3.Error as e:
            self.logger.error(f"Error guardando glosa item: {e}")
            raise
    
    def update_cuenta_estado(self, idcuenta: str, estado: EstadoCuenta, 
                           motivo_fallo: str = "", 
                           glosas_stats: dict = None) -> bool:
        """
        Actualiza el estado de una cuenta.
        
        Args:
            idcuenta (str): ID de la cuenta
            estado (EstadoCuenta): Nuevo estado
            motivo_fallo (str): Motivo del fallo si aplica
            glosas_stats (dict): Estadísticas de glosas procesadas
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            with self.get_connection() as conn:
                update_data = [estado.value, motivo_fallo]
                update_fields = "estado = ?, motivo_fallo = ?"
                
                if estado == EstadoCuenta.COMPLETADO:
                    update_fields += ", fecha_fin = ?"
                    update_data.append(datetime.now())
                
                if glosas_stats:
                    update_fields += ", glosas_encontradas = ?, glosas_tarifas = ?, glosas_procesadas = ?"
                    update_data.extend([
                        glosas_stats.get('encontradas', 0),
                        glosas_stats.get('tarifas', 0),
                        glosas_stats.get('procesadas', 0)
                    ])
                
                update_data.append(idcuenta)  # WHERE clause
                
                cursor = conn.execute(f"""
                    UPDATE cuenta_glosas_principal 
                    SET {update_fields}, updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, update_data)
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Estado de cuenta {idcuenta} actualizado a {estado.value}")
                    return True
                else:
                    self.logger.warning(f"No se encontró cuenta {idcuenta} para actualizar")
                    return False
                    
        except sqlite3.Error as e:
            self.logger.error(f"Error actualizando estado de cuenta: {e}")
            return False
    
    def get_cuentas_pendientes(self, limit: int = 100) -> List[CuentaGlosasPrincipal]:
        """
        Obtiene cuentas que están pendientes de procesar.
        
        Args:
            limit (int): Límite de cuentas a retornar
            
        Returns:
            List[CuentaGlosasPrincipal]: Lista de cuentas pendientes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM cuenta_glosas_principal 
                    WHERE estado IN ('PENDIENTE', 'FALLIDO')
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                cuentas = [CuentaGlosasPrincipal.from_dict(dict(row)) for row in rows]
                
                self.logger.info(f"Obtenidas {len(cuentas)} cuentas pendientes")
                return cuentas
                
        except sqlite3.Error as e:
            self.logger.error(f"Error obteniendo cuentas pendientes: {e}")
            return []
    
    def crear_cuenta_glosa_pausa(self, idcuenta, proveedor, valor_glosado, fecha_radicacion, **kwargs):
        print(f"⚠️ [DEBUG] crear_cuenta_glosa_pausa llamado para idcuenta={idcuenta}")  # <-- Depuración
        self.logger.info(f"⚠️ [DEBUG] creando cuenta EN PAUSA {idcuenta} como FALLIDO")
       
        """
        Crea una cuenta glosa para EN PAUSA con estado FALLIDO por defecto.
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO cuenta_glosas_principal 
                (idcuenta, proveedor, estado, valor_glosado, fecha_radicacion)
                VALUES (?, ?, ?, ?, ?)
            """, (
                idcuenta,
                proveedor,
                "FALLIDO",  # Estado fijo para EN PAUSA
                valor_glosado,
                fecha_radicacion
            ))
            conn.commit()