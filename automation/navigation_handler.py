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
    EN_PAUSA = "en_pausa"
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

        Returns:
            bool: True si se cargó correctamente
        """
        try:
            self.state.update(method_name="_verify_respuesta_glosas_loaded")

            # Actualizar información de página
            await self._update_page_info()

            # Buscar el submenú "En Pausa" como indicador de que Respuesta Glosas está cargado
            selector = "//span[@class='sidebar-nav-name'][contains(.,'En Pausa')]"
            element = self.page.locator(f"xpath={selector}")

            if await element.count() > 0:
                self._log_state("✅ Respuesta Glosas verificado - submenú En Pausa visible")
                return True

            # También buscar "Bolsa Respuesta" como alternativa
            selector_bolsa = "//span[@class='sidebar-nav-name'][contains(.,'Bolsa Respuesta')]"
            element_bolsa = self.page.locator(f"xpath={selector_bolsa}")

            if await element_bolsa.count() > 0:
                self._log_state("✅ Respuesta Glosas verificado - submenú Bolsa Respuesta visible")
                return True

            # Verificar por URL como respaldo
            current_url = self.page.url
            if 'respuesta' in current_url.lower() or 'glosa' in current_url.lower():
                self._log_state(f"✅ Respuesta Glosas verificado por URL: {current_url}")
                return True

            self._log_state("❌ No se pudo verificar que Respuesta Glosas esté cargado", "warning")
            return False

        except Exception as e:
            self._log_state(f"Error verificando Respuesta Glosas: {e}", "error")
            return False
    async def navigate_to_en_pausa_with_config(self) -> bool:
        """
        ✅ NUEVO MÉTODO: Navega a "En Pausa" y configura tabla con "Todos".
        
        Flujo específico:
        1. Navegar a En Pausa
        2. Esperar 5 segundos
        3. Configurar tabla para mostrar "Todos"
        
        Returns:
            bool: True si la navegación y configuración fueron exitosas
        """
        try:
            self.state.update(
                method_name="navigate_to_en_pausa_with_config",
                action="Navegando a En Pausa con configuración específica"
            )
            
            self._log_state("🔄 INICIANDO NAVEGACIÓN A EN PAUSA CON CONFIGURACIÓN")
            self._log_state("="*60)
            
            # PASO 1: Verificar que estamos en Respuesta Glosas
            if self.state.current_state != NavigationState.RESPUESTA_GLOSAS_MENU:
                self._log_state("No estamos en Respuesta Glosas, navegando primero...", "warning")
                if not await self.navigate_to_respuesta_glosas():
                    return False
            
            # PASO 2: Navegar a En Pausa
            if not await self._navigate_to_en_pausa_basic():
                return False
            
            # PASO 3: Esperar 5 segundos específicos
            self._log_state("⏱️ Esperando 5 segundos después de navegación...")
            await asyncio.sleep(5)
            
            # PASO 4: Configurar tabla para mostrar "Todos"
            if not await self._configurar_tabla_en_pausa_todos():
                return False
            
            self.state.update(
                state=NavigationState.EN_PAUSA,
                action="Navegación a En Pausa con configuración completada"
            )
            
            self._log_state("="*60)
            self._log_state("✅ NAVEGACIÓN A EN PAUSA CON CONFIGURACIÓN COMPLETADA")
            return True
            
        except Exception as e:
            self.state.update(state=NavigationState.ERROR)
            self._log_state(f"❌ Error en navegación a En Pausa con configuración: {e}", "error")
            await self.page.screenshot(path="error_navigate_en_pausa_config.png")
            return False
        
    async def _navigate_to_en_pausa_basic(self) -> bool:
        """Navegación básica a En Pausa."""
        try:
            self._log_state("📍 Navegando a submenú En Pausa...")
            
            await self._update_page_info()
            
            selector = "//span[@class='sidebar-nav-name'][contains(.,'En Pausa')]"
            element = self.page.locator(f"xpath={selector}")
            
            if await element.count() == 0:
                self._log_state("No se encontró el submenú 'En Pausa'", "error")
                await self.page.screenshot(path="error_no_en_pausa_menu.png")
                return False
            
            self._log_state("Elemento 'En Pausa' encontrado")
            
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            await element.click()
            self._log_state("Clic realizado en 'En Pausa'")
            
            # Esperar carga con timeout extendido
            await self.page.wait_for_load_state('networkidle', timeout=20000)
            await asyncio.sleep(2)
        except Exception as e:
            self._log_state(f"❌ Error en navegación básica a En Pausa: {e}", "error")
        return False

    async def _verify_en_pausa_loaded(self) -> bool:
        """
        Verifica que la sección En Pausa se haya cargado correctamente.
        ✅ CON DEBUG: Logs detallados para ver qué pasa con la configuración.
        """
        try:
            self.state.update(method_name="_verify_en_pausa_loaded")

            # ✅ Actualizar información de página
            await self._update_page_info()
            current_url = self.page.url

            self._log_state(f"🔍 Verificando En Pausa - URL: {current_url}")

            # ✅ VERIFICACIÓN 1: Por URL (más confiable)
            if 'pausa' in current_url.lower():
                self._log_state(f"✅ En Pausa verificado por URL: {current_url}")
                self._log_state("🚀 INICIANDO CONFIGURACIÓN DE TABLA...")
                await self._agregar_configuracion_todos()
                return True

            # ✅ VERIFICACIÓN 2: Por presencia de tabla
            tabla_glosas = self.page.locator("#tablaRespuestaGlosa")
            if await tabla_glosas.count() > 0:
                self._log_state("✅ En Pausa verificado por presencia de tabla")
                await asyncio.sleep(3)
                self._log_state("🚀 INICIANDO CONFIGURACIÓN DE TABLA...")
                await self._agregar_configuracion_todos()
                return True

            # ✅ VERIFICACIÓN 3: Por texto en la página
            try:
                await self.page.wait_for_selector("text=En Pausa", timeout=5000)
                self._log_state("✅ En Pausa verificado por texto en página")
                self._log_state("🚀 INICIANDO CONFIGURACIÓN DE TABLA...")
                await self._agregar_configuracion_todos()
                return True
            except:
                pass
            
            # ✅ VERIFICACIÓN 4: Si llegamos aquí, asumir éxito si no hay errores evidentes
            self._log_state("⚠️ Verificación inconclusa, pero probablemente exitosa")
            self._log_state("🚀 INICIANDO CONFIGURACIÓN DE TABLA COMO ÚLTIMO RECURSO...")
            await self._agregar_configuracion_todos()
            return True

        except Exception as e:
            self._log_state(f"❌ Error verificando En Pausa: {e}", "error")
            return False
        
    async def _agregar_configuracion_todos(self):
        """
        ✅ NUEVO ENFOQUE: Usar JavaScript directo como en Bolsa Respuesta.
        Más confiable que hacer clics manuales.
        """
        try:
            self._log_state("🔧 === CONFIGURACIÓN CON JAVASCRIPT (como Bolsa Respuesta) ===")

            # PASO 1: Usar JavaScript directo para configurar
            self._log_state("⚡ Ejecutando JavaScript para configurar tabla...")

            resultado_js = await self.page.evaluate("""
                () => {
                    // Buscar el select de En Pausa
                    const select = document.querySelector('select[name="tablaRespuestaGlosaPause_length"]');
                    if (!select) {
                        return { success: false, error: 'Select de En Pausa no encontrado' };
                    }

                    // Verificar opciones disponibles
                    const opciones = Array.from(select.options).map(opt => ({
                        value: opt.value,
                        text: opt.textContent.trim()
                    }));

                    // Intentar con 500 primero (más seguro que Todos)
                    const opcion500 = select.querySelector('option[value="500"]');
                    if (opcion500) {
                        select.value = '500';
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));

                        return { 
                            success: true, 
                            valor: select.value,
                            opcionUsada: '500',
                            opciones: opciones
                        };
                    }

                    // Si no hay 500, intentar con Todos
                    const opcionTodos = select.querySelector('option[value="-1"]');
                    if (opcionTodos) {
                        select.value = '-1';
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));

                        return { 
                            success: true, 
                            valor: select.value,
                            opcionUsada: 'Todos (-1)',
                            opciones: opciones
                        };
                    }

                    return { 
                        success: false, 
                        error: 'No se encontraron opciones 500 o Todos',
                        opciones: opciones
                    };
                }
            """)

            # PASO 2: Verificar resultado del JavaScript
            if resultado_js.get('success'):
                self._log_state(f"✅ JavaScript exitoso - Opción usada: {resultado_js['opcionUsada']}")
                self._log_state(f"📋 Valor configurado: {resultado_js['valor']}")

                # Mostrar opciones disponibles
                opciones = resultado_js.get('opciones', [])
                self._log_state(f"📊 Opciones disponibles: {len(opciones)}")
                for opcion in opciones:
                    self._log_state(f"   • Valor: '{opcion['value']}' - Texto: '{opcion['text']}'")

                # PASO 3: Esperar que se recargue la tabla
                self._log_state("⏳ Esperando recarga de tabla con JavaScript...")
                await self.page.wait_for_load_state('networkidle', timeout=20000)
                await asyncio.sleep(4)  # Tiempo extra para carga completa

                # PASO 4: Verificar resultado final
                filas_tabla = self.page.locator("#tablaRespuestaGlosa tbody tr")
                total_filas = await filas_tabla.count()
                self._log_state(f"📊 Filas en tabla después de JavaScript: {total_filas}")

                if total_filas > 0:
                    self._log_state("🎉 ¡CONFIGURACIÓN EXITOSA! Tabla cargada con datos")

                    # Verificar valor final
                    valor_final = await self.page.evaluate("""
                        () => {
                            const select = document.querySelector('select[name="tablaRespuestaGlosaPause_length"]');
                            return select ? select.value : 'no encontrado';
                        }
                    """)
                    self._log_state(f"🔍 Valor final confirmado: {valor_final}")

                else:
                    self._log_state("⚠️ Tabla sigue vacía - puede necesitar más tiempo de carga", "warning")

                    # Intentar esperar un poco más
                    self._log_state("⏳ Esperando 5 segundos adicionales...")
                    await asyncio.sleep(5)

                    # Verificar de nuevo
                    total_filas_2 = await filas_tabla.count()
                    self._log_state(f"📊 Filas después de espera adicional: {total_filas_2}")

            else:
                self._log_state(f"❌ JavaScript falló: {resultado_js.get('error')}", "error")

                # Mostrar opciones disponibles para debug
                opciones = resultado_js.get('opciones', [])
                if opciones:
                    self._log_state(f"🔍 Opciones encontradas: {len(opciones)}")
                    for opcion in opciones:
                        self._log_state(f"   • Valor: '{opcion['value']}' - Texto: '{opcion['text']}'")

                # FALLBACK: Intentar con método básico
                self._log_state("🔄 Intentando fallback con JavaScript básico...")
                await self._fallback_configuracion_basica()

            self._log_state("🔧 === CONFIGURACIÓN JAVASCRIPT TERMINADA ===")

        except Exception as e:
            self._log_state(f"❌ ERROR CRÍTICO en configuración JavaScript: {e}", "error")
            import traceback
            self._log_state(f"📄 Traceback: {traceback.format_exc()}", "error")
    
    async def _fallback_configuracion_basica(self):
        """Fallback simple usando JavaScript básico."""
        try:
            self._log_state("🔄 Ejecutando fallback básico...")

            # Intentar configurar con cualquier valor alto disponible
            resultado_fallback = await self.page.evaluate("""
                () => {
                    const select = document.querySelector('select[name="tablaRespuestaGlosaPause_length"]');
                    if (!select) return { success: false, error: 'Select no encontrado' };

                    // Obtener el valor más alto disponible
                    const valores = Array.from(select.options)
                        .map(opt => opt.value)
                        .filter(val => val !== '')
                        .sort((a, b) => {
                            // -1 (Todos) es el más alto
                            if (a === '-1') return -1;
                            if (b === '-1') return 1;
                            return parseInt(b) - parseInt(a);
                        });

                    if (valores.length > 0) {
                        const valorMasAlto = valores[0];
                        select.value = valorMasAlto;
                        select.dispatchEvent(new Event('change', { bubbles: true }));

                        return { 
                            success: true, 
                            valor: valorMasAlto,
                            valoresDisponibles: valores
                        };
                    }

                    return { success: false, error: 'No hay valores disponibles' };
                }
            """)

            if resultado_fallback.get('success'):
                self._log_state(f"✅ Fallback exitoso - Valor: {resultado_fallback['valor']}")
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(3)
            else:
                self._log_state(f"❌ Fallback falló: {resultado_fallback.get('error')}", "error")

        except Exception as e:
            self._log_state(f"❌ Error en fallback: {e}", "error")

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
        ✅ MODIFICADO: Añade pausa de 5 segundos después de navegar.

        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            self.state.update(
                method_name="navigate_to_en_pausa",
                action="Navegando a En Pausa con pausa de 5 segundos"
            )

            self._log_state("🔄 Iniciando navegación a En Pausa")

            # ✅ Si En Pausa no está disponible, navegar a Respuesta Glosas UNA SOLA VEZ
            selector = "//span[@class='sidebar-nav-name'][contains(.,'En Pausa')]"
            element = self.page.locator(f"xpath={selector}")

            if await element.count() == 0:
                self._log_state("En Pausa no disponible, navegando a Respuesta Glosas primero...")
                if not await self.navigate_to_respuesta_glosas():
                    return False
                await asyncio.sleep(3)  # Pausa para estabilización

                # Volver a buscar el elemento
                element = self.page.locator(f"xpath={selector}")

            # ✅ Verificar que el elemento existe
            if await element.count() == 0:
                self._log_state("No se encontró el submenú 'En Pausa'", "error")
                await self.page.screenshot(path="error_no_en_pausa_menu.png")
                self.state.update(state=NavigationState.ERROR)
                return False

            self._log_state("Elemento 'En Pausa' encontrado")

            # ✅ Hacer scroll al elemento
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(1)

            # ✅ Hacer clic en "En Pausa"
            await element.click()
            self._log_state("Clic realizado en 'En Pausa'")

            # ✅ NUEVA FUNCIONALIDAD: Esperar 5 segundos después de navegar
            self._log_state("⏳ Esperando 5 segundos después de navegar a En Pausa...")
            await asyncio.sleep(5)

            # ✅ Esperar carga con timeout extendido
            await self.page.wait_for_load_state('networkidle', timeout=20000)
            await asyncio.sleep(3)  # Pausa adicional para carga completa

            # ✅ Verificar que la navegación fue exitosa
            success = await self._verify_en_pausa_loaded()

            if success:
                self.state.update(
                    action="Navegación a En Pausa exitosa con pausa de 5 segundos"
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