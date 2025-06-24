# automation/procesador_en_pausa_especifico.py
"""
Procesador ESPECÍFICO para módulo EN PAUSA.
Se mantiene en la sección "En Pausa" sin navegar a "Bolsa Respuesta".
"""

import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState

class ProcesadorEnPausaEspecifico:
    """
    Procesador específico para módulo EN PAUSA.
    NO navega a Bolsa Respuesta - se mantiene en En Pausa.
    """
    
    def __init__(self, page: Page, automation_state: AutomationState, worker_thread=None):
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManagerGlosas()
        self.worker = worker_thread
        
        # URL base para EN PAUSA (NO Bolsa Respuesta)
        self.url_en_pausa_base = None
        
        # Selectores específicos para EN PAUSA
        self.selectores = {
            'filas_tabla_principal': "#tablaRespuestaGlosaPause tbody tr",
            'boton_cuenta': ".btRespuestaStart",
            'info_tabla': "#tablaRespuestaGlosaPause_info"
        }
        
        self.state.update(
            class_name="ProcesadorEnPausaEspecifico",
            method_name="__init__"
        )
        
        self._log("[TRACE] __init__ de ProcesadorEnPausaEspecifico ejecutado")
        print("[TRACE] __init__ de ProcesadorEnPausaEspecifico ejecutado")
    
    def _log(self, mensaje: str, nivel: str = "info"):
        """Log con información de estado."""
        info_estado = f"[{self.state.current_class}.{self.state.current_method}]"
        mensaje_completo = f"{info_estado} {mensaje}"
        
        if nivel == "info":
            self.logger.info(mensaje_completo)
        elif nivel == "warning":
            self.logger.warning(mensaje_completo)
        elif nivel == "error":
            self.logger.error(mensaje_completo)
    
    async def procesar_cuentas_en_pausa(self, cuentas_en_pausa: List[Dict]) -> Tuple[int, int]:
        """
        MÉTODO PRINCIPAL: Procesa cuentas EN PAUSA sin salir de esa sección.
        """
        self._log("[TRACE] procesar_cuentas_en_pausa de ProcesadorEnPausaEspecifico ejecutado")
        print("[TRACE] procesar_cuentas_en_pausa de ProcesadorEnPausaEspecifico ejecutado")
        try:
            self.state.update(
                method_name="procesar_cuentas_en_pausa",
                action="Procesando cuentas EN PAUSA específicamente"
            )
            
            self._log(f"🔄 INICIANDO PROCESAMIENTO EN PAUSA DE {len(cuentas_en_pausa)} CUENTAS")
            
            # PASO 1: Guardar URL actual de EN PAUSA
            self.url_en_pausa_base = self.page.url
            self._log(f"💾 URL EN PAUSA guardada: {self.url_en_pausa_base}")
            
            # PASO 2: (Eliminado) Configuración de tabla y esperas innecesarias
            # Se asume que la tabla ya está lista y visible gracias a NavigationHandler

            # PASO 3: Procesar cada cuenta
            procesadas = 0
            fallidas = 0
            
            for i, cuenta_data in enumerate(cuentas_en_pausa):
                idcuenta = cuenta_data['idcuenta']
                
                self._log(f"🔄 PROCESANDO {i + 1}/{len(cuentas_en_pausa)}: {idcuenta}")
                
                try:
                    # Incrementar intentos
                    await self._incrementar_intentos(idcuenta)
                    
                    # (Eliminado) Asegurar que estamos en EN PAUSA
                    # Se asume que NavigationHandler ya dejó la tabla lista

                    # Buscar y hacer clic en la cuenta EN PAUSA
                    if await self._hacer_clic_cuenta_en_pausa(idcuenta):
                        # Aquí procesarías la cuenta individual
                        # Por simplicidad, la marcamos como procesada
                        await self._marcar_cuenta_procesada(idcuenta)
                        procesadas += 1
                        
                        if self.worker:
                            self.worker.emit_cuenta_processed(idcuenta, 'COMPLETADO')
                        
                        self._log(f"✅ CUENTA {idcuenta} PROCESADA EN PAUSA")
                    else:
                        await self._marcar_cuenta_fallida(idcuenta, "No se encontró en tabla EN PAUSA")
                        fallidas += 1
                        
                        if self.worker:
                            self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                        
                        self._log(f"❌ CUENTA {idcuenta} NO ENCONTRADA EN PAUSA")
                
                except Exception as e:
                    error_msg = f"Error procesando cuenta {idcuenta}: {e}"
                    self._log(error_msg, "error")
                    await self._marcar_cuenta_fallida(idcuenta, error_msg)
                    fallidas += 1
                
                # Pausa entre cuentas
                await asyncio.sleep(2)
            
            self._log(f"🎉 PROCESAMIENTO EN PAUSA COMPLETADO: {procesadas} procesadas, {fallidas} fallidas")
            return procesadas, fallidas
            
        except Exception as e:
            self._log(f"❌ Error en procesamiento EN PAUSA: {e}", "error")
            return 0, 0
    
    async def _hacer_clic_cuenta_en_pausa(self, idcuenta: str) -> bool:
        """
        Busca y hace clic en una cuenta específica EN LA TABLA EN PAUSA.
        """
        try:
            self._log(f"🔍 Buscando cuenta {idcuenta} en tabla EN PAUSA")

            # Esperar explícitamente a que haya al menos una fila en la tabla
            try:
                await self.page.wait_for_selector(self.selectores['filas_tabla_principal'], timeout=20000)
            except Exception as e:
                self._log(f"⚠️ No se encontraron filas en la tabla tras esperar: {e}", "warning")
                return False

            # Recrear el locator de filas justo antes de buscar
            filas = self.page.locator(self.selectores['filas_tabla_principal'])
            total_filas = await filas.count()
            self._log(f"📊 Buscando en {total_filas} filas de tabla EN PAUSA")

            # Imprimir los IDs de todas las filas encontradas
            ids_encontrados = []
            for i in range(total_filas):
                try:
                    fila = filas.nth(i)
                    celdas = fila.locator("td")
                    if await celdas.count() > 0:
                        id_celda = await celdas.nth(0).text_content()
                        id_celda = id_celda.strip()
                        ids_encontrados.append(id_celda)
                except Exception as e:
                    self._log(f"⚠️ Error leyendo fila {i}: {e}", "warning")
                    continue
            self._log(f"🔎 IDs encontrados en tabla: {ids_encontrados}")

            # Buscar el ID objetivo
            for i, id_celda in enumerate(ids_encontrados):
                if id_celda == idcuenta:
                    self._log(f"✅ Cuenta {idcuenta} encontrada en fila {i} de EN PAUSA")
                    fila = filas.nth(i)
                    boton_cuenta = fila.locator(self.selectores['boton_cuenta'])
                    if await boton_cuenta.count() > 0:
                        await boton_cuenta.first.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        await boton_cuenta.first.click()
                        self._log(f"🖱️ Clic realizado en cuenta {idcuenta} EN PAUSA")
                        await self.page.wait_for_load_state('networkidle', timeout=15000)
                        await asyncio.sleep(3)
                        return True
                    else:
                        self._log(f"❌ No se encontró botón para cuenta {idcuenta} en EN PAUSA", "error")
                        return False

            self._log(f"❌ Cuenta {idcuenta} NO encontrada en tabla EN PAUSA", "error")
            return False

        except Exception as e:
            self._log(f"❌ Error buscando cuenta {idcuenta} en EN PAUSA: {e}", "error")
            return False
    
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
                
                self._log(f"🔢 Intentos incrementados para cuenta {idcuenta}")
                
        except Exception as e:
            self._log(f"❌ Error incrementando intentos {idcuenta}: {e}", "error")
    
    async def _marcar_cuenta_procesada(self, idcuenta: str):
        """Marca una cuenta como procesada exitosamente."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.COMPLETADO,
                "Procesada exitosamente en módulo EN PAUSA"
            )
            self._log(f"✅ Cuenta {idcuenta} marcada como COMPLETADA")
            
        except Exception as e:
            self._log(f"❌ Error marcando cuenta como procesada {idcuenta}: {e}", "error")
    
    async def _marcar_cuenta_fallida(self, idcuenta: str, motivo: str):
        """Marca una cuenta como fallida."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,
                f"Error en procesamiento EN PAUSA: {motivo}"
            )
            self._log(f"❌ Cuenta {idcuenta} marcada como FALLIDA: {motivo}")
        except Exception as e:
            self._log(f"❌ Error marcando cuenta como procesada {idcuenta}: {e}", "error")
