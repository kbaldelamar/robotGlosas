import asyncio
import logging
from typing import Optional
from playwright.async_api import Page
from automation.login_handler import LoginHandler
from automation.navigation_handler import NavigationHandler, AutomationState, NavigationState
# CAMBIO: Usar el nuevo procesador completo implementado
from automation.procesador_completo_glosas_final import ProcesadorCompletoGlosasImplementado
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from config.settings import Settings

class WebScraperGlosas:
    """
    Automatizador específico para gestión de glosas.
    VERSIÓN FINAL CON PROCESADOR COMPLETO IMPLEMENTADO:
    - Hace clic en cada botón de cuenta
    - Procesa todas las glosas individuales con modales
    - Maneja errores y regresa a tabla principal
    - Termina correctamente cada cuenta
    """
    
    def __init__(self):
        """Inicializa el web scraper de glosas con procesador completo."""
        self.logger = logging.getLogger(__name__)
        self.login_handler = LoginHandler()
        self.navigation_handler: Optional[NavigationHandler] = None
        self.procesador_completo: Optional[ProcesadorCompletoGlosasImplementado] = None
        self.page: Optional[Page] = None
        
        # Base de datos específica para glosas
        self.db_manager = DatabaseManagerGlosas()
        self.db_manager.create_glosas_tables()
        
        # Estado compartido de la automatización
        self.automation_state = AutomationState(
            current_class="WebScraperGlosas",
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
        
        self._log_state("WebScraperGlosas inicializado con procesador completo")
        
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
        MÉTODO PRINCIPAL: Inicia la automatización completa de glosas.
        VERSIÓN FINAL con procesamiento real de modales.
        
        Args:
            username (str): Usuario para login
            password (str): Contraseña para login
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            self.automation_state.update(
                method_name="start_glosas_automation",
                action="Iniciando automatización completa de glosas"
            )
            
            self.estadisticas_globales['inicio_proceso'] = asyncio.get_event_loop().time()
            
            self._log_state("🚀 === INICIANDO AUTOMATIZACIÓN COMPLETA DE GLOSAS (FINAL) ===")
            self._log_state("🎯 INCLUYE: Login → Navegación → Procesamiento Real de Modales → Terminar")
            self._log_state("="*100)
            
            # ETAPA 1: LOGIN
            if not await self._etapa1_login(username, password):
                return False
            
            # ETAPA 2: NAVEGACIÓN A BOLSA RESPUESTA
            if not await self._etapa2_navegacion():
                return False
            
            # ETAPA 3: PROCESAMIENTO COMPLETO CON MODALES REALES
            if not await self._etapa3_procesamiento_completo_final():
                return False
            
            self.estadisticas_globales['fin_proceso'] = asyncio.get_event_loop().time()
            self.estadisticas_globales['tiempo_total'] = (
                self.estadisticas_globales['fin_proceso'] - 
                self.estadisticas_globales['inicio_proceso']
            )
            
            self._log_state("🎉 === AUTOMATIZACIÓN COMPLETA DE GLOSAS FINALIZADA ===")
            await self._mostrar_resumen_final()
            
            return True
            
        except Exception as e:
            self.automation_state.update(state=NavigationState.ERROR)
            self._log_state(f"❌ Error crítico en automatización de glosas: {e}", "error")
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
                action="ETAPA 1: Realizando login"
            )
            
            self._log_state("🔐 ETAPA 1: PROCESO DE LOGIN")
            self._log_state("-"*50)
            self._log_state(f"Usuario: {username}")
            
            login_success = await self.login_handler.login(username, password)
            
            if login_success:
                self.page = self.login_handler.page
                self.automation_state.update(
                    state=NavigationState.DASHBOARD,
                    action="Login exitoso"
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
    
    async def _etapa2_navegacion(self) -> bool:
        """ETAPA 2: Navega hasta la tabla de Bolsa Respuesta."""
        try:
            self.automation_state.update(
                method_name="_etapa2_navegacion",
                action="ETAPA 2: Navegando a Bolsa Respuesta"
            )
            
            self._log_state("🧭 ETAPA 2: NAVEGACIÓN A BOLSA RESPUESTA")
            self._log_state("-"*50)
            
            # Inicializar manejador de navegación
            self.navigation_handler = NavigationHandler(self.page, self.automation_state)
            
            # Navegar a Respuesta Glosas
            self._log_state("📍 Navegando a Respuesta Glosas...")
            if not await self.navigation_handler.navigate_to_respuesta_glosas():
                self._log_state("❌ Error navegando a Respuesta Glosas", "error")
                return False
            
            # Navegar a Bolsa Respuesta
            self._log_state("📍 Navegando a Bolsa Respuesta...")
            if not await self.navigation_handler.navigate_to_bolsa_respuesta():
                self._log_state("❌ Error navegando a Bolsa Respuesta", "error")
                return False
            
            self._log_state("✅ ETAPA 2 COMPLETADA: Navegación exitosa")
            self._log_state("-"*50)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 2 (navegación): {e}", "error")
            return False
    
    async def _etapa3_procesamiento_completo_final(self) -> bool:
        """
        ETAPA 3: Procesamiento completo FINAL con modales reales.
        
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            self.automation_state.update(
                method_name="_etapa3_procesamiento_completo_final",
                action="ETAPA 3: Procesamiento completo final con modales"
            )
            
            self._log_state("⚙️ ETAPA 3: PROCESAMIENTO COMPLETO FINAL")
            self._log_state("-"*50)
            self._log_state("🎯 FUNCIONALIDADES INCLUIDAS:")
            self._log_state("   • Clic en botones de cuentas")
            self._log_state("   • Procesamiento de modales de glosas individuales")
            self._log_state("   • Llenado automático de campos")
            self._log_state("   • Subida de archivos PDF")
            self._log_state("   • Finalización de cuentas")
            self._log_state("   • Manejo de errores y regreso a tabla principal")
            self._log_state("-"*50)
            
            # Inicializar procesador completo implementado
            self.procesador_completo = ProcesadorCompletoGlosasImplementado(
                self.page, 
                self.automation_state
            )
            
            self._log_state("🚀 Iniciando procesamiento completo final...")
            
            # Procesar todas las cuentas con funcionalidad completa
            procesadas, fallidas = await self.procesador_completo.procesar_filas_tabla()
            
            # Actualizar estadísticas globales
            self.estadisticas_globales['total_cuentas_procesadas'] = procesadas
            self.estadisticas_globales['total_cuentas_fallidas'] = fallidas
            
            self._log_state("-"*50)
            self._log_state("📊 RESULTADOS DE PROCESAMIENTO FINAL:")
            self._log_state(f"   • Cuentas procesadas completamente: {procesadas}")
            self._log_state(f"   • Cuentas con errores: {fallidas}")
            
            if procesadas == 0 and fallidas == 0:
                self._log_state("⚠️ ETAPA 3: No se procesaron cuentas", "warning")
                return False
            
            self._log_state("✅ ETAPA 3 COMPLETADA: Procesamiento final terminado")
            self._log_state("-"*50)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 3 (procesamiento final): {e}", "error")
            return False
    
    async def _mantener_abierto_para_inspeccion(self):
        """Mantiene el navegador abierto para inspeccionar la página."""
        try:
            self.automation_state.update(
                method_name="_mantener_abierto_para_inspeccion",
                action="Manteniendo navegador abierto para inspección"
            )
            
            self._log_state("🔍 INSPECCIÓN FINAL")
            self._log_state("-"*50)
            self._log_state("🌐 Navegador abierto para inspección - Se cerrará en 60 segundos")
            
            # Obtener estado final
            if self.navigation_handler:
                final_info = await self.navigation_handler.get_current_page_info()
                self._log_state(f"📋 Estado final: {final_info}")
            
            # Mostrar estadísticas finales de BD
            await self._mostrar_estadisticas_bd()
            
            self._log_state("⏳ Manteniendo navegador abierto por 60 segundos...")
            await asyncio.sleep(60)
            
            self._log_state("🔒 Cerrando navegador...")
            await self.login_handler.logout()
            
        except Exception as e:
            self._log_state(f"❌ Error manteniendo navegador abierto: {e}", "error")
    
    async def _mostrar_resumen_final(self):
        """Muestra resumen final completo del procesamiento."""
        try:
            tiempo_total = self.estadisticas_globales['tiempo_total']
            procesadas = self.estadisticas_globales['total_cuentas_procesadas']
            fallidas = self.estadisticas_globales['total_cuentas_fallidas']
            total = procesadas + fallidas
            
            self._log_state("")
            self._log_state("🎯 RESUMEN FINAL DE AUTOMATIZACIÓN COMPLETA")
            self._log_state("="*100)
            self._log_state(f"⏱️  TIEMPO TOTAL: {tiempo_total:.2f} segundos ({tiempo_total/60:.1f} minutos)")
            self._log_state(f"🏢 CUENTAS TOTALES PROCESADAS: {total}")
            self._log_state(f"✅ CUENTAS COMPLETADAS: {procesadas}")
            self._log_state(f"❌ CUENTAS CON ERRORES: {fallidas}")
            
            if total > 0:
                tasa_exito = (procesadas / total) * 100
                self._log_state(f"📈 TASA DE ÉXITO GLOBAL: {tasa_exito:.1f}%")
                
                if procesadas > 0:
                    tiempo_promedio = tiempo_total / procesadas
                    self._log_state(f"⚡ TIEMPO PROMEDIO POR CUENTA: {tiempo_promedio:.2f} segundos")
                    
                    velocidad = procesadas / (tiempo_total / 3600)  # cuentas por hora
                    self._log_state(f"🚀 VELOCIDAD DE PROCESAMIENTO: {velocidad:.1f} cuentas/hora")
            
            self._log_state("")
            self._log_state("🎯 FUNCIONALIDADES IMPLEMENTADAS:")
            self._log_state("   ✅ Login automático")
            self._log_state("   ✅ Navegación a Bolsa Respuesta")
            self._log_state("   ✅ Clic en botones de cuentas")
            self._log_state("   ✅ Procesamiento de modales de glosas")
            self._log_state("   ✅ Llenado automático de campos")
            self._log_state("   ✅ Subida de archivos PDF")
            self._log_state("   ✅ Finalización de cuentas")
            self._log_state("   ✅ Manejo de errores")
            self._log_state("   ✅ Base de datos completa")
            
            self._log_state("="*100)
            
            # Determinar resultado final
            if procesadas > 0:
                if tasa_exito >= 80:
                    self._log_state("🎉 RESULTADO: AUTOMATIZACIÓN EXITOSA")
                elif tasa_exito >= 50:
                    self._log_state("⚠️ RESULTADO: AUTOMATIZACIÓN PARCIALMENTE EXITOSA")
                else:
                    self._log_state("❌ RESULTADO: AUTOMATIZACIÓN CON PROBLEMAS")
            else:
                self._log_state("❌ RESULTADO: AUTOMATIZACIÓN FALLIDA")
            
        except Exception as e:
            self._log_state(f"❌ Error mostrando resumen final: {e}", "error")
    
    async def _mostrar_estadisticas_bd(self):
        """Muestra estadísticas finales desde la base de datos."""
        try:
            stats = await self._obtener_estadisticas_bd()
            
            self._log_state("")
            self._log_state("💾 ESTADÍSTICAS DESDE BASE DE DATOS")
            self._log_state("-"*50)
            self._log_state(f"🏢 Cuentas PENDIENTES: {stats['pendientes']}")
            self._log_state(f"⚙️ Cuentas EN_PROCESO: {stats['en_proceso']}")
            self._log_state(f"✅ Cuentas COMPLETADAS: {stats['completadas']}")
            self._log_state(f"❌ Cuentas FALLIDAS: {stats['fallidas']}")
            self._log_state(f"📋 Glosas procesadas: {stats['glosas_procesadas']}")
            self._log_state(f"⚠️ Glosas sin configuración: {stats['glosas_sin_config']}")
            self._log_state("-"*50)
            
        except Exception as e:
            self._log_state(f"❌ Error obteniendo estadísticas de BD: {e}", "error")
    
    async def _obtener_estadisticas_bd(self) -> dict:
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
                    'glosas_procesadas': 0,
                    'glosas_sin_config': 0
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
                
                # Estadísticas de glosas procesadas
                try:
                    cursor = conn.execute("""
                        SELECT 
                            COUNT(CASE WHEN estado_procesamiento = 'PROCESADO' THEN 1 END) as procesadas,
                            COUNT(CASE WHEN estado_procesamiento = 'SIN_CONFIG' THEN 1 END) as sin_config
                        FROM glosa_items_detalle
                    """)
                    
                    row = cursor.fetchone()
                    if row:
                        stats['glosas_procesadas'] = row['procesadas'] or 0
                        stats['glosas_sin_config'] = row['sin_config'] or 0
                except:
                    # Si no existe la tabla de detalles, usar 0
                    pass
                
                return stats
                
        except Exception as e:
            self._log_state(f"❌ Error obteniendo estadísticas de BD: {e}", "error")
            return {
                'pendientes': 0,
                'en_proceso': 0,
                'completadas': 0,
                'fallidas': 0,
                'glosas_procesadas': 0,
                'glosas_sin_config': 0
            }