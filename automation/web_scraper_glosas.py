import asyncio
import logging
from typing import Optional
from playwright.async_api import Page
from automation.login_handler import LoginHandler
from automation.navigation_handler import NavigationHandler, AutomationState, NavigationState
from automation.glosas_table_processor import GlosasTableProcessor
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from config.settings import Settings

class WebScraperGlosas:
    """
    Automatizador específico para gestión de glosas.
    Extiende la funcionalidad base con lógica específica de glosas.
    """
    
    def __init__(self):
        """Inicializa el web scraper de glosas."""
        self.logger = logging.getLogger(__name__)
        self.login_handler = LoginHandler()
        self.navigation_handler: Optional[NavigationHandler] = None
        self.glosas_processor: Optional[GlosasTableProcessor] = None
        self.page: Optional[Page] = None
        
        # Base de datos específica para glosas
        self.db_manager = DatabaseManagerGlosas()
        self.db_manager.create_glosas_tables()  # Crear tablas si no existen
        
        # Estado compartido de la automatización
        self.automation_state = AutomationState(
            current_class="WebScraperGlosas",
            current_method="__init__"
        )
        
        self._log_state("WebScraperGlosas inicializado")
        
    def _log_state(self, message: str, level: str = "info"):
        """Log con información de estado actual."""
        state_info = f"[{self.automation_state.current_class}.{self.automation_state.current_method}] [{self.automation_state.current_state.value}]"
        full_message = f"{state_info} {message}"
        
        if level == "info":
            self.logger.info(full_message)
        elif level == "warning":
            self.logger.warning(full_message)
        elif level == "error":
            self.logger.error(full_message)
        
    async def start_glosas_automation(self, username: str, password: str) -> bool:
        """
        Inicia la automatización completa de glosas.
        
        Args:
            username (str): Usuario para login
            password (str): Contraseña para login
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="start_glosas_automation",
                action="Iniciando automatización de glosas"
            )
            
            self._log_state("=== INICIANDO AUTOMATIZACIÓN DE GLOSAS ===")
            
            # PASO 1: LOGIN
            if not await self._do_login(username, password):
                return False
            
            # PASO 2: NAVEGACIÓN A BOLSA RESPUESTA
            if not await self._navigate_to_bolsa_respuesta():
                return False
            
            # PASO 3: PROCESAMIENTO DE TABLA PRINCIPAL
            if not await self._process_main_table():
                return False
            
            self._log_state("=== AUTOMATIZACIÓN DE GLOSAS COMPLETADA ===")
            return True
            
        except Exception as e:
            self.automation_state.update(state=NavigationState.ERROR)
            self._log_state(f"Error en automatización de glosas: {e}", "error")
            return False
        finally:
            # Mantener navegador abierto para inspección
            await self._keep_open_for_inspection()
    
    async def _do_login(self, username: str, password: str) -> bool:
        """Realiza el proceso de login."""
        try:
            self.automation_state.update(
                method_name="_do_login",
                state=NavigationState.LOGIN_PAGE,
                action="Realizando login"
            )
            
            self._log_state("Iniciando proceso de login")
            
            login_success = await self.login_handler.login(username, password)
            
            if login_success:
                self.page = self.login_handler.page
                self.automation_state.update(
                    state=NavigationState.DASHBOARD,
                    action="Login exitoso"
                )
                self._log_state("Login completado exitosamente")
                return True
            else:
                self.automation_state.update(state=NavigationState.ERROR)
                self._log_state("Login falló", "error")
                return False
                
        except Exception as e:
            self.automation_state.update(state=NavigationState.ERROR)
            self._log_state(f"Error en login: {e}", "error")
            return False
    
    async def _navigate_to_bolsa_respuesta(self) -> bool:
        """Navega hasta la tabla de Bolsa Respuesta."""
        try:
            self.automation_state.update(
                method_name="_navigate_to_bolsa_respuesta",
                action="Navegando a Bolsa Respuesta"
            )
            
            self._log_state("Iniciando navegación a Bolsa Respuesta")
            
            # Inicializar manejador de navegación
            self.navigation_handler = NavigationHandler(self.page, self.automation_state)
            
            # Navegar a Respuesta Glosas
            if not await self.navigation_handler.navigate_to_respuesta_glosas():
                self._log_state("Error navegando a Respuesta Glosas", "error")
                return False
            
            # Navegar a Bolsa Respuesta
            if not await self.navigation_handler.navigate_to_bolsa_respuesta():
                self._log_state("Error navegando a Bolsa Respuesta", "error")
                return False
            
            self._log_state("Navegación a Bolsa Respuesta completada")
            return True
            
        except Exception as e:
            self._log_state(f"Error en navegación: {e}", "error")
            return False
    
    async def _process_main_table(self) -> bool:
        """
        Procesa la tabla principal de Bolsa Respuesta.
        
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            self.automation_state.update(
                method_name="_process_main_table",
                action="Procesando tabla principal de Bolsa Respuesta"
            )
            
            self._log_state("Iniciando procesamiento de tabla principal")
            
            # Inicializar procesador de tabla
            self.glosas_processor = GlosasTableProcessor(self.page, self.automation_state)
            
            # Procesar todas las filas
            procesadas, saltadas = await self.glosas_processor.process_table_rows()
            
            self._log_state(f"Tabla principal procesada - Procesadas: {procesadas}, Saltadas: {saltadas}")
            
            if procesadas == 0 and saltadas == 0:
                self._log_state("No se procesaron filas", "warning")
                return False
            
            return True
            
        except Exception as e:
            self._log_state(f"Error procesando tabla principal: {e}", "error")
            return False
    
    async def _keep_open_for_inspection(self):
        """Mantiene el navegador abierto para inspeccionar la página."""
        try:
            self.automation_state.update(
                method_name="_keep_open_for_inspection",
                action="Manteniendo navegador abierto para inspección"
            )
            
            self._log_state("Navegador abierto para inspección - Se cerrará en 60 segundos")
            
            # Obtener estado final
            if self.navigation_handler:
                final_info = await self.navigation_handler.get_current_page_info()
                self._log_state(f"Estado final: {final_info}")
            
            # Mostrar estadísticas finales
            await self._show_final_stats()
            
            # Mantener abierto por 1 minuto
            await asyncio.sleep(60)
            
            self._log_state("Cerrando navegador...")
            await self.login_handler.logout()
            
        except Exception as e:
            self._log_state(f"Error manteniendo navegador abierto: {e}", "error")
    
    async def _show_final_stats(self):
        """Muestra estadísticas finales del procesamiento."""
        try:
            # Obtener estadísticas de la base de datos
            stats = await self._get_processing_stats()
            
            self._log_state("=== ESTADÍSTICAS FINALES ===")
            self._log_state(f"Cuentas PENDIENTES: {stats['pendientes']}")
            self._log_state(f"Cuentas EN_PROCESO: {stats['en_proceso']}")
            self._log_state(f"Cuentas COMPLETADAS: {stats['completadas']}")
            self._log_state(f"Cuentas FALLIDAS: {stats['fallidas']}")
            self._log_state(f"Total de glosas procesadas: {stats['glosas_procesadas']}")
            self._log_state("============================")
            
        except Exception as e:
            self._log_state(f"Error obteniendo estadísticas: {e}", "error")
    
    async def _get_processing_stats(self) -> dict:
        """Obtiene estadísticas del procesamiento desde la BD."""
        try:
            with self.db_manager.get_connection() as conn:
                # Estadísticas de cuentas por estado
                cursor = conn.execute("""
                    SELECT estado, COUNT(*) as count 
                    FROM cuenta_glosas_principal 
                    GROUP BY estado
                """)
                
                stats = {
                    'pendientes': 0,
                    'en_proceso': 0,
                    'completadas': 0,
                    'fallidas': 0,
                    'glosas_procesadas': 0
                }
                
                for row in cursor.fetchall():
                    estado = row['estado'].lower()
                    count = row['count']
                    
                    if estado == 'pendiente':
                        stats['pendientes'] = count
                    elif estado == 'en_proceso':
                        stats['en_proceso'] = count
                    elif estado == 'completado':
                        stats['completadas'] = count
                    elif estado == 'fallido':
                        stats['fallidas'] = count
                
                # Total de glosas procesadas
                cursor = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM glosa_items_detalle 
                    WHERE fue_procesado = 1
                """)
                
                row = cursor.fetchone()
                if row:
                    stats['glosas_procesadas'] = row['count']
                
                return stats
                
        except Exception as e:
            self._log_state(f"Error obteniendo estadísticas de BD: {e}", "error")
            return {
                'pendientes': 0,
                'en_proceso': 0,
                'completadas': 0,
                'fallidas': 0,
                'glosas_procesadas': 0
            }

# EJEMPLO DE USO
async def main_glosas_example():
    """Ejemplo de uso del automatizador de glosas."""
    scraper = WebScraperGlosas()
    
    # Usar credenciales de configuración
    username = Settings.DEFAULT_USERNAME
    password = Settings.DEFAULT_PASSWORD
    
    success = await scraper.start_glosas_automation(username, password)
    
    if success:
        print("✅ Automatización de glosas completada exitosamente")
    else:
        print("❌ Error en automatización de glosas")

if __name__ == "__main__":
    asyncio.run(main_glosas_example())