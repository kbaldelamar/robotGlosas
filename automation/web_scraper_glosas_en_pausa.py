# automation/web_scraper_glosas_en_pausa.py
import asyncio
import logging
from typing import Optional, List, Dict, Tuple
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
    Reutiliza componentes base pero con navegación y lógica específica.
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
            'total_cuentas_recuperadas': 0,
            'tiempo_total': 0
        }
        
        self._log_state("WebScraperGlosasEnPausa inicializado")
        
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
            
            self._log_state("🔄 === INICIANDO AUTOMATIZACIÓN EN PAUSA ===")
            self._log_state("🎯 OBJETIVO: Reprocesar cuentas FALLIDAS y EN_PROCESO con control de intentos")
            self._log_state("="*100)
            
            # ETAPA 1: LOGIN
            if not await self._etapa1_login(username, password):
                return False
            
            # ETAPA 2: NAVEGACIÓN A EN PAUSA
            if not await self._etapa2_navegacion_en_pausa():
                return False
            
            # ETAPA 3: PROCESAMIENTO CON CONTROL DE INTENTOS
            if not await self._etapa3_procesamiento_con_intentos():
                return False
            
            self.estadisticas_globales['fin_proceso'] = asyncio.get_event_loop().time()
            self.estadisticas_globales['tiempo_total'] = (
                self.estadisticas_globales['fin_proceso'] - 
                self.estadisticas_globales['inicio_proceso']
            )
            
            self._log_state("🎉 === AUTOMATIZACIÓN EN PAUSA FINALIZADA ===")
            await self._mostrar_resumen_final()
            
            # Emitir signal final para actualizar interfaz
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
        """ETAPA 2: Navega específicamente a EN PAUSA."""
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
            
            # Navegar específicamente a EN PAUSA
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
    
    async def _etapa3_procesamiento_con_intentos(self) -> bool:
        """
        ETAPA 3: Procesamiento con control específico de intentos.
        
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            self.automation_state.update(
                method_name="_etapa3_procesamiento_con_intentos",
                action="ETAPA 3: Procesamiento con control de intentos"
            )
            
            self._log_state("⚙️ ETAPA 3: PROCESAMIENTO CON CONTROL DE INTENTOS")
            self._log_state("-"*50)
            self._log_state("🎯 FUNCIONALIDADES ESPECÍFICAS EN PAUSA:")
            self._log_state("   • Filtrado de cuentas FALLIDAS y EN_PROCESO")
            self._log_state("   • Control de intentos (máximo 5)")
            self._log_state("   • Incremento automático de intentos")
            self._log_state("   • Actualización de estados en BD")
            self._log_state("-"*50)
            
            # Obtener cuentas EN PAUSA específicas
            cuentas_en_pausa = await self._obtener_cuentas_en_pausa()
            
            if not cuentas_en_pausa:
                self._log_state("⚠️ No hay cuentas EN PAUSA para reprocesar", "warning")
                return False
            
            # Emitir signal de importación de datos
            if self.worker:
                self.worker.emit_data_imported(len(cuentas_en_pausa))
                await asyncio.sleep(1)
            
            # Inicializar procesador con worker
            self.procesador_completo = ProcesadorCompletoGlosasImplementado(
                self.page, 
                self.automation_state,
                worker_thread=self.worker
            )
            
            self._log_state(f"🚀 Iniciando reprocesamiento de {len(cuentas_en_pausa)} cuentas EN PAUSA")
            
            # Procesar cada cuenta con control de intentos
            cuentas_procesadas = 0
            cuentas_fallidas = 0
            cuentas_recuperadas = 0
            
            for i, cuenta_data in enumerate(cuentas_en_pausa):
                idcuenta = cuenta_data['idcuenta']
                intentos_actuales = cuenta_data.get('intentos', 0)
                
                self._log_state(f"🔄 REPROCESANDO {i + 1}/{len(cuentas_en_pausa)}: {idcuenta} (intentos: {intentos_actuales})")
                
                try:
                    # Verificar límite de intentos
                    if intentos_actuales >= 5:
                        self._log_state(f"🚫 Cuenta {idcuenta} excede 5 intentos, saltando")
                        cuentas_fallidas += 1
                        continue
                    
                    # Incrementar intentos ANTES de procesar
                    await self._incrementar_intentos(idcuenta)
                    
                    # Procesar usando el procesador completo
                    resultado = await self.procesador_completo._procesar_cuenta_completa(idcuenta)
                    
                    if resultado['exito']:
                        cuentas_recuperadas += 1
                        cuentas_procesadas += 1
                        self.estadisticas_globales['total_cuentas_recuperadas'] += 1
                        self._log_state(f"✅ CUENTA {idcuenta} RECUPERADA")
                        
                        # Emitir signal de cuenta recuperada
                        if self.worker:
                            self.worker.emit_cuenta_processed(idcuenta, 'COMPLETADO')
                    else:
                        cuentas_fallidas += 1
                        self.estadisticas_globales['total_cuentas_fallidas'] += 1
                        
                        # Marcar como fallida o determinar si sigue en proceso
                        nuevo_intentos = intentos_actuales + 1
                        if nuevo_intentos >= 5:
                            await self._marcar_como_fallida_definitiva(idcuenta, resultado.get('error', ''))
                            if self.worker:
                                self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO_DEFINITIVO')
                        else:
                            if self.worker:
                                self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                        
                        self._log_state(f"❌ CUENTA {idcuenta} FALLÓ (intento {nuevo_intentos}/5)")
                
                except Exception as e:
                    cuentas_fallidas += 1
                    await self._marcar_error_procesamiento(idcuenta, f"Error general: {e}")
                    self._log_state(f"❌ Error procesando {idcuenta}: {e}", "error")
                
                # Pausa entre cuentas
                await asyncio.sleep(3)
                
                # Log de progreso cada 5 cuentas
                if (i + 1) % 5 == 0:
                    porcentaje = ((i + 1) / len(cuentas_en_pausa)) * 100
                    self._log_state(f"📊 PROGRESO: {i + 1}/{len(cuentas_en_pausa)} ({porcentaje:.1f}%)")
            
            # Actualizar estadísticas globales
            self.estadisticas_globales['total_cuentas_procesadas'] = cuentas_procesadas
            self.estadisticas_globales['total_cuentas_fallidas'] = cuentas_fallidas
            
            self._log_state("-"*50)
            self._log_state("📊 RESULTADOS DE REPROCESAMIENTO EN PAUSA:")
            self._log_state(f"   • Cuentas recuperadas: {cuentas_recuperadas}")
            self._log_state(f"   • Cuentas que siguen fallando: {cuentas_fallidas}")
            
            if cuentas_procesadas == 0 and cuentas_fallidas == 0:
                self._log_state("⚠️ ETAPA 3: No se procesaron cuentas", "warning")
                return False
            
            self._log_state("✅ ETAPA 3 COMPLETADA: Reprocesamiento EN PAUSA terminado")
            self._log_state("-"*50)
            return True
            
        except Exception as e:
            self._log_state(f"❌ Error en ETAPA 3 (procesamiento EN PAUSA): {e}", "error")
            return False
    
    async def _obtener_cuentas_en_pausa(self) -> List[Dict]:
        """
        Obtiene cuentas que están EN PAUSA (FALLIDAS y EN_PROCESO) con menos de 5 intentos.
        """
        try:
            self._log_state("📋 Obteniendo cuentas EN PAUSA para reprocesamiento")
            
            # Buscar en BD primero
            cuentas_bd_en_pausa = []
            
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT idcuenta, proveedor, estado, valor_glosado, 
                               fecha_radicacion, COALESCE(intentos, 0) as intentos
                        FROM cuenta_glosas_principal 
                        WHERE estado IN ('FALLIDO', 'EN_PROCESO') 
                        AND COALESCE(intentos, 0) < 5
                        ORDER BY intentos ASC, created_at ASC
                    """)
                    
                    for row in cursor.fetchall():
                        cuentas_bd_en_pausa.append({
                            'idcuenta': row['idcuenta'],
                            'proveedor': row['proveedor'],
                            'estado': row['estado'],
                            'valor_glosado': row['valor_glosado'],
                            'fecha_radicacion': row['fecha_radicacion'],
                            'intentos': row['intentos']
                        })
                    
                    self._log_state(f"🔍 Encontradas {len(cuentas_bd_en_pausa)} cuentas EN PAUSA en BD")
                    
            except Exception as e:
                self._log_state(f"⚠️ Error consultando BD: {e}", "warning")
            
            # Si hay cuentas EN PAUSA en BD, devolverlas
            if cuentas_bd_en_pausa:
                self._log_state("✅ Devolviendo cuentas EN PAUSA desde BD")
                return cuentas_bd_en_pausa
            
            # Si no hay en BD, buscar nuevas desde tabla web
            self._log_state("⚠️ No hay cuentas EN PAUSA en BD, importando desde tabla web")
            cuentas_importadas = await self._obtener_cuentas_desde_tabla_en_pausa()
            
            if cuentas_importadas:
                self._log_state(f"📥 Importadas {len(cuentas_importadas)} cuentas nuevas desde tabla")
                return cuentas_importadas
            else:
                self._log_state("❌ No se pudieron importar cuentas desde la tabla", "error")
                return []
                
        except Exception as e:
            self._log_state(f"❌ Error obteniendo cuentas EN PAUSA: {e}", "error")
            return []
    
    async def _obtener_cuentas_desde_tabla_en_pausa(self) -> List[Dict]:
        """
        Obtiene cuentas desde la tabla web de EN PAUSA y las marca apropiadamente.
        """
        try:
            # Reutilizar el procesador completo para extraer datos
            await self.procesador_completo._preparar_sistema()
            todas_las_cuentas = await self.procesador_completo.extraer_datos_filas_tabla()
            
            if not todas_las_cuentas:
                return []
            
            cuentas_nuevas = []
            
            for cuenta_data in todas_las_cuentas:
                idcuenta = cuenta_data['idcuenta']
                
                # Verificar si debe procesarse
                if self.db_manager.should_process_cuenta(idcuenta):
                    # Crear/actualizar como PENDIENTE inicialmente
                    cuenta_bd_id = self.db_manager.create_or_update_cuenta(cuenta_data)
                    
                    # Marcar como EN_PROCESO para EN PAUSA
                    self.db_manager.update_cuenta_estado(
                        idcuenta, 
                        EstadoCuenta.EN_PROCESO,
                        "Cuenta importada para reprocesamiento EN PAUSA"
                    )
                    
                    cuenta_data['bd_id'] = cuenta_bd_id
                    cuenta_data['intentos'] = 0
                    cuentas_nuevas.append(cuenta_data)
                    
                    self._log_state(f"✅ Cuenta {idcuenta} importada para EN PAUSA")
            
            return cuentas_nuevas
            
        except Exception as e:
            self._log_state(f"❌ Error obteniendo desde tabla EN PAUSA: {e}", "error")
            return []
    
    async def _incrementar_intentos(self, idcuenta: str):
        """Incrementa el número de intentos para una cuenta."""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cuenta_glosas_principal 
                    SET intentos = COALESCE(intentos, 0) + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, (idcuenta,))
                conn.commit()
                
                self._log_state(f"🔢 Intentos incrementados para cuenta {idcuenta}")
                
        except Exception as e:
            self._log_state(f"❌ Error incrementando intentos {idcuenta}: {e}", "error")
    
    async def _marcar_como_fallida_definitiva(self, idcuenta: str, motivo: str):
        """Marca una cuenta como fallida definitiva (5+ intentos)."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,
                f"Fallida definitiva después de 5 intentos: {motivo[:200]}"
            )
            
            self._log_state(f"🚫 Cuenta {idcuenta} marcada como fallida definitiva")
            
        except Exception as e:
            self._log_state(f"❌ Error marcando como fallida definitiva {idcuenta}: {e}", "error")
    
    async def _marcar_error_procesamiento(self, idcuenta: str, error: str):
        """Marca error de procesamiento."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,
                f"Error en procesamiento: {error[:200]}"
            )
            
        except Exception as e:
            self._log_state(f"❌ Error marcando error de procesamiento {idcuenta}: {e}", "error")
    
    async def _mostrar_resumen_final(self):
        """Muestra resumen final del reprocesamiento EN PAUSA."""
        try:
            tiempo_total = self.estadisticas_globales['tiempo_total']
            procesadas = self.estadisticas_globales['total_cuentas_procesadas']
            fallidas = self.estadisticas_globales['total_cuentas_fallidas']
            recuperadas = self.estadisticas_globales['total_cuentas_recuperadas']
            total = procesadas + fallidas
            
            self._log_state("")
            self._log_state("🎯 RESUMEN FINAL DE REPROCESAMIENTO EN PAUSA")
            self._log_state("="*100)
            self._log_state(f"⏱️  TIEMPO TOTAL: {tiempo_total:.2f} segundos ({tiempo_total/60:.1f} minutos)")
            self._log_state(f"🔄 CUENTAS EN PAUSA PROCESADAS: {total}")
            self._log_state(f"✅ CUENTAS RECUPERADAS: {recuperadas}")
            self._log_state(f"❌ CUENTAS AÚN FALLIDAS: {fallidas}")
            
            if total > 0:
                tasa_recuperacion = (recuperadas / total) * 100
                self._log_state(f"📈 TASA DE RECUPERACIÓN: {tasa_recuperacion:.1f}%")
                
                if recuperadas > 0:
                    tiempo_promedio = tiempo_total / recuperadas
                    self._log_state(f"⚡ TIEMPO PROMEDIO POR RECUPERACIÓN: {tiempo_promedio:.2f} segundos")
                    
                    velocidad = recuperadas / (tiempo_total / 3600)  # recuperaciones por hora
                    self._log_state(f"🚀 VELOCIDAD DE RECUPERACIÓN: {velocidad:.1f} cuentas/hora")
            
            self._log_state("")
            self._log_state("🎯 ESPECÍFICO PARA EN PAUSA:")
            self._log_state("   ✅ Navegación específica a 'En Pausa'")
            self._log_state("   ✅ Filtrado de cuentas FALLIDAS y EN_PROCESO")
            self._log_state("   ✅ Control de intentos (máximo 5)")
            self._log_state("   ✅ Incremento automático de intentos")
            self._log_state("   ✅ Separación completa de lógica")
            self._log_state("="*100)
            
            # Determinar resultado final
            if recuperadas > 0:
                if tasa_recuperacion >= 50:
                    self._log_state("🎉 RESULTADO: REPROCESAMIENTO EN PAUSA EXITOSO")
                else:
                    self._log_state("⚠️ RESULTADO: REPROCESAMIENTO EN PAUSA PARCIAL")
            else:
                self._log_state("❌ RESULTADO: NO SE RECUPERARON CUENTAS")
            
        except Exception as e:
            self._log_state(f"❌ Error mostrando resumen final: {e}", "error")
    
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
            
            # Mostrar estadísticas finales de BD
            await self._mostrar_estadisticas_bd()
            
            self._log_state("⏳ Manteniendo navegador abierto por 60 segundos...")
            await asyncio.sleep(60)
            
            self._log_state("🔒 Cerrando navegador...")
            await self.login_handler.logout()
            
        except Exception as e:
            self._log_state(f"❌ Error manteniendo navegador abierto: {e}", "error")
    
    async def _mostrar_estadisticas_bd(self):
        """Muestra estadísticas finales desde la base de datos."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        estado,
                        COUNT(*) as count,
                        AVG(COALESCE(intentos, 0)) as promedio_intentos,
                        MAX(COALESCE(intentos, 0)) as max_intentos
                    FROM cuenta_glosas_principal 
                    GROUP BY estado
                """)
                
                self._log_state("")
                self._log_state("💾 ESTADÍSTICAS FINALES DESDE BASE DE DATOS")
                self._log_state("-"*50)
                
                for row in cursor.fetchall():
                    estado = row['estado']
                    count = row['count']
                    promedio = row['promedio_intentos']
                    maximo = row['max_intentos']
                    
                    self._log_state(f"🏢 {estado}: {count} cuentas (promedio intentos: {promedio:.1f}, máx: {maximo})")
                
                self._log_state("-"*50)
                
        except Exception as e:
            self._log_state(f"❌ Error obteniendo estadísticas de BD: {e}", "error")