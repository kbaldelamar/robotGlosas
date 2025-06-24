import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState

class ProcesadorGlosasEnPausaIndependiente:
    def __init__(self, page: Page, automation_state: AutomationState, worker_thread=None):
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManagerGlosas()
        self.worker = worker_thread

        self.selectores = {
            'filas_tabla_principal': "#tablaRespuestaGlosaPause tbody tr",
            'boton_cuenta': ".btRespuestaStart",
            'tabla_glosas': "#tableAuditGlosas",
            'filas_glosas': "#tableAuditGlosas tbody tr",
            'boton_glosa_individual': ".btnAnswerGlosaModal",
            'modal_titulo': "#titleModalAnswerGlosa",
            'form_modal': "#formAnswerGlosa",
            'select2_container': "#select2-glosaRespTipo-container",
            'textarea_justificacion': "#glosaRespObs",
            'input_archivo': "#glosaRespFile",
            'boton_responder': "#btnAnswerGlosa",
            'boton_terminar': "#btRespuestaFinish",
            'boton_confirmar_terminar': ".swal2-confirm"
        }
        self.configuraciones_respuesta = {}
        self.url_tabla_en_pausa = None

    def _log(self, mensaje: str, nivel: str = "info"):
        if nivel == "info":
            self.logger.info(mensaje)
        elif nivel == "warning":
            self.logger.warning(mensaje)
        elif nivel == "error":
            self.logger.error(mensaje)

    async def preparar_sistema(self):
        self.url_tabla_en_pausa = self.page.url
        await self.cargar_configuraciones_respuesta()
        await self.configurar_tabla_100_registros()

    async def cargar_configuraciones_respuesta(self):
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT tipo, justificacion_patron, respuesta_automatica, url_pdf
                    FROM glosas_respuestas_config 
                    WHERE activo = 1
                    ORDER BY tipo, justificacion_patron
                """)
                self.configuraciones_respuesta = {}
                for row in cursor.fetchall():
                    key = f"{row['tipo']}_{row['justificacion_patron']}"
                    self.configuraciones_respuesta[key] = {
                        'respuesta': row['respuesta_automatica'],
                        'pdf_path': row['url_pdf'],
                        'tipo': row['tipo'],
                        'patron': row['justificacion_patron']
                    }
        except Exception as e:
            self._log(f"Error cargando configuraciones: {e}", "error")
            self.configuraciones_respuesta = {}

    async def configurar_tabla_100_registros(self):
        try:
            await self.page.evaluate("""
                () => {
                    const select = document.querySelector('select[name="tablaRespuestaGlosaPause_length"]');
                    if (select) {
                        select.value = '100';
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                }
            """)
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(2)
        except Exception as e:
            self._log(f"Error configurando tabla: {e}", "warning")

    async def procesar_cuentas_en_pausa(self, cuentas_en_pausa: List[Dict]) -> Tuple[int, int]:
        await self.preparar_sistema()
        procesadas = 0
        fallidas = 0
        for i, cuenta_data in enumerate(cuentas_en_pausa):
            idcuenta = cuenta_data['idcuenta']
            self._log(f"🔄 PROCESANDO {i + 1}/{len(cuentas_en_pausa)}: {idcuenta}")
            try:
                if await self.hacer_clic_cuenta_en_pausa(idcuenta):
                    self._log(f"[TRACE] Llamando a procesar_glosas_cuenta para {idcuenta}")
                    resultado = await self.procesar_glosas_cuenta(idcuenta)
                    self._log(f"[TRACE] Resultado de procesar_glosas_cuenta: {resultado}")
                    if resultado['exito']:
                        procesadas += 1
                        self._log(f"✅ CUENTA {idcuenta} PROCESADA EN PAUSA")
                        await self.terminar_cuenta()
                    else:
                        fallidas += 1
                        self._log(f"❌ CUENTA {idcuenta} FALLIDA EN PAUSA: {resultado.get('error', '')}")
                else:
                    fallidas += 1
                    self._log(f"❌ CUENTA {idcuenta} NO ENCONTRADA EN PAUSA")
            except Exception as e:
                fallidas += 1
                self._log(f"❌ Error procesando cuenta {idcuenta} EN PAUSA: {e}", "error")
            await asyncio.sleep(2)
        self._log(f"🎉 PROCESAMIENTO EN PAUSA COMPLETADO: {procesadas} procesadas, {fallidas} fallidas")
        return procesadas, fallidas

    async def hacer_clic_cuenta_en_pausa(self, idcuenta: str) -> bool:
        try:
            filas = self.page.locator(self.selectores['filas_tabla_principal'])
            total_filas = await filas.count()
            for i in range(total_filas):
                fila = filas.nth(i)
                celdas = fila.locator("td")
                if await celdas.count() > 0:
                    id_celda = await celdas.nth(0).text_content()
                    if id_celda and id_celda.strip() == idcuenta:
                        boton_cuenta = fila.locator(self.selectores['boton_cuenta'])
                        if await boton_cuenta.count() > 0:
                            await boton_cuenta.first.scroll_into_view_if_needed()
                            await asyncio.sleep(1)
                            await boton_cuenta.first.click()
                            await self.page.wait_for_load_state('networkidle', timeout=15000)
                            await asyncio.sleep(3)
                            return True
            return False
        except Exception as e:
            self._log(f"Error haciendo clic en cuenta EN PAUSA: {e}", "error")
            return False

    async def procesar_glosas_cuenta(self, idcuenta: str) -> Dict:
        try:
            self._log(f"[TRACE] Esperando 6 segundos antes de hacer scroll a la tabla hija de glosas...")
            await asyncio.sleep(6)
            self._log(f"[TRACE] Llamando a hacer_scroll_hasta_tabla_glosas para cuenta {idcuenta}")
            await self.hacer_scroll_hasta_tabla_glosas()
            self._log(f"[TRACE] Llamando a extraer_glosas_de_tabla para cuenta {idcuenta}")
            glosas = await self.extraer_glosas_de_tabla(idcuenta)
            self._log(f"[TRACE] Resultado de extraer_glosas_de_tabla: {len(glosas)} glosas extraidas para cuenta {idcuenta}")
            if not glosas:
                self._log(f"[TRACE] No se encontraron glosas para procesar en cuenta {idcuenta}")
                return {'exito': False, 'error': 'No se encontraron glosas para procesar'}
            glosas_procesadas = 0
            glosas_fallidas = 0
            for glosa in glosas:
                resultado = await self.procesar_glosa_individual(glosa)
                if resultado['exito']:
                    glosas_procesadas += 1
                else:
                    glosas_fallidas += 1
            self._log(f"[TRACE] Fin de procesar_glosas_cuenta para {idcuenta}: {glosas_procesadas} procesadas, {glosas_fallidas} fallidas")
            return {
                'exito': glosas_procesadas > 0,
                'glosas_procesadas': glosas_procesadas,
                'glosas_fallidas': glosas_fallidas
            }
        except Exception as e:
            self._log(f"[TRACE] Excepción en procesar_glosas_cuenta para {idcuenta}: {e}", "error")
            return {'exito': False, 'error': str(e)}

    async def hacer_scroll_hasta_tabla_glosas(self) -> bool:
        try:
            self._log(f"[TRACE] INICIO hacer_scroll_hasta_tabla_glosas")
            tabla_glosas = self.page.locator(self.selectores['tabla_glosas'])
            if await tabla_glosas.count() > 0:
                await tabla_glosas.scroll_into_view_if_needed()
                await asyncio.sleep(2)
                self._log(f"[TRACE] Scroll hasta tabla de glosas realizado")
                return True
            else:
                self._log(f"[TRACE] Tabla de glosas no encontrada, haciendo scroll general")
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
                await asyncio.sleep(3)
                return True
        except Exception as e:
            self._log(f"[TRACE] Error haciendo scroll: {e}", "warning")
            return False

    async def extraer_glosas_de_tabla(self, idcuenta: str) -> List[Dict]:
        try:
            self._log(f"[TRACE] INICIO extraer_glosas_de_tabla para cuenta {idcuenta}")
            glosas = []
            filas = self.page.locator(self.selectores['filas_glosas'])
            total_filas = await filas.count()
            self._log(f"[TRACE] Filas encontradas en tabla hija: {total_filas}")
            for i in range(total_filas):
                fila = filas.nth(i)
                celdas = fila.locator("td")
                if await celdas.count() >= 8:
                    glosa_info = {
                        'id_glosa': await celdas.nth(0).text_content() or "",
                        'id_item': await celdas.nth(1).text_content() or "",
                        'descripcion_item': await celdas.nth(2).text_content() or "",
                        'tipo': await celdas.nth(3).text_content() or "",
                        'descripcion': await celdas.nth(4).text_content() or "",
                        'justificacion': await celdas.nth(5).text_content() or "",
                        'valor_glosado': await celdas.nth(6).text_content() or "",
                        'estado': await celdas.nth(7).text_content() or "",
                        'idcuenta': idcuenta
                    }
                    glosas.append(glosa_info)
            self._log(f"[TRACE] Fin extraer_glosas_de_tabla para cuenta {idcuenta}: {len(glosas)} glosas extraidas")
            return glosas
        except Exception as e:
            self._log(f"[TRACE] Error extrayendo glosas: {e}", "error")
            return []

    async def procesar_glosa_individual(self, glosa_info: Dict) -> Dict:
        try:
            id_glosa = glosa_info.get('id_glosa', '')
            tipo = glosa_info.get('tipo', '')
            justificacion = glosa_info.get('justificacion', '')
            if not await self.hacer_clic_boton_glosa(id_glosa):
                return {'exito': False, 'error': 'No se pudo hacer clic en botón de glosa'}
            if not await self.esperar_modal_abierto(id_glosa):
                return {'exito': False, 'error': 'Modal no se abrió correctamente'}
            configuracion = self.buscar_configuracion_glosa(tipo, justificacion)
            if not configuracion:
                await self.cerrar_modal()
                return {'exito': False, 'error': 'Sin configuración disponible'}
            if not await self.llenar_modal_respuesta(configuracion, glosa_info):
                await self.cerrar_modal()
                return {'exito': False, 'error': 'Error llenando campos del modal'}
            if not await self.guardar_respuesta_modal():
                await self.cerrar_modal()
                return {'exito': False, 'error': 'Error guardando respuesta'}
            await asyncio.sleep(3)
            return {'exito': True}
        except Exception as e:
            await self.cerrar_modal()
            return {'exito': False, 'error': str(e)}

    async def hacer_clic_boton_glosa(self, id_glosa: str) -> bool:
        try:
            boton_glosa = self.page.locator(f'button.btnAnswerGlosaModal[idglosa="{id_glosa}"]')
            if await boton_glosa.count() == 0:
                return False
            await boton_glosa.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            await boton_glosa.click()
            return True
        except Exception:
            return False

    async def esperar_modal_abierto(self, id_glosa: str) -> bool:
        try:
            titulo_modal = self.page.locator(self.selectores['modal_titulo'])
            await titulo_modal.wait_for(state="visible", timeout=10000)
            await asyncio.sleep(2)
            titulo_texto = await titulo_modal.text_content()
            return id_glosa in titulo_texto
        except Exception:
            return False

    def buscar_configuracion_glosa(self, tipo: str, justificacion: str) -> Optional[Dict]:
        for key, config in self.configuraciones_respuesta.items():
            if config['tipo'].upper() == tipo.upper():
                patron = config['patron'].replace('%', '').upper()
                if patron in justificacion.upper():
                    return config
        return None

    async def llenar_modal_respuesta(self, configuracion: Dict, glosa_info: Dict) -> bool:
        try:
            select2_container = self.page.locator(self.selectores['select2_container'])
            await select2_container.click()
            await asyncio.sleep(2)
            opcion = self.page.locator("li.select2-results__option:has-text('999 SUBSANADA')")
            if await opcion.count() > 0:
                await opcion.first.click()
                await asyncio.sleep(1)
            textarea = self.page.locator(self.selectores['textarea_justificacion'])
            await textarea.scroll_into_view_if_needed()
            await textarea.click()
            await asyncio.sleep(0.5)
            await textarea.press('Control+a')
            await textarea.press('Delete')
            await asyncio.sleep(0.5)
            texto = configuracion['respuesta'].upper()
            await self.page.evaluate("""
                (texto) => {
                    const textarea = document.getElementById('glosaRespObs');
                    if (textarea) {
                        textarea.value = texto;
                        textarea.focus();
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                        textarea.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """, texto)
            await asyncio.sleep(0.3)
            await textarea.press('Tab')
            await asyncio.sleep(1)
            pdf_path = configuracion['pdf_path']
            if pdf_path:
                input_file = self.page.locator(self.selectores['input_archivo'])
                await input_file.set_input_files(pdf_path)
                await asyncio.sleep(2)
            return True
        except Exception as e:
            self._log(f"Error llenando modal: {e}", "error")
            return False

    async def guardar_respuesta_modal(self) -> bool:
        try:
            boton_responder = self.page.locator(self.selectores['boton_responder'])
            await boton_responder.scroll_into_view_if_needed()
            await boton_responder.click()
            return True
        except Exception:
            return False

    async def cerrar_modal(self):
        try:
            boton_x = self.page.locator('.close[data-dismiss=\"modal\"]')
            if await boton_x.count() > 0:
                await boton_x.first.click(timeout=3000)
                await asyncio.sleep(1)
                return True
            await self.page.keyboard.press('Escape', timeout=2000)
            await asyncio.sleep(1)
            return True
        except Exception:
            return False

    async def terminar_cuenta(self) -> bool:
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            boton_terminar = self.page.locator(self.selectores['boton_terminar']).filter(has_not=self.page.locator('[disabled]'))
            if await boton_terminar.count() == 0:
                return False
            await boton_terminar.scroll_into_view_if_needed()
            await boton_terminar.click()
            await asyncio.sleep(3)
            boton_confirmar = self.page.locator(self.selectores['boton_confirmar_terminar'])
            await boton_confirmar.wait_for(state="visible", timeout=10000)
            await boton_confirmar.click()
            await asyncio.sleep(2)
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(5)
            return True
        except Exception as e:
            self._log(f"Error terminando cuenta: {e}", "error")
            return False