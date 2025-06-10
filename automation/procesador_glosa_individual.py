import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState, NavigationState

class ProcesadorGlosaIndividualMejorado:
    """
    Procesador mejorado que integra con la BD de configuración de respuestas.
    MEJORAS PRINCIPALES:
    1. Usa tabla glosas_respuestas_config para respuestas automáticas
    2. Selectores específicos para CTA Médicas
    3. Lógica de procesamiento más inteligente
    """
    
    def __init__(self, page: Page, automation_state: AutomationState, db_manager: DatabaseManagerGlosas):
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager
        
        # SELECTORES ESPECÍFICOS PARA CTA MÉDICAS (ACTUALIZAR SEGÚN TU APP)
        self.selectores_glosa = {
            # Selectores reales que debes identificar en tu aplicación
            'tabla_glosas_detalle': "#tablaDetalleGlosas tbody tr",  # Tabla de glosas específicas
            'campo_respuesta_textarea': "textarea[name='respuesta']",  # Campo de respuesta principal
            'campo_observaciones': "input[name='observaciones']",     # Campo de observaciones
            'boton_guardar_respuesta': ".btn-guardar-respuesta",     # Botón para guardar
            'boton_subir_archivo': "input[type='file']",             # Para subir PDFs
            'select_tipo_respuesta': "select[name='tipoRespuesta']", # Dropdown de tipo
            'mensaje_exito': ".alert-success",                       # Mensaje de éxito
            'info_cuenta_header': ".info-cuenta-header",            # Header con info de cuenta
            'tabla_items_glosa': ".tabla-items-glosa tr"            # Items específicos de glosa
        }
        
        # Cache de configuraciones de respuesta automática
        self.config_respuestas = None
        
        self.state.update(
            class_name="ProcesadorGlosaIndividualMejorado",
            method_name="__init__"
        )
        
        self._registrar_estado("ProcesadorGlosaIndividualMejorado inicializado con integración BD")
    
    def _registrar_estado(self, mensaje: str, nivel: str = "info"):
        """Log con información de estado actual."""
        info_estado = f"[{self.state.current_class}.{self.state.current_method}]"
        mensaje_completo = f"{info_estado} {mensaje}"
        
        if nivel == "info":
            self.logger.info(mensaje_completo)
        elif nivel == "warning":
            self.logger.warning(mensaje_completo)
        elif nivel == "error":
            self.logger.error(mensaje_completo)
    
    async def procesar_glosa_completa(self, idcuenta: str, datos_cuenta: Dict) -> Dict:
        """
        MÉTODO PRINCIPAL MEJORADO: Procesa completamente una glosa individual.
        INTEGRADO CON BD DE CONFIGURACIÓN.
        """
        try:
            self.state.update(
                method_name="procesar_glosa_completa",
                action=f"Procesando glosa individual MEJORADA para cuenta {idcuenta}"
            )
            
            self._registrar_estado(f"🔍 INICIANDO PROCESAMIENTO MEJORADO - Cuenta: {idcuenta}")
            
            # PASO 0: Cargar configuraciones de respuesta automática
            await self._cargar_configuraciones_respuesta()
            
            # PASO 1: Verificar pantalla 
            if not await self._verificar_pantalla_glosa_individual(idcuenta):
                return self._crear_resultado_error(idcuenta, "No se pudo acceder a la pantalla de glosa")
            
            # PASO 2: Extraer información detallada
            info_glosa = await self._extraer_informacion_glosa_detallada(idcuenta)
            if not info_glosa['exito']:
                return self._crear_resultado_error(idcuenta, "Error extrayendo información de glosa")
            
            # PASO 3: Procesar con lógica inteligente basada en BD
            resultado_procesamiento = await self._procesar_con_logica_bd(idcuenta, info_glosa['datos'])
            if not resultado_procesamiento['exito']:
                return self._crear_resultado_error(idcuenta, f"Error en procesamiento: {resultado_procesamiento['error']}")
            
            # PASO 4: Finalizar y guardar
            if not await self._finalizar_procesamiento_glosa(idcuenta):
                return self._crear_resultado_error(idcuenta, "Error finalizando procesamiento")
            
            # PASO 5: Actualizar estado en BD con estadísticas
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.COMPLETADO, 
                f"Procesada con lógica BD - {resultado_procesamiento.get('glosas_procesadas', 0)} glosas",
                glosas_stats=resultado_procesamiento.get('estadisticas', {})
            )
            
            self._registrar_estado(f"✅ GLOSA MEJORADA COMPLETADA - Cuenta: {idcuenta}")
            
            return {
                'exito': True,
                'idcuenta': idcuenta,
                'mensaje': 'Glosa procesada con lógica de BD',
                'glosas_procesadas': resultado_procesamiento.get('glosas_procesadas', 0),
                'respuestas_aplicadas': resultado_procesamiento.get('respuestas_aplicadas', []),
                'tiempo_procesamiento': resultado_procesamiento.get('tiempo_procesamiento', 0)
            }
            
        except Exception as e:
            error_msg = f"Error general procesando glosa mejorada {idcuenta}: {e}"
            self._registrar_estado(error_msg, "error")
            return self._crear_resultado_error(idcuenta, error_msg)
    
    async def _cargar_configuraciones_respuesta(self):
        """
        NUEVA FUNCIONALIDAD: Carga configuraciones de respuesta automática desde BD.
        """
        try:
            self._registrar_estado("📋 Cargando configuraciones de respuesta automática desde BD")
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT tipo, justificacion_patron, respuesta_automatica, url_pdf
                    FROM glosas_respuestas_config 
                    WHERE activo = 1
                    ORDER BY tipo, justificacion_patron
                """)
                
                self.config_respuestas = []
                for row in cursor.fetchall():
                    config = {
                        'tipo': row['tipo'],
                        'patron': row['justificacion_patron'],
                        'respuesta': row['respuesta_automatica'],
                        'url_pdf': row['url_pdf']
                    }
                    self.config_respuestas.append(config)
                
                self._registrar_estado(f"✅ Cargadas {len(self.config_respuestas)} configuraciones de respuesta")
                
        except Exception as e:
            self._registrar_estado(f"⚠️ Error cargando configuraciones: {e}", "warning")
            self.config_respuestas = []
    
    async def _extraer_informacion_glosa_detallada(self, idcuenta: str) -> Dict:
        """
        VERSIÓN MEJORADA: Extrae información más detallada y específica.
        """
        try:
            self._registrar_estado(f"📊 Extrayendo información detallada para cuenta {idcuenta}")
            
            datos_extraidos = {
                'idcuenta': idcuenta,
                'items_glosa': [],
                'info_cuenta': {},
                'campos_formulario': [],
                'url_procesamiento': self.page.url,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # EXTRAER ITEMS DE GLOSA ESPECÍFICOS
            await self._extraer_items_glosa_especificos(datos_extraidos)
            
            # EXTRAER INFORMACIÓN DE CUENTA
            await self._extraer_info_cuenta_detallada(datos_extraidos)
            
            # EXTRAER CAMPOS DE FORMULARIO ESPECÍFICOS
            await self._extraer_campos_formulario_especificos(datos_extraidos)
            
            self._registrar_estado(f"✅ Información detallada extraída - {len(datos_extraidos['items_glosa'])} items")
            
            return {
                'exito': True,
                'datos': datos_extraidos
            }
            
        except Exception as e:
            error_msg = f"Error extrayendo información detallada: {e}"
            self._registrar_estado(error_msg, "error")
            return {'exito': False, 'error': error_msg}
    
    async def _extraer_items_glosa_especificos(self, datos_extraidos: Dict):
        """Extrae items específicos de glosa con más detalle."""
        try:
            # Buscar tabla de items de glosa específicos
            items_selector = self.selectores_glosa.get('tabla_items_glosa', 'tbody tr')
            filas_items = self.page.locator(items_selector)
            total_items = await filas_items.count()
            
            self._registrar_estado(f"📈 Encontrados {total_items} items de glosa")
            
            for i in range(min(total_items, 100)):  # Límite seguro
                try:
                    fila = filas_items.nth(i)
                    celdas = fila.locator('td')
                    total_celdas = await celdas.count()
                    
                    if total_celdas >= 5:  # Mínimo esperado para una glosa
                        item_data = {
                            'indice': i,
                            'id_glosa': await celdas.nth(0).text_content() or "",
                            'descripcion': await celdas.nth(1).text_content() or "",
                            'tipo': await celdas.nth(2).text_content() or "",
                            'justificacion': await celdas.nth(3).text_content() or "",
                            'valor': await celdas.nth(4).text_content() or "",
                            'estado': await celdas.nth(5).text_content() if total_celdas > 5 else "",
                            'tiene_campos_input': False,
                            'campos_disponibles': []
                        }
                        
                        # Verificar campos de input en la fila
                        inputs = fila.locator('input, textarea, select')
                        if await inputs.count() > 0:
                            item_data['tiene_campos_input'] = True
                            
                            # Catalogar tipos de campos disponibles
                            for j in range(await inputs.count()):
                                input_elem = inputs.nth(j)
                                tipo = await input_elem.get_attribute('type') or 'text'
                                name = await input_elem.get_attribute('name') or f'campo_{j}'
                                item_data['campos_disponibles'].append({
                                    'tipo': tipo,
                                    'nombre': name,
                                    'indice': j
                                })
                        
                        # Limpiar textos
                        for key, value in item_data.items():
                            if isinstance(value, str):
                                item_data[key] = value.strip()
                        
                        datos_extraidos['items_glosa'].append(item_data)
                        
                except Exception as e:
                    self._registrar_estado(f"⚠️ Error procesando item {i}: {e}", "warning")
                    continue
                    
        except Exception as e:
            self._registrar_estado(f"❌ Error extrayendo items de glosa: {e}", "error")
    
    async def _procesar_con_logica_bd(self, idcuenta: str, info_glosa: Dict) -> Dict:
        """
        NUEVA FUNCIONALIDAD: Procesa usando configuraciones de BD.
        """
        try:
            self._registrar_estado(f"⚙️ Procesando con lógica de BD para cuenta {idcuenta}")
            
            tiempo_inicio = asyncio.get_event_loop().time()
            items_glosa = info_glosa.get('items_glosa', [])
            respuestas_aplicadas = []
            items_procesados = 0
            errores = []
            
            self._registrar_estado(f"📊 Iniciando procesamiento inteligente: {len(items_glosa)} items")
            
            for i, item in enumerate(items_glosa):
                try:
                    # BUSCAR CONFIGURACIÓN APLICABLE
                    config_aplicable = self._buscar_configuracion_aplicable(item)
                    
                    if config_aplicable:
                        # PROCESAR CON CONFIGURACIÓN ESPECÍFICA
                        resultado = await self._procesar_item_con_configuracion(
                            idcuenta, i, item, config_aplicable
                        )
                        
                        if resultado['exito']:
                            items_procesados += 1
                            respuestas_aplicadas.append({
                                'item_indice': i,
                                'id_glosa': item.get('id_glosa', ''),
                                'tipo_config': config_aplicable['tipo'],
                                'respuesta': config_aplicable['respuesta'],
                                'patron_usado': config_aplicable['patron']
                            })
                            
                            # GUARDAR EN BD DETALLE
                            self._guardar_detalle_procesamiento(idcuenta, item, config_aplicable, "PROCESADO")
                        else:
                            errores.append(resultado.get('error', 'Error desconocido'))
                            self._guardar_detalle_procesamiento(idcuenta, item, config_aplicable, "ERROR", resultado.get('error'))
                    else:
                        # SIN CONFIGURACIÓN APLICABLE
                        self._registrar_estado(f"⚠️ Sin configuración para item {i}: {item.get('tipo', 'N/A')} - {item.get('justificacion', 'N/A')[:50]}...")
                        self._guardar_detalle_procesamiento(idcuenta, item, None, "SIN_CONFIG")
                
                except Exception as e:
                    error_msg = f"Error procesando item {i}: {e}"
                    errores.append(error_msg)
                    self._registrar_estado(error_msg, "error")
                    self._guardar_detalle_procesamiento(idcuenta, item, None, "ERROR", str(e))
            
            tiempo_fin = asyncio.get_event_loop().time()
            tiempo_total = tiempo_fin - tiempo_inicio
            
            # ESTADÍSTICAS
            estadisticas = {
                'total_items': len(items_glosa),
                'items_procesados': items_procesados,
                'items_con_config': len(respuestas_aplicadas),
                'items_sin_config': len(items_glosa) - len(respuestas_aplicadas) - len(errores),
                'errores': len(errores)
            }
            
            self._registrar_estado(f"✅ Procesamiento BD completado en {tiempo_total:.2f}s")
            self._registrar_estado(f"📊 Stats: {items_procesados} procesados, {len(respuestas_aplicadas)} con config, {len(errores)} errores")
            
            return {
                'exito': True,
                'glosas_procesadas': items_procesados,
                'respuestas_aplicadas': respuestas_aplicadas,
                'estadisticas': estadisticas,
                'errores': errores,
                'tiempo_procesamiento': tiempo_total
            }
            
        except Exception as e:
            error_msg = f"Error general en procesamiento con BD: {e}"
            self._registrar_estado(error_msg, "error")
            return {'exito': False, 'error': error_msg}
    
    def _buscar_configuracion_aplicable(self, item: Dict) -> Optional[Dict]:
        """
        NUEVA FUNCIONALIDAD: Busca configuración aplicable en BD.
        """
        try:
            if not self.config_respuestas:
                return None
            
            tipo_item = item.get('tipo', '').upper()
            justificacion = item.get('justificacion', '').upper()
            
            # Buscar coincidencia exacta de tipo primero
            for config in self.config_respuestas:
                if config['tipo'].upper() == tipo_item:
                    # Verificar patrón de justificación
                    patron = config['patron'].replace('%', '').upper()
                    
                    # Verificar si el patrón coincide (usando LIKE de SQL)
                    if self._patron_coincide(patron, justificacion):
                        self._registrar_estado(f"✅ Configuración encontrada: {config['tipo']} - {patron[:30]}...")
                        return config
            
            # Si no hay coincidencia exacta, buscar patrones genéricos
            for config in self.config_respuestas:
                patron = config['patron'].replace('%', '').upper()
                if patron in justificacion:
                    self._registrar_estado(f"✅ Configuración genérica encontrada: {config['tipo']} - {patron[:30]}...")
                    return config
            
            return None
            
        except Exception as e:
            self._registrar_estado(f"⚠️ Error buscando configuración: {e}", "warning")
            return None
    
    def _patron_coincide(self, patron: str, texto: str) -> bool:
        """Verifica si un patrón coincide con el texto (simulando LIKE de SQL)."""
        try:
            # Convertir patrón SQL LIKE a verificación simple
            # Ejemplo: "MAYOR VALOR COBRADO EN" -> buscar en texto
            if not patron or not texto:
                return False
            
            # Si el patrón contiene múltiples palabras, verificar que todas estén presentes
            palabras_patron = patron.split()
            for palabra in palabras_patron:
                if len(palabra) > 2 and palabra not in texto:  # Ignorar palabras muy cortas
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _procesar_item_con_configuracion(self, idcuenta: str, indice: int, 
                                             item: Dict, config: Dict) -> Dict:
        """
        NUEVA FUNCIONALIDAD: Procesa un item usando configuración específica de BD.
        """
        try:
            self._registrar_estado(f"⚙️ Procesando item {indice} con configuración {config['tipo']}")
            
            # Buscar campo de respuesta en la fila del item
            fila_selector = f"tr:nth-child({indice + 1})"
            
            # Intentar múltiples tipos de campos
            campos_respuesta = [
                f"{fila_selector} textarea",
                f"{fila_selector} input[type='text']",
                f"{fila_selector} input[name*='respuesta']",
                self.selectores_glosa.get('campo_respuesta_textarea', '')
            ]
            
            campo_encontrado = None
            for selector in campos_respuesta:
                if selector:
                    elemento = self.page.locator(selector)
                    if await elemento.count() > 0:
                        campo_encontrado = elemento.first
                        break
            
            if campo_encontrado:
                # APLICAR RESPUESTA DE LA CONFIGURACIÓN
                respuesta = config['respuesta']
                await campo_encontrado.fill(respuesta)
                await asyncio.sleep(0.5)
                
                self._registrar_estado(f"✅ Respuesta aplicada en item {indice}: {respuesta[:50]}...")
                
                return {
                    'exito': True,
                    'respuesta_aplicada': respuesta,
                    'campo_usado': 'encontrado'
                }
            else:
                error_msg = f"No se encontró campo de respuesta para item {indice}"
                self._registrar_estado(error_msg, "warning")
                return {
                    'exito': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Error procesando item {indice} con configuración: {e}"
            self._registrar_estado(error_msg, "error")
            return {
                'exito': False,
                'error': error_msg
            }
    
    def _guardar_detalle_procesamiento(self, idcuenta: str, item: Dict, 
                                     config: Optional[Dict], estado: str, error: str = None):
        """
        NUEVA FUNCIONALIDAD: Guarda detalle del procesamiento en BD.
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    INSERT INTO glosas_detalles_procesadas 
                    (idcuenta, id_glosa, id_item, descripcion_item, tipo, 
                     justificacion, valor_glosado, estado_original,
                     respuesta_aplicada, config_id, estado_procesamiento, 
                     fecha_procesamiento, error_mensaje)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (
                    idcuenta,
                    item.get('id_glosa', ''),
                    item.get('indice', ''),
                    item.get('descripcion', ''),
                    item.get('tipo', ''),
                    item.get('justificacion', ''),
                    self._parsear_moneda(item.get('valor', '0')),
                    item.get('estado', ''),
                    config['respuesta'] if config else None,
                    None,  # config_id (podrías agregar si tienes IDs de config)
                    estado,
                    error
                ))
                conn.commit()
                
        except Exception as e:
            self._registrar_estado(f"⚠️ Error guardando detalle: {e}", "warning")
    
    def _parsear_moneda(self, valor: str) -> float:
        """Convierte texto de moneda a float."""
        try:
            if not valor:
                return 0.0
            limpio = valor.replace('$', '').replace(',', '').replace('.', '').replace(' ', '').strip()
            if not limpio:
                return 0.0
            return float(limpio) / 100  # Asumir últimos 2 dígitos son decimales
        except Exception:
            return 0.0
    
    async def _verificar_pantalla_glosa_individual(self, idcuenta: str) -> bool:
        """Versión mejorada de verificación de pantalla."""
        try:
            self._registrar_estado(f"🔍 Verificando pantalla mejorada para cuenta {idcuenta}")
            
            # Verificar URL específica
            url_actual = self.page.url
            if "respuestaGlosastart" not in url_actual:
                self._registrar_estado(f"❌ URL incorrecta: {url_actual}", "error")
                return False
            
            # Esperar carga completa
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(3)
            
            # Verificar elementos específicos con selectores mejorados
            elementos_clave = [
                (self.selectores_glosa.get('info_cuenta_header'), 'Header de cuenta'),
                (self.selectores_glosa.get('tabla_items_glosa'), 'Tabla de items'),
                ('form, .form', 'Formulario de respuesta')
            ]
            
            elementos_encontrados = 0
            for selector, descripcion in elementos_clave:
                if selector:
                    elemento = self.page.locator(selector)
                    if await elemento.count() > 0:
                        elementos_encontrados += 1
                        self._registrar_estado(f"✅ {descripcion} encontrado")
                    else:
                        self._registrar_estado(f"⚠️ {descripcion} no encontrado", "warning")
            
            # Consideramos exitoso si encontramos al menos 1 elemento
            if elementos_encontrados >= 1:
                self._registrar_estado(f"✅ Pantalla verificada ({elementos_encontrados}/3 elementos)")
                return True
            else:
                self._registrar_estado(f"❌ Pantalla no verificada (0/3 elementos)", "error")
                return False
                
        except Exception as e:
            self._registrar_estado(f"❌ Error verificando pantalla: {e}", "error")
            return False
    
    async def _finalizar_procesamiento_glosa(self, idcuenta: str) -> bool:
        """Versión mejorada de finalización."""
        try:
            self._registrar_estado(f"🏁 Finalizando procesamiento mejorado para cuenta {idcuenta}")
            
            # Intentar múltiples selectores para botón de guardar/finalizar
            selectores_finalizar = [
                self.selectores_glosa.get('boton_guardar_respuesta', ''),
                '.btn-guardar',
                '.btn-finalizar',
                'button[type="submit"]',
                '.btn-primary',
                '.btn-success'
            ]
            
            for selector in selectores_finalizar:
                if selector:
                    boton = self.page.locator(selector)
                    if await boton.count() > 0:
                        try:
                            await boton.first.scroll_into_view_if_needed()
                            await boton.first.click()
                            await asyncio.sleep(3)
                            
                            self._registrar_estado(f"✅ Botón clickeado: {selector}")
                            
                            # Verificar mensaje de éxito
                            mensaje_exito = self.page.locator(self.selectores_glosa.get('mensaje_exito', '.alert-success'))
                            if await mensaje_exito.count() > 0:
                                self._registrar_estado(f"✅ Confirmación de éxito detectada")
                                return True
                            
                            # Si no hay mensaje específico, asumir éxito
                            return True
                            
                        except Exception as e:
                            self._registrar_estado(f"⚠️ Error con botón {selector}: {e}", "warning")
                            continue
            
            self._registrar_estado("⚠️ No se encontró botón de finalizar, continuando...", "warning")
            return True  # Asumir éxito si no hay botón específico
            
        except Exception as e:
            self._registrar_estado(f"❌ Error finalizando procesamiento: {e}", "error")
            return False
    
    def _crear_resultado_error(self, idcuenta: str, mensaje: str) -> Dict:
        """Crea resultado de error y actualiza BD."""
        self.db_manager.update_cuenta_estado(
            idcuenta, 
            EstadoCuenta.FALLIDO, 
            mensaje
        )
        
        return {
            'exito': False,
            'idcuenta': idcuenta,
            'error': mensaje,
            'glosas_procesadas': 0,
            'tiempo_procesamiento': 0
        }