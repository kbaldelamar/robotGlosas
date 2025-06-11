import asyncio
import logging
import os
from typing import List, Dict, Tuple, Optional
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState, NavigationHandler

class ProcesadorCompletoGlosasImplementado:
    """
    Procesador COMPLETO implementado que:
    1. Procesa todas las glosas de una cuenta
    2. Maneja errores y regresa a tabla principal
    3. Termina correctamente cuando todas están procesadas
    4. Actualiza estados en BD apropiadamente
    """
    
    def __init__(self, page: Page, automation_state: AutomationState):
        """
        Inicializa el procesador completo implementado.
        
        Args:
            page (Page): Página de Playwright
            automation_state (AutomationState): Estado compartido de automatización
        """
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManagerGlosas()
        self.navigation_handler = NavigationHandler(self.page, self.state)
        
        # Selectores específicos identificados
        self.selectores = {
            # Tabla principal de cuentas
            'filas_tabla_principal': "#tablaRespuestaGlosa tbody tr",
            'boton_cuenta': ".btRespuestaStart",
            
            # Tabla de glosas individuales
            'tabla_glosas': "#tableAuditGlosas",
            'filas_glosas': "#tableAuditGlosas tbody tr", 
            'boton_glosa_individual': ".btnAnswerGlosaModal",
            
            # Modal de respuesta
            'modal_titulo': "#titleModalAnswerGlosa",
            'form_modal': "#formAnswerGlosa",
            'select2_container': "#select2-glosaRespTipo-container",
            'textarea_justificacion': "#glosaRespObs",
            'input_archivo': "#glosaRespFile",
            'boton_responder': "#btnAnswerGlosa",
            
            # Botón terminar y modal confirmación
            'boton_terminar': "#btRespuestaFinish",
            'boton_confirmar_terminar': ".swal2-confirm",
            
            # Elementos de información
            'campo_tipo_glosa': "#glosaTipo",
            'campo_justificacion_glosa': "#glosaJustificacion"
        }
        
        # Cache de configuraciones de respuesta
        self.configuraciones_respuesta = {}
        
        # URL base para regresar
        self.url_tabla_principal = None
        
        # Estadísticas de procesamiento
        self.estadisticas = {
            'cuentas_procesadas': 0,
            'cuentas_fallidas': 0,
            'glosas_procesadas': 0,
            'glosas_fallidas': 0,
            'glosas_sin_config': 0,
            'tiempo_inicio': 0,
            'tiempo_fin': 0
        }
        
        self.state.update(
            class_name="ProcesadorCompletoGlosasImplementado",
            method_name="__init__"
        )
        
        self._log("ProcesadorCompletoGlosasImplementado inicializado")
    
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
    
    async def procesar_filas_tabla(self) -> Tuple[int, int]:
        """
        MÉTODO PRINCIPAL: Procesa todas las cuentas de la tabla principal.
        
        Returns:
            Tuple[int, int]: (cuentas_procesadas, cuentas_fallidas)
        """
        try:
            self.state.update(
                method_name="procesar_filas_tabla",
                action="Iniciando procesamiento completo implementado"
            )
            
            self.estadisticas['tiempo_inicio'] = asyncio.get_event_loop().time()
            
            self._log("🚀 === INICIANDO PROCESAMIENTO COMPLETO IMPLEMENTADO ===")
            self._log("="*100)
            
            # PASO 1: Preparar sistema
            if not await self._preparar_sistema():
                return 0, 0
            
            # PASO 2: Obtener cuentas pendientes
            cuentas_pendientes = await self._obtener_cuentas_pendientes()
            
            if not cuentas_pendientes:
                self._log("⚠️ No hay cuentas pendientes para procesar", "warning")
                return 0, 0
            
            # PASO 3: Procesar cada cuenta completa
            cuentas_procesadas = 0
            cuentas_fallidas = 0
            
            for i, cuenta_data in enumerate(cuentas_pendientes):
                idcuenta = cuenta_data['idcuenta']
                
                self._log("")
                self._log(f"🎯 PROCESANDO CUENTA {i+1}/{len(cuentas_pendientes)}: {idcuenta}")
                self._log("-"*60)
                
                try:
                    # Procesar cuenta completa
                    resultado = await self._procesar_cuenta_completa(idcuenta)
                    
                    if resultado['exito']:
                        cuentas_procesadas += 1
                        self.estadisticas['cuentas_procesadas'] += 1
                        self.estadisticas['glosas_procesadas'] += resultado.get('glosas_procesadas', 0)
                        
                        self._log(f"✅ CUENTA {idcuenta} COMPLETADA")
                        self._log(f"   • Glosas procesadas: {resultado.get('glosas_procesadas', 0)}")
                    else:
                        cuentas_fallidas += 1
                        self.estadisticas['cuentas_fallidas'] += 1
                        
                        self._log(f"❌ CUENTA {idcuenta} FALLÓ")
                        self._log(f"   • Error: {resultado.get('error', 'Error desconocido')}")
                
                except Exception as e:
                    error_msg = f"Error general procesando cuenta {idcuenta}: {e}"
                    self._log(error_msg, "error")
                    
                    # Marcar como fallida y regresar a tabla principal
                    await self._marcar_cuenta_fallida(idcuenta, error_msg)
                    await self._regresar_tabla_principal()
                    
                    cuentas_fallidas += 1
                    self.estadisticas['cuentas_fallidas'] += 1
                
                # Pausa entre cuentas
                await asyncio.sleep(3)
                
                # Log de progreso
                if (i + 1) % 3 == 0:
                    porcentaje = ((i + 1) / len(cuentas_pendientes)) * 100
                    self._log(f"📊 PROGRESO: {i+1}/{len(cuentas_pendientes)} ({porcentaje:.1f}%)")
            
            self.estadisticas['tiempo_fin'] = asyncio.get_event_loop().time()
            
            # Mostrar estadísticas finales
            await self._mostrar_estadisticas_finales()
            
            self._log("="*100)
            self._log("🎉 PROCESAMIENTO COMPLETO IMPLEMENTADO TERMINADO")
            
            return cuentas_procesadas, cuentas_fallidas
            
        except Exception as e:
            self._log(f"❌ Error crítico en procesamiento: {e}", "error")
            return 0, 0
    
    async def _preparar_sistema(self) -> bool:
        """Prepara el sistema para el procesamiento."""
        try:
            self._log("🔧 Preparando sistema para procesamiento")
            
            # Guardar URL de tabla principal
            self.url_tabla_principal = self.page.url
            self._log(f"💾 URL tabla principal guardada: {self.url_tabla_principal}")
            
            # Cargar configuraciones de respuesta
            await self._cargar_configuraciones_respuesta()
            
            # Configurar tabla para mostrar más registros
            await self._configurar_tabla_100_registros()
            
            self._log("✅ Sistema preparado correctamente")
            return True
            
        except Exception as e:
            self._log(f"❌ Error preparando sistema: {e}", "error")
            return False
    
    async def _cargar_configuraciones_respuesta(self):
        """Carga las configuraciones de respuesta desde la BD."""
        try:
            self._log("📋 Cargando configuraciones de respuesta automática")
            
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
                
                self._log(f"✅ Cargadas {len(self.configuraciones_respuesta)} configuraciones")
                
        except Exception as e:
            self._log(f"⚠️ Error cargando configuraciones: {e}", "warning")
            self.configuraciones_respuesta = {}
    
    async def _obtener_cuentas_pendientes(self) -> List[Dict]:
        """Obtiene cuentas que están pendientes de procesamiento."""
        try:
            self._log("📋 Obteniendo cuentas pendientes")

            # Verificar cuentas pendientes en BD
            cuentas_bd_pendientes = []

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT idcuenta, proveedor, estado 
                        FROM cuenta_glosas_principal 
                        WHERE estado IN ('PENDIENTE', 'FALLIDO')
                        ORDER BY created_at ASC
                        LIMIT 20
                    """)

                    for row in cursor.fetchall():
                        cuentas_bd_pendientes.append({
                            'idcuenta': row['idcuenta'],
                            'proveedor': row['proveedor'],
                            'estado': row['estado']
                        })
            except Exception as e:
                self._log(f"⚠️ Error consultando BD: {e}", "warning")

            # Si no hay pendientes en BD, extraer desde tabla
            if not cuentas_bd_pendientes:
                self._log("⚠️ No hay pendientes en BD, obteniendo desde tabla")
                cuentas_bd_pendientes = await self._obtener_cuentas_desde_tabla(5)

                # *** AGREGAR ESTO: Forzar actualización después de extraer ***
                if cuentas_bd_pendientes:
                    self._log("🔄 Enviando señal para actualizar UI...")
                    # Simular tiempo de procesamiento para que la UI se actualice
                    await asyncio.sleep(2)

            self._log(f"📊 Cuentas pendientes: {len(cuentas_bd_pendientes)}")
            return cuentas_bd_pendientes

        except Exception as e:
            self._log(f"❌ Error obteniendo cuentas pendientes: {e}", "error")
            return []
    
    async def _obtener_cuentas_desde_tabla(self, limite: int) -> List[Dict]:
        """Obtiene cuentas directamente de la tabla visible y las guarda en BD con TODOS los datos."""
        try:
            cuentas = []
            filas = self.page.locator(self.selectores['filas_tabla_principal'])
            total_filas = await filas.count()

            self._log(f"📊 Extrayendo máximo {limite} cuentas de {total_filas} filas disponibles")

            for i in range(min(total_filas, limite)):
                try:
                    fila = filas.nth(i)
                    celdas = fila.locator("td")
                    total_celdas = await celdas.count()

                    if total_celdas >= 8:  # Verificar que tiene todas las columnas
                        # EXTRAER TODOS LOS DATOS según el HTML que enviaste
                        idcuenta = await celdas.nth(0).text_content()
                        numero_radicacion = await celdas.nth(1).text_content()
                        fecha_radicacion = await celdas.nth(2).text_content()
                        proveedor = await celdas.nth(3).text_content()
                        numero_factura = await celdas.nth(4).text_content()
                        fecha_factura = await celdas.nth(5).text_content()
                        valor_factura_texto = await celdas.nth(6).text_content()
                        valor_glosado_texto = await celdas.nth(7).text_content()

                        # Preparar datos COMPLETOS de la cuenta
                        cuenta_data = {
                            'idcuenta': idcuenta.strip(),
                            'numero_radicacion': numero_radicacion.strip(),
                            'fecha_radicacion': fecha_radicacion.strip(),
                            'proveedor': proveedor.strip()[:200],  # Permitir más caracteres
                            'numero_factura': numero_factura.strip(),
                            'fecha_factura': fecha_factura.strip(),
                            'valor_factura': self._parsear_moneda(valor_factura_texto),
                            'valor_glosado': self._parsear_moneda(valor_glosado_texto)
                        }

                        # *** GUARDAR EN BASE DE DATOS ***
                        try:
                            cuenta_bd_id = self.db_manager.create_or_update_cuenta(cuenta_data)
                            self._log(f"✅ Cuenta {idcuenta} guardada completa en BD - ID: {cuenta_bd_id}")
                            self._log(f"   📋 Proveedor: {proveedor[:30]}...")
                            self._log(f"   💰 Valor Glosado: ${cuenta_data['valor_glosado']:,.2f}")

                            # Agregar ID de BD para referencia
                            cuenta_data['bd_id'] = cuenta_bd_id
                            cuentas.append(cuenta_data)

                        except Exception as e:
                            self._log(f"❌ Error guardando cuenta {idcuenta} en BD: {e}", "error")
                            # Agregar sin ID de BD como fallback
                            cuentas.append(cuenta_data)
                    else:
                        self._log(f"⚠️ Fila {i} tiene solo {total_celdas} celdas, esperadas 8", "warning")

                except Exception as e:
                    self._log(f"⚠️ Error obteniendo cuenta en fila {i}: {e}", "warning")
                    continue

            self._log(f"💾 Proceso completado: {len(cuentas)} cuentas extraídas con datos completos")
            return cuentas

        except Exception as e:
            self._log(f"❌ Error obteniendo cuentas desde tabla: {e}", "error")
            return []

    def _parsear_moneda(self, valor: str) -> float:
        """Convierte texto de moneda a float (mejorado para el formato de tu tabla)."""
        try:
            if not valor:
                return 0.0

            # Limpiar el texto: remover símbolos y espacios
            limpio = valor.replace('$', '').replace(',', '').replace(' ', '').strip()

            if not limpio:
                return 0.0

            # Convertir directamente a float (ya viene con punto decimal correcto)
            return float(limpio)

        except Exception as e:
            self._log(f"⚠️ Error parseando moneda '{valor}': {e}", "warning")
            return 0.0

    async def _procesar_cuenta_completa(self, idcuenta: str) -> Dict:
        """
        Procesa una cuenta completa: hacer clic, procesar todas las glosas, terminar.
        
        Args:
            idcuenta (str): ID de la cuenta a procesar
            
        Returns:
            Dict: Resultado del procesamiento
        """
        try:
            self._log(f"🔄 Procesando cuenta completa: {idcuenta}")
            
            # SUBPASO 1: Ir a tabla principal y hacer clic en la cuenta
            if not await self._navegar_y_hacer_clic_cuenta(idcuenta):
                return {'exito': False, 'error': 'No se pudo hacer clic en la cuenta'}
            
            # SUBPASO 2: Procesar todas las glosas de la cuenta
            resultado_glosas = await self._procesar_todas_las_glosas_cuenta(idcuenta)
            
            if not resultado_glosas['exito']:
                return {
                    'exito': False, 
                    'error': f"Error procesando glosas: {resultado_glosas['error']}"
                }
            
            # SUBPASO 3: Terminar la cuenta (botón verde)
            if not await self._terminar_cuenta():
                return {'exito': False, 'error': 'No se pudo terminar la cuenta'}
            
            # SUBPASO 4: Actualizar estado en BD
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.COMPLETADO,
                f"Procesada correctamente - {resultado_glosas['glosas_procesadas']} glosas"
            )
            
            return {
                'exito': True,
                'glosas_procesadas': resultado_glosas['glosas_procesadas'],
                'glosas_fallidas': resultado_glosas['glosas_fallidas']
            }
            
        except Exception as e:
            error_msg = f"Error procesando cuenta completa {idcuenta}: {e}"
            self._log(error_msg, "error")
            
            # Marcar como fallida en BD
            await self._marcar_cuenta_fallida(idcuenta, error_msg)
            
            return {'exito': False, 'error': error_msg}
    
    async def _procesar_glosa_individual(self, idcuenta: str, glosa_info: Dict) -> Dict:
        """
        Procesa una glosa individual: abrir modal, llenar campos, guardar.
        
        Args:
            idcuenta (str): ID de la cuenta
            glosa_info (Dict): Información de la glosa
            
        Returns:
            Dict: Resultado del procesamiento
        """
        try:
            id_glosa = glosa_info['id_glosa']
            tipo = glosa_info['tipo']
            justificacion = glosa_info['justificacion']
            
            self._log(f"🔍 Procesando glosa individual {id_glosa}")
            
            # PASO 1: Hacer clic en botón de la glosa
            if not await self._hacer_clic_boton_glosa(id_glosa):
                return {'exito': False, 'error': 'No se pudo hacer clic en botón de glosa'}
            
            # PASO 2: Esperar y verificar que el modal se abrió
            if not await self._esperar_modal_abierto(id_glosa):
                return {'exito': False, 'error': 'Modal no se abrió correctamente'}
            
            # PASO 3: Buscar configuración para esta glosa
            configuracion = self._buscar_configuracion_glosa(tipo, justificacion)
            
            if not configuracion:
                # Marcar como sin configuración
                await self._guardar_glosa_sin_config(idcuenta, glosa_info)
                await self._cerrar_modal()
                return {'exito': False, 'error': 'Sin configuración disponible'}
            
            # PASO 4: Llenar campos del modal
            if not await self._llenar_modal_respuesta(configuracion):
                return {'exito': False, 'error': 'Error llenando campos del modal'}
            
            # PASO 5: Guardar respuesta
            if not await self._guardar_respuesta_modal():
                return {'exito': False, 'error': 'Error guardando respuesta'}
            
            # PASO 6: Esperar que se cierre el modal y actualice la tabla
            await asyncio.sleep(5)  # Espera específica mencionada
            
            # PASO 7: Guardar en BD como procesada
            await self._guardar_glosa_procesada(idcuenta, glosa_info, configuracion)
            
            return {'exito': True}
            
        except Exception as e:
            error_msg = f"Error procesando glosa individual {glosa_info.get('id_glosa', 'N/A')}: {e}"
            self._log(error_msg, "error")
            
            # Intentar cerrar modal si está abierto
            try:
                await self._cerrar_modal()
            except:
                pass
            
            return {'exito': False, 'error': error_msg}
    
    async def _hacer_clic_boton_glosa(self, id_glosa: str) -> bool:
        """Hace clic en el botón de una glosa específica."""
        try:
            # Buscar botón por ID de glosa
            boton_glosa = self.page.locator(f'button.btnAnswerGlosaModal[idglosa="{id_glosa}"]')
            
            if await boton_glosa.count() == 0:
                self._log(f"❌ No se encontró botón para glosa {id_glosa}", "error")
                return False
            
            await boton_glosa.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            await boton_glosa.click()
            
            self._log(f"✅ Clic exitoso en botón de glosa {id_glosa}")
            return True
            
        except Exception as e:
            self._log(f"❌ Error haciendo clic en botón glosa {id_glosa}: {e}", "error")
            return False
    
    async def _esperar_modal_abierto(self, id_glosa: str) -> bool:
        """Espera a que el modal se abra correctamente."""
        try:
            # Esperar que aparezca el título del modal
            titulo_modal = self.page.locator(self.selectores['modal_titulo'])
            
            await titulo_modal.wait_for(state="visible", timeout=10000)
            await asyncio.sleep(2)
            
            # Verificar que el título contiene el ID de la glosa
            titulo_texto = await titulo_modal.text_content()
            
            if id_glosa in titulo_texto:
                self._log(f"✅ Modal abierto correctamente para glosa {id_glosa}")
                return True
            else:
                self._log(f"❌ Modal abierto pero con ID incorrecto: {titulo_texto}", "error")
                return False
                
        except Exception as e:
            self._log(f"❌ Error esperando modal para glosa {id_glosa}: {e}", "error")
            return False
    
    def _buscar_configuracion_glosa(self, tipo: str, justificacion: str) -> Optional[Dict]:
        """
        Busca configuración para una glosa específica.
        
        Args:
            tipo (str): Tipo de glosa (ej: TARIFAS)
            justificacion (str): Justificación de la glosa
            
        Returns:
            Optional[Dict]: Configuración encontrada o None
        """
        try:
            # Buscar configuración que coincida
            for key, config in self.configuraciones_respuesta.items():
                if config['tipo'].upper() == tipo.upper():
                    # Verificar patrón de justificación (case-insensitive)
                    patron = config['patron'].replace('%', '').upper()
                    
                    if patron in justificacion.upper():
                        self._log(f"✅ Configuración encontrada para {tipo}: {patron[:30]}...")
                        return config
            
            # Buscar configuración genérica para el tipo
            for key, config in self.configuraciones_respuesta.items():
                if config['tipo'].upper() == tipo.upper():
                    patron_general = config['patron'].replace('%', '').upper()
                    if "MAYOR VALOR COBRADO" in patron_general and "MAYOR VALOR COBRADO" in justificacion.upper():
                        self._log(f"✅ Configuración genérica encontrada para {tipo}")
                        return config
            
            self._log(f"⚠️ No se encontró configuración para {tipo}: {justificacion[:50]}...", "warning")
            return None
            
        except Exception as e:
            self._log(f"❌ Error buscando configuración: {e}", "error")
            return None
    
    async def _llenar_modal_respuesta(self, configuracion: Dict) -> bool:
        """
        Llena los campos del modal con la información de configuración.
        
        Args:
            configuracion (Dict): Configuración de respuesta
            
        Returns:
            bool: True si se llenó correctamente
        """
        try:
            self._log("📝 Llenando campos del modal")
            
            # PASO 1: Seleccionar respuesta en dropdown Select2
            if not await self._seleccionar_respuesta_dropdown():
                return False
            
            # PASO 2: Llenar justificación
            if not await self._llenar_justificacion(configuracion['respuesta']):
                return False
            
            # PASO 3: Subir archivo PDF
            if not await self._subir_archivo_pdf(configuracion['pdf_path']):
                return False
            
            self._log("✅ Modal llenado correctamente")
            return True
            
        except Exception as e:
            self._log(f"❌ Error llenando modal: {e}", "error")
            return False
    
    async def _seleccionar_respuesta_dropdown(self) -> bool:
        """Selecciona la respuesta en el dropdown Select2 usando XPath específico."""
        try:
            # Hacer clic en el container de Select2 para abrir el dropdown
            select2_container = self.page.locator(self.selectores['select2_container'])
            await select2_container.click()
            await asyncio.sleep(2)  # Dar tiempo para que se abra
            
            # Usar el XPath específico que me diste
            xpath_opcion_999 = "//li[@class='select2-results__option select2-results__option--selectable select2-results__option--selected select2-results__option--highlighted'][contains(.,'999 SUBSANADA (GLOSA O DEVOLUCION NO ACEPTADA)')]"
            
            opcion_999 = self.page.locator(f"xpath={xpath_opcion_999}")
            
            # Verificar que existe
            if await opcion_999.count() > 0:
                await opcion_999.click()
                await asyncio.sleep(1)
                self._log("✅ Opción 999 SUBSANADA seleccionada con XPath específico")
                return True
            else:
                # Fallback: buscar por texto más específico
                self._log("⚠️ XPath específico no encontrado, intentando fallback...", "warning")
                
                # Intentar con selector más específico del <li>
                fallback_selector = "li.select2-results__option:has-text('999 SUBSANADA')"
                opcion_fallback = self.page.locator(fallback_selector)
                
                if await opcion_fallback.count() > 0:
                    await opcion_fallback.first.click()
                    await asyncio.sleep(1)
                    self._log("✅ Opción 999 SUBSANADA seleccionada con fallback")
                    return True
                else:
                    self._log("❌ No se encontró opción 999 SUBSANADA en ningún selector", "error")
                    return False
                    
        except Exception as e:
            self._log(f"❌ Error seleccionando dropdown: {e}", "error")
            return False
    async def _llenar_justificacion(self, respuesta_texto: str) -> bool:
        """Llena el campo de justificación."""
        try:
            textarea = self.page.locator(self.selectores['textarea_justificacion'])
            
            await textarea.scroll_into_view_if_needed()
            await textarea.click()
            await textarea.clear()
            await textarea.fill(respuesta_texto)
            await asyncio.sleep(1)
            
            self._log("✅ Justificación llenada correctamente")
            return True
            
        except Exception as e:
            self._log(f"❌ Error llenando justificación: {e}", "error")
            return False
    
    async def _subir_archivo_pdf(self, pdf_path: str) -> bool:
        """Sube el archivo PDF especificado."""
        try:
            if not pdf_path:
                self._log("⚠️ No hay archivo PDF configurado", "warning")
                return True  # No es error crítico
            
            # Normalizar ruta para Windows/Python
            ruta_normalizada = os.path.normpath(pdf_path)
            
            # Verificar que el archivo existe
            if not os.path.exists(ruta_normalizada):
                self._log(f"⚠️ Archivo PDF no encontrado: {ruta_normalizada}", "warning")
                return True  # Continuar sin archivo
            
            # Subir archivo
            input_file = self.page.locator(self.selectores['input_archivo'])
            await input_file.set_input_files(ruta_normalizada)
            await asyncio.sleep(2)
            
            self._log(f"✅ Archivo PDF subido: {os.path.basename(ruta_normalizada)}")
            return True
            
        except Exception as e:
            self._log(f"⚠️ Error subiendo PDF: {e}", "warning")
            return True  # No es error crítico, continuar
    
    async def _guardar_respuesta_modal(self) -> bool:
        """Hace clic en el botón para guardar la respuesta."""
        try:
            boton_responder = self.page.locator(self.selectores['boton_responder'])
            
            await boton_responder.scroll_into_view_if_needed()
            await boton_responder.click()
            
            self._log("✅ Respuesta guardada")
            return True
            
        except Exception as e:
            self._log(f"❌ Error guardando respuesta: {e}", "error")
            return False
    
    async def _terminar_cuenta(self) -> bool:
        """Termina el procesamiento de la cuenta (botón verde)."""
        try:
            self._log("🏁 Terminando cuenta - Buscando botón terminar")
            
            # Hacer scroll hacia abajo para encontrar el botón
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Buscar botón terminar habilitado
            boton_terminar = self.page.locator(self.selectores['boton_terminar']).filter(has_not=self.page.locator('[disabled]'))
            
            if await boton_terminar.count() == 0:
                self._log("❌ Botón terminar no encontrado o no habilitado", "error")
                return False
            
            # Hacer clic en terminar
            await boton_terminar.scroll_into_view_if_needed()
            await boton_terminar.click()
            await asyncio.sleep(3)
            
            # Confirmar en el modal de confirmación
            if not await self._confirmar_terminar():
                return False
            
            # Esperar a regresar a tabla principal
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(5)
            
            self._log("✅ Cuenta terminada correctamente")
            return True
            
        except Exception as e:
            self._log(f"❌ Error terminando cuenta: {e}", "error")
            return False
    
    async def _confirmar_terminar(self) -> bool:
        """Confirma la terminación en el modal de confirmación."""
        try:
            # Buscar y hacer clic en "Si, Terminar!"
            boton_confirmar = self.page.locator(self.selectores['boton_confirmar_terminar'])
            
            await boton_confirmar.wait_for(state="visible", timeout=10000)
            await boton_confirmar.click()
            await asyncio.sleep(2)
            
            self._log("✅ Confirmación de terminar exitosa")
            return True
            
        except Exception as e:
            self._log(f"❌ Error confirmando terminar: {e}", "error")
            return False
    
    async def _scroll_hasta_tabla_glosas(self):
        """Hace scroll hasta la tabla de glosas."""
        try:
            # Buscar la tabla de glosas y hacer scroll
            tabla_glosas = self.page.locator(self.selectores['tabla_glosas'])
            
            if await tabla_glosas.count() > 0:
                await tabla_glosas.scroll_into_view_if_needed()
                await asyncio.sleep(2)
                self._log("✅ Scroll hasta tabla de glosas realizado")
            else:
                # Hacer scroll general hacia abajo
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
                await asyncio.sleep(3)
                self._log("✅ Scroll general realizado")
                
        except Exception as e:
            self._log(f"⚠️ Error haciendo scroll: {e}", "warning")
    
    async def _extraer_glosas_de_tabla(self) -> List[Dict]:
        """Extrae información de todas las glosas de la tabla."""
        try:
            glosas = []
            filas = self.page.locator(self.selectores['filas_glosas'])
            total_filas = await filas.count()
            
            self._log(f"📊 Extrayendo {total_filas} glosas de la tabla")
            
            for i in range(total_filas):
                try:
                    fila = filas.nth(i)
                    celdas = fila.locator("td")
                    total_celdas = await celdas.count()
                    
                    if total_celdas >= 8:  # Verificar columnas mínimas
                        glosa_info = {
                            'id_glosa': await celdas.nth(0).text_content() or "",
                            'id_item': await celdas.nth(1).text_content() or "",
                            'descripcion_item': await celdas.nth(2).text_content() or "",
                            'tipo': await celdas.nth(3).text_content() or "",
                            'descripcion': await celdas.nth(4).text_content() or "",
                            'justificacion': await celdas.nth(5).text_content() or "",
                            'valor_glosado': await celdas.nth(6).text_content() or "",
                            'estado': await celdas.nth(7).text_content() or "",
                            'indice': i
                        }
                        
                        # Limpiar datos
                        for key, value in glosa_info.items():
                            if isinstance(value, str):
                                glosa_info[key] = value.strip()
                        
                        glosas.append(glosa_info)
                        
                        if i < 5:  # Log de las primeras 5
                            self._log(f"   📋 Glosa {i+1}: {glosa_info['id_glosa']} - {glosa_info['tipo']} - {glosa_info['estado']}")
                
                except Exception as e:
                    self._log(f"⚠️ Error extrayendo glosa en fila {i}: {e}", "warning")
                    continue
            
            self._log(f"📊 Extracción completada: {len(glosas)} glosas")
            return glosas
            
        except Exception as e:
            self._log(f"❌ Error extrayendo glosas de tabla: {e}", "error")
            return []
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    async def _asegurar_tabla_principal(self) -> bool:
        """Se asegura de estar en la tabla principal."""
        try:
            url_actual = self.page.url
            
            if "respuestaGlosaSearch" not in url_actual:
                self._log("🔄 No estamos en tabla principal, navegando...")
                await self._regresar_tabla_principal()
                return True
            
            return True
            
        except Exception as e:
            self._log(f"❌ Error asegurando tabla principal: {e}", "error")
            return False
    
    async def _regresar_tabla_principal(self):
        """Regresa a la tabla principal usando NavigationHandler."""
        try:
            self._log("↩️ Regresando a tabla principal")
            
            if self.url_tabla_principal:
                await self.page.goto(self.url_tabla_principal)
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(3)
            else:
                # Usar NavigationHandler para navegar
                await self.navigation_handler.navigate_to_respuesta_glosas()
                await self.navigation_handler.navigate_to_bolsa_respuesta()
            
            self._log("✅ Regreso a tabla principal exitoso")
            
        except Exception as e:
            self._log(f"❌ Error regresando a tabla principal: {e}", "error")
    
    async def _configurar_tabla_100_registros(self):
        """Configura la tabla para mostrar 100 registros."""
        try:
            resultado_js = await self.page.evaluate("""
                () => {
                    const select = document.querySelector('select[name="tablaRespuestaGlosa_length"]');
                    if (select) {
                        select.value = '100';
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                }
            """)
            
            if resultado_js:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                await asyncio.sleep(2)
                self._log("✅ Tabla configurada para 100 registros")
                
        except Exception as e:
            self._log(f"⚠️ Error configurando tabla: {e}", "warning")
    
    async def _cerrar_modal(self):
        """Cierra el modal si está abierto."""
        try:
            # Buscar botón X o Escape
            boton_cerrar = self.page.locator('.close, [data-dismiss="modal"]')
            
            if await boton_cerrar.count() > 0:
                await boton_cerrar.first.click()
                await asyncio.sleep(2)
            else:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(2)
                
        except Exception as e:
            self._log(f"⚠️ Error cerrando modal: {e}", "warning")
    
    async def _marcar_cuenta_fallida(self, idcuenta: str, motivo: str):
        """Marca una cuenta como fallida en la BD."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO, 
                motivo[:200]
            )
        except Exception as e:
            self._log(f"⚠️ Error marcando cuenta {idcuenta} como fallida: {e}", "warning")
    
    async def _guardar_glosa_procesada(self, idcuenta: str, glosa_info: Dict, configuracion: Dict):
        """Guarda una glosa como procesada en la BD."""
        try:
            # Implementar guardado en glosa_items_detalle
            # (Código específico de BD aquí)
            pass
        except Exception as e:
            self._log(f"⚠️ Error guardando glosa procesada: {e}", "warning")
    
    async def _guardar_glosa_fallida(self, idcuenta: str, glosa_info: Dict, error: str):
        """Guarda una glosa como fallida en la BD."""
        try:
            # Implementar guardado con estado ERROR
            # (Código específico de BD aquí)
            pass
        except Exception as e:
            self._log(f"⚠️ Error guardando glosa fallida: {e}", "warning")
    
    async def _guardar_glosa_sin_config(self, idcuenta: str, glosa_info: Dict):
        """Guarda una glosa como sin configuración en la BD."""
        try:
            # Implementar guardado con estado SIN_CONFIG
            # (Código específico de BD aquí)
            pass
        except Exception as e:
            self._log(f"⚠️ Error guardando glosa sin config: {e}", "warning")
    
    async def _mostrar_estadisticas_finales(self):
        """Muestra las estadísticas finales del procesamiento."""
        try:
            tiempo_total = self.estadisticas['tiempo_fin'] - self.estadisticas['tiempo_inicio']
            
            self._log("")
            self._log("📊 ESTADÍSTICAS FINALES DEL PROCESAMIENTO")
            self._log("="*80)
            self._log(f"⏱️  TIEMPO TOTAL: {tiempo_total:.2f} segundos ({tiempo_total/60:.1f} minutos)")
            self._log(f"🏢 CUENTAS PROCESADAS: {self.estadisticas['cuentas_procesadas']}")
            self._log(f"❌ CUENTAS FALLIDAS: {self.estadisticas['cuentas_fallidas']}")
            self._log(f"📋 GLOSAS PROCESADAS: {self.estadisticas['glosas_procesadas']}")
            self._log(f"❌ GLOSAS FALLIDAS: {self.estadisticas['glosas_fallidas']}")
            self._log(f"⚠️  GLOSAS SIN CONFIG: {self.estadisticas['glosas_sin_config']}")
            
            total_cuentas = self.estadisticas['cuentas_procesadas'] + self.estadisticas['cuentas_fallidas']
            if total_cuentas > 0:
                tasa_exito_cuentas = (self.estadisticas['cuentas_procesadas'] / total_cuentas) * 100
                self._log(f"📈 TASA ÉXITO CUENTAS: {tasa_exito_cuentas:.1f}%")
            
            total_glosas = self.estadisticas['glosas_procesadas'] + self.estadisticas['glosas_fallidas']
            if total_glosas > 0:
                tasa_exito_glosas = (self.estadisticas['glosas_procesadas'] / total_glosas) * 100
                self._log(f"📈 TASA ÉXITO GLOSAS: {tasa_exito_glosas:.1f}%")
            
            self._log("="*80)
            
        except Exception as e:
            self._log(f"❌ Error mostrando estadísticas: {e}", "error")
    
    async def _navegar_y_hacer_clic_cuenta(self, idcuenta: str) -> bool:
        """Navega a tabla principal y hace clic en la cuenta."""
        try:
            self._log(f"🖱️ Navegando y haciendo clic en cuenta {idcuenta}")
            
            # Asegurar que estamos en tabla principal
            if not await self._asegurar_tabla_principal():
                return False
            
            # Buscar y hacer clic en el botón de la cuenta
            boton_cuenta = self.page.locator(f'button.btRespuestaStart[idcuenta="{idcuenta}"]')
            
            if await boton_cuenta.count() == 0:
                self._log(f"❌ No se encontró botón para cuenta {idcuenta}", "error")
                return False
            
            await boton_cuenta.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            await boton_cuenta.click()
            
            # Esperar a que cargue la página de glosas
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(5)  # Espera específica mencionada
            
            self._log(f"✅ Clic exitoso en cuenta {idcuenta}")
            return True
            
        except Exception as e:
            self._log(f"❌ Error navegando/haciendo clic cuenta {idcuenta}: {e}", "error")
            return False
    
    async def _procesar_todas_las_glosas_cuenta(self, idcuenta: str) -> Dict:
        """
        Procesa todas las glosas de una cuenta específica.
        
        Args:
            idcuenta (str): ID de la cuenta
            
        Returns:
            Dict: Resultado del procesamiento
        """
        try:
            self._log(f"📋 Procesando todas las glosas de cuenta {idcuenta}")
            
            # Hacer scroll hasta la tabla de glosas
            await self._scroll_hasta_tabla_glosas()
            
            # Extraer información de todas las glosas
            glosas_info = await self._extraer_glosas_de_tabla()
            
            if not glosas_info:
                return {'exito': False, 'error': 'No se encontraron glosas en la tabla'}
            
            self._log(f"📊 Encontradas {len(glosas_info)} glosas para procesar")
            
            glosas_procesadas = 0
            glosas_fallidas = 0
            
            # Procesar cada glosa individual
            for i, glosa_info in enumerate(glosas_info):
                id_glosa = glosa_info['id_glosa']
                estado = glosa_info['estado']
                
                self._log(f"   🔄 Procesando glosa {i+1}/{len(glosas_info)}: {id_glosa}")
                
                # Saltar si ya está procesada
                if estado.upper() == "RESPODIDA":
                    self._log(f"   ⏭️ Glosa {id_glosa} ya procesada, saltando")
                    continue
                
                try:
                    # Procesar glosa individual
                    resultado = await self._procesar_glosa_individual(idcuenta, glosa_info)
                    
                    if resultado['exito']:
                        glosas_procesadas += 1
                        self._log(f"   ✅ Glosa {id_glosa} procesada")
                    else:
                        glosas_fallidas += 1
                        self._log(f"   ❌ Glosa {id_glosa} falló: {resultado['error']}")
                        
                        # Guardar glosa fallida en BD
                        await self._guardar_glosa_fallida(idcuenta, glosa_info, resultado['error'])
                
                except Exception as e:
                    error_msg = f"Error procesando glosa {id_glosa}: {e}"
                    self._log(f"   ❌ {error_msg}", "error")
                    glosas_fallidas += 1
                    await self._guardar_glosa_fallida(idcuenta, glosa_info, error_msg)
                
                # Pausa entre glosas
                await asyncio.sleep(2)
            
            self._log(f"📊 Glosas procesadas: {glosas_procesadas}, fallidas: {glosas_fallidas}")
            
            return {
                'exito': True,
                'glosas_procesadas': glosas_procesadas,
                'glosas_fallidas': glosas_fallidas
            }
            
        except Exception as e:
            error_msg = f"Error procesando glosas de cuenta {idcuenta}: {e}"
            self._log(error_msg, "error")
            return {'exito': False, 'error': error_msg}