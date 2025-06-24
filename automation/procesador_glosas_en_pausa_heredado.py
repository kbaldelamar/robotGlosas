# automation/procesador_glosas_en_pausa_heredado.py
import asyncio
import logging
from typing import List, Dict, Tuple
from playwright.async_api import Page
from automation.procesador_completo_glosas_final import ProcesadorCompletoGlosasImplementado
from automation.navigation_handler import AutomationState, NavigationHandler
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta

class ProcesadorGlosasEnPausaHeredado(ProcesadorCompletoGlosasImplementado):
    """
    Procesador específico para "En Pausa" que hereda toda la lógica de procesamiento
    del ProcesadorCompletoGlosasImplementado pero adapta la navegación.
    
    ✅ VENTAJAS:
    - Reutiliza TODA la lógica de procesamiento existente
    - No daña el código que funciona
    - Solo modifica la navegación específica
    - Mantiene compatibilidad completa
    
    ✅ SOBRESCRIBE SOLO:
    - URL base (mantiene "En Pausa" en lugar de "Bolsa Respuesta")
    - Método de regreso a tabla principal
    - Preparación del sistema (para "En Pausa")
    """
    
    def __init__(self, page: Page, automation_state: AutomationState, worker_thread=None):
        """
        Inicializa el procesador heredado específico para EN PAUSA.
        
        Args:
            page (Page): Página de Playwright
            automation_state (AutomationState): Estado compartido de automatización
            worker_thread: Thread con signals para actualización en tiempo real
        """
        # Llamar al constructor padre (hereda TODA la funcionalidad)
        super().__init__(page, automation_state, worker_thread)
        
        # Cambiar identificador de clase para logs
        self.state.update(
            class_name="ProcesadorGlosasEnPausaHeredado",
            method_name="__init__"
        )
        
        # ✅ ESPECÍFICO PARA EN PAUSA: URL base diferente
        self.url_tabla_en_pausa = None  # Se establecerá dinámicamente
        
        # ✅ ESPECÍFICO PARA EN PAUSA: Estadísticas adicionales
        self.estadisticas_en_pausa = {
            'cuentas_recuperadas': 0,
            'intentos_previos_promedio': 0,
            'cuentas_definitivamente_fallidas': 0
        }
        
        self._log("🔄 ProcesadorGlosasEnPausaHeredado inicializado - HEREDA funcionalidad completa")
        self._log("✅ Lógica de procesamiento: REUTILIZADA del padre")
        self._log("🔄 Navegación: ADAPTADA para En Pausa")
    
    # ========================================================================
    # ✅ MÉTODOS SOBRESCRITOS (SOLO LOS DE NAVEGACIÓN)
    # ========================================================================
    
    async def _preparar_sistema(self) -> bool:
        """
        ✅ SOBRESCRITO: Prepara el sistema pero mantiene URL de "En Pausa".
        """
        try:
            self._log("🔧 Preparando sistema para EN PAUSA (versión heredada)")
            
            # ✅ DIFERENCIA: Guardar URL de EN PAUSA en lugar de Bolsa Respuesta
            self.url_tabla_en_pausa = self.page.url
            self.url_tabla_principal = self.url_tabla_en_pausa  # Para compatibilidad con métodos padre
            
            self._log(f"💾 URL EN PAUSA guardada: {self.url_tabla_en_pausa}")
            
            # ✅ REUTILIZAR: Resto de la lógica del padre
            await self._cargar_configuraciones_respuesta()
            await self._configurar_tabla_100_registros()
            
            self._log("✅ Sistema preparado para EN PAUSA (funcionalidad heredada)")
            return True
            
        except Exception as e:
            self._log(f"❌ Error preparando sistema EN PAUSA: {e}", "error")
            return False
    
    async def _regresar_tabla_principal(self):
        """
        ✅ SOBRESCRITO: Regresa a "En Pausa" en lugar de "Bolsa Respuesta".
        """
        try:
            self._log("↩️ Regresando a tabla EN PAUSA (no a Bolsa Respuesta)")
            
            if self.url_tabla_en_pausa:
                await self.page.goto(self.url_tabla_en_pausa)
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(3)
                self._log("✅ Regresado a tabla EN PAUSA exitosamente")
            else:
                # ✅ FALLBACK: Navegar específicamente a En Pausa
                self._log("🔄 URL EN PAUSA no guardada, navegando con NavigationHandler...")
                await self.navigation_handler.navigate_to_respuesta_glosas()
                await self.navigation_handler.navigate_to_en_pausa()
                self._log("✅ Navegación a EN PAUSA completada como fallback")
            
        except Exception as e:
            self._log(f"❌ Error regresando a tabla EN PAUSA: {e}", "error")
    
    async def _asegurar_tabla_principal(self) -> bool:
        """
        ✅ SOBRESCRITO: Se asegura de estar en tabla EN PAUSA.
        """
        try:
            url_actual = self.page.url
            
            # ✅ VERIFICAR: Si estamos en una URL de procesamiento, regresar a EN PAUSA
            if "respuestaGlosastart" in url_actual and self.url_tabla_en_pausa:
                if url_actual != self.url_tabla_en_pausa:
                    self._log("🔄 No estamos en tabla EN PAUSA, regresando...")
                    await self._regresar_tabla_principal()
                    return True
            
            return True
            
        except Exception as e:
            self._log(f"❌ Error asegurando tabla EN PAUSA: {e}", "error")
            return False
    
    # ========================================================================
    # ✅ MÉTODOS ESPECÍFICOS PARA EN PAUSA (NUEVOS)
    # ========================================================================
    
    async def procesar_cuentas_en_pausa_especificas(self, cuentas_en_pausa: List[Dict]) -> Tuple[int, int]:
        """
        ✅ MÉTODO PRINCIPAL ESPECÍFICO: Procesa cuentas EN PAUSA con lógica adaptada.
        
        Args:
            cuentas_en_pausa (List[Dict]): Lista de cuentas para reprocesar
            
        Returns:
            Tuple[int, int]: (cuentas_recuperadas, cuentas_fallidas)
        """
        try:
            self.state.update(
                method_name="procesar_cuentas_en_pausa_especificas",
                action="Procesando cuentas EN PAUSA con herencia"
            )
            
            self._log("🔄 === INICIANDO PROCESAMIENTO EN PAUSA HEREDADO ===")
            self._log(f"📊 Cuentas a reprocesar: {len(cuentas_en_pausa)}")
            self._log("✅ Funcionalidad heredada: Procesamiento completo de glosas")
            self._log("🔄 Funcionalidad adaptada: Navegación específica EN PAUSA")
            self._log("="*80)
            
            # ✅ REUTILIZAR: Preparación del sistema (pero adaptada)
            if not await self._preparar_sistema():
                return 0, 0
            
            cuentas_recuperadas = 0
            cuentas_fallidas = 0
            
            for i, cuenta_data in enumerate(cuentas_en_pausa):
                idcuenta = cuenta_data['idcuenta']
                intentos_actuales = cuenta_data.get('intentos', 0)
                
                self._log("")
                self._log(f"🎯 REPROCESANDO EN PAUSA {i + 1}/{len(cuentas_en_pausa)}: {idcuenta}")
                self._log(f"   Intentos anteriores: {intentos_actuales}")
                self._log(f"   Estado actual: {cuenta_data.get('estado', 'N/A')}")
                
                try:
                    # ✅ ESPECÍFICO EN PAUSA: Incrementar intentos
                    await self._incrementar_intentos_en_pausa(idcuenta)
                    
                    # ✅ REUTILIZAR: Lógica completa del padre
                    resultado = await self._procesar_cuenta_completa(idcuenta)
                    
                    if resultado['exito']:
                        cuentas_recuperadas += 1
                        self.estadisticas_en_pausa['cuentas_recuperadas'] += 1
                        
                        self._log(f"✅ CUENTA {idcuenta} RECUPERADA EN PAUSA")
                        self._log(f"   • Glosas procesadas: {resultado.get('glosas_procesadas', 0)}")
                        
                        # Emitir signal de recuperación
                        if self.worker:
                            self.worker.emit_cuenta_processed(idcuenta, 'COMPLETADO')
                    else:
                        cuentas_fallidas += 1
                        
                        # ✅ ESPECÍFICO EN PAUSA: Verificar límite de intentos
                        nuevo_intentos = intentos_actuales + 1
                        if nuevo_intentos >= 5:
                            await self._marcar_como_fallida_definitiva_en_pausa(idcuenta, resultado.get('error', ''))
                            self.estadisticas_en_pausa['cuentas_definitivamente_fallidas'] += 1
                            self._log(f"🚫 CUENTA {idcuenta} FALLÓ DEFINITIVAMENTE (5+ intentos)")
                            
                            if self.worker:
                                self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO_DEFINITIVO')
                        else:
                            self._log(f"❌ CUENTA {idcuenta} FALLÓ (intento {nuevo_intentos}/5)")
                            
                            if self.worker:
                                self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                
                except Exception as e:
                    cuentas_fallidas += 1
                    error_msg = f"Error procesando cuenta EN PAUSA {idcuenta}: {e}"
                    self._log(error_msg, "error")
                    
                    await self._marcar_error_procesamiento_en_pausa(idcuenta, str(e))
                    
                    if self.worker:
                        self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                
                # Pausa entre cuentas
                await asyncio.sleep(3)
                
                # Log de progreso
                if (i + 1) % 3 == 0:
                    porcentaje = ((i + 1) / len(cuentas_en_pausa)) * 100
                    self._log(f"📊 PROGRESO EN PAUSA: {i + 1}/{len(cuentas_en_pausa)} ({porcentaje:.1f}%)")
                    self._log(f"   • ✅ Recuperadas: {cuentas_recuperadas}")
                    self._log(f"   • ❌ Fallidas: {cuentas_fallidas}")
            
            # ✅ MOSTRAR ESTADÍSTICAS ESPECÍFICAS
            await self._mostrar_estadisticas_en_pausa(cuentas_recuperadas, cuentas_fallidas, len(cuentas_en_pausa))
            
            self._log("="*80)
            self._log("🎉 PROCESAMIENTO EN PAUSA HEREDADO COMPLETADO")
            
            return cuentas_recuperadas, cuentas_fallidas
            
        except Exception as e:
            self._log(f"❌ Error crítico en procesamiento EN PAUSA heredado: {e}", "error")
            return 0, 0
    
    # ========================================================================
    # ✅ MÉTODOS AUXILIARES ESPECÍFICOS PARA EN PAUSA
    # ========================================================================
    async def _navegar_y_hacer_clic_cuenta(self, idcuenta: str) -> bool:
        try:
            self._log(f"🖱️ [EN PAUSA] Navegando y haciendo clic en cuenta {idcuenta}")
            filas = self.page.locator("#tablaRespuestaGlosaPause tbody tr")
            total_filas = await filas.count()
            self._log(f"🔍 [EN PAUSA] Buscando cuenta {idcuenta} en {total_filas} filas disponibles")
            for i in range(total_filas):
                fila = filas.nth(i)
                celdas = fila.locator("td")
                if await celdas.count() > 0:
                    id_celda = await celdas.nth(0).text_content()
                    if id_celda and id_celda.strip() == idcuenta:
                        self._log(f"✅ [EN PAUSA] Cuenta {idcuenta} encontrada en fila {i}")
                        boton_cuenta = fila.locator(".btRespuestaStart")
                        if await boton_cuenta.count() == 0:
                            self._log(f"❌ [EN PAUSA] No se encontró botón en la fila de cuenta {idcuenta}", "error")
                            return False
                        await boton_cuenta.first.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        await boton_cuenta.first.click()
                        self._log(f"🖱️ [EN PAUSA] Clic realizado en botón de cuenta {idcuenta}")
                        await self.page.wait_for_load_state('networkidle', timeout=15000)
                        await asyncio.sleep(5)
                        return True
            self._log(f"❌ [EN PAUSA] Cuenta {idcuenta} no encontrada en la tabla actual", "error")
            return False
        except Exception as e:
            self._log(f"❌ [EN PAUSA] Error navegando/haciendo clic cuenta {idcuenta}: {e}", "error")
            return False
    
    async def _incrementar_intentos_en_pausa(self, idcuenta: str):
        """Incrementa el número de intentos para una cuenta EN PAUSA."""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cuenta_glosas_principal 
                    SET intentos = COALESCE(intentos, 0) + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idcuenta = ?
                """, (idcuenta,))
                conn.commit()
                self._log(f"🔢 Intentos incrementados para cuenta EN PAUSA {idcuenta}")
        except Exception as e:
            self._log(f"❌ Error incrementando intentos EN PAUSA {idcuenta}: {e}", "error")


    async def _marcar_como_fallida_definitiva_en_pausa(self, idcuenta: str, motivo: str):
        """Marca una cuenta como fallida definitiva EN PAUSA (5+ intentos)."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,
                f"FALLIDA DEFINITIVA EN PAUSA después de 5 intentos: {motivo[:200]}"
            )
            self._log(f"🚫 Cuenta EN PAUSA {idcuenta} marcada como fallida definitiva")
        except Exception as e:
            self._log(f"❌ Error marcando como fallida definitiva EN PAUSA {idcuenta}: {e}", "error")

    
    async def _marcar_error_procesamiento_en_pausa(self, idcuenta: str, error: str):
     """Marca error de procesamiento EN PAUSA."""
     try:
         self.db_manager.update_cuenta_estado(
             idcuenta, 
             EstadoCuenta.FALLIDO,
             f"Error EN PAUSA: {error[:200]}"
         )
     except Exception as e:
         self._log(f"❌ Error marcando error EN PAUSA {idcuenta}: {e}", "error")

    
    async def _mostrar_estadisticas_en_pausa(self, recuperadas: int, fallidas: int, total: int):
        """Muestra estadísticas específicas del reprocesamiento EN PAUSA."""
        try:
            tiempo_total = asyncio.get_event_loop().time() - self.estadisticas['tiempo_inicio']
            self._log("")
            self._log("📊 ESTADÍSTICAS ESPECÍFICAS DE REPROCESAMIENTO EN PAUSA")
            self._log("="*80)
            self._log(f"⏱️  TIEMPO TOTAL EN PAUSA: {tiempo_total:.2f} segundos")
            self._log(f"🔄 CUENTAS REPROCESADAS: {total}")
            self._log(f"✅ CUENTAS RECUPERADAS: {recuperadas}")
            self._log(f"❌ CUENTAS AÚN FALLIDAS: {fallidas}")
            self._log(f"🚫 FALLIDAS DEFINITIVAS: {self.estadisticas_en_pausa['cuentas_definitivamente_fallidas']}")
            if total > 0:
                tasa_recuperacion = (recuperadas / total) * 100
                self._log(f"📈 TASA DE RECUPERACIÓN EN PAUSA: {tasa_recuperacion:.1f}%")
                if recuperadas > 0:
                    tiempo_promedio = tiempo_total / recuperadas
                    self._log(f"⚡ TIEMPO PROMEDIO POR RECUPERACIÓN: {tiempo_promedio:.2f}s")
            self._log("")
            self._log("🎯 FUNCIONALIDADES HEREDADAS UTILIZADAS:")
            self._log("   ✅ Lógica completa de procesamiento de glosas")
            self._log("   ✅ Manejo de modales y respuestas automáticas")
            self._log("   ✅ Base de datos y estados")
            self._log("   ✅ Sistema de configuraciones")
            self._log("   🔄 Navegación adaptada para EN PAUSA")
            self._log("="*80)
        except Exception as e:
            self._log(f"❌ Error mostrando estadísticas EN PAUSA: {e}", "error")
        


    # ========================================================================
    # ✅ TODOS LOS DEMÁS MÉTODOS SE HEREDAN AUTOMÁTICAMENTE
    # ========================================================================
    # 
    # Los siguientes métodos se heredan del padre sin cambios:
    # - _procesar_cuenta_completa()
    # - _procesar_todas_las_glosas_cuenta()
    # - _procesar_glosa_individual()
    # - _hacer_clic_boton_glosa()
    # - _esperar_modal_abierto()
    # - _buscar_configuracion_glosa()
    # - _llenar_modal_respuesta()
    # - _seleccionar_respuesta_dropdown()
    # - _llenar_justificacion()
    # - _subir_archivo_pdf()
    # - _guardar_respuesta_modal()
    # - _terminar_cuenta()
    # - _confirmar_terminar()
    # - _extraer_glosas_de_tabla()
    # - _parsear_moneda()
    # - Y TODOS los demás métodos de procesamiento
        # ✅ RESULTADO: Funcionalidad completa con navegación adaptada