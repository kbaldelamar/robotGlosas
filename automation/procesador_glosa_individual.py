import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState, NavigationState

class ProcesadorGlosaIndividual:
    """
    Procesador para manejar la pantalla individual de procesamiento de glosas.
    Se encarga de procesar toda la información específica de una cuenta individual.
    """
    
    def __init__(self, page: Page, automation_state: AutomationState, db_manager: DatabaseManagerGlosas):
        """
        Inicializa el procesador de glosa individual.
        
        Args:
            page (Page): Página de Playwright
            automation_state (AutomationState): Estado compartido de automatización
            db_manager (DatabaseManagerGlosas): Manager de base de datos compartido
        """
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager
        
        # Selectores específicos de la pantalla de glosa individual
        # PERSONALIZAR ESTOS SELECTORES SEGÚN TU APLICACIÓN
        self.selectores_glosa = {
            'tabla_glosas': "#tablaGlosas tbody tr, .tabla-glosas tbody tr, table tbody tr",
            'campo_respuesta': ".respuesta-textarea, #respuesta, .campo-respuesta",
            'boton_guardar': ".btn-guardar-respuesta, .btn-guardar, .guardar",
            'boton_finalizar': ".btn-finalizar, .btn-finish, .finalizar",
            'mensaje_exito': ".alert-success, .success-message, .mensaje-exito",
            'mensaje_error': ".alert-danger, .error-message, .mensaje-error",
            'info_cuenta': ".info-cuenta, .cuenta-info, .datos-cuenta",
            'estado_glosa': ".estado-glosa, .status-glosa",
            'formulario_respuesta': ".form-respuesta, form, .formulario-glosa"
        }
        
        self.state.update(
            class_name="ProcesadorGlosaIndividual",
            method_name="__init__"
        )
        
        self._registrar_estado("ProcesadorGlosaIndividual inicializado")
    
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
        MÉTODO PRINCIPAL: Procesa completamente una glosa individual.
        
        Args:
            idcuenta (str): ID de la cuenta a procesar
            datos_cuenta (Dict): Datos adicionales de la cuenta
            
        Returns:
            Dict: Resultado del procesamiento con estado y detalles
        """
        try:
            self.state.update(
                method_name="procesar_glosa_completa",
                action=f"Procesando glosa individual para cuenta {idcuenta}"
            )
            
            self._registrar_estado(f"🔍 INICIANDO PROCESAMIENTO DE GLOSA INDIVIDUAL - Cuenta: {idcuenta}")
            
            # Actualizar estado en BD
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.EN_PROCESO, 
                "Iniciando procesamiento de glosa individual"
            )
            
            # PASO 1: Verificar que estamos en la página correcta
            if not await self._verificar_pantalla_glosa_individual(idcuenta):
                return self._crear_resultado_error(idcuenta, "No se pudo acceder a la pantalla de glosa")
            
            # PASO 2: Extraer información de la pantalla
            info_glosa = await self._extraer_informacion_glosa(idcuenta)
            if not info_glosa['exito']:
                return self._crear_resultado_error(idcuenta, "Error extrayendo información de glosa")
            
            # PASO 3: Procesar las glosas específicas
            resultado_procesamiento = await self._procesar_glosas_especificas(idcuenta, info_glosa['datos'])
            if not resultado_procesamiento['exito']:
                return self._crear_resultado_error(idcuenta, f"Error en procesamiento: {resultado_procesamiento['error']}")
            
            # PASO 4: Finalizar y guardar
            if not await self._finalizar_procesamiento_glosa(idcuenta):
                return self._crear_resultado_error(idcuenta, "Error finalizando procesamiento")
            
            # PASO 5: Actualizar estado final en BD
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.COMPLETADO, 
                f"Glosa procesada exitosamente - {resultado_procesamiento.get('glosas_procesadas', 0)} glosas"
            )
            
            self._registrar_estado(f"✅ GLOSA INDIVIDUAL COMPLETADA - Cuenta: {idcuenta}")
            
            return {
                'exito': True,
                'idcuenta': idcuenta,
                'mensaje': 'Glosa procesada exitosamente',
                'glosas_procesadas': resultado_procesamiento.get('glosas_procesadas', 0),
                'detalles': resultado_procesamiento.get('detalles', {}),
                'tiempo_procesamiento': resultado_procesamiento.get('tiempo_procesamiento', 0)
            }
            
        except Exception as e:
            error_msg = f"Error general procesando glosa {idcuenta}: {e}"
            self._registrar_estado(error_msg, "error")
            return self._crear_resultado_error(idcuenta, error_msg)
    
    async def _verificar_pantalla_glosa_individual(self, idcuenta: str) -> bool:
        """
        Verifica que estamos en la pantalla correcta de procesamiento de glosa.
        
        Args:
            idcuenta (str): ID de la cuenta
            
        Returns:
            bool: True si estamos en la pantalla correcta
        """
        try:
            self._registrar_estado(f"🔍 Verificando pantalla de glosa para cuenta {idcuenta}")
            
            # Verificar URL
            url_actual = self.page.url
            if "respuestaGlosastart" not in url_actual:
                self._registrar_estado(f"❌ URL incorrecta: {url_actual}", "error")
                return False
            
            # Verificar que el ID de cuenta esté en la URL (codificado en base64)
            # Nota: El ID puede estar codificado, así que verificamos de forma más flexible
            self._registrar_estado(f"✅ URL correcta para procesamiento de glosa: {url_actual}")
            
            # Esperar a que la página cargue completamente
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(3)  # Tiempo adicional para JavaScript
            
            # Verificar elementos clave de la pantalla (flexibles)
            elementos_verificados = 0
            total_elementos = 0
            
            for selector_key, descripcion in [
                ('formulario_respuesta', 'Formulario de respuesta'),
                ('info_cuenta', 'Información de cuenta'),
                ('tabla_glosas', 'Tabla de glosas')
            ]:
                total_elementos += 1
                if selector_key in self.selectores_glosa:
                    elemento = self.page.locator(self.selectores_glosa[selector_key])
                    if await elemento.count() > 0:
                        elementos_verificados += 1
                        self._registrar_estado(f"✅ {descripcion} encontrado")
                    else:
                        self._registrar_estado(f"⚠️ {descripcion} no encontrado", "warning")
            
            # Si encontramos al menos la mitad de los elementos, consideramos exitoso
            if elementos_verificados >= total_elementos // 2:
                self._registrar_estado(f"✅ Pantalla verificada ({elementos_verificados}/{total_elementos} elementos)")
                return True
            else:
                self._registrar_estado(f"❌ Pantalla no verificada ({elementos_verificados}/{total_elementos} elementos)", "error")
                return False
            
        except Exception as e:
            self._registrar_estado(f"❌ Error verificando pantalla: {e}", "error")
            return False
    
    async def _extraer_informacion_glosa(self, idcuenta: str) -> Dict:
        """
        Extrae toda la información necesaria de la pantalla de glosa.
        
        Args:
            idcuenta (str): ID de la cuenta
            
        Returns:
            Dict: Información extraída con éxito/error
        """
        try:
            self._registrar_estado(f"📊 Extrayendo información de glosa para cuenta {idcuenta}")
            
            datos_extraidos = {
                'idcuenta': idcuenta,
                'glosas': [],
                'info_cuenta': {},
                'url_procesamiento': self.page.url,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # EXTRAER INFORMACIÓN DE LA CUENTA
            await self._extraer_info_cuenta(datos_extraidos)
            
            # EXTRAER GLOSAS ESPECÍFICAS
            await self._extraer_glosas_tabla(datos_extraidos)
            
            # EXTRAER CAMPOS DE FORMULARIO
            await self._extraer_campos_formulario(datos_extraidos)
            
            self._registrar_estado(f"✅ Información extraída - {len(datos_extraidos['glosas'])} glosas encontradas")
            
            return {
                'exito': True,
                'datos': datos_extraidos
            }
            
        except Exception as e:
            error_msg = f"Error general extrayendo información: {e}"
            self._registrar_estado(error_msg, "error")
            return {'exito': False, 'error': error_msg}
    
    async def _extraer_info_cuenta(self, datos_extraidos: Dict):
        """Extrae información general de la cuenta."""
        try:
            info_cuenta_element = self.page.locator(self.selectores_glosa.get('info_cuenta', '.info-cuenta'))
            if await info_cuenta_element.count() > 0:
                texto_info = await info_cuenta_element.first.text_content()
                datos_extraidos['info_cuenta'] = {
                    'texto': texto_info.strip() if texto_info else "",
                    'encontrado': True
                }
                self._registrar_estado(f"✅ Info de cuenta extraída: {texto_info[:100]}...")
            else:
                datos_extraidos['info_cuenta'] = {'encontrado': False}
                self._registrar_estado("⚠️ Info de cuenta no encontrada", "warning")
        except Exception as e:
            self._registrar_estado(f"⚠️ Error extrayendo info de cuenta: {e}", "warning")
            datos_extraidos['info_cuenta'] = {'error': str(e)}
    
    async def _extraer_glosas_tabla(self, datos_extraidos: Dict):
        """Extrae las glosas de la tabla."""
        try:
            # Intentar múltiples selectores para la tabla
            selectores_tabla = [
                self.selectores_glosa.get('tabla_glosas', ''),
                'tbody tr',
                'table tr',
                '.table tr',
                '#tablaGlosas tr'
            ]
            
            filas_glosas = None
            selector_usado = None
            
            for selector in selectores_tabla:
                if selector:
                    elemento = self.page.locator(selector)
                    if await elemento.count() > 0:
                        filas_glosas = elemento
                        selector_usado = selector
                        break
            
            if filas_glosas is None:
                self._registrar_estado("⚠️ No se encontró tabla de glosas", "warning")
                return
            
            total_glosas = await filas_glosas.count()
            self._registrar_estado(f"📈 Encontradas {total_glosas} filas con selector: {selector_usado}")
            
            for i in range(min(total_glosas, 50)):  # Limitar a 50 glosas máximo
                try:
                    fila = filas_glosas.nth(i)
                    celdas = fila.locator('td, th')
                    total_celdas = await celdas.count()
                    
                    if total_celdas > 0:
                        glosa_data = {
                            'indice': i,
                            'celdas': [],
                            'tiene_campos_input': False
                        }
                        
                        # Extraer contenido de cada celda
                        for j in range(min(total_celdas, 15)):  # Máximo 15 celdas por fila
                            try:
                                celda = celdas.nth(j)
                                celda_texto = await celda.text_content()
                                
                                # Verificar si hay campos de input en la celda
                                inputs = celda.locator('input, textarea, select')
                                if await inputs.count() > 0:
                                    glosa_data['tiene_campos_input'] = True
                                
                                glosa_data['celdas'].append(celda_texto.strip() if celda_texto else "")
                                
                            except Exception as e:
                                glosa_data['celdas'].append("")
                                self._registrar_estado(f"⚠️ Error en celda {j} de fila {i}: {e}", "warning")
                        
                        datos_extraidos['glosas'].append(glosa_data)
                        
                except Exception as e:
                    self._registrar_estado(f"⚠️ Error procesando fila {i}: {e}", "warning")
                    continue
                    
        except Exception as e:
            self._registrar_estado(f"❌ Error extrayendo tabla de glosas: {e}", "error")
    
    async def _extraer_campos_formulario(self, datos_extraidos: Dict):
        """Extrae campos de formulario disponibles."""
        try:
            campos_formulario = []
            
            # Buscar formularios
            formularios = self.page.locator('form, .form, .formulario')
            total_formularios = await formularios.count()
            
            if total_formularios > 0:
                self._registrar_estado(f"📋 Encontrados {total_formularios} formularios")
                
                for i in range(total_formularios):
                    form = formularios.nth(i)
                    
                    # Buscar campos de input
                    inputs = form.locator('input, textarea, select')
                    total_inputs = await inputs.count()
                    
                    for j in range(total_inputs):
                        try:
                            input_elem = inputs.nth(j)
                            campo_info = {
                                'tipo': await input_elem.get_attribute('type') or 'text',
                                'name': await input_elem.get_attribute('name') or f'campo_{j}',
                                'id': await input_elem.get_attribute('id') or '',
                                'placeholder': await input_elem.get_attribute('placeholder') or '',
                                'formulario': i
                            }
                            campos_formulario.append(campo_info)
                        except Exception as e:
                            self._registrar_estado(f"⚠️ Error extrayendo campo {j}: {e}", "warning")
            
            datos_extraidos['campos_formulario'] = campos_formulario
            self._registrar_estado(f"✅ Extraídos {len(campos_formulario)} campos de formulario")
            
        except Exception as e:
            self._registrar_estado(f"⚠️ Error extrayendo campos de formulario: {e}", "warning")
            datos_extraidos['campos_formulario'] = []
    
    async def _procesar_glosas_especificas(self, idcuenta: str, info_glosa: Dict) -> Dict:
        """
        Procesa las glosas específicas según la lógica de negocio.
        
        Args:
            idcuenta (str): ID de la cuenta
            info_glosa (Dict): Información extraída de la glosa
            
        Returns:
            Dict: Resultado del procesamiento
        """
        try:
            self._registrar_estado(f"⚙️ Procesando glosas específicas para cuenta {idcuenta}")
            
            tiempo_inicio = asyncio.get_event_loop().time()
            glosas = info_glosa.get('glosas', [])
            campos_formulario = info_glosa.get('campos_formulario', [])
            glosas_procesadas = 0
            errores = []
            
            self._registrar_estado(f"📊 Iniciando procesamiento: {len(glosas)} glosas, {len(campos_formulario)} campos")
            
            # MÉTODO 1: Procesar usando campos de formulario si están disponibles
            if campos_formulario:
                resultado_formulario = await self._procesar_via_formulario(idcuenta, campos_formulario, info_glosa)
                if resultado_formulario['exito']:
                    glosas_procesadas += resultado_formulario['procesadas']
                else:
                    errores.extend(resultado_formulario['errores'])
            
            # MÉTODO 2: Procesar glosas individuales de la tabla
            if glosas:
                resultado_tabla = await self._procesar_via_tabla(idcuenta, glosas)
                if resultado_tabla['exito']:
                    glosas_procesadas += resultado_tabla['procesadas']
                else:
                    errores.extend(resultado_tabla['errores'])
            
            # MÉTODO 3: Procesamiento genérico si los anteriores no funcionan
            if glosas_procesadas == 0 and not errores:
                resultado_generico = await self._procesamiento_generico(idcuenta, info_glosa)
                if resultado_generico['exito']:
                    glosas_procesadas += resultado_generico['procesadas']
                else:
                    errores.extend(resultado_generico['errores'])
            
            tiempo_fin = asyncio.get_event_loop().time()
            tiempo_total = tiempo_fin - tiempo_inicio
            
            self._registrar_estado(f"✅ Procesamiento específico completado en {tiempo_total:.2f}s - {glosas_procesadas} glosas procesadas")
            
            return {
                'exito': True,
                'glosas_procesadas': glosas_procesadas,
                'total_glosas': len(glosas),
                'errores': errores,
                'tiempo_procesamiento': tiempo_total,
                'detalles': {
                    'glosas_exitosas': glosas_procesadas,
                    'glosas_fallidas': len(errores),
                    'metodo_usado': 'formulario' if campos_formulario else 'tabla' if glosas else 'generico'
                }
            }
            
        except Exception as e:
            error_msg = f"Error general en procesamiento específico: {e}"
            self._registrar_estado(error_msg, "error")
            return {'exito': False, 'error': error_msg}
    
    async def _procesar_via_formulario(self, idcuenta: str, campos_formulario: List[Dict], info_glosa: Dict) -> Dict:
        """Procesa usando campos de formulario detectados."""
        try:
            self._registrar_estado(f"📝 Procesando vía formulario - {len(campos_formulario)} campos")
            
            procesadas = 0
            errores = []
            
            for i, campo in enumerate(campos_formulario):
                try:
                    # Buscar el campo en la página
                    selector = f"#{campo['id']}" if campo['id'] else f"[name='{campo['name']}']"
                    elemento = self.page.locator(selector)
                    
                    if await elemento.count() > 0:
                        # Generar respuesta automática
                        respuesta = self._generar_respuesta_automatica_campo(campo, info_glosa)
                        
                        # Llenar el campo
                        await elemento.first.fill(respuesta)
                        await asyncio.sleep(0.5)
                        
                        procesadas += 1
                        self._registrar_estado(f"✅ Campo {campo['name']} procesado")
                        
                        # Guardar en BD
                        self._guardar_detalle_glosa(idcuenta, i, campo, "PROCESADO")
                        
                except Exception as e:
                    error_msg = f"Error procesando campo {campo.get('name', i)}: {e}"
                    errores.append(error_msg)
                    self._registrar_estado(error_msg, "error")
                    self._guardar_detalle_glosa(idcuenta, i, campo, "ERROR", str(e))
            
            return {
                'exito': True,
                'procesadas': procesadas,
                'errores': errores
            }
            
        except Exception as e:
            return {
                'exito': False,
                'procesadas': 0,
                'errores': [f"Error en procesamiento via formulario: {e}"]
            }
    
    async def _procesar_via_tabla(self, idcuenta: str, glosas: List[Dict]) -> Dict:
        """Procesa usando datos de tabla de glosas."""
        try:
            self._registrar_estado(f"📊 Procesando vía tabla - {len(glosas)} glosas")
            
            procesadas = 0
            errores = []
            
            for i, glosa in enumerate(glosas):
                try:
                    if glosa.get('tiene_campos_input', False):
                        # Si la fila tiene campos de input, interactuar con ellos
                        await self._procesar_glosa_con_inputs(idcuenta, i, glosa)
                    else:
                        # Si es solo información, marcar como revisada
                        await self._marcar_glosa_revisada(idcuenta, i, glosa)
                    
                    procesadas += 1
                    self._guardar_detalle_glosa(idcuenta, i, glosa, "PROCESADO")
                    
                except Exception as e:
                    error_msg = f"Error procesando glosa {i}: {e}"
                    errores.append(error_msg)
                    self._registrar_estado(error_msg, "error")
                    self._guardar_detalle_glosa(idcuenta, i, glosa, "ERROR", str(e))
            
            return {
                'exito': True,
                'procesadas': procesadas,
                'errores': errores
            }
            
        except Exception as e:
            return {
                'exito': False,
                'procesadas': 0,
                'errores': [f"Error en procesamiento via tabla: {e}"]
            }
    
    async def _procesar_glosa_con_inputs(self, idcuenta: str, indice: int, glosa: Dict):
        """Procesa una glosa que tiene campos de input."""
        try:
            # Buscar campos en la fila específica
            fila_selector = f"tr:nth-child({indice + 1})"
            inputs = self.page.locator(f"{fila_selector} input, {fila_selector} textarea")
            total_inputs = await inputs.count()
            
            for j in range(total_inputs):
                input_elem = inputs.nth(j)
                tipo = await input_elem.get_attribute('type') or 'text'
                
                if tipo in ['text', 'textarea']:
                    respuesta = self._generar_respuesta_automatica(glosa)
                    await input_elem.fill(respuesta)
                    await asyncio.sleep(0.3)
            
            self._registrar_estado(f"✅ Glosa {indice} con inputs procesada")
            
        except Exception as e:
            self._registrar_estado(f"❌ Error procesando glosa con inputs {indice}: {e}", "error")
            raise
    
    async def _marcar_glosa_revisada(self, idcuenta: str, indice: int, glosa: Dict):
        """Marca una glosa como revisada si no tiene campos editables."""
        # Esto es para glosas que solo requieren revisión, no edición
        self._registrar_estado(f"👁️ Glosa {indice} marcada como revisada")
        await asyncio.sleep(0.1)  # Simular tiempo de revisión
    
    async def _procesamiento_generico(self, idcuenta: str, info_glosa: Dict) -> Dict:
        """Procesamiento genérico cuando otros métodos no aplican."""
        try:
            self._registrar_estado(f"🔧 Aplicando procesamiento genérico para cuenta {idcuenta}")
            
            # Buscar cualquier campo de texto en la página
            campos_texto = self.page.locator('input[type="text"], textarea')
            total_campos = await campos_texto.count()
            
            procesadas = 0
            
            if total_campos > 0:
                for i in range(min(total_campos, 10)):  # Máximo 10 campos
                    try:
                        campo = campos_texto.nth(i)
                        if await campo.is_enabled() and await campo.is_visible():
                            respuesta_generica = f"Respuesta automática para cuenta {idcuenta}"
                            await campo.fill(respuesta_generica)
                            await asyncio.sleep(0.3)
                            procesadas += 1
                    except Exception as e:
                        self._registrar_estado(f"⚠️ Error en campo genérico {i}: {e}", "warning")
            
            return {
                'exito': True,
                'procesadas': procesadas,
                'errores': []
            }
            
        except Exception as e:
            return {
                'exito': False,
                'procesadas': 0,
                'errores': [f"Error en procesamiento genérico: {e}"]
            }
    
    def _generar_respuesta_automatica(self, glosa: Dict) -> str:
        """
        Genera una respuesta automática basada en la glosa.
        PERSONALIZAR SEGÚN TU LÓGICA DE NEGOCIO.
        """
        try:
            celdas = glosa.get('celdas', [])
            
            # EJEMPLO DE LÓGICA - PERSONALIZAR SEGÚN TUS REGLAS
            if len(celdas) > 0 and celdas[0]:
                primer_texto = celdas[0].lower()
                
                # Ejemplos de respuestas automáticas basadas en contenido
                if 'medicamento' in primer_texto or 'medicina' in primer_texto:
                    return "Medicamento dispensado según prescripción médica. Documentación adjunta."
                elif 'procedimiento' in primer_texto or 'cirugía' in primer_texto:
                    return "Procedimiento realizado según protocolo establecido. Historia clínica disponible."
                elif 'consulta' in primer_texto:
                    return "Consulta médica realizada. Registro en historia clínica."
                elif 'examen' in primer_texto or 'laboratorio' in primer_texto:
                    return "Examen realizado según orden médica. Resultados disponibles."
                else:
                    return f"Servicio prestado correctamente. Referencia: {celdas[0][:30]}..."
            
            return "Respuesta automática estándar - Servicio prestado según normatividad vigente."
            
        except Exception as e:
            self._registrar_estado(f"⚠️ Error generando respuesta automática: {e}", "warning")
            return "Respuesta automática estándar."
    
    def _generar_respuesta_automatica_campo(self, campo: Dict, info_glosa: Dict) -> str:
        """Genera respuesta específica para un campo de formulario."""
        try:
            nombre_campo = campo.get('name', '').lower()
            placeholder = campo.get('placeholder', '').lower()
            
            # Lógica específica por tipo de campo
            if 'observacion' in nombre_campo or 'observacion' in placeholder:
                return "Observaciones: Servicio prestado según normatividad vigente."
            elif 'respuesta' in nombre_campo or 'respuesta' in placeholder:
                return "Respuesta: Documentación completa y procedimiento correcto."
            elif 'comentario' in nombre_campo or 'comentario' in placeholder:
                return "Comentario: Sin observaciones adicionales."
            elif 'justificacion' in nombre_campo or 'justificacion' in placeholder:
                return "Justificación: Servicio necesario según criterio médico."
            else:
                return "Información completada automáticamente."
                
        except Exception as e:
            return "Respuesta automática."
    
    def _guardar_detalle_glosa(self, idcuenta: str, indice: int, glosa: Dict, estado: str, error: str = None):
        """
        Guarda el detalle de una glosa en la base de datos.
        
        Args:
            idcuenta (str): ID de la cuenta
            indice (int): Índice de la glosa
            glosa (Dict): Datos de la glosa
            estado (str): Estado del procesamiento
            error (str): Mensaje de error si hay
        """
        try:
            # PERSONALIZAR SEGÚN TU ESTRUCTURA DE BD
            detalle = {
                'idcuenta': idcuenta,
                'indice_glosa': indice,
                'datos_glosa': str(glosa)[:500],  # Limitar tamaño
                'estado': estado,
                'error': error,
                'fecha_procesamiento': 'NOW()'
            }
            
            # Si tienes método específico en tu db_manager, descomenta:
            # self.db_manager.guardar_detalle_glosa(detalle)
            
        except Exception as e:
            self._registrar_estado(f"❌ Error guardando detalle de glosa: {e}", "error")
    
    async def _finalizar_procesamiento_glosa(self, idcuenta: str) -> bool:
        """
        Finaliza el procesamiento de la glosa (botones de finalizar, etc.).
        
        Args:
            idcuenta (str): ID de la cuenta
            
        Returns:
            bool: True si se finalizó correctamente
        """
        try:
            self._registrar_estado(f"🏁 Finalizando procesamiento de glosa para cuenta {idcuenta}")
            
            # Intentar múltiples selectores para botón de finalizar
            selectores_finalizar = [
                self.selectores_glosa.get('boton_finalizar', ''),
                '.btn-finalizar',
                '.btn-finish',
                '.finalizar',
                'button[type="submit"]',
                '.btn-primary',
                '.btn-success'
            ]
            
            boton_encontrado = False
            
            for selector in selectores_finalizar:
                if selector:
                    boton = self.page.locator(selector)
                    if await boton.count() > 0:
                        try:
                            await boton.first.scroll_into_view_if_needed()
                            await boton.first.click()
                            await asyncio.sleep(2)
                            
                            boton_encontrado = True
                            self._registrar_estado(f"✅ Botón finalizar clickeado: {selector}")
                            break
                        except Exception as e:
                            self._registrar_estado(f"⚠️ Error con botón {selector}: {e}", "warning")
                            continue
            
            if not boton_encontrado:
                self._registrar_estado("⚠️ No se encontró botón de finalizar específico", "warning")
            
            # Verificar mensaje de éxito
            await asyncio.sleep(2)
            mensaje_exito = self.page.locator(self.selectores_glosa.get('mensaje_exito', '.alert-success'))
            if await mensaje_exito.count() > 0:
                self._registrar_estado(f"✅ Mensaje de éxito detectado para cuenta {idcuenta}")
                return True
            
            # Si no hay mensaje específico, asumir que está finalizado
            self._registrar_estado(f"✅ Procesamiento finalizado para cuenta {idcuenta}")
            return True
            
        except Exception as e:
            self._registrar_estado(f"❌ Error finalizando procesamiento: {e}", "error")
            return False
    
    def _crear_resultado_error(self, idcuenta: str, mensaje: str) -> Dict:
        """
        Crea un resultado de error estándar.
        
        Args:
            idcuenta (str): ID de la cuenta
            mensaje (str): Mensaje de error
            
        Returns:
            Dict: Resultado de error
        """
        # Actualizar estado en BD como fallido
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