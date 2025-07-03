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
    
    def __init__(self, page: Page, automation_state: AutomationState, worker_thread=None):
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

        self.worker = worker_thread
        
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
            self._log("=" * 100)
    
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
                # Revisa si el usuario pulsó "Detener"
                if self.worker and hasattr(self.worker, "_should_stop") and self.worker._should_stop:
                    self._log("🛑 Proceso detenido por el usuario.", "warning")
                    break
                
                idcuenta = cuenta_data['idcuenta']
                self._log("")
                self._log(f"🎯 PROCESANDO CUENTA {i + 1}/{len(cuentas_pendientes)}: {idcuenta}")
                self._log("-" * 60)
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
                        error_msg = resultado.get('error', 'Error desconocido en procesamiento')
                        estado_actual = self.db_manager.get_cuenta_estado(idcuenta)
                        if estado_actual != EstadoCuenta.FALLIDO:
                            await self._marcar_cuenta_fallida(idcuenta, error_msg)
                        cuentas_fallidas += 1
                        self.estadisticas['cuentas_fallidas'] += 1
                        self._log(f"❌ CUENTA {idcuenta} FALLÓ: {error_msg[:100]}...")
                except Exception as e:
                    error_msg = f"Error general procesando cuenta {idcuenta}: {e}"
                    self._log(error_msg, "error")
                    # SOLO DETÉN EL PROCESO SI EL NAVEGADOR SE CERRÓ
                    if "Target page, context or browser has been closed" in str(e):
                        self._log("🚨 Navegador/contexto cerrado. Deteniendo procesamiento de cuentas.", "error")
                        if self.worker and hasattr(self.worker, "stop"):
                            self.worker.stop()
                        # Cierra el navegador/contexto si tienes acceso
                        if hasattr(self, "browser") and self.browser:
                            try:
                                await self.browser.close()
                            except Exception as e2:
                                self._log(f"❌ Error cerrando navegador/contexto: {e2}", "error")
                        break
                    # Si no es cierre de navegador, sigue con el manejo normal
                    await self._marcar_cuenta_fallida(idcuenta, error_msg)
                    try:
                        await self._regresar_tabla_principal()
                    except Exception as e2:
                        self._log(f"❌ Error regresando a tabla principal: {e2}", "error")
                    cuentas_fallidas += 1
                    self.estadisticas['cuentas_fallidas'] += 1
                await asyncio.sleep(3)
    
                # Log de progreso
                if (i + 1) % 3 == 0:
                    porcentaje = ((i + 1) / len(cuentas_pendientes)) * 100
                    self._log(f"📊 PROGRESO: {i + 1}/{len(cuentas_pendientes)} ({porcentaje:.1f}%)")
    
            self.estadisticas['tiempo_fin'] = asyncio.get_event_loop().time()
            await self._mostrar_estadisticas_finales()
            self._log("=" * 100)
            self._log("🎉 PROCESAMIENTO COMPLETO IMPLEMENTADO TERMINADO")
            return cuentas_procesadas, cuentas_fallidas
    
        except Exception as e:
            self._log(f"❌ Error crítico en procesamiento: {e}", "error")
            return 0, 0
    async def _procesar_cuenta_completa(self, idcuenta: str) -> Dict:
            """
            Procesa una cuenta completa: hacer clic, procesar todas las glosas, terminar.
            ✅ EMITE SEÑALES CUANDO CAMBIA EL ESTADO DE LA CUENTA.
            ✅ CORREGIDO: Marca como EN_PROCESO justo antes de procesar y maneja todos los errores correctamente.

            Args:
                idcuenta (str): ID de la cuenta a procesar

            Returns:
                Dict: Resultado del procesamiento
            """
            try:
                self._log(f"🔄 Procesando cuenta completa: {idcuenta}")

                # ✅ NUEVO: Marcar como EN_PROCESO justo antes de procesar
                self.db_manager.update_cuenta_estado(
                    idcuenta, 
                    EstadoCuenta.EN_PROCESO,
                    "Iniciando procesamiento automático"
                )
                self._log(f"🔄 Cuenta {idcuenta} marcada como EN_PROCESO")

                # ✅ EMITIR SIGNAL DE CAMBIO DE ESTADO
                if self.worker:
                    self.worker.emit_cuenta_processed(idcuenta, 'EN_PROCESO')

                # SUBPASO 1: Ir a tabla principal y hacer clic en la cuenta
                if not await self._navegar_y_hacer_clic_cuenta(idcuenta):
                    resultado_fallo = {'exito': False, 'error': 'No se pudo hacer clic en la cuenta'}

                    # ✅ MARCAR COMO FALLIDO si no se puede hacer clic
                    await self._marcar_cuenta_fallida(idcuenta, "No se pudo hacer clic en la cuenta")

                    # ✅ EMITIR SIGNAL DE ERROR
                    if self.worker:
                        self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                        self.worker.emit_tabla_refresh()

                    return resultado_fallo

                # SUBPASO 2: Procesar todas las glosas de la cuenta
                resultado_glosas = await self._procesar_todas_las_glosas_cuenta(idcuenta)

                if not resultado_glosas['exito']:
                    resultado_fallo = {
                        'exito': False,
                        'error': f"Error procesando glosas: {resultado_glosas['error']}"
                    }

                    # ✅ MARCAR COMO FALLIDO si fallan las glosas
                    await self._marcar_cuenta_fallida(idcuenta, f"Error procesando glosas: {resultado_glosas['error']}")

                    # ✅ EMITIR SIGNAL DE ERROR
                    if self.worker:
                        self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                        self.worker.emit_tabla_refresh()

                    return resultado_fallo

                # SUBPASO 3: Terminar la cuenta (botón verde)
                if not await self._terminar_cuenta():
                    resultado_fallo = {'exito': False, 'error': 'No se pudo terminar la cuenta'}

                    # ✅ MARCAR COMO FALLIDO si no se puede terminar
                    await self._marcar_cuenta_fallida(idcuenta, "No se pudo terminar la cuenta")

                    # ✅ EMITIR SIGNAL DE ERROR
                    if self.worker:
                        self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                        self.worker.emit_tabla_refresh()

                    return resultado_fallo

                # ✅ SUBPASO 4: Marcar como COMPLETADO solo si todo salió bien
                self.db_manager.update_cuenta_estado(
                    idcuenta, 
                    EstadoCuenta.COMPLETADO,
                    f"Procesada correctamente - {resultado_glosas['glosas_procesadas']} glosas"
                )

                # ✅ PREPARAR RESULTADO EXITOSO
                resultado_exitoso = {
                    'exito': True,
                    'glosas_procesadas': resultado_glosas['glosas_procesadas'],
                    'glosas_fallidas': resultado_glosas['glosas_fallidas']
                }

                # ✅ EMITIR SIGNAL DE ÉXITO
                if self.worker:
                    self.worker.emit_cuenta_processed(idcuenta, 'COMPLETADO')
                    self.worker.emit_tabla_refresh()

                return resultado_exitoso

            except Exception as e:
                error_msg = f"Error procesando cuenta completa {idcuenta}: {e}"
                self._log(error_msg, "error")

                # ✅ Marcar como fallida en BD con signal incluido
                await self._marcar_cuenta_fallida(idcuenta, error_msg)

                # ✅ EMITIR SIGNAL DE ERROR EN EXCEPCIÓN
                if self.worker:
                    self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                    self.worker.emit_tabla_refresh()

                # ✅ REGRESAR A LA TABLA PRINCIPAL EN CASO DE EXCEPCIÓN
                await self._regresar_tabla_principal()

                return {'exito': False, 'error': error_msg}
    
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
        """
        Obtiene cuentas que están pendientes de procesamiento.
        ✅ CORREGIDO: NO marca como EN_PROCESO hasta que se vaya a procesar individualmente.
        """
        try:
            self._log("📋 Obteniendo cuentas pendientes para procesamiento")

            # ✅ PASO 1: Buscar cuentas PENDIENTES en BD (sin cambiar estado)
            cuentas_bd_pendientes = []

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT idcuenta, proveedor, estado, valor_glosado, fecha_radicacion
                        FROM cuenta_glosas_principal 
                        WHERE estado = 'PENDIENTE'
                        ORDER BY created_at ASC
                        
                    """)

                    for row in cursor.fetchall():
                        cuentas_bd_pendientes.append({
                            'idcuenta': row['idcuenta'],
                            'proveedor': row['proveedor'],
                            'estado': row['estado'],
                            'valor_glosado': row['valor_glosado'],
                            'fecha_radicacion': row['fecha_radicacion']
                        })

                    self._log(f"🔍 Encontradas {len(cuentas_bd_pendientes)} cuentas PENDIENTES en BD")

            except Exception as e:
                self._log(f"⚠️ Error consultando BD: {e}", "warning")

            # ✅ PASO 2: Si hay cuentas PENDIENTES, devolverlas SIN cambiar estado
            if cuentas_bd_pendientes:
                self._log("✅ Devolviendo cuentas PENDIENTES existentes en BD (sin marcar como EN_PROCESO)")

                # ❌ ELIMINAR ESTE BLOQUE COMPLETO:
                # NO marcar como EN_PROCESO aquí - se hará individualmente en _procesar_cuenta_completa

                return cuentas_bd_pendientes

            # ✅ PASO 3: Si NO hay pendientes, importar nuevas desde tabla
            self._log("⚠️ No hay cuentas PENDIENTES en BD, importando desde tabla web")
            cuentas_importadas = await self._obtener_cuentas_desde_tabla(100)

            if cuentas_importadas:
                self._log(f"📥 Importadas {len(cuentas_importadas)} cuentas nuevas como PENDIENTE")

                # Buscar directamente en BD las recién importadas
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT idcuenta, proveedor, estado, valor_glosado, fecha_radicacion
                        FROM cuenta_glosas_principal 
                        WHERE estado = 'PENDIENTE'
                        ORDER BY created_at ASC
                    """)

                    nuevas_pendientes = []
                    for row in cursor.fetchall():
                        nuevas_pendientes.append({
                            'idcuenta': row['idcuenta'],
                            'proveedor': row['proveedor'],
                            'estado': row['estado'],
                            'valor_glosado': row['valor_glosado'],
                            'fecha_radicacion': row['fecha_radicacion']
                        })

                    # ❌ ELIMINAR ESTE BLOQUE COMPLETO:
                    # NO marcar como EN_PROCESO las recién importadas - se hará individualmente

                    self._log(f"✅ Devolviendo {len(nuevas_pendientes)} cuentas recién importadas (sin marcar como EN_PROCESO)")
                    return nuevas_pendientes
            else:
                self._log("❌ No se pudieron importar cuentas desde la tabla", "error")
                return []

        except Exception as e:
            self._log(f"❌ Error obteniendo cuentas pendientes: {e}", "error")
            return []
    
    async def _obtener_cuentas_desde_tabla(self, limite: int = 100) -> List[Dict]:
        """
        Obtiene cuentas directamente de la tabla visible y las guarda en BD.
        SIMPLIFICADO: Usa solo el método create_or_update_cuenta existente.
        ✅ EMITE SEÑALES CUANDO TERMINA LA IMPORTACIÓN.
        """
        try:
            cuentas = []
            filas = self.page.locator(self.selectores['filas_tabla_principal'])
            total_filas = await filas.count()
            limite_real = min(total_filas, limite)

            self._log(f"📊 Extrayendo {limite_real} de {total_filas} filas")

            for i in range(limite_real):
                try:
                    fila = filas.nth(i)
                    celdas = fila.locator("td")
                    total_celdas = await celdas.count()

                    if total_celdas >= 8:
                        # Extraer datos de la tabla
                        idcuenta = await celdas.nth(0).text_content()
                        numero_radicacion = await celdas.nth(1).text_content()
                        fecha_radicacion = await celdas.nth(2).text_content()
                        proveedor = await celdas.nth(3).text_content()
                        numero_factura = await celdas.nth(4).text_content()
                        fecha_factura = await celdas.nth(5).text_content()
                        valor_factura_texto = await celdas.nth(6).text_content()
                        valor_glosado_texto = await celdas.nth(7).text_content()

                        # Preparar datos
                        cuenta_data = {
                            'idcuenta': idcuenta.strip(),
                            'numero_radicacion': numero_radicacion.strip(),
                            'fecha_radicacion': fecha_radicacion.strip(),
                            'proveedor': proveedor.strip()[:200],
                            'numero_factura': numero_factura.strip(),
                            'fecha_factura': fecha_factura.strip(),
                            'valor_factura': self._parsear_moneda(valor_factura_texto),
                            'valor_glosado': self._parsear_moneda(valor_glosado_texto)
                        }

                        # ✅ USAR SOLO EL MÉTODO ÚNICO
                        try:
                            if self.db_manager.should_process_cuenta(cuenta_data['idcuenta']):
                                cuenta_bd_id = self.db_manager.create_or_update_cuenta(cuenta_data)
                                cuenta_data['bd_id'] = cuenta_bd_id
                                cuentas.append(cuenta_data)

                                if i % 10 == 0 or i < 10:
                                    self._log(f"✅ Cuenta {cuenta_data['idcuenta']} guardada como PENDIENTE - ID: {cuenta_bd_id}")
                            else:
                                self._log(f"⏭️ Cuenta {cuenta_data['idcuenta']} saltada por estado")

                        except Exception as e:
                            self._log(f"❌ Error guardando cuenta {cuenta_data['idcuenta']}: {e}", "error")
                            # Agregar sin ID como fallback
                            cuentas.append(cuenta_data)

                    else:
                        self._log(f"⚠️ Fila {i} tiene solo {total_celdas} celdas, esperadas 8", "warning")

                except Exception as e:
                    self._log(f"⚠️ Error en fila {i}: {e}", "warning")
                    continue

            self._log(f"💾 IMPORTACIÓN COMPLETADA: {len(cuentas)} cuentas procesadas como PENDIENTE")

            # ✅ EMITIR SEÑALES CUANDO TERMINA DE IMPORTAR
            if self.worker and cuentas:
                self.worker.emit_data_imported(len(cuentas))
                self.worker.emit_tabla_refresh()

                # Pequeña pausa para que la UI se actualice
                await asyncio.sleep(1)

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
    """
    async def _procesar_todas_las_glosas_cuenta(self, idcuenta: str) -> Dict:
    
        ✅ MODIFICAR ESTE MÉTODO (no _procesar_cuenta_completa)
        Procesa todas las glosas de una cuenta con verificación previa de configuraciones.
        
        try:
            self._log(f"📋 Procesando todas las glosas de cuenta {idcuenta}")

            # PASO 1: Extraer glosas (código existente)
            if not await self._hacer_scroll_hasta_tabla_glosas():
                return {'exito': False, 'error': 'No se pudo hacer scroll hasta tabla de glosas'}

            glosas_extraidas = await self._extraer_glosas_de_tabla()

            if not glosas_extraidas:
                return {'exito': False, 'error': 'No se encontraron glosas para procesar'}

            self._log(f"📊 Encontradas {len(glosas_extraidas)} glosas para procesar")

            # ✅ PASO 2 NUEVO: Verificar configuraciones ANTES de procesar
            glosas_con_config = []
            glosas_sin_config = []

            for glosa in glosas_extraidas:
                codigo_glosa = glosa.get('codigo_glosa', '')
                descripcion = glosa.get('descripcion', '')

                # Buscar configuración usando tu método existente
                configuracion = self._obtener_configuracion_glosa(codigo_glosa, descripcion)

                if configuracion:
                    glosa['configuracion'] = configuracion
                    glosas_con_config.append(glosa)
                    self._log(f"   ✅ Glosa {glosa['idglosa']}: Configuración encontrada")
                else:
                    glosas_sin_config.append(glosa)
                    self._log(f"   ❌ Glosa {glosa['idglosa']}: SIN configuración para {codigo_glosa}")

            # ✅ PASO 3 NUEVO: Si hay glosas sin configuración, manejar correctamente
            if glosas_sin_config:
                self._log(f"⚠️ {len(glosas_sin_config)} glosas sin configuración - Guardando en BD")

                # Guardar glosas sin configuración
                await self._guardar_glosas_sin_configuracion(idcuenta, glosas_sin_config)

                # Si NO hay glosas procesables, es un fallo total
                if not glosas_con_config:
                    return {
                        'exito': False, 
                        'error': f"Todas las glosas ({len(glosas_sin_config)}) sin configuración",
                        'glosas_sin_config': len(glosas_sin_config)
                    }

            # ✅ PASO 4: Procesar solo las glosas CON configuración (código existente mejorado)
            if glosas_con_config:
                self._log(f"🚀 Procesando {len(glosas_con_config)} glosas con configuración")

                glosas_procesadas = 0
                glosas_fallidas = 0

                for i, glosa in enumerate(glosas_con_config):
                    self._log(f"   🔄 Procesando glosa {i+1}/{len(glosas_con_config)}: {glosa['idglosa']}")

                    try:
                        # Usar tu método existente
                        resultado = await self._procesar_glosa_individual(glosa)

                        if resultado['exito']:
                            glosas_procesadas += 1
                            self._log(f"   ✅ Glosa {glosa['idglosa']} procesada exitosamente")
                        else:
                            glosas_fallidas += 1
                            self._log(f"   ❌ Glosa {glosa['idglosa']} falló: {resultado.get('error', '')}")

                    except Exception as e:
                        glosas_fallidas += 1
                        self._log(f"   ❌ Error procesando glosa {glosa['idglosa']}: {e}", "error")

                    # Pausa entre glosas (mantener tu lógica)
                    await asyncio.sleep(2)

                # ✅ RESULTADO: Incluir información de glosas sin configuración
                return {
                    'exito': True,
                    'glosas_procesadas': glosas_procesadas,
                    'glosas_fallidas': glosas_fallidas,
                    'glosas_sin_config': len(glosas_sin_config) if glosas_sin_config else 0
                }

            return {'exito': False, 'error': 'No hay glosas procesables'}

        except Exception as e:
            error_msg = f"Error procesando glosas de cuenta {idcuenta}: {e}"
            self._log(error_msg, "error")
            return {'exito': False, 'error': error_msg}
    """
    async def _guardar_glosas_sin_configuracion(self, idcuenta: str, glosas_sin_config: List[Dict]):
        """
        ✅ CORREGIDO: Usar nombres correctos de campos
        """
        try:
            self._log(f"💾 Guardando {len(glosas_sin_config)} glosas sin configuración en BD")

            with self.db_manager.get_connection() as conn:
                for glosa in glosas_sin_config:
                    # ✅ CORREGIR: Usar nombres correctos de campos extraídos
                    conn.execute("""
                        INSERT OR REPLACE INTO glosa_items_detalle 
                        (idglosa, idcuenta, codigo_glosa, descripcion_glosa, estado, motivo_fallo, fecha_procesamiento)
                        VALUES (?, ?, ?, ?, 'SIN_CONFIGURACION', 'No se encontró configuración para esta glosa', CURRENT_TIMESTAMP)
                    """, (
                        glosa['id_glosa'],  # ✅ CORREGIR: campo correcto
                        idcuenta,
                        glosa.get('tipo', ''),  # ✅ CORREGIR: campo correcto
                        glosa.get('justificacion', ''),  # ✅ CORREGIR: campo correcto
                    ))

                conn.commit()
                self._log(f"✅ {len(glosas_sin_config)} glosas marcadas como SIN_CONFIGURACION en BD")

        except Exception as e:
            self._log(f"❌ Error guardando glosas sin configuración: {e}", "error")
        
    async def _procesar_glosa_individual(self, glosa_info: Dict) -> Dict:
        """
        MEJORADO: Procesa una glosa individual con mejor manejo de modales.
        
        Args:
            glosa_info (Dict): Información de la glosa (no necesita idcuenta separado)
            
        Returns:
            Dict: Resultado del procesamiento
        """
        try:
            id_glosa = glosa_info.get('id_glosa', '')
            tipo = glosa_info.get('tipo', '')
            justificacion = glosa_info.get('justificacion', '')
            
            self._log(f"🔍 Procesando glosa individual {id_glosa} - Tipo: {tipo}")
            
            # PASO 1: Hacer clic en botón de la glosa
            if not await self._hacer_clic_boton_glosa(id_glosa):
                return {'exito': False, 'error': 'No se pudo hacer clic en botón de glosa'}
            
            # PASO 2: Esperar que el modal se abra
            if not await self._esperar_modal_abierto(id_glosa):
                return {'exito': False, 'error': 'Modal no se abrió correctamente'}
            
            # Capturar el número de factura del modal antes de hacer scroll
            
            num_factura_elem = self.page.locator("//div//label[@class='form-label'][contains(., 'Nro Factura')]/following-sibling::div[@id='numFactura']")
            num_factura = ""
            if await num_factura_elem.count() > 0:
                num_factura = (await num_factura_elem.text_content()).strip()
                self._log(f"📄 Número de factura capturado: {num_factura}")
            else:
                self._log("⚠️ No se pudo capturar el número de factura en el modal", "warning")
            glosa_info['num_factura'] = num_factura

            # ✅ PASO 3: ÚNICA LÍNEA A CAMBIAR - Usar método que SÍ existe
            configuracion = self._buscar_configuracion_glosa(tipo, justificacion)
            
            if not configuracion:
                self._log(f"⚠️ Sin configuración para glosa {id_glosa} - Cerrando modal...")
                
                # ✅ MEJORADO: Cerrar modal y continuar sin marcas de error
                modal_cerrado = await self._cerrar_modal()
                if not modal_cerrado:
                    self._log(f"❌ Error cerrando modal para glosa {id_glosa}", "error")
                    # Intentar forzar el cierre navegando
                    try:
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(1)
                        await self.page.keyboard.press('Escape') 
                        await asyncio.sleep(1)
                    except:
                        pass
                        
                return {'exito': False, 'error': 'Sin configuración disponible', 'sin_config': True}
            
                # PASO 4: Llenar campos del modal y subir PDF
            if not await self._llenar_modal_respuesta(configuracion, glosa_info):
                await self._cerrar_modal()
                await self._guardar_glosa_fallida(glosa_info.get('idcuenta', ''), glosa_info, "Error llenando campos del modal")
                return {'exito': False, 'error': 'Error llenando campos del modal'}

            # PASO 5: Guardar respuesta
            if not await self._guardar_respuesta_modal():
                await self._cerrar_modal()
                await self._guardar_glosa_fallida(glosa_info.get('idcuenta', ''), glosa_info, "Error guardando respuesta")
                return {'exito': False, 'error': 'Error guardando respuesta'}

            # PASO 6: Esperar que se procese y se cierre el modal automáticamente
            await asyncio.sleep(3)

            # ÉXITO: Marcar como procesada
            await self._guardar_glosa_procesada(glosa_info.get('idcuenta', ''), glosa_info, configuracion)
            self._log(f"✅ Glosa {glosa_info.get('id_glosa', '')} guardada como procesada en ambas tablas")
            return {'exito': True, 'configuracion_usada': configuracion['tipo']}

        except Exception as e:
            error_msg = f"Error procesando glosa individual {glosa_info.get('id_glosa', 'N/A')}: {e}"
            self._log(error_msg, "error")
            try:
                await self._cerrar_modal()
            except:
                pass
            await self._guardar_glosa_fallida(glosa_info.get('idcuenta', ''), glosa_info, error_msg)
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
    
    async def _llenar_modal_respuesta(self, configuracion: Dict, glosa_info: Dict) -> bool:
        try:
            self._log("📝 Llenando campos del modal")
            # PASO 1: Seleccionar respuesta en dropdown Select2
            if not await self._seleccionar_respuesta_dropdown():
                return False
            # PASO 2: Llenar justificación
            if not await self._llenar_justificacion(configuracion['respuesta']):
                return False

            # PASO 3: Subir archivo PDF
            pdf_path = configuracion['pdf_path']
            tipo = glosa_info.get('tipo', '')
            num_factura = glosa_info.get('num_factura', '')
            idcuenta = glosa_info.get('idcuenta', '')

            # Si es AUTORIZACION y hay número de factura, ajusta la ruta y valida existencia
            if tipo.upper() == "AUTORIZACION" and num_factura:
                ruta_final = os.path.normpath(os.path.join(pdf_path, num_factura, "OTROS.PDF"))
                self._log(f"Ruta PDF ajustada por AUTORIZACION: {ruta_final}")
                if not os.path.exists(ruta_final):
                    self._log(f"❌ PDF de AUTORIZACION no encontrado: {ruta_final}", "error")
                    await self._guardar_glosa_fallida(idcuenta, glosa_info, "PDF de AUTORIZACION no encontrado")
                    await self._marcar_cuenta_fallida(idcuenta, "PDF de AUTORIZACION no encontrado")
                    return False
            else:
                ruta_final = os.path.normpath(pdf_path)
                if pdf_path and not os.path.exists(ruta_final):
                    self._log(f"⚠️ Archivo PDF no encontrado: {ruta_final}", "warning")
                    # No es error crítico para otros tipos

            # Solo sube el archivo si existe
            if pdf_path and os.path.exists(ruta_final):
                if not await self._subir_archivo_pdf(ruta_final):
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
        """Llena el campo de justificación simulando escritura humana y luego pegando texto."""
        try:
            # Preparar texto en mayúsculas
            texto_mayuscula = respuesta_texto.upper()

            # Localizar y preparar el textarea
            textarea = self.page.locator(self.selectores['textarea_justificacion'])
            await textarea.scroll_into_view_if_needed()
            await textarea.click()
            await asyncio.sleep(0.5)

            # Limpiar campo completamente
            await textarea.press('Control+a')
            await textarea.press('Delete')
            await asyncio.sleep(0.5)

            # ✅ PEGAR TEXTO PRIMERO: Usar JavaScript para pegar directamente desde BD
            self._log("📋 Pegando texto de la base de datos...")
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
            """, texto_mayuscula)

            await asyncio.sleep(0.3)

            # ✅ SIMULACIÓN HUMANA: Agregar espacios al final
            self._log("📝 Agregando espacios finales...")
            await textarea.press_sequentially("   ", delay=120)  # 3 espacios al final con delay humano
            await asyncio.sleep(0.2)

            # Simular Tab para salir del campo (dispara validación)
            await textarea.press('Tab')
            await asyncio.sleep(1)

            # Verificar resultado
            clases = await textarea.get_attribute('class')
            if clases and 'is-valid' in clases:
                self._log("✅ Justificación llenada correctamente")
                return True
            elif not clases or 'is-invalid' not in clases:
                self._log("✅ Justificación llenada (estado neutro)")
                return True
            else:
                # ✅ ÚLTIMO RECURSO: JavaScript como fallback
                self._log("🔄 Aplicando fallback con JavaScript...")
                await self.page.evaluate("""
                    (texto) => {
                        const textarea = document.getElementById('glosaRespObs');
                        if (textarea) {
                            textarea.value = texto;
                            textarea.focus();

                            // Disparar eventos de validación
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            textarea.dispatchEvent(new Event('change', { bubbles: true }));
                            textarea.dispatchEvent(new Event('blur', { bubbles: true }));

                            // Actualizar clases
                            textarea.classList.remove('is-invalid');
                            textarea.classList.add('is-valid');

                            // Ocultar mensaje de error si existe
                            const errorMsg = document.getElementById('glosaRespObsHelp');
                            if (errorMsg) errorMsg.style.display = 'none';
                        }
                    }
                """, texto_mayuscula)

                self._log("✅ Justificación llenada con JavaScript")
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
        """
        Termina el procesamiento de la cuenta (botón verde).
        MEJORADO: No marca como FALLIDO aquí porque se maneja en el método padre.
        """
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
    
    async def _extraer_glosas_de_tabla(self, idcuenta: str) -> List[Dict]:
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
                            'indice': i,
                            'idcuenta': idcuenta  # Amarra el ítem a la cuenta principal
                        }

                        # Limpiar datos
                        for key, value in glosa_info.items():
                            if isinstance(value, str):
                                glosa_info[key] = value.strip()
                        cuenta_id = await self._obtener_cuenta_id(idcuenta)
                        self._guardar_glosa_en_detalle(cuenta_id, glosa_info)
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
        """
        Cierra el modal de respuesta de glosa con múltiples métodos.
        MEJORADO: Múltiples estrategias para cerrar el modal sin timeout.
        """
        try:
            self._log("🔄 Intentando cerrar modal de glosa...")
            
            # MÉTODO 1: Botón X de cerrar (más confiable)
            try:
                boton_x = self.page.locator('.close[data-dismiss="modal"]')
                if await boton_x.count() > 0:
                    await boton_x.first.click(timeout=3000)
                    await asyncio.sleep(1)
                    self._log("✅ Modal cerrado con botón X")
                    return True
            except Exception as e:
                self._log(f"⚠️ Método 1 falló: {e}")
            
            # MÉTODO 2: Escape key
            try:
                await self.page.keyboard.press('Escape', timeout=2000)
                await asyncio.sleep(1)
                self._log("✅ Modal cerrado con Escape")
                return True
            except Exception as e:
                self._log(f"⚠️ Método 2 falló: {e}")
            
            # MÉTODO 3: Clic fuera del modal (backdrop)
            try:
                await self.page.locator('.modal-backdrop').click(timeout=3000)
                await asyncio.sleep(1)
                self._log("✅ Modal cerrado con backdrop")
                return True
            except Exception as e:
                self._log(f"⚠️ Método 3 falló: {e}")
            
            # MÉTODO 4: JavaScript directo para cerrar modal Bootstrap
            try:
                await self.page.evaluate("""
                    () => {
                        // Cerrar modal de Bootstrap
                        const modal = document.querySelector('.modal.show');
                        if (modal) {
                            // Método Bootstrap
                            if (window.$ && window.$('.modal.show').length > 0) {
                                window.$('.modal.show').modal('hide');
                            }
                            // Método directo
                            modal.style.display = 'none';
                            modal.classList.remove('show');
                            
                            // Remover backdrop
                            const backdrop = document.querySelector('.modal-backdrop');
                            if (backdrop) {
                                backdrop.remove();
                            }
                            
                            // Restaurar scroll del body
                            document.body.classList.remove('modal-open');
                            document.body.style.overflow = '';
                            document.body.style.paddingRight = '';
                            
                            return true;
                        }
                        return false;
                    }
                """, timeout=3000)
                await asyncio.sleep(1)
                self._log("✅ Modal cerrado con JavaScript")
                return True
            except Exception as e:
                self._log(f"⚠️ Método 4 falló: {e}")
            
            # MÉTODO 5: Forzar recarga de página como último recurso
            try:
                current_url = self.page.url
                if "respuestaGlosastart" in current_url:
                    await self.page.reload(timeout=10000)
                    await asyncio.sleep(2)
                    self._log("⚠️ Modal cerrado forzando recarga de página")
                    return True
            except Exception as e:
                self._log(f"⚠️ Método 5 falló: {e}")
            
            self._log("❌ No se pudo cerrar el modal con ningún método")
            return False
                
        except Exception as e:
            self._log(f"❌ Error general cerrando modal: {e}", "error")
            return False
    
    async def _marcar_cuenta_fallida(self, idcuenta: str, motivo: str):
        """
        🔄 MEJORAR MÉTODO EXISTENTE (conservar signals y lógica actual)
        """
        try:
            self._log(f"❌ Marcando cuenta {idcuenta} como FALLIDA: {motivo}")

            # Usar tu método existente del db_manager
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,  # o EstadoCuenta.FALLIDA según tu enum
                motivo
            )

            # ✅ CONSERVAR tus signals existentes
            if self.worker:
                self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')
                self.worker.emit_tabla_refresh()

            self._log(f"✅ Cuenta {idcuenta} marcada como FALLIDA en BD")

        except Exception as e:
            self._log(f"❌ Error marcando cuenta como fallida: {e}", "error")
    
    async def _guardar_glosa_procesada(self, idcuenta: str, glosa_info: Dict, configuracion: Dict):
        print(f"🟢 [DEBUG] Llamando a _guardar_glosa_procesada para idcuenta={idcuenta}, id_glosa={glosa_info.get('id_glosa', '')}")
    
        """Guarda una glosa como procesada en ambas tablas."""
        try:
            cuenta_id = await self._obtener_cuenta_id(idcuenta)
            if not cuenta_id:
                return
            with self.db_manager.get_connection() as conn:
                # Verifica si la fila existe antes del UPDATE
                cursor = conn.execute(
                    "SELECT id FROM glosa_items_detalle WHERE cuenta_principal_id = ? AND id_glosa = ?",
                    (cuenta_id, glosa_info.get('id_glosa', ''))
                )
                existe = cursor.fetchone()
                if not existe:
                    self._log(f"❌ No existe la fila en glosa_items_detalle para cuenta_principal_id={cuenta_id}, id_glosa={glosa_info.get('id_glosa', '')}", "error")
                # UPDATE
                conn.execute("""
                    UPDATE glosa_items_detalle
                    SET fue_procesado = TRUE,
                        fecha_procesamiento = CURRENT_TIMESTAMP,
                        respuesta_enviada = ?,
                        archivo_subido = ?,
                        error_procesamiento = ''
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (
                    configuracion.get('respuesta', ''),
                    configuracion.get('pdf_path', ''),
                    cuenta_id,
                    glosa_info.get('id_glosa', '')
                ))
                self._log(f"Filas actualizadas: {conn.total_changes}")
                conn.commit()
            self._log(f"✅ Glosa {glosa_info.get('id_glosa', '')} guardada como procesada en ambas tablas")

        except Exception as e:
            self._log(f"⚠️ Error guardando glosa procesada: {e}", "warning")
    
    async def _guardar_glosa_fallida(self, idcuenta: str, glosa_info: Dict, error: str):
        """Guarda una glosa como fallida en ambas tablas."""
        print(f"🔴 [DEBUG] Llamando a _guardar_glosa_fallida para idcuenta={idcuenta}, id_glosa={glosa_info.get('id_glosa', '')}, error={error}")
   
        try:
            cuenta_id = await self._obtener_cuenta_id(idcuenta)
            if not cuenta_id:
                return
                
            with self.db_manager.get_connection() as conn:
            # 1. Insertar en glosas_detalles_procesadas con error
             conn.execute("""
                 INSERT INTO glosas_detalles_procesadas 
                 (idcuenta, id_glosa, estado_procesamiento, error_mensaje)
                 VALUES (?, ?, 'ERROR', ?)
             """, (idcuenta, glosa_info['id_glosa'], error))

             # 2. Actualizar glosa_items_detalle
             conn.execute("""
                 UPDATE glosa_items_detalle 
                 SET error_procesamiento = ?,
                     fecha_procesamiento = CURRENT_TIMESTAMP
                 WHERE cuenta_principal_id = ? AND id_glosa = ?
             """, (error, cuenta_id, glosa_info['id_glosa']))

             conn.commit()
            
        except Exception as e:
            self._log(f"⚠️ Error guardando glosa fallida: {e}", "warning")

    async def _guardar_glosa_sin_config(self, idcuenta: str, glosa_info: Dict):
        """Guarda una glosa como sin configuración."""
        try:
            cuenta_id = await self._obtener_cuenta_id(idcuenta)
            if not cuenta_id:
                return

            with self.db_manager.get_connection() as conn:
                # Solo actualizar glosa_items_detalle
                conn.execute("""
                    UPDATE glosa_items_detalle 
                    SET error_procesamiento = 'SIN_CONFIGURACION',
                        es_procesable = FALSE
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (cuenta_id, glosa_info['id_glosa']))

                conn.commit()

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
        """
        Navega a tabla principal y hace clic en la cuenta.
        MEJORADO: Marca como FALLIDO si no puede hacer clic.
        """
        try:
            self._log(f"🖱️ Navegando y haciendo clic en cuenta {idcuenta}")

            # Asegurar que estamos en tabla principal
            if not await self._asegurar_tabla_principal():
                error_msg = "No se pudo regresar a la tabla principal"
                await self._marcar_cuenta_fallida(idcuenta, error_msg)
                return False

            # Buscar la cuenta dinámicamente en la tabla actual
            filas = self.page.locator(self.selectores['filas_tabla_principal'])
            total_filas = await filas.count()

            self._log(f"🔍 Buscando cuenta {idcuenta} en {total_filas} filas disponibles")

            for i in range(total_filas):
                try:
                    fila = filas.nth(i)
                    celdas = fila.locator("td")

                    if await celdas.count() > 0:
                        id_celda = await celdas.nth(0).text_content()
                        id_celda = id_celda.strip()

                        if id_celda == idcuenta:
                            self._log(f"✅ Cuenta {idcuenta} encontrada en fila {i}")

                            # Buscar el botón dentro de esta fila
                            boton_cuenta = fila.locator(self.selectores['boton_cuenta'])

                            if await boton_cuenta.count() == 0:
                                # Marcar como FALLIDO si no hay botón
                                error_msg = f"No se encontró botón en la fila de cuenta {idcuenta}"
                                await self._marcar_cuenta_fallida(idcuenta, error_msg)
                                return False

                            # Hacer scroll al botón
                            await boton_cuenta.first.scroll_into_view_if_needed()
                            await asyncio.sleep(1)

                            # Hacer clic
                            await boton_cuenta.first.click()
                            self._log(f"🖱️ Clic realizado en botón de cuenta {idcuenta}")

                            # Esperar a que cargue la página de glosas
                            await self.page.wait_for_load_state('networkidle', timeout=15000)
                            await asyncio.sleep(5)

                            return True

                except Exception as e:
                    self._log(f"⚠️ Error verificando fila {i}: {e}", "warning")
                    continue

            # Si no se encuentra la cuenta, marcar como FALLIDO
            error_msg = f"Cuenta {idcuenta} no encontrada en la tabla actual"
            await self._marcar_cuenta_fallida(idcuenta, error_msg)
            return False

        except Exception as e:
            error_msg = f"Error navegando/haciendo clic cuenta {idcuenta}: {e}"
            self._log(error_msg, "error")

            # Marcar como FALLIDO en caso de excepción
            await self._marcar_cuenta_fallida(idcuenta, error_msg)
            return False

    
    async def _obtener_cuenta_id(self, idcuenta: str) -> Optional[int]:
        """Obtiene el ID interno de la cuenta desde la BD."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id FROM cuenta_glosas_principal WHERE idcuenta = ?",
                    (idcuenta,)
                )
                row = cursor.fetchone()
                return row['id'] if row else None
        except Exception as e:
            self._log(f"❌ Error obteniendo ID de cuenta: {e}", "error")
            return None


    async def _procesar_todas_las_glosas_cuenta(self, idcuenta: str) -> Dict:
        """
        ✅ CORREGIDO: Usar nombres correctos de métodos y campos
        """
        try:
            self._log(f"📋 Procesando todas las glosas de cuenta {idcuenta}")
    
            # PASO 1: Extraer glosas
            if not await self._hacer_scroll_hasta_tabla_glosas():
                return {'exito': False, 'error': 'No se pudo hacer scroll hasta tabla de glosas'}
    
            glosas_extraidas = await self._extraer_glosas_de_tabla(idcuenta)
    
            if not glosas_extraidas:
                return {'exito': False, 'error': 'No se encontraron glosas para procesar'}
    
            self._log(f"📊 Encontradas {len(glosas_extraidas)} glosas para procesar")
    
            # ✅ PASO 2 CORREGIDO: Verificar configuraciones usando método correcto
            glosas_con_config = []
            glosas_sin_config = []
    
            for glosa in glosas_extraidas:
                # ✅ CORREGIR: Usar nombres correctos de campos extraídos
                tipo_glosa = glosa.get('tipo', '')
                justificacion_glosa = glosa.get('justificacion', '')
    
                # ✅ CORREGIR: Usar método que SÍ existe
                configuracion = self._buscar_configuracion_glosa(tipo_glosa, justificacion_glosa)
    
                if configuracion:
                    glosa['configuracion'] = configuracion
                    glosas_con_config.append(glosa)
                    self._log(f"   ✅ Glosa {glosa['id_glosa']}: Configuración encontrada")
                else:
                    glosas_sin_config.append(glosa)
                    self._log(f"   ❌ Glosa {glosa['id_glosa']}: SIN configuración para {tipo_glosa}")
    
            # PASO 3: Si hay glosas sin configuración, manejar correctamente
            if glosas_sin_config:
                self._log(f"⚠️ {len(glosas_sin_config)} glosas sin configuración - Guardando en BD")
                await self._guardar_glosas_sin_configuracion(idcuenta, glosas_sin_config)
    
                if not glosas_con_config:
                    return {
                        'exito': False, 
                        'error': f"Todas las glosas ({len(glosas_sin_config)}) sin configuración",
                        'glosas_sin_config': len(glosas_sin_config)
                    }
    
            # ✅ PASO 4 CORREGIDO: Procesar solo las glosas CON configuración
            if glosas_con_config:
                self._log(f"🚀 Procesando {len(glosas_con_config)} glosas con configuración")
    
                glosas_procesadas = 0
                glosas_fallidas = 0
    
                for i, glosa in enumerate(glosas_con_config):
                    self._log(f"   🔄 Procesando glosa {i+1}/{len(glosas_con_config)}: {glosa['id_glosa']}")
    
                    try:
                        # ✅ CORREGIR: Usar método con parámetro correcto
                        resultado = await self._procesar_glosa_individual(glosa)
    
                        if resultado['exito']:
                            glosas_procesadas += 1
                            self._log(f"   ✅ Glosa {glosa['id_glosa']} procesada exitosamente")
                        else:
                            glosas_fallidas += 1
                            self._log(f"   ❌ Glosa {glosa['id_glosa']} falló: {resultado.get('error', '')}")
    
                    except Exception as e:
                        glosas_fallidas += 1
                        self._log(f"   ❌ Error procesando glosa {glosa['id_glosa']}: {e}", "error")
    
                    await asyncio.sleep(2)
    
                return {
                    'exito': True,
                    'glosas_procesadas': glosas_procesadas,
                    'glosas_fallidas': glosas_fallidas,
                    'glosas_sin_config': len(glosas_sin_config) if glosas_sin_config else 0
                }
    
            return {'exito': False, 'error': 'No hay glosas procesables'}
    
        except Exception as e:
            error_msg = f"Error procesando glosas de cuenta {idcuenta}: {e}"
            self._log(error_msg, "error")
            return {'exito': False, 'error': error_msg}

    async def _hacer_scroll_hasta_tabla_glosas(self) -> bool:
        """
        ✅ MÉTODO FALTANTE AGREGADO
        Hace scroll hasta la tabla de glosas.
        """
        try:
            # Buscar la tabla de glosas y hacer scroll
            
            tabla_glosas = self.page.locator(self.selectores['tabla_glosas'])

            if await tabla_glosas.count() > 0:
                await tabla_glosas.scroll_into_view_if_needed()
                await asyncio.sleep(2)
                self._log("✅ Scroll hasta tabla de glosas realizado")
                return True
            else:
                # Hacer scroll general hacia abajo
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
                await asyncio.sleep(3)
                self._log("✅ Scroll general realizado")
                return True

        except Exception as e:
            self._log(f"⚠️ Error haciendo scroll: {e}", "warning")
            return False

    def _guardar_glosa_en_detalle(self, cuenta_id: int, glosa_info: Dict):
        """
        MEJORADO: Guarda una glosa en la tabla de detalle con mejor logging.
        """
        try:
            self._log(f"💾 Guardando glosa {glosa_info.get('id_glosa', 'N/A')} en detalle...")
            
            with self.db_manager.get_connection() as conn:
                # Verificar si ya existe
                cursor = conn.execute("""
                    SELECT id FROM glosa_items_detalle 
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (cuenta_id, glosa_info.get('id_glosa', '')))

                existe = cursor.fetchone()
                
                if existe:
                    self._log(f"🔄 Actualizando glosa existente {glosa_info['id_glosa']}")
                    # Actualizar
                    conn.execute("""
                        UPDATE glosa_items_detalle 
                        SET descripcion_item = ?, tipo = ?, descripcion = ?,
                            justificacion = ?, valor_glosado = ?, estado_original = ?,
                            es_procesable = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE cuenta_principal_id = ? AND id_glosa = ?
                    """, (
                        glosa_info.get('descripcion_item', ''),
                        glosa_info.get('tipo', ''),
                        glosa_info.get('descripcion', ''),
                        glosa_info.get('justificacion', ''),
                        self._parsear_moneda(glosa_info.get('valor_glosado', '0')),
                        glosa_info.get('estado', 'SIN RESPUESTA'),
                        self._es_procesable(glosa_info),
                        cuenta_id,
                        glosa_info['id_glosa']
                    ))
                    self._log(f"✅ Glosa {glosa_info['id_glosa']} actualizada")
                else:
                    self._log(f"➕ Insertando nueva glosa {glosa_info['id_glosa']}")
                    # Insertar nueva
                    conn.execute("""
                        INSERT INTO glosa_items_detalle 
                        (cuenta_principal_id, id_glosa, id_item, descripcion_item,
                         tipo, descripcion, justificacion, valor_glosado, 
                         estado_original, es_procesable, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        cuenta_id,
                        glosa_info.get('id_glosa', ''),
                        glosa_info.get('id_item', ''),
                        glosa_info.get('descripcion_item', ''),
                        glosa_info.get('tipo', ''),
                        glosa_info.get('descripcion', ''),
                        glosa_info.get('justificacion', ''),
                        self._parsear_moneda(glosa_info.get('valor_glosado', '0')),
                        glosa_info.get('estado', 'SIN RESPUESTA'),
                        self._es_procesable(glosa_info)
                    ))
                    self._log(f"✅ Glosa {glosa_info['id_glosa']} insertada")

                conn.commit()

        except Exception as e:
            self._log(f"❌ Error guardando glosa en detalle: {e}", "error")
    
    def _es_procesable(self, glosa_info: Dict) -> bool:
        """Determina si una glosa es procesable según las reglas de negocio."""
        tipo = glosa_info.get('tipo', '').upper()
        justificacion = glosa_info.get('justificacion', '').upper()
        estado = glosa_info.get('estado', '').upper()

        # Es procesable si:
        # 1. Tipo es TARIFAS y contiene MAYOR VALOR
        # 2. Estado es SIN RESPUESTA
        # 3. Hay configuración disponible para ella

        if estado != 'SIN RESPUESTA':
            return False

        if tipo == 'TARIFAS' and 'MAYOR VALOR' in justificacion:
            return True

        # Verificar si hay configuración
        return self._buscar_configuracion_glosa(tipo, justificacion) is not None
    

    async def _diagnosticar_bd_glosas(self, idcuenta: str):
        """
        MÉTODO DE DIAGNÓSTICO: Verifica qué se está guardando en la BD.
        Agregar temporalmente para debuggear.
        """
        try:
            self._log(f"🔍 DIAGNÓSTICO BD para cuenta {idcuenta}")
            
            with self.db_manager.get_connection() as conn:
                # 1. Verificar cuenta principal
                cursor = conn.execute("""
                    SELECT id, idcuenta, estado, glosas_encontradas, glosas_procesadas 
                    FROM cuenta_glosas_principal 
                    WHERE idcuenta = ?
                """, (idcuenta,))
                
                cuenta_info = cursor.fetchone()
                if cuenta_info:
                    self._log(f"✅ Cuenta principal encontrada:")
                    self._log(f"   ID: {cuenta_info['id']}")
                    self._log(f"   Estado: {cuenta_info['estado']}")
                    self._log(f"   Glosas encontradas: {cuenta_info['glosas_encontradas']}")
                    self._log(f"   Glosas procesadas: {cuenta_info['glosas_procesadas']}")
                    
                    cuenta_id = cuenta_info['id']
                else:
                    self._log(f"❌ Cuenta principal NO encontrada para {idcuenta}")
                    return
                
                # 2. Verificar glosas en detalle
                cursor = conn.execute("""
                    SELECT id_glosa, tipo, estado_original, es_procesable, fue_procesado, 
                           error_procesamiento, fecha_procesamiento
                    FROM glosa_items_detalle 
                    WHERE cuenta_principal_id = ?
                    ORDER BY id_glosa
                """, (cuenta_id,))
                
                glosas_detalle = cursor.fetchall()
                
                self._log(f"📋 Glosas en detalle: {len(glosas_detalle)}")
                for i, glosa in enumerate(glosas_detalle):
                    if i < 3:  # Solo mostrar las primeras 3
                        self._log(f"   Glosa {glosa['id_glosa']}:")
                        self._log(f"     Tipo: {glosa['tipo']}")
                        self._log(f"     Estado: {glosa['estado_original']}")
                        self._log(f"     Procesable: {glosa['es_procesable']}")
                        self._log(f"     Fue procesado: {glosa['fue_procesado']}")
                        if glosa['error_procesamiento']:
                            self._log(f"     Error: {glosa['error_procesamiento']}")
                
                # 3. Verificar tabla de procesadas
                cursor = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM glosas_detalles_procesadas 
                    WHERE idcuenta = ?
                """, (idcuenta,))
                
                procesadas_count = cursor.fetchone()['count']
                self._log(f"📊 Glosas en tabla procesadas: {procesadas_count}")
                
        except Exception as e:
            self._log(f"❌ Error en diagnóstico BD: {e}", "error")