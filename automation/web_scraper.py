import asyncio
import logging
from typing import Optional
from playwright.async_api import Page
from automation.login_handler import LoginHandler
from automation.navigation_handler import NavigationHandler, AutomationState, NavigationState
from config.settings import Settings

class WebScraper:
    """
    Automatiza tareas en CTA Médicas.
    Coordina login, navegación y procesamiento de datos.
    """
    
    def __init__(self):
        """Inicializa el web scraper."""
        self.logger = logging.getLogger(__name__)
        self.login_handler = LoginHandler()
        self.navigation_handler: Optional[NavigationHandler] = None
        self.page: Optional[Page] = None
        
        # Estado compartido de la automatización
        self.automation_state = AutomationState(
            current_class="WebScraper",
            current_method="__init__"
        )
        
        self._log_state("WebScraper inicializado")
        
    def _log_state(self, message: str, level: str = "info"):
        """
        Log con información de estado actual.
        
        Args:
            message (str): Mensaje a logear
            level (str): Nivel de log (info, warning, error)
        """
        state_info = f"[{self.automation_state.current_class}.{self.automation_state.current_method}] [{self.automation_state.current_state.value}]"
        full_message = f"{state_info} {message}"
        
        if level == "info":
            self.logger.info(full_message)
        elif level == "warning":
            self.logger.warning(full_message)
        elif level == "error":
            self.logger.error(full_message)
        
    async def start_automation(self, username: str, password: str) -> bool:
        """
        Inicia la automatización completa en CTA Médicas.
        
        Args:
            username (str): Usuario para login
            password (str): Contraseña para login
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="start_automation",
                action="Iniciando automatización completa"
            )
            
            self._log_state("Iniciando automatización en CTA Médicas")
            
            # 1. HACER LOGIN
            if not await self._do_login(username, password):
                return False
            
            # 2. INICIALIZAR NAVEGACIÓN
            if not await self._initialize_navigation():
                return False
            
            # 3. NAVEGAR A RESPUESTA GLOSAS
            if not await self._navigate_to_respuesta_glosas():
                return False
            
            # 4. NAVEGAR A BOLSA RESPUESTA
            if not await self._navigate_to_bolsa_respuesta():
                return False
            
            # 5. PROCESAR DATOS (futuro)
            await self._process_bolsa_respuesta_data()
            
            self._log_state("Automatización completada exitosamente")
            return True
            
        except Exception as e:
            self.automation_state.update(state=NavigationState.ERROR)
            self._log_state(f"Error en automatización: {e}", "error")
            return False
        finally:
            # Mantener navegador abierto para inspección
            await self._keep_open_for_inspection()
    
    async def _do_login(self, username: str, password: str) -> bool:
        """
        Realiza el proceso de login.
        
        Args:
            username (str): Usuario
            password (str): Contraseña
            
        Returns:
            bool: True si fue exitoso
        """
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
    
    async def _initialize_navigation(self) -> bool:
        """
        Inicializa el manejador de navegación.
        
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="_initialize_navigation",
                action="Inicializando navegación"
            )
            
            self._log_state("Inicializando manejador de navegación")
            
            if not self.page:
                self._log_state("No hay página disponible para navegación", "error")
                return False
            
            # Crear manejador de navegación con estado compartido
            self.navigation_handler = NavigationHandler(self.page, self.automation_state)
            
            self._log_state("Navegación inicializada correctamente")
            return True
            
        except Exception as e:
            self._log_state(f"Error inicializando navegación: {e}", "error")
            return False
    
    async def _navigate_to_respuesta_glosas(self) -> bool:
        """
        Navega al menú Respuesta Glosas.
        
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="_navigate_to_respuesta_glosas",
                action="Navegando a Respuesta Glosas"
            )
            
            self._log_state("Iniciando navegación a Respuesta Glosas")
            
            if not self.navigation_handler:
                self._log_state("NavigationHandler no está inicializado", "error")
                return False
            
            success = await self.navigation_handler.navigate_to_respuesta_glosas()
            
            if success:
                self._log_state("Navegación a Respuesta Glosas exitosa")
                return True
            else:
                self._log_state("Falló navegación a Respuesta Glosas", "error")
                return False
                
        except Exception as e:
            self._log_state(f"Error navegando a Respuesta Glosas: {e}", "error")
            return False
    
    async def _navigate_to_bolsa_respuesta(self) -> bool:
        """
        Navega al submenú Bolsa Respuesta.
        
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="_navigate_to_bolsa_respuesta",
                action="Navegando a Bolsa Respuesta"
            )
            
            self._log_state("Iniciando navegación a Bolsa Respuesta")
            
            if not self.navigation_handler:
                self._log_state("NavigationHandler no está inicializado", "error")
                return False
            
            success = await self.navigation_handler.navigate_to_bolsa_respuesta()
            
            if success:
                self._log_state("Navegación a Bolsa Respuesta exitosa")
                return True
            else:
                self._log_state("Falló navegación a Bolsa Respuesta", "error")
                return False
                
        except Exception as e:
            self._log_state(f"Error navegando a Bolsa Respuesta: {e}", "error")
            return False
    
    async def _process_bolsa_respuesta_data(self):
        """
        Procesa los datos en la página de Bolsa Respuesta.
        (Por implementar según necesidades específicas)
        """
        try:
            self.automation_state.update(
                method_name="_process_bolsa_respuesta_data",
                action="Procesando datos de Bolsa Respuesta"
            )
            
            self._log_state("Iniciando procesamiento de datos en Bolsa Respuesta")
            
            # Obtener información de página actual
            if self.navigation_handler:
                page_info = await self.navigation_handler.get_current_page_info()
                self._log_state(f"Información de página actual: {page_info}")
            
            # AQUÍ AGREGAR LÓGICA ESPECÍFICA DE PROCESAMIENTO
            # Por ejemplo:
            # - Buscar tabla de datos
            # - Extraer información específica
            # - Hacer clic en botones de acción
            # - Llenar formularios
            
            self._log_state("Procesamiento de datos completado (placeholder)")
            
        except Exception as e:
            self._log_state(f"Error procesando datos: {e}", "error")
    
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
            
            # Mantener abierto por 1 minuto
            await asyncio.sleep(60)
            
            self._log_state("Cerrando navegador...")
            await self.login_handler.logout()
            
        except Exception as e:
            self._log_state(f"Error manteniendo navegador abierto: {e}", "error")