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
from automation.procesador_completo_glosas_final import ProcesadorCompletoGlosasImplementado



class ProcesadorEnPausaEspecifico(ProcesadorCompletoGlosasImplementado):
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

        # Selector para las filas de la tabla EN PAUSA (ajusta según tu HTML real)
        self.selectores = {
            "filas_tabla_principal": "table#tablaRespuestaGlosaPause > tbody > tr"
        }

        self.state.update(
            class_name="ProcesadorEnPausaEspecifico",
            method_name="__init__"
        )
        self._log("[CORREGIDO] ProcesadorEnPausaEspecifico inicializado con procesador heredado")
    
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
        Procesa las cuentas en pausa usando la lógica heredada.
        """
        try:
            self.state.update(
                method_name="procesar_cuentas_en_pausa",
                action="Procesando cuentas en pausa usando lógica base"
            )
            self._log(f"🔄 Procesando {len(cuentas_en_pausa)} cuentas EN PAUSA")
            # Llama al método heredado (ajusta el nombre si es diferente)
            procesadas, fallidas = await self.procesar_cuentas_en_pausa_especificas(cuentas_en_pausa)
            self._log(f"✅ Procesamiento completado: Procesadas: {procesadas} | Fallidas: {fallidas}")
            return procesadas, fallidas
        except Exception as e:
            self._log(f"❌ Error en procesamiento: {e}", "error")
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
    
    async def extraer_datos_filas_tabla(self) -> List[Dict]:
        """
        Extrae los datos de todas las filas visibles en la tabla EN PAUSA.
        Retorna una lista de diccionarios con los datos de cada cuenta.
        """
        self._log("📋 Extrayendo datos de filas de la tabla EN PAUSA")
        cuentas = []
        try:
            # Ajusta el selector al de la tabla EN PAUSA
            filas = self.page.locator(self.selectores['filas_tabla_principal'])
            total_filas = await filas.count()
            self._log(f"🔎 Total filas encontradas en EN PAUSA: {total_filas}")

            for i in range(total_filas):
                fila = filas.nth(i)
                celdas = fila.locator("td")
                if await celdas.count() < 5:
                    continue  # Salta filas incompletas

                # Ajusta los índices según el orden de columnas de la tabla EN PAUSA
                idcuenta = (await celdas.nth(0).text_content() or "").strip()
                proveedor = (await celdas.nth(1).text_content() or "").strip()
                estado = (await celdas.nth(2).text_content() or "").strip()
                valor_glosado = (await celdas.nth(3).text_content() or "").strip()
                fecha_radicacion = (await celdas.nth(4).text_content() or "").strip()
                # Agrega más campos si tu tabla tiene más columnas relevantes

                cuentas.append({
                    "idcuenta": idcuenta,
                    "proveedor": proveedor,
                    "estado": estado,
                    "valor_glosado": valor_glosado,
                    "fecha_radicacion": fecha_radicacion,
                    # ...otros campos si es necesario...
                })
            self._log(f"✅ Extracción completada. Total cuentas: {len(cuentas)}")
        except Exception as e:
            self._log(f"❌ Error extrayendo filas de tabla EN PAUSA: {e}", "error")
        return cuentas
    
    async def procesar_y_guardar_cuentas(self, cuentas_extraidas: List[Dict]):
        """
        Guarda las cuentas extraídas en la base de datos con estado FALLIDO.
        """
        self._log(f"💾 Guardando {len(cuentas_extraidas)} cuentas EN PAUSA en base de datos")
        try:
            for cuenta in cuentas_extraidas:
                self.db_manager.crear_cuenta_glosa_pausa(
                    idcuenta=cuenta['idcuenta'],
                    proveedor=cuenta['proveedor'],
                    valor_glosado=cuenta['valor_glosado'],
                    fecha_radicacion=cuenta['fecha_radicacion'],
                    # ...otros campos si necesitas...
                )
            self._log(f"✅ Guardado completado. Total cuentas guardadas: {len(cuentas_extraidas)}")
        except Exception as e:
            self._log(f"❌ Error guardando cuentas en base de datos: {e}", "error")
    
    async def ejecutar(self):
        """Método principal para ejecutar el procesador en pausa específico."""
        self._log("▶️ Iniciando procesamiento de cuentas en pausa")
        try:
            # Extraer cuentas en pausa de la tabla
            cuentas_extraidas = await self.extraer_datos_filas_tabla()
            await self.procesar_y_guardar_cuentas(cuentas_extraidas)

            self._log("✅ Proceso de cuentas en pausa completado")
        except Exception as e:
            self._log(f"❌ Error en el proceso de cuentas en pausa: {e}", "error")
