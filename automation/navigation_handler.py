import asyncio
import logging
from typing import Optional
from playwright.async_api import Page
from dataclasses import dataclass
from enum import Enum

class NavigationState(Enum):
    """Estados de navegación en CTA Médicas."""
    LOGIN_PAGE = "login_page"
    DASHBOARD = "dashboard"
    RESPUESTA_GLOSAS_MENU = "respuesta_glosas_menu"
    BOLSA_RESPUESTA = "bolsa_respuesta"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class AutomationState:
    """Estado actual de la automatización."""
    current_state: NavigationState = NavigationState.UNKNOWN
    current_class: str = ""
    current_method: str = ""
    page_url: str = ""
    page_title: str = ""
    last_action: str = ""
    
    def update(self, state: NavigationState = None, class_name: str = "", 
               method_name: str = "", action: str = ""):
        """Actualiza el estado actual."""
        if state:
            self.current_state = state
        if class_name:
            self.current_class = class_name
        if method_name:
            self.current_method = method_name
        if action:
            self.last_action = action

class NavigationHandler:
    """
    Maneja la navegación específica en el sistema CTA Médicas.
    Controla el flujo entre menús y secciones del sistema.
    Versión optimizada con selectores únicos.
    """
    
    def __init__(self, page: Page, automation_state: AutomationState):
        """
        Inicializa el manejador de navegación.
        
        Args:
            page (Page): Página de Playwright
            automation_state (AutomationState): Estado compartido de la automatización
        """
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        
        # Actualizar estado inicial
        self.state.update(
            state=NavigationState.DASHBOARD,
            class_name="NavigationHandler",
            method_name="__init__"
        )
        
        self._log_state("NavigationHandler inicializado")
    
    def _log_state(self, message: str, level: str = "info"):
        """
        Log con información de estado actual.
        
        Args:
            message (str): Mensaje a logear
            level (str): Nivel de log (info, warning, error)
        """
        state_info = f"[{self.state.current_class}.{self.state.current_method}] [{self.state.current_state.value}]"
        full_message = f"{state_info} {message}"
        
        if level == "info":
            self.logger.info(full_message)
        elif level == "warning":
            self.logger.warning(full_message)
        elif level == "error":
            self.logger.error(full_message)
    
    async def navigate_to_respuesta_glosas(self) -> bool:
        """
        Navega al menú 'Respuesta Glosas'.
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            self.state.update(
                method_name="navigate_to_respuesta_glosas",
                action="Navegando a Respuesta Glosas"
            )
            
            self._log_state("Iniciando navegación a Respuesta Glosas")
            
            # Actualizar información de página actual
            await self._update_page_info()
            
            # USAR SOLO EL SELECTOR QUE FUNCIONA - XPath específico
            selector = "//span[@class='sidebar-nav-name'][contains(.,'Respuesta Glosas')]"
            
            # Buscar el elemento
            element = self.page.locator(f"xpath={selector}")
            
            # Verificar que existe
            if await element.count() == 0:
                self._log_state("No se encontró el menú 'Respuesta Glosas'", "error")
                await self.page.screenshot(path="error_no_respuesta_glosas_menu.png")
                self.state.update(state=NavigationState.ERROR)
                return False
            
            self._log_state("Elemento 'Respuesta Glosas' encontrado")
            
            # Hacer scroll al elemento si es necesario
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # Hacer clic en "Respuesta Glosas"
            await element.click()
            self._log_state("Clic realizado en 'Respuesta Glosas'")
            
            # Esperar a que cargue
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(1)
            
            # Verificar que la navegación fue exitosa
            success = await self._verify_respuesta_glosas_loaded()
            
            if success:
                self.state.update(
                    state=NavigationState.RESPUESTA_GLOSAS_MENU,
                    action="Navegación a Respuesta Glosas exitosa"
                )
                self._log_state("Navegación a Respuesta Glosas completada exitosamente")
                return True
            else:
                self.state.update(state=NavigationState.ERROR)
                self._log_state("Falló la verificación de navegación a Respuesta Glosas", "error")
                return False
                
        except Exception as e:
            self.state.update(state=NavigationState.ERROR)
            self._log_state(f"Error navegando a Respuesta Glosas: {e}", "error")
            await self.page.screenshot(path="error_navigate_respuesta_glosas.png")
            return False
    
    async def navigate_to_bolsa_respuesta(self) -> bool:
        """
        Navega al submenú 'Bolsa Respuesta' (debe estar en Respuesta Glosas primero).
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            self.state.update(
                method_name="navigate_to_bolsa_respuesta",
                action="Navegando a Bolsa Respuesta"
            )
            
            self._log_state("Iniciando navegación a Bolsa Respuesta")
            
            # Verificar que estamos en el estado correcto
            if self.state.current_state != NavigationState.RESPUESTA_GLOSAS_MENU:
                self._log_state("No estamos en Respuesta Glosas, navegando primero...", "warning")
                if not await self.navigate_to_respuesta_glosas():
                    return False
            
            # Actualizar información de página actual
            await self._update_page_info()
            
            # USAR SOLO EL SELECTOR QUE FUNCIONA - XPath específico
            selector = "//span[@class='sidebar-nav-name'][contains(.,'Bolsa Respuesta')]"
            
            # Buscar el elemento
            element = self.page.locator(f"xpath={selector}")
            
            # Verificar que existe
            if await element.count() == 0:
                self._log_state("No se encontró el submenú 'Bolsa Respuesta'", "error")
                await self.page.screenshot(path="error_no_bolsa_respuesta_menu.png")
                self.state.update(state=NavigationState.ERROR)
                return False
            
            self._log_state("Elemento 'Bolsa Respuesta' encontrado")
            
            # Hacer scroll al elemento si es necesario
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # Hacer clic en "Bolsa Respuesta"
            await element.click()
            self._log_state("Clic realizado en 'Bolsa Respuesta'")
            
            # Esperar a que cargue
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)
            
            # Verificar que la navegación fue exitosa
            success = await self._verify_bolsa_respuesta_loaded()
            
            if success:
                self.state.update(
                    state=NavigationState.BOLSA_RESPUESTA,
                    action="Navegación a Bolsa Respuesta exitosa"
                )
                self._log_state("Navegación a Bolsa Respuesta completada exitosamente")
                return True
            else:
                self.state.update(state=NavigationState.ERROR)
                self._log_state("Falló la verificación de navegación a Bolsa Respuesta", "error")
                return False
                
        except Exception as e:
            self.state.update(state=NavigationState.ERROR)
            self._log_state(f"Error navegando a Bolsa Respuesta: {e}", "error")
            await self.page.screenshot(path="error_navigate_bolsa_respuesta.png")
            return False
    
    async def _verify_respuesta_glosas_loaded(self) -> bool:
        """
        Verifica que la sección Respuesta Glosas se haya cargado correctamente.
        Versión optimizada con selector único.
        
        Returns:
            bool: True si se cargó correctamente
        """
        try:
            self.state.update(method_name="_verify_respuesta_glosas_loaded")
            
            # Actualizar información de página
            await self._update_page_info()
            
            # USAR SOLO EL SELECTOR QUE FUNCIONA
            # El indicador principal es que aparezca el submenú "Bolsa Respuesta"
            selector = "//span[@class='sidebar-nav-name'][contains(.,'Bolsa Respuesta')]"
            element = self.page.locator(f"xpath={selector}")
            
            if await element.count() > 0:
                self._log_state("✅ Respuesta Glosas verificado - submenú visible")
                return True
            
            # Si el selector principal falla, verificar URL como respaldo
            current_url = self.page.url
            if 'respuesta' in current_url.lower() or 'glosa' in current_url.lower():
                self._log_state(f"✅ Respuesta Glosas verificado por URL: {current_url}")
                return True
            
            self._log_state("❌ No se pudo verificar que Respuesta Glosas esté cargado", "warning")
            return False
            
        except Exception as e:
            self._log_state(f"Error verificando Respuesta Glosas: {e}", "error")
            return False
    
    async def _verify_bolsa_respuesta_loaded(self) -> bool:
        """
        Verifica que la sección Bolsa Respuesta se haya cargado correctamente.
        Versión optimizada con selector único.
        
        Returns:
            bool: True si se cargó correctamente
        """
        try:
            self.state.update(method_name="_verify_bolsa_respuesta_loaded")
            
            # Actualizar información de página
            await self._update_page_info()
            
            # USAR SOLO EL SELECTOR QUE FUNCIONA MEJOR
            # El texto "Bolsa Respuesta" es el indicador más confiable
            selector = "text=Bolsa Respuesta"
            element = self.page.locator(selector)
            
            if await element.count() > 0:
                self._log_state("✅ Bolsa Respuesta verificado con text selector")
                return True
            
            # Si el selector principal falla, verificar URL como respaldo
            current_url = self.page.url
            if 'bolsa' in current_url.lower() or 'respuesta' in current_url.lower():
                self._log_state(f"✅ Bolsa Respuesta verificado por URL: {current_url}")
                return True
            
            self._log_state("❌ No se pudo verificar que Bolsa Respuesta esté cargado", "warning")
            return False
            
        except Exception as e:
            self._log_state(f"Error verificando Bolsa Respuesta: {e}", "error")
            return False
    
    async def _update_page_info(self):
        """Actualiza la información actual de la página en el estado."""
        try:
            self.state.page_url = self.page.url
            self.state.page_title = await self.page.title()
        except Exception as e:
            self._log_state(f"Error actualizando info de página: {e}", "warning")
    
    async def get_current_page_info(self) -> dict:
        """
        Obtiene información detallada de la página actual.
        
        Returns:
            dict: Información de la página actual
        """
        try:
            self.state.update(method_name="get_current_page_info")
            
            await self._update_page_info()
            
            info = {
                "url": self.state.page_url,
                "title": self.state.page_title,
                "state": self.state.current_state.value,
                "last_action": self.state.last_action
            }
            
            self._log_state(f"Info de página actual: {info}")
            return info
            
        except Exception as e:
            self._log_state(f"Error obteniendo info de página: {e}", "error")
            return {}
    
    async def wait_for_page_ready(self, timeout: int = 10000):
        """
        Espera a que la página esté completamente cargada.
        
        Args:
            timeout (int): Timeout en milisegundos
        """
        try:
            self.state.update(method_name="wait_for_page_ready")
            self._log_state(f"Esperando que la página esté lista (timeout: {timeout}ms)")
            
            await self.page.wait_for_load_state('networkidle', timeout=timeout)
            await asyncio.sleep(1)  # Pausa adicional para JavaScript
            
            self._log_state("Página lista")
            
        except Exception as e:
            self._log_state(f"Timeout esperando página: {e}", "warning")
    async def navigate_to_en_pausa(self) -> bool:
        """
        Navega al submenú 'En Pausa' (debe estar en Respuesta Glosas primero).
        NUEVO: Específico para el módulo de reprocesamiento.

        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            self.state.update(
                method_name="navigate_to_en_pausa",
                action="Navegando a En Pausa"
            )

            self._log_state("Iniciando navegación a En Pausa")

            # Verificar que estamos en el estado correcto
            if self.state.current_state != NavigationState.RESPUESTA_GLOSAS_MENU:
                self._log_state("No estamos en Respuesta Glosas, navegando primero...", "warning")
                if not await self.navigate_to_respuesta_glosas():
                    return False

            # Actualizar información de página actual
            await self._update_page_info()

            # Selector específico para En Pausa
            selector = "//span[@class='sidebar-nav-name'][contains(.,'En Pausa')]"

            # Buscar el elemento
            element = self.page.locator(f"xpath={selector}")

            # Verificar que existe
            if await element.count() == 0:
                self._log_state("No se encontró el submenú 'En Pausa'", "error")
                await self.page.screenshot(path="error_no_en_pausa_menu.png")
                self.state.update(state=NavigationState.ERROR)
                return False

            self._log_state("Elemento 'En Pausa' encontrado")

            # Hacer scroll al elemento si es necesario
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

            # Hacer clic en "En Pausa"
            await element.click()
            self._log_state("Clic realizado en 'En Pausa'")

            # Esperar a que cargue
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)

            # Verificar que la navegación fue exitosa
            success = await self._verify_en_pausa_loaded()

            if success:
                self.state.update(
                    action="Navegación a En Pausa exitosa"
                )
                self._log_state("Navegación a En Pausa completada exitosamente")
                return True
            else:
                self.state.update(state=NavigationState.ERROR)
                self._log_state("Falló la verificación de navegación a En Pausa", "error")
                return False

        except Exception as e:
            self.state.update(state=NavigationState.ERROR)
            self._log_state(f"Error navegando a En Pausa: {e}", "error")
            await self.page.screenshot(path="error_navigate_en_pausa.png")
            return False
    
    async def _verify_en_pausa_loaded(self) -> bool:
        """
        Verifica que la sección En Pausa se haya cargado correctamente.
        
        Returns:
            bool: True si se cargó correctamente
        """
        try:
            self.state.update(method_name="_verify_en_pausa_loaded")
            
            # Actualizar información de página
            await self._update_page_info()
            
            # Verificar por URL
            current_url = self.page.url
            if 'pausa' in current_url.lower():
                self._log_state(f"✅ En Pausa verificado por URL: {current_url}")
                return True
            
            # Verificar por texto en la página
            texto_elemento = self.page.locator("text=En Pausa")
            if await texto_elemento.count() > 0:
                self._log_state("✅ En Pausa verificado por texto en página")
                return True
            
            # Verificar por tabla de glosas (mismo ID que Bolsa Respuesta)
            tabla_glosas = self.page.locator("#tablaRespuestaGlosa")
            if await tabla_glosas.count() > 0:
                self._log_state("✅ En Pausa verificado por presencia de tabla")
                return True
            
            self._log_state("❌ No se pudo verificar que En Pausa esté cargado", "warning")
            return False
            
        except Exception as e:
            self._log_state(f"Error verificando En Pausa: {e}", "error")
            return False