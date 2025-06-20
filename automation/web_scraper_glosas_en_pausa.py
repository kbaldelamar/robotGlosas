# automation/web_scraper_glosas_en_pausa.py
import asyncio
import logging
from typing import Optional, Tuple, List, Dict
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
    ✅ DISEÑO: Reutiliza 100% la lógica existente sin modificar código que funciona.
    ✅ DIFERENCIA: Solo agrega control de intentos y filtrado específico.
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
        
        # ✅ COMPOSICIÓN: Usar el procesador existente SIN modificarlo
        self.procesador_original = None
        
        # Estadísticas globales
        self.estadisticas_globales = {
            'inicio_proceso': 0,
            'fin_proceso': 0,
            'total_cuentas_procesadas': 0,
            'total_cuentas_fallidas': 0,
            'tiempo_total': 0
        }
        
        self._log_state("WebScraperGlosasEnPausa inicializado con COMPOSICIÓN")
        
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
        ✅ ESTRATEGIA: Usar procesador existente + wrapper de intentos.
        
        Args:
            username (str): Usuario para login
            password (str): Contraseña para login
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="start_glosas_en_pausa_automation",
                action="Iniciando automatización EN PAUSA con COMPOSICIÓN"
            )
            
            self.estadisticas_globales['inicio_proceso'] = asyncio.get_event_loop().time()
            
            self._log_state("🔄 === INICIANDO AUTOMATIZACIÓN EN PAUSA (COMPOSICIÓN) ===")
            self._log_state("✅ REUTILIZA: 100% lógica existente + wrapper de intentos")
            self._log_state("="*100)
            
            # ETAPA 1: LOGIN (igual que el original)
            if not await self._etapa1_login(username, password):
                return False
            
            # ETAPA 2: NAVEGACIÓN A EN PAUSA (modificado)
            if not await self._etapa2_navegacion_en_pausa():
                return False
            
            # ETAPA 3: PROCESAMIENTO CON WRAPPER DE INTENTOS
            if not await self._etapa3_procesamiento_con_wrapper():
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
        """ETAPA 1: Login (idéntico al original)."""
        try:
            self.automation_state.update(
                method_name="_etapa1_login",
                state=NavigationState.LOGIN_PAGE,
                action="ETAPA 1: Login para EN PAUSA"
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
        """ETAPA 2: Navegar a EN PAUSA (igual que Bolsa Respuesta pero diferente selector)."""
        try:
            self.automation_state.update(
                method_name="_etapa2_navegacion_en_pausa",
                action="ETAPA 2: Navegando a EN PAUSA"
            )
            
            self._log_state("🧭 ETAPA 2: NAVEGACIÓN A EN PAUSA")
            self._log_state("-"*50)
            
            # Inicializar manejador de navegación
            self.navigation_handler = NavigationHandler(self.page, self.automation_state)
            
            # Navegar a Respuesta Glosas
            self._log_state("📍 Navegando a Respuesta Glosas...")
            if not await self.navigation_handler.navigate_to_respuesta_glosas():
                self._log_state("❌ Error navegando a Respuesta Glosas", "error")
                return False
            
            # ✅ NAVEGACIÓN ESPECÍFICA A EN PAUSA
            self._log_state("📍 Navegando a EN PAUSA...")
            if not await self._navegar_a_en_pausa_especifico():
                self._log_state("❌ Error navegando a EN PAUSA", "error")
                return False
            
            self._log_state("✅ ETAPA 2 COMPLETADA: Navegación a EN PAUSA exitosa")
            self._log_state("-"*50)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 2 (navegación EN PAUSA): {e}", "error")
            return False
    
    async def _navegar_a_en_pausa_especifico(self) -> bool:
        """Navegación específica a EN PAUSA (sin modificar NavigationHandler)."""
        try:
            # Selector específico para EN PAUSA
            selector_en_pausa = "//span[@class='sidebar-nav-name'][contains(.,'En Pausa')]"
            
            element = self.page.locator(f"xpath={selector_en_pausa}")
            
            if await element.count() == 0:
                self._log_state("❌ No se encontró el submenú 'En Pausa'", "error")
                return False
            
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await element.click()
            
            # Esperar carga
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)
            
            # Verificar que se cargó
            if "pausa" in self.page.url.lower() or await self.page.locator("text=En Pausa").count() > 0:
                self._log_state("✅ Navegación a EN PAUSA verificada")
                return True
            else:
                self._log_state("❌ No se pudo verificar navegación a EN PAUSA", "error")
                return False
                
        except Exception as e:
            self._log_state(f"❌ Error navegando específicamente a EN PAUSA: {e}", "error")
            return False
    
    async def _etapa3_procesamiento_con_wrapper(self) -> bool:
        """
        ETAPA 3: Procesamiento usando el procesador ORIGINAL con wrapper de intentos.
        ✅ NO MODIFICA CÓDIGO EXISTENTE - USA COMPOSICIÓN.
        """
        try:
            self.automation_state.update(
                method_name="_etapa3_procesamiento_con_wrapper",
                action="ETAPA 3: Procesamiento con wrapper de intentos"
            )
            
            self._log_state("⚙️ ETAPA 3: PROCESAMIENTO CON WRAPPER (SIN MODIFICAR ORIGINAL)")
            self._log_state("-"*50)
            self._log_state("✅ ESTRATEGIA: Procesador original + wrapper de intentos")
            self._log_state("✅ NO MODIFICA: Métodos existentes que funcionan")
            self._log_state("-"*50)
            
            # ✅ PASO 1: Crear procesador original (sin modificar)
            self.procesador_original = ProcesadorCompletoGlosasImplementado(
                self.page, 
                self.automation_state,
                worker_thread=self.worker
            )
            
            # ✅ PASO 2: Obtener cuentas EN PAUSA con filtro específico
            cuentas_en_pausa = await self._obtener_cuentas_en_pausa_independiente()
            
            if not cuentas_en_pausa:
                self._log_state("⚠️ No hay cuentas EN PAUSA para reprocesar", "warning")
                return False
            
            # ✅ PASO 3: Procesar cada cuenta con wrapper de intentos
            cuentas_procesadas = 0
            cuentas_fallidas = 0
            
            for i, cuenta_data in enumerate(cuentas_en_pausa):
                idcuenta = cuenta_data['idcuenta']
                intentos_actuales = cuenta_data.get('intentos', 0)
                
                self._log_state(f"🔄 REPROCESANDO {i + 1}/{len(cuentas_en_pausa)}: {idcuenta} (intentos: {intentos_actuales})")
                
                try:
                    # ✅ WRAPPER: Control de intentos ANTES de procesar
                    if not await self._pre_proceso_control_intentos(idcuenta, intentos_actuales):
                        cuentas_fallidas += 1
                        continue
                    
                    # ✅ USAR PROCESADOR ORIGINAL SIN MODIFICAR
                    resultado = await self._procesar_con_original(idcuenta)
                    
                    # ✅ WRAPPER: Manejo de resultado CON intentos
                    if resultado['exito']:
                        cuentas_procesadas += 1
                        self.estadisticas_globales['total_cuentas_procesadas'] += 1
                        await self._post_proceso_exitoso(idcuenta)
                        self._log_state(f"✅ CUENTA {idcuenta} RECUPERADA")
                    else:
                        cuentas_fallidas += 1
                        self.estadisticas_globales['total_cuentas_fallidas'] += 1
                        await self._post_proceso_fallido(idcuenta, intentos_actuales + 1, resultado.get('error', ''))
                        self._log_state(f"❌ CUENTA {idcuenta} FALLÓ (intento {intentos_actuales + 1})")
                
                except Exception as e:
                    cuentas_fallidas += 1
                    await self._post_proceso_fallido(idcuenta, intentos_actuales + 1, f"Error general: {e}")
                    self._log_state(f"❌ Error procesando {idcuenta}: {e}", "error")
                
                await asyncio.sleep(3)
            
            self._log_state("-"*50)
            self._log_state("📊 ETAPA 3 COMPLETADA:")
            self._log_state(f"   • Reprocesadas exitosamente: {cuentas_procesadas}")
            self._log_state(f"   • Que siguen fallando: {cuentas_fallidas}")
            self._log_state("-"*50)
            
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 3 (procesamiento wrapper): {e}", "error")
            return False
    
    async def _obtener_cuentas_en_pausa_independiente(self) -> List[Dict]:
        """
        Obtiene cuentas EN PAUSA usando métodos del procesador original.
        ✅ INDEPENDIENTE: No modifica código existente.
        """
        try:
            self._log_state("📋 Obteniendo cuentas EN PAUSA (método independiente)")
            
            # ✅ USAR MÉTODO EXISTENTE del procesador original
            await self.procesador_original._preparar_sistema()
            todas_las_cuentas = await self.procesador_original.extraer_datos_filas_tabla()
            
            if not todas_las_cuentas:
                return []
            
            # ✅ FILTRO ESPECÍFICO PARA EN PAUSA
            cuentas_para_reprocesar = []
            
            for cuenta_web in todas_las_cuentas:
                idcuenta = cuenta_web['idcuenta']
                
                # Consultar estado e intentos desde BD
                estado_bd, intentos_bd = self._consultar_estado_intentos_independiente(idcuenta)
                
                # ✅ FILTRO: Solo FALLIDAS/EN_PROCESO con menos de 5 intentos
                if estado_bd in ['FALLIDO', 'EN_PROCESO'] and intentos_bd < 5:
                    cuenta_web['estado_bd'] = estado_bd
                    cuenta_web['intentos'] = intentos_bd
                    cuentas_para_reprocesar.append(cuenta_web)
                    
                    self._log_state(f"✅ {idcuenta} elegible: {estado_bd} (intentos: {intentos_bd})")
                else:
                    if intentos_bd >= 5:
                        self._log_state(f"⏭️ {idcuenta} saltada: +5 intentos")
                    else:
                        self._log_state(f"⏭️ {idcuenta} saltada: estado {estado_bd}")
            
            self._log_state(f"✅ {len(cuentas_para_reprocesar)} cuentas EN PAUSA encontradas")
            
            # Emitir signal
            if self.worker and cuentas_para_reprocesar:
                self.worker.emit_data_imported(len(cuentas_para_reprocesar))
                await asyncio.sleep(1)
            
            return cuentas_para_reprocesar
            
        except Exception as e:
            self._log_state(f"❌ Error obteniendo cuentas EN PAUSA: {e}", "error")
            return []
    
    def _consultar_estado_intentos_independiente(self, idcuenta: str) -> Tuple[str, int]:
        """Consulta estado e intentos (método independiente)."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT estado, COALESCE(intentos, 0) as intentos 
                    FROM cuenta_glosas_principal 
                    WHERE idcuenta = ?
                """, (idcuenta,))
                
                row = cursor.fetchone()
                if row:
                    return row['estado'], row['intentos']
                else:
                    return 'PENDIENTE', 0
                    
        except Exception as e:
            self._log_state(f"❌ Error consultando BD {idcuenta}: {e}", "error")
            return 'DESCONOCIDO', 0
    
    async def _pre_proceso_control_intentos(self, idcuenta: str, intentos_actuales: int) -> bool:
        """Pre-procesamiento: Control de intentos ANTES de usar procesador original."""
        try:
            # Verificar límite de intentos
            if intentos_actuales >= 5:
                await self._marcar_como_falla_total_independiente(idcuenta)
                self._log_state(f"🚫 {idcuenta} FALLA TOTAL (5+ intentos)")
                return False
            
            # Incrementar intentos y marcar como EN_PROCESO
            await self._incrementar_intentos_independiente(idcuenta)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en pre-proceso {idcuenta}: {e}", "error")
            return False
    
    async def _procesar_con_original(self, idcuenta: str) -> Dict:
        """
        Procesa cuenta usando el procesador ORIGINAL sin modificaciones.
        ✅ COMPOSICIÓN PURA: Usa método existente tal como está.
        """
        try:
            # ✅ USAR MÉTODO ORIGINAL SIN MODIFICAR
            resultado = await self.procesador_original._procesar_cuenta_completa(idcuenta)
            return resultado
            
        except Exception as e:
            return {'exito': False, 'error': f"Error en procesador original: {e}"}
    
    async def _post_proceso_exitoso(self, idcuenta: str):
        """Post-procesamiento: Manejo de cuenta exitosa."""
        try:
            # El procesador original ya marca como COMPLETADO
            # Solo emitir signal adicional
            if self.worker:
                self.worker.emit_cuenta_processed(idcuenta, 'COMPLETADO')
                
        except Exception as e:
            self._log_state(f"❌ Error en post-proceso exitoso {idcuenta}: {e}", "error")
    
    async def _post_proceso_fallido(self, idcuenta: str, intentos_nuevos: int, error: str):
        """Post-procesamiento: Manejo de cuenta fallida con intentos."""
        try:
            if intentos_nuevos >= 5:
                await self._marcar_como_falla_total_independiente(idcuenta)
                if self.worker:
                    self.worker.emit_cuenta_processed(idcuenta, 'FALLA_TOTAL')
            else:
                await self._marcar_como_fallido_con_intentos(idcuenta, intentos_nuevos, error)
                if self.worker:
                    self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                    
        except Exception as e:
            self._log_state(f"❌ Error en post-proceso fallido {idcuenta}: {e}", "error")
    
    async def _incrementar_intentos_independiente(self, idcuenta: str):
        """Incrementa intentos (método independiente)."""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cuenta_glosas_principal 
                    SET intentos = COALESCE(intentos, 0) + 1, 
                        estado = 'EN_PROCESO',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, (idcuenta,))
                conn.commit()
                
                if self.worker:
                    self.worker.emit_cuenta_processed(idcuenta, 'EN_PROCESO')
                
        except Exception as e:
            self._log_state(f"❌ Error incrementando intentos {idcuenta}: {e}", "error")
    
    async def _marcar_como_falla_total_independiente(self, idcuenta: str):
        """Marca como falla total (método independiente)."""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cuenta_glosas_principal 
                    SET estado = 'FALLA_TOTAL',
                        motivo_fallo = 'Superó 5 intentos de procesamiento',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, (idcuenta,))
                conn.commit()
                
        except Exception as e:
            self._log_state(f"❌ Error marcando falla total {idcuenta}: {e}", "error")
    
    async def _marcar_como_fallido_con_intentos(self, idcuenta: str, intentos: int, error: str):
        """Marca como fallido con número de intentos (método independiente)."""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cuenta_glosas_principal 
                    SET estado = 'FALLIDO',
                        motivo_fallo = ?,
                        intentos = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, (f"Intento {intentos}/5: {error[:200]}", intentos, idcuenta))
                conn.commit()
                
        except Exception as e:
            self._log_state(f"❌ Error marcando fallido con intentos {idcuenta}: {e}", "error")
    
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
            
            self._log_state("")
            self._log_state("✅ VENTAJAS DEL ENFOQUE COMPOSICIÓN:")
            self._log_state("   • 100% reutilización de código existente")
            self._log_state("   • Sin modificar métodos que funcionan")
            self._log_state("   • Mantenimiento independiente")
            self._log_state("   • Control de intentos específico")
            self._log_state("="*100)
            
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
            
            self._log_state("⏳ Manteniendo navegador abierto por 60 segundos...")
            await asyncio.sleep(60)
            
            self._log_state("🔒 Cerrando navegador...")
            await self.login_handler.logout()
            
        except Exception as e:
            self._log_state(f"❌ Error manteniendo navegador abierto: {e}", "error")