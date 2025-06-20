# automation/web_scraper_glosas_en_pausa.py
import asyncio
import logging
from typing import Optional, Tuple, List, Dict  # ✅ CORREGIDO PARA PYTHON 3.8
from playwright.async_api import Page
from automation.login_handler import LoginHandler
from automation.navigation_handler import NavigationHandler, AutomationState, NavigationState
from automation.procesador_completo_glosas_final import ProcesadorCompletoGlosasImplementado
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from config.settings import Settings

class WebScraperGlosasEnPausa:
    """
    Automatizador específico para gestión de glosas EN PAUSA.
    DIFERENCIA CLAVE: Navega a "En Pausa" en lugar de "Bolsa Respuesta"
    y procesa solo cuentas FALLIDAS y EN_PROCESO.
    """
    
    def __init__(self, worker_thread=None):
        """
        Inicializa el web scraper de glosas EN PAUSA.
        
        Args:
            worker_thread: Thread con signals para actualización en tiempo real
        """
        self.logger = logging.getLogger(__name__)
        self.login_handler = LoginHandler()
        self.navigation_handler: Optional[NavigationHandler] = None
        self.procesador_completo: Optional[ProcesadorCompletoGlosasImplementado] = None
        self.page: Optional[Page] = None
        
        # Worker para emitir signals en tiempo real
        self.worker = worker_thread
        
        # Base de datos específica para glosas
        self.db_manager = DatabaseManagerGlosas()
        self.db_manager.create_glosas_tables()
        
        # Estado compartido de la automatización
        self.automation_state = AutomationState(
            current_class="WebScraperGlosasEnPausa",
            current_method="__init__"
        )
        
        # Estadísticas globales
        self.estadisticas_globales = {
            'inicio_proceso': 0,
            'fin_proceso': 0,
            'total_cuentas_procesadas': 0,
            'total_cuentas_fallidas': 0,
            'tiempo_total': 0
        }
        
        self._log_state("WebScraperGlosasEnPausa inicializado para reprocesamiento EN PAUSA")
        
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
        
    async def start_glosas_en_pausa_automation(self, username: str, password: str) -> bool:
        """
        MÉTODO PRINCIPAL: Inicia la automatización de glosas EN PAUSA.
        
        Args:
            username (str): Usuario para login
            password (str): Contraseña para login
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="start_glosas_en_pausa_automation",
                action="Iniciando automatización EN PAUSA"
            )
            
            self.estadisticas_globales['inicio_proceso'] = asyncio.get_event_loop().time()
            
            self._log_state("🔄 === INICIANDO AUTOMATIZACIÓN DE GLOSAS EN PAUSA ===")
            self._log_state("🎯 OBJETIVO: Reprocesar cuentas FALLIDAS y EN_PROCESO")
            self._log_state("🎯 NAVEGACIÓN: Respuesta Glosas → En Pausa")
            self._log_state("="*100)
            
            # ETAPA 1: LOGIN
            if not await self._etapa1_login(username, password):
                return False
            
            # ETAPA 2: NAVEGACIÓN A EN PAUSA
            if not await self._etapa2_navegacion_en_pausa():
                return False
            
            # ETAPA 3: PROCESAMIENTO DE CUENTAS EN PAUSA
            if not await self._etapa3_procesamiento_en_pausa():
                return False
            
            self.estadisticas_globales['fin_proceso'] = asyncio.get_event_loop().time()
            self.estadisticas_globales['tiempo_total'] = (
                self.estadisticas_globales['fin_proceso'] - 
                self.estadisticas_globales['inicio_proceso']
            )
            
            self._log_state("🎉 === AUTOMATIZACIÓN EN PAUSA FINALIZADA ===")
            await self._mostrar_resumen_final()
            
            # Emitir signal final
            if self.worker:
                self.worker.emit_tabla_refresh()
                self._log_state("📡 Signal final enviado para actualizar interfaz EN PAUSA")
            
            return True
            
        except Exception as e:
            self.automation_state.update(state=NavigationState.ERROR)
            self._log_state(f"❌ Error crítico en automatización EN PAUSA: {e}", "error")
            return False
        finally:
            # Mantener navegador abierto para inspección
            await self._mantener_abierto_para_inspeccion()
    
    async def _etapa1_login(self, username: str, password: str) -> bool:
        """ETAPA 1: Realiza el proceso de login."""
        try:
            self.automation_state.update(
                method_name="_etapa1_login",
                state=NavigationState.LOGIN_PAGE,
                action="ETAPA 1: Realizando login para EN PAUSA"
            )
            
            self._log_state("🔐 ETAPA 1: PROCESO DE LOGIN PARA EN PAUSA")
            self._log_state("-"*50)
            self._log_state(f"Usuario: {username}")
            
            login_success = await self.login_handler.login(username, password)
            
            if login_success:
                self.page = self.login_handler.page
                self.automation_state.update(
                    state=NavigationState.DASHBOARD,
                    action="Login exitoso para EN PAUSA"
                )
                self._log_state("✅ ETAPA 1 COMPLETADA: Login exitoso")
                self._log_state("-"*50)
                return True
            else:
                self.automation_state.update(state=NavigationState.ERROR)
                self._log_state("❌ ETAPA 1 FALLIDA: Login falló", "error")
                return False
                
        except Exception as e:
            self.automation_state.update(state=NavigationState.ERROR)
            self._log_state(f"❌ Error en ETAPA 1 (login): {e}", "error")
            return False
    
    async def _etapa2_navegacion_en_pausa(self) -> bool:
        """ETAPA 2: Navega hasta EN PAUSA en lugar de Bolsa Respuesta."""
        try:
            self.automation_state.update(
                method_name="_etapa2_navegacion_en_pausa",
                action="ETAPA 2: Navegando a EN PAUSA"
            )
            
            self._log_state("🧭 ETAPA 2: NAVEGACIÓN A EN PAUSA")
            self._log_state("-"*50)
            
            # Inicializar manejador de navegación
            self.navigation_handler = NavigationHandlerEnPausa(self.page, self.automation_state)
            
            # Navegar a Respuesta Glosas
            self._log_state("📍 Navegando a Respuesta Glosas...")
            if not await self.navigation_handler.navigate_to_respuesta_glosas():
                self._log_state("❌ Error navegando a Respuesta Glosas", "error")
                return False
            
            # ✅ DIFERENCIA CLAVE: Navegar a EN PAUSA en lugar de Bolsa Respuesta
            self._log_state("📍 Navegando a EN PAUSA...")
            if not await self.navigation_handler.navigate_to_en_pausa():
                self._log_state("❌ Error navegando a EN PAUSA", "error")
                return False
            
            self._log_state("✅ ETAPA 2 COMPLETADA: Navegación a EN PAUSA exitosa")
            self._log_state("-"*50)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 2 (navegación EN PAUSA): {e}", "error")
            return False
    
    async def _etapa3_procesamiento_en_pausa(self) -> bool:
        """
        ETAPA 3: Procesamiento específico para cuentas EN PAUSA.
        
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            self.automation_state.update(
                method_name="_etapa3_procesamiento_en_pausa",
                action="ETAPA 3: Procesamiento EN PAUSA"
            )
            
            self._log_state("⚙️ ETAPA 3: PROCESAMIENTO EN PAUSA")
            self._log_state("-"*50)
            self._log_state("🎯 FUNCIONALIDADES ESPECÍFICAS EN PAUSA:")
            self._log_state("   • Buscar solo cuentas FALLIDAS y EN_PROCESO")
            self._log_state("   • Incrementar contador de intentos")
            self._log_state("   • Procesamiento con lógica de reintentos")
            self._log_state("   • ✅ ACTUALIZACIÓN EN TIEMPO REAL")
            self._log_state("-"*50)
            
            # Inicializar procesador CON worker para signals y modo EN PAUSA
            self.procesador_completo = ProcesadorCompletoEnPausa(
                self.page, 
                self.automation_state,
                worker_thread=self.worker
            )
            
            self._log_state("🚀 Iniciando procesamiento EN PAUSA con signals en tiempo real...")
            
            # Procesar cuentas EN PAUSA con funcionalidad específica
            procesadas, fallidas = await self.procesador_completo.procesar_filas_tabla_en_pausa()
            
            # Actualizar estadísticas globales
            self.estadisticas_globales['total_cuentas_procesadas'] = procesadas
            self.estadisticas_globales['total_cuentas_fallidas'] = fallidas
            
            self._log_state("-"*50)
            self._log_state("📊 RESULTADOS DE PROCESAMIENTO EN PAUSA:")
            self._log_state(f"   • Cuentas reprocesadas exitosamente: {procesadas}")
            self._log_state(f"   • Cuentas que siguen fallando: {fallidas}")
            
            if procesadas == 0 and fallidas == 0:
                self._log_state("⚠️ ETAPA 3: No se procesaron cuentas EN PAUSA", "warning")
                return False
            
            self._log_state("✅ ETAPA 3 COMPLETADA: Procesamiento EN PAUSA terminado")
            self._log_state("-"*50)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 3 (procesamiento EN PAUSA): {e}", "error")
            return False
    
    async def _mostrar_resumen_final(self):
        """Muestra resumen final del reprocesamiento EN PAUSA."""
        try:
            tiempo_total = self.estadisticas_globales['tiempo_total']
            procesadas = self.estadisticas_globales['total_cuentas_procesadas']
            fallidas = self.estadisticas_globales['total_cuentas_fallidas']
            total = procesadas + fallidas
            
            self._log_state("")
            self._log_state("🎯 RESUMEN FINAL DE REPROCESAMIENTO EN PAUSA")
            self._log_state("="*100)
            self._log_state(f"⏱️  TIEMPO TOTAL: {tiempo_total:.2f} segundos ({tiempo_total/60:.1f} minutos)")
            self._log_state(f"🔄 CUENTAS EN PAUSA PROCESADAS: {total}")
            self._log_state(f"✅ CUENTAS RECUPERADAS: {procesadas}")
            self._log_state(f"❌ CUENTAS AÚN FALLIDAS: {fallidas}")
            
            if total > 0:
                tasa_recuperacion = (procesadas / total) * 100
                self._log_state(f"📈 TASA DE RECUPERACIÓN: {tasa_recuperacion:.1f}%")
                
                if procesadas > 0:
                    tiempo_promedio = tiempo_total / procesadas
                    self._log_state(f"⚡ TIEMPO PROMEDIO POR CUENTA: {tiempo_promedio:.2f} segundos")
            
            self._log_state("")
            self._log_state("🎯 FUNCIONALIDADES IMPLEMENTADAS EN PAUSA:")
            self._log_state("   ✅ Login automático")
            self._log_state("   ✅ Navegación a EN PAUSA")
            self._log_state("   ✅ Filtrado de cuentas FALLIDAS/EN_PROCESO")
            self._log_state("   ✅ Control de reintentos")
            self._log_state("   ✅ Procesamiento con modales")
            self._log_state("   ✅ ACTUALIZACIÓN EN TIEMPO REAL")
            
            self._log_state("="*100)
            
            # Determinar resultado final
            if procesadas > 0:
                if tasa_recuperacion >= 70:
                    self._log_state("🎉 RESULTADO: REPROCESAMIENTO EXITOSO")
                elif tasa_recuperacion >= 40:
                    self._log_state("⚠️ RESULTADO: REPROCESAMIENTO PARCIALMENTE EXITOSO")
                else:
                    self._log_state("❌ RESULTADO: REPROCESAMIENTO CON PROBLEMAS")
            else:
                self._log_state("❌ RESULTADO: REPROCESAMIENTO FALLIDO")
            
        except Exception as e:
            self._log_state(f"❌ Error mostrando resumen final EN PAUSA: {e}", "error")
    
    async def _mantener_abierto_para_inspeccion(self):
        """Mantiene el navegador abierto para inspeccionar la página."""
        try:
            self.automation_state.update(
                method_name="_mantener_abierto_para_inspeccion",
                action="Manteniendo navegador abierto para inspección EN PAUSA"
            )
            
            self._log_state("🔍 INSPECCIÓN FINAL EN PAUSA")
            self._log_state("-"*50)
            self._log_state("🌐 Navegador abierto para inspección - Se cerrará en 60 segundos")
            
            # Obtener estado final
            if self.navigation_handler:
                final_info = await self.navigation_handler.get_current_page_info()
                self._log_state(f"📋 Estado final: {final_info}")
            
            self._log_state("⏳ Manteniendo navegador abierto por 60 segundos...")
            await asyncio.sleep(60)
            
            self._log_state("🔒 Cerrando navegador...")
            await self.login_handler.logout()
            
        except Exception as e:
            self._log_state(f"❌ Error manteniendo navegador abierto: {e}", "error")


class NavigationHandlerEnPausa(NavigationHandler):
    """
    Extensión del NavigationHandler para navegar a EN PAUSA.
    """
    
    async def navigate_to_en_pausa(self) -> bool:
        """
        Navega al submenú 'En Pausa' (debe estar en Respuesta Glosas primero).
        
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
            
            # ✅ SELECTOR ESPECÍFICO PARA EN PAUSA
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
                    state=NavigationState.BOLSA_RESPUESTA,  # Usar mismo estado
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
            
            # Verificar por texto "En Pausa"
            selector = "text=En Pausa"
            element = self.page.locator(selector)
            
            if await element.count() > 0:
                self._log_state("✅ En Pausa verificado con text selector")
                return True
            
            # Si el selector principal falla, verificar URL como respaldo
            current_url = self.page.url
            if 'pausa' in current_url.lower() or 'respuesta' in current_url.lower():
                self._log_state(f"✅ En Pausa verificado por URL: {current_url}")
                return True
            
            self._log_state("❌ No se pudo verificar que En Pausa esté cargado", "warning")
            return False
            
        except Exception as e:
            self._log_state(f"Error verificando En Pausa: {e}", "error")
            return False


class ProcesadorCompletoEnPausa(ProcesadorCompletoGlosasImplementado):
    """
    Extensión del procesador para manejar específicamente cuentas EN PAUSA.
    """
    
    async def procesar_filas_tabla_en_pausa(self) -> Tuple[int, int]:  # ✅ CORREGIDO PARA PYTHON 3.8
        """
        MÉTODO PRINCIPAL MODIFICADO: Procesa solo cuentas EN PAUSA.
        
        Returns:
            Tuple[int, int]: (cuentas_procesadas, cuentas_fallidas)
        """
        try:
            self.state.update(
                method_name="procesar_filas_tabla_en_pausa",
                action="Procesando filas EN PAUSA específicamente"
            )
            
            self.estadisticas['tiempo_inicio'] = asyncio.get_event_loop().time()
            
            self._log("🔄 === INICIANDO PROCESAMIENTO EN PAUSA ===")
            self._log("🎯 OBJETIVO: Solo cuentas FALLIDAS y EN_PROCESO")
            self._log("=" * 100)
            
            # PASO 1: Preparar sistema
            if not await self._preparar_sistema():
                return 0, 0
            
            # PASO 2: Obtener SOLO cuentas EN PAUSA
            cuentas_en_pausa = await self._obtener_cuentas_en_pausa()
            
            if not cuentas_en_pausa:
                self._log("⚠️ No hay cuentas EN PAUSA para reprocesar", "warning")
                return 0, 0
            
            # PASO 3: Procesar cada cuenta EN PAUSA
            cuentas_procesadas = 0
            cuentas_fallidas = 0
            
            for i, cuenta_data in enumerate(cuentas_en_pausa):
                idcuenta = cuenta_data['idcuenta']
                
                self._log("")
                self._log(f"🔄 REPROCESANDO CUENTA EN PAUSA {i + 1}/{len(cuentas_en_pausa)}: {idcuenta}")
                self._log(f"   Estado actual: {cuenta_data.get('estado', 'N/A')}")
                self._log(f"   Intentos previos: {cuenta_data.get('intentos', 0)}")
                self._log("-" * 60)
                
                try:
                    # ✅ INCREMENTAR CONTADOR DE INTENTOS
                    await self._incrementar_intentos(idcuenta)
                    
                    # Procesar cuenta completa
                    resultado = await self._procesar_cuenta_completa(idcuenta)
                    
                    if resultado['exito']:
                        cuentas_procesadas += 1
                        self.estadisticas['cuentas_procesadas'] += 1
                        self.estadisticas['glosas_procesadas'] += resultado.get('glosas_procesadas', 0)
                        
                        self._log(f"✅ CUENTA EN PAUSA {idcuenta} RECUPERADA")
                        self._log(f"   • Glosas procesadas: {resultado.get('glosas_procesadas', 0)}")
                    else:
                        error_msg = resultado.get('error', 'Error desconocido en reprocesamiento')
                        
                        # Marcar como fallida nuevamente
                        estado_actual = self.db_manager.get_cuenta_estado(idcuenta)
                        if estado_actual != EstadoCuenta.FALLIDO:
                            await self._marcar_cuenta_fallida(idcuenta, f"Reintento fallido: {error_msg}")
                        
                        cuentas_fallidas += 1
                        self.estadisticas['cuentas_fallidas'] += 1
                        
                        self._log(f"❌ CUENTA EN PAUSA {idcuenta} SIGUE FALLANDO: {error_msg[:100]}...")
                
                except Exception as e:
                    error_msg = f"Error general reprocesando cuenta EN PAUSA {idcuenta}: {e}"
                    self._log(error_msg, "error")
                    
                    # Marcar como fallida y regresar a tabla principal
                    await self._marcar_cuenta_fallida(idcuenta, error_msg)
                    await self._regresar_tabla_principal()
                    
                    cuentas_fallidas += 1
                    self.estadisticas['cuentas_fallidas'] += 1
                
                # Pausa entre cuentas
                await asyncio.sleep(3)
                
                # Log de progreso
                if (i + 1) % 2 == 0:
                    porcentaje = ((i + 1) / len(cuentas_en_pausa)) * 100
                    self._log(f"📊 PROGRESO EN PAUSA: {i + 1}/{len(cuentas_en_pausa)} ({porcentaje:.1f}%)")
            
            self.estadisticas['tiempo_fin'] = asyncio.get_event_loop().time()
            
            # Mostrar estadísticas finales
            await self._mostrar_estadisticas_finales()
            
            self._log("=" * 100)
            self._log("🎉 PROCESAMIENTO EN PAUSA TERMINADO")
            
            return cuentas_procesadas, cuentas_fallidas
            
        except Exception as e:
            self._log(f"❌ Error crítico en procesamiento EN PAUSA: {e}", "error")
            return 0, 0
    
    async def _obtener_cuentas_en_pausa(self) -> List[Dict]:  # ✅ CORREGIDO PARA PYTHON 3.8
        """
        Obtiene SOLO cuentas que están EN PAUSA (FALLIDAS y EN_PROCESO).
        
        Returns:
            List[Dict]: Lista de cuentas EN PAUSA
        """
        try:
            self._log("📋 Obteniendo cuentas EN PAUSA para reprocesamiento")
            
            cuentas_en_pausa = []
            
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT idcuenta, proveedor, estado, valor_glosado, 
                               fecha_radicacion, intentos
                        FROM cuenta_glosas_principal 
                        WHERE estado IN ('FALLIDO', 'EN_PROCESO')
                        AND intentos < 5  -- Limitar reintentos
                        ORDER BY intentos ASC, created_at ASC
                    """)
                    
                    for row in cursor.fetchall():
                        cuentas_en_pausa.append({
                            'idcuenta': row['idcuenta'],
                            'proveedor': row['proveedor'],
                            'estado': row['estado'],
                            'valor_glosado': row['valor_glosado'],
                            'fecha_radicacion': row['fecha_radicacion'],
                            'intentos': row['intentos']
                        })
                    
                    self._log(f"🔍 Encontradas {len(cuentas_en_pausa)} cuentas EN PAUSA en BD")
            
            except Exception as e:
                self._log(f"⚠️ Error consultando BD EN PAUSA: {e}", "warning")
            
            # Emitir signal de datos importados
            if self.worker and cuentas_en_pausa:
                self.worker.emit_data_imported(len(cuentas_en_pausa))
                await asyncio.sleep(1)
            
            return cuentas_en_pausa
            
        except Exception as e:
            self._log(f"❌ Error obteniendo cuentas EN PAUSA: {e}", "error")
            return []
    
    async def _incrementar_intentos(self, idcuenta: str):
        """Incrementa el contador de intentos para una cuenta."""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cuenta_glosas_principal 
                    SET intentos = intentos + 1, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, (idcuenta,))
                conn.commit()
                
                self._log(f"🔢 Intentos incrementados para cuenta {idcuenta}")
                
        except Exception as e:
            self._log(f"❌ Error incrementando intentos para {idcuenta}: {e}", "error")