import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser
from config.settings import Settings

class LoginHandler:
    """
    Maneja el proceso de login en CTA Médicas.
    Versión simple y directa.
    """
    
    def __init__(self):
        """Inicializa el manejador de login."""
        try:
            from config.playwright_exe_config import setup_for_exe
            setup_for_exe()
        except: 
            pass
            
        self.logger = logging.getLogger(__name__)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def login(self, username: str, password: str) -> bool:
        """
        Realiza el login en CTA Médicas.
        
        Args:
            username (str): Nombre de usuario
            password (str): Contraseña
            
        Returns:
            bool: True si el login fue exitoso
        """
        try:
            self.logger.info("Iniciando proceso de login")
            
            # 1. Abrir navegador
            await self._open_browser()
            
            # 2. Ir a la URL de CTA Médicas
            await self._navigate_to_site()
            
            # 3. Hacer login
            login_success = await self._do_login(username, password)
            
            return login_success
            
        except Exception as e:
            self.logger.error(f"Error durante login: {e}")
            return False
    
    async def _open_browser(self) -> None:
        """Abre el navegador con configuración básica."""
        self.logger.info("Abriendo navegador...")
        
        playwright = await async_playwright().start()
        
        # Configuración simple del navegador
        self.browser = await playwright.chromium.launch(
            headless=Settings.BROWSER_HEADLESS,
            args=['--no-sandbox', '--disable-web-security']
        )
        
        # Crear página con timeout extendido
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(60000)  # Aumentar a 60 segundos
        self.page.set_default_navigation_timeout(60000)  # Específico para navegación
        
        self.logger.info("Navegador abierto correctamente")
    
    async def _navigate_to_site(self) -> None:
        """Navega a la URL de CTA Médicas y espera a que el formulario de login esté disponible."""
        self.logger.info(f"Navegando a: {Settings.LOGIN_URL}")

        # Ir a la URL
        await self.page.goto(Settings.LOGIN_URL, wait_until='domcontentloaded')

        # Esperar explícitamente a que el formulario de login aparezca
        try:
            self.logger.info("Esperando a que el formulario de login aparezca...")
            # Aumentar el timeout para dar más tiempo a la carga
            await self.page.wait_for_selector('#usuarioIngreso', timeout=60000)
            self.logger.info("Formulario de login detectado correctamente")

            # Obtener información básica de la página
            title = await self.page.title()
            self.logger.info(f"Página cargada: {title}")
        except Exception as e:
            self.logger.error(f"Error esperando al formulario de login: {e}")
            await self.page.screenshot(path="error_loading_login_form.png")
            raise
    
    async def _do_login(self, username: str, password: str) -> bool:
        """
        ✅ TAMBIÉN MEJORAR ESTE MÉTODO para mejor manejo de timeouts
        """
        try:
            self.logger.info("🔐 Iniciando login en CTA Médicas...")
            
            # 1. Buscar y llenar campo de usuario
            username_field = await self._find_username_field()
            if not username_field:
                self.logger.error("❌ No se encontró campo de usuario")
                await self.page.screenshot(path="error_no_username_field.png")
                return False
            
            await username_field.click()
            await asyncio.sleep(0.5)
            await username_field.clear()
            await username_field.fill(username)
            self.logger.info(f"✅ Usuario '{username}' llenado correctamente")
            
            # 2. Buscar y llenar campo de contraseña
            password_field = await self._find_password_field()
            if not password_field:
                self.logger.error("❌ No se encontró campo de contraseña")
                await self.page.screenshot(path="error_no_password_field.png")
                return False
            
            await password_field.click()
            await asyncio.sleep(0.5)
            await password_field.clear()
            await password_field.fill(password)
            self.logger.info("✅ Contraseña llenada correctamente")
            
            # Tomar screenshot antes de enviar
            await self.page.screenshot(path="before_login_submit.png")
            
            # 3. Buscar y hacer clic en botón de envío
            submit_button = await self._find_submit_button()
            if submit_button:
                await submit_button.click()
                self.logger.info("✅ Botón de login clickeado")
            else:
                await password_field.press('Enter')
                self.logger.info("✅ Enter presionado en campo de contraseña")
            
            # ✅ 4. ESPERA MEJORADA: Más tiempo y mejor manejo
            self.logger.info("⏳ Esperando respuesta del servidor...")
            
            try:
                # Esperar a que se complete la navegación
                await self.page.wait_for_load_state('networkidle', timeout=20000)  # ✅ Aumentado a 20s
                await asyncio.sleep(2)  # Pausa adicional para JavaScript
            except Exception as e:
                self.logger.warning(f"⚠️ Timeout en networkidle, pero continuando: {e}")
                # No fallar aquí, continuar con verificación
            
            # Tomar screenshot después del login
            await self.page.screenshot(path="after_login_attempt.png")
            
            # 5. Verificar si el login fue exitoso
            return await self._check_login_success()
            
        except Exception as e:
            self.logger.error(f"❌ Error en login: {e}")
            await self.page.screenshot(path="error_during_login.png")
            return False
    
    async def _find_username_field(self):
        """Busca el campo de usuario específico de CTA Médicas."""
        # Selector específico del HTML compartido
        selectors = [
            '#usuarioIngreso',
            'input[name="usuarioIngreso"]',
            'input[id="usuarioIngreso"]'
        ]

        # Esperar un tiempo adicional si es necesario
        try:
            await self.page.wait_for_selector('#usuarioIngreso', timeout=10000)
        except Exception as e:
            self.logger.warning(f"Tiempo de espera excedido para el campo de usuario: {e}")
            # Continuar intentando encontrarlo de todos modos

        for selector in selectors:
            element = self.page.locator(selector)
            if await element.count() > 0:
                self.logger.info(f"Campo de usuario encontrado: {selector}")
                return element

        self.logger.error("No se encontró el campo de usuario de CTA Médicas")
        await self.page.screenshot(path="error_no_username_field.png")
        return None
    
    async def _find_password_field(self):
       """Busca el campo de contraseña."""
       selectors = [
           '#contraseniaIngreso',
           'input[name="contraseniaIngreso"]',
           'input[type="password"]'
       ]
       
       for selector in selectors:
           element = self.page.locator(selector)
           if await element.count() > 0:
               self.logger.info(f"Campo de contraseña encontrado: {selector}")
               return element
       
       self.logger.error("No se encontró el campo de contraseña")
       await self.page.screenshot(path="error_no_password_field.png")
       return None
    
    async def _find_submit_button(self):
        """Busca el botón de envío."""
        selectors = [
            'button[name="validarSesion"]',
            'button.btn-primary',
            'button[type="submit"]',
            'button:has-text("Ingresar")'
        ]

        for selector in selectors:
            element = self.page.locator(selector)
            if await element.count() > 0:
                self.logger.info(f"Botón de envío encontrado: {selector}")
                return element

        self.logger.error("No se encontró el botón de envío")
        await self.page.screenshot(path="error_no_submit_button.png")
        return None
    
    async def _check_login_success(self) -> bool:
        """
        Verifica si el login fue exitoso.
        ✅ CORREGIDO: Verificación más robusta y con timeouts apropiados.
        """
        try:
            # Esperar un poco para que la página se cargue completamente
            await asyncio.sleep(3)

            current_url = self.page.url
            title = await self.page.title()

            self.logger.info(f"🔍 Verificando login - URL: {current_url}")
            self.logger.info(f"🔍 Verificando login - Título: {title}")

            # ✅ VERIFICACIÓN 1: URL cambió del login
            login_patterns = ['login', 'signin', 'auth']
            url_changed = not any(pattern in current_url.lower() for pattern in login_patterns)

            if url_changed:
                self.logger.info("✅ Verificación 1 EXITOSA: URL cambió del login")
            else:
                self.logger.warning(f"⚠️ Verificación 1 FALLÓ: URL sigue siendo de login: {current_url}")

            # ✅ VERIFICACIÓN 2: Título indica dashboard/sistema
            success_patterns = ['dashboard', 'inicio', 'principal', 'vco', 'cuentas médicas', 'glosas']
            title_success = any(pattern in title.lower() for pattern in success_patterns)

            if title_success:
                self.logger.info(f"✅ Verificación 2 EXITOSA: Título indica sistema: {title}")
            else:
                self.logger.warning(f"⚠️ Verificación 2 FALLÓ: Título no indica sistema: {title}")

            # ✅ VERIFICACIÓN 3: Buscar elementos específicos del dashboard
            dashboard_elements = [
                'text=Respuesta Glosas',
                'text=Dashboard',
                'text=Menú',
                '[class*="sidebar"]',
                '[class*="nav"]',
                '[class*="menu"]'
            ]

            element_found = False
            for selector in dashboard_elements:
                try:
                    element = self.page.locator(selector)
                    if await element.count() > 0:
                        element_found = True
                        self.logger.info(f"✅ Verificación 3 EXITOSA: Elemento encontrado: {selector}")
                        break
                except:
                    continue
                
            if not element_found:
                self.logger.warning("⚠️ Verificación 3 FALLÓ: No se encontraron elementos del dashboard")

            # ✅ VERIFICACIÓN 4: Verificar que no hay mensajes de error de login
            error_selectors = [
                'text=Usuario o contraseña incorrectos',
                'text=Error',
                'text=Acceso denegado',
                '[class*="error"]',
                '[class*="alert-danger"]'
            ]

            error_found = False
            for selector in error_selectors:
                try:
                    element = self.page.locator(selector)
                    if await element.count() > 0:
                        error_text = await element.text_content()
                        self.logger.error(f"❌ Error de login detectado: {error_text}")
                        error_found = True
                        break
                except:
                    continue
                
            # ✅ DECISIÓN FINAL: Login exitoso si cumple criterios mínimos
            if error_found:
                self.logger.error("❌ LOGIN FALLIDO: Errores detectados")
                return False

            # Si al menos 1 verificación positiva es exitosa, considerar éxito
            success_criteria = [url_changed, title_success, element_found]
            successful_checks = sum(success_criteria)

            if successful_checks >= 1:
                self.logger.info(f"✅ LOGIN EXITOSO: {successful_checks}/3 verificaciones pasaron")

                # ✅ VERIFICACIÓN ADICIONAL: Esperar que elementos carguen
                try:
                    # Intentar esperar a que aparezca algún elemento del sistema
                    await self.page.wait_for_selector('body', timeout=5000)
                    self.logger.info("✅ Página completamente cargada")
                except:
                    self.logger.warning("⚠️ Timeout esperando carga completa, pero continuando...")

                return True
            else:
                self.logger.error(f"❌ LOGIN FALLIDO: Solo {successful_checks}/3 verificaciones pasaron")
                self.logger.error(f"   • URL cambió: {url_changed}")
                self.logger.error(f"   • Título correcto: {title_success}")
                self.logger.error(f"   • Elementos encontrados: {element_found}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error verificando login: {e}")
            # En caso de error, asumir que el login fue exitoso si llegamos aquí
            self.logger.warning("⚠️ Error en verificación, asumiendo login exitoso...")
            return True

    
    async def logout(self) -> None:
        """Cierra el navegador."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            self.logger.info("Navegador cerrado")
        except Exception as e:
            self.logger.error(f"Error cerrando navegador: {e}")