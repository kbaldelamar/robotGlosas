import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState, NavigationState
from automation.procesador_glosa_individual import ProcesadorGlosaIndividual

class ProcesadorTablaGlosas:
    """
    Procesador de la tabla principal de glosas (Bolsa Respuesta).
    VERSIÓN INTEGRADA CON ARQUITECTURA SEPARADA: 
    1. Extrae todos los datos de la tabla
    2. Procesa cada cuenta usando ProcesadorGlosaIndividual
    3. Maneja la navegación entre tabla y procesamiento individual
    """
    
    def __init__(self, page: Page, automation_state: AutomationState):
        """
        Inicializa el procesador de tabla de glosas.
        
        Args:
            page (Page): Página de Playwright
            automation_state (AutomationState): Estado compartido de automatización
        """
        self.page = page
        self.state = automation_state
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManagerGlosas()
        
        # INSTANCIA DE PROCESADOR INDIVIDUAL
        self.procesador_individual = ProcesadorGlosaIndividual(
            page=self.page,
            automation_state=self.state,
            db_manager=self.db_manager
        )
        
        # Selectores específicos de la tabla
        self.selectores = {
            'select_longitud_tabla': "//select[contains(@name,'tablaRespuestaGlosa_length')]",
            'opcion_100_xpath': "//option[@value='100']",
            'opcion_100_css': "option[value='100']",
            'opcion_100_especifica': "//option[@value='100'][contains(.,'100')]",
            'cuerpo_tabla': "#tablaRespuestaGlosa tbody",
            'filas_tabla': "#tablaRespuestaGlosa tbody tr",
            'boton_iniciar': ".btRespuestaStart",
            'info_tabla': "#tablaRespuestaGlosa_info"
        }
        
        # URL base para regresar a la tabla
        self.url_tabla_base = None
        
        # Estadísticas de procesamiento
        self.estadisticas = {
            'total_cuentas': 0,
            'procesadas_exitosas': 0,
            'procesadas_fallidas': 0,
            'saltadas': 0,
            'tiempo_inicio': 0,
            'tiempo_fin': 0
        }
        
        self.state.update(
            class_name="ProcesadorTablaGlosas",
            method_name="__init__"
        )
        
        self._registrar_estado("ProcesadorTablaGlosas inicializado con procesador individual integrado")
    
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
    
    async def procesar_filas_tabla(self) -> Tuple[int, int]:
        """
        MÉTODO PRINCIPAL: Procesa filas con lógica separada e integración completa.
        
        PASO 1: Extrae todos los datos y los guarda en BD
        PASO 2: Procesa cada cuenta usando ProcesadorGlosaIndividual
        
        Returns:
            Tuple[int, int]: (filas_procesadas, filas_saltadas)
        """
        try:
            self.state.update(
                method_name="procesar_filas_tabla",
                action="Procesando filas con arquitectura separada completa"
            )
            
            self.estadisticas['tiempo_inicio'] = asyncio.get_event_loop().time()
            
            self._registrar_estado("🚀 INICIANDO PROCESAMIENTO COMPLETO CON ARQUITECTURA SEPARADA")
            self._registrar_estado("="*80)
            
            # PASO 1: CONFIGURAR TABLA Y EXTRAER DATOS
            cuentas_para_procesar = await self._paso1_extraer_y_guardar_datos()
            
            if not cuentas_para_procesar:
                self._registrar_estado("⚠️ No hay cuentas para procesar", "warning")
                return 0, 0
            
            self.estadisticas['total_cuentas'] = len(cuentas_para_procesar)
            
            # PASO 2: PROCESAR CADA CUENTA CON CLASE ESPECIALIZADA
            filas_procesadas, filas_saltadas = await self._paso2_procesar_con_clase_individual(cuentas_para_procesar)
            
            self.estadisticas['tiempo_fin'] = asyncio.get_event_loop().time()
            
            # MOSTRAR ESTADÍSTICAS FINALES
            await self._mostrar_estadisticas_finales()
            
            self._registrar_estado("="*80)
            self._registrar_estado(f"📊 PROCESAMIENTO COMPLETO TERMINADO - Procesadas: {filas_procesadas}, Saltadas: {filas_saltadas}")
            
            return filas_procesadas, filas_saltadas
            
        except Exception as e:
            self._registrar_estado(f"❌ Error en procesamiento completo: {e}", "error")
            return 0, 0
    
    async def _paso1_extraer_y_guardar_datos(self) -> List[Dict]:
        """
        PASO 1: Extrae todos los datos de la tabla y los guarda en BD.
        
        Returns:
            List[Dict]: Lista de cuentas que necesitan procesarse
        """
        try:
            self.state.update(
                method_name="_paso1_extraer_y_guardar_datos",
                action="PASO 1: Extrayendo y guardando datos masivamente"
            )
            
            self._registrar_estado("📋 PASO 1: EXTRACCIÓN MASIVA DE DATOS")
            self._registrar_estado("-"*50)
            
            # Configurar tabla para mostrar 100
            if not await self.configurar_tabla_mostrar_100():
                self._registrar_estado("❌ Error configurando tabla", "error")
                return []
            
            # Guardar URL actual para poder regresar
            self.url_tabla_base = self.page.url
            self._registrar_estado(f"💾 URL base guardada: {self.url_tabla_base}")
            
            # Extraer datos de todas las filas
            todos_los_datos = await self.extraer_datos_filas_tabla()
            
            if not todos_los_datos:
                self._registrar_estado("❌ No se extrajeron datos de la tabla", "error")
                return []
            
            # Procesar datos y guardar en BD
            cuentas_para_procesar = []
            cuentas_saltadas = 0
            
            self._registrar_estado(f"💾 Guardando {len(todos_los_datos)} cuentas en base de datos...")
            
            for i, datos_fila in enumerate(todos_los_datos):
                idcuenta = datos_fila['idcuenta']
                
                try:
                    # Verificar si debe procesarse esta cuenta
                    if self.db_manager.should_process_cuenta(idcuenta):
                        # Crear/actualizar registro en BD
                        cuenta_id = self.db_manager.create_or_update_cuenta(datos_fila)
                        
                        # Agregar a lista de procesamiento
                        datos_fila['cuenta_bd_id'] = cuenta_id
                        cuentas_para_procesar.append(datos_fila)
                        
                        if i % 10 == 0 or i < 5:  # Log cada 10 cuentas o las primeras 5
                            self._registrar_estado(f"💾 Cuenta {idcuenta} guardada en BD - ID: {cuenta_id}")
                    else:
                        cuentas_saltadas += 1
                        if cuentas_saltadas <= 5:  # Log solo las primeras 5 saltadas
                            self._registrar_estado(f"⏭️ Cuenta {idcuenta} saltada por estado")
                except Exception as e:
                    self._registrar_estado(f"❌ Error procesando cuenta {idcuenta}: {e}", "error")
                    continue
            
            self._registrar_estado("-"*50)
            self._registrar_estado(f"📊 PASO 1 COMPLETADO:")
            self._registrar_estado(f"   • Total extraídas: {len(todos_los_datos)}")
            self._registrar_estado(f"   • Para procesar: {len(cuentas_para_procesar)}")
            self._registrar_estado(f"   • Saltadas: {cuentas_saltadas}")
            self._registrar_estado("-"*50)
            
            return cuentas_para_procesar
            
        except Exception as e:
            self._registrar_estado(f"❌ Error en PASO 1: {e}", "error")
            return []
    
    async def _paso2_procesar_con_clase_individual(self, cuentas_para_procesar: List[Dict]) -> Tuple[int, int]:
        """
        PASO 2: Procesa cada cuenta usando la clase ProcesadorGlosaIndividual.
        
        Args:
            cuentas_para_procesar (List[Dict]): Lista de cuentas a procesar
            
        Returns:
            Tuple[int, int]: (filas_procesadas, filas_saltadas)
        """
        try:
            self.state.update(
                method_name="_paso2_procesar_con_clase_individual",
                action="PASO 2: Procesamiento individual con clase especializada"
            )
            
            self._registrar_estado("🔄 PASO 2: PROCESAMIENTO INDIVIDUAL")
            self._registrar_estado("-"*50)
            self._registrar_estado(f"🎯 Procesando {len(cuentas_para_procesar)} cuentas con ProcesadorGlosaIndividual")
            self._registrar_estado("-"*50)
            
            filas_procesadas = 0
            filas_saltadas = 0
            
            for i, datos_cuenta in enumerate(cuentas_para_procesar):
                idcuenta = datos_cuenta['idcuenta']
                indice_fila = datos_cuenta['indice_fila']
                
                # Header de procesamiento de cuenta
                self._registrar_estado("")
                self._registrar_estado(f"🎯 PROCESANDO CUENTA {i+1}/{len(cuentas_para_procesar)}")
                self._registrar_estado(f"   ID: {idcuenta}")
                self._registrar_estado(f"   Proveedor: {datos_cuenta.get('proveedor', 'N/A')}")
                self._registrar_estado(f"   Valor Glosado: ${datos_cuenta.get('valor_glosado', 0):,.2f}")
                
                try:
                    # SUBPASO 2.1: Asegurar que estamos en la tabla
                    if not await self._asegurar_en_tabla():
                        self._registrar_estado(f"❌ No se pudo regresar a la tabla para cuenta {idcuenta}", "error")
                        self._marcar_cuenta_fallida(idcuenta, "No se pudo regresar a tabla")
                        filas_saltadas += 1
                        self.estadisticas['procesadas_fallidas'] += 1
                        continue
                    
                    # SUBPASO 2.2: Hacer clic en el botón para ir a la pantalla individual
                    self._registrar_estado(f"   🖱️ Haciendo clic en botón de fila {indice_fila}...")
                    if not await self._hacer_clic_boton_fila_individual(indice_fila, idcuenta):
                        self._registrar_estado(f"❌ No se pudo hacer clic para cuenta {idcuenta}", "error")
                        self._marcar_cuenta_fallida(idcuenta, "Error haciendo clic en botón")
                        filas_saltadas += 1
                        self.estadisticas['procesadas_fallidas'] += 1
                        continue
                    
                    # SUBPASO 2.3: PROCESAR CON CLASE ESPECIALIZADA
                    self._registrar_estado(f"   🔍 Delegando a ProcesadorGlosaIndividual...")
                    
                    resultado_procesamiento = await self.procesador_individual.procesar_glosa_completa(
                        idcuenta=idcuenta,
                        datos_cuenta=datos_cuenta
                    )
                    
                    # SUBPASO 2.4: Evaluar resultado
                    if resultado_procesamiento['exito']:
                        glosas_proc = resultado_procesamiento.get('glosas_procesadas', 0)
                        tiempo_proc = resultado_procesamiento.get('tiempo_procesamiento', 0)
                        
                        self._registrar_estado(f"   ✅ CUENTA PROCESADA EXITOSAMENTE")
                        self._registrar_estado(f"      • Glosas procesadas: {glosas_proc}")
                        self._registrar_estado(f"      • Tiempo: {tiempo_proc:.2f}s")
                        
                        filas_procesadas += 1
                        self.estadisticas['procesadas_exitosas'] += 1
                    else:
                        error_msg = resultado_procesamiento.get('error', 'Error desconocido')
                        self._registrar_estado(f"   ❌ ERROR EN PROCESAMIENTO INDIVIDUAL")
                        self._registrar_estado(f"      • Error: {error_msg[:100]}")
                        
                        filas_saltadas += 1
                        self.estadisticas['procesadas_fallidas'] += 1
                    
                except Exception as e:
                    self._registrar_estado(f"   ❌ ERROR GENERAL procesando cuenta {idcuenta}: {e}", "error")
                    self._marcar_cuenta_fallida(idcuenta, f"Error general: {e}")
                    filas_saltadas += 1
                    self.estadisticas['procesadas_fallidas'] += 1
                
                # Pausa entre procesamiento
                await asyncio.sleep(1)
                
                # Log de progreso cada 5 cuentas
                if (i + 1) % 5 == 0:
                    porcentaje = ((i + 1) / len(cuentas_para_procesar)) * 100
                    self._registrar_estado("")
                    self._registrar_estado(f"📊 PROGRESO: {i+1}/{len(cuentas_para_procesar)} ({porcentaje:.1f}%)")
                    self._registrar_estado(f"   • Exitosas: {filas_procesadas}")
                    self._registrar_estado(f"   • Fallidas: {filas_saltadas}")
                    self._registrar_estado("")
            
            self._registrar_estado("-"*50)
            self._registrar_estado(f"📊 PASO 2 COMPLETADO:")
            self._registrar_estado(f"   • Procesadas exitosamente: {filas_procesadas}")
            self._registrar_estado(f"   • Fallidas/Saltadas: {filas_saltadas}")
            self._registrar_estado("-"*50)
            
            return filas_procesadas, filas_saltadas
            
        except Exception as e:
            self._registrar_estado(f"❌ Error en PASO 2: {e}", "error")
            return 0, 0
    
    async def _mostrar_estadisticas_finales(self):
        """Muestra estadísticas detalladas del procesamiento."""
        try:
            tiempo_total = self.estadisticas['tiempo_fin'] - self.estadisticas['tiempo_inicio']
            
            self._registrar_estado("")
            self._registrar_estado("📊 ESTADÍSTICAS FINALES")
            self._registrar_estado("="*80)
            self._registrar_estado(f"⏱️  TIEMPO TOTAL: {tiempo_total:.2f} segundos")
            self._registrar_estado(f"📋 CUENTAS TOTALES: {self.estadisticas['total_cuentas']}")
            self._registrar_estado(f"✅ PROCESADAS EXITOSAS: {self.estadisticas['procesadas_exitosas']}")
            self._registrar_estado(f"❌ PROCESADAS FALLIDAS: {self.estadisticas['procesadas_fallidas']}")
            self._registrar_estado(f"⏭️  SALTADAS: {self.estadisticas['saltadas']}")
            
            if self.estadisticas['total_cuentas'] > 0:
                tasa_exito = (self.estadisticas['procesadas_exitosas'] / self.estadisticas['total_cuentas']) * 100
                self._registrar_estado(f"📈 TASA DE ÉXITO: {tasa_exito:.1f}%")
                
                if self.estadisticas['procesadas_exitosas'] > 0:
                    tiempo_promedio = tiempo_total / self.estadisticas['procesadas_exitosas']
                    self._registrar_estado(f"⚡ TIEMPO PROMEDIO POR CUENTA: {tiempo_promedio:.2f}s")
            
            self._registrar_estado("="*80)
            
        except Exception as e:
            self._registrar_estado(f"❌ Error mostrando estadísticas: {e}", "error")
    
    async def _asegurar_en_tabla(self) -> bool:
        """
        Se asegura de que estamos en la página de la tabla.
        Si no, navega de vuelta.
        
        Returns:
            bool: True si estamos en la tabla
        """
        try:
            # Verificar si estamos en la URL de la tabla
            url_actual = self.page.url
            
            # Si estamos en una URL de procesamiento de glosa, regresar
            if "respuestaGlosastart" in url_actual or url_actual != self.url_tabla_base:
                self._registrar_estado("🔄 No estamos en la tabla, regresando...")
                
                # Navegar de vuelta a la tabla
                await self.page.goto(self.url_tabla_base)
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(2)
                
                # Verificar que la tabla esté presente
                tabla_presente = await self.page.locator(self.selectores['filas_tabla']).count() > 0
                
                if tabla_presente:
                    self._registrar_estado("✅ Regresado a la tabla exitosamente")
                    return True
                else:
                    self._registrar_estado("❌ Error: tabla no encontrada después de regresar", "error")
                    return False
            
            # Ya estamos en la tabla
            return True
            
        except Exception as e:
            self._registrar_estado(f"❌ Error asegurando estar en tabla: {e}", "error")
            return False
    
    async def _hacer_clic_boton_fila_individual(self, indice_fila: int, idcuenta: str) -> bool:
        """
        Hace clic en el botón de una fila específica para ir a procesamiento individual.
        
        Args:
            indice_fila (int): Índice de la fila
            idcuenta (str): ID de la cuenta para logs
            
        Returns:
            bool: True si se hizo clic correctamente
        """
        try:
            # Verificar que la página esté activa
            if not await self._verificar_pagina_activa():
                self._registrar_estado(f"❌ Página no activa para cuenta {idcuenta}", "error")
                return False
            
            # Obtener la fila específica
            fila = self.page.locator(self.selectores['filas_tabla']).nth(indice_fila)
            
            # Verificar que la fila existe
            if await fila.count() == 0:
                self._registrar_estado(f"❌ Fila {indice_fila} no encontrada para cuenta {idcuenta}", "error")
                return False
            
            # Buscar el botón dentro de la fila
            boton = fila.locator(self.selectores['boton_iniciar'])
            
            if await boton.count() == 0:
                self._registrar_estado(f"❌ Botón no encontrado en fila {indice_fila} para cuenta {idcuenta}", "error")
                return False
            
            # Hacer scroll al botón si es necesario
            await boton.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # Hacer clic con timeout
            await boton.click(timeout=5000)
            self._registrar_estado(f"✅ Clic realizado en botón para cuenta {idcuenta}")
            
            # Esperar a que cargue la nueva página
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            self._registrar_estado(f"❌ Error haciendo clic para cuenta {idcuenta}: {e}", "error")
            return False
    
    def _marcar_cuenta_fallida(self, idcuenta: str, motivo: str):
        """Marca una cuenta como fallida en la BD."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO, 
                motivo
            )
        except Exception as e:
            self._registrar_estado(f"❌ Error marcando cuenta {idcuenta} como fallida: {e}", "error")
    
    # ========== MÉTODOS AUXILIARES ==========
    
    async def configurar_tabla_mostrar_100(self) -> bool:
        """Configura la tabla para mostrar 100 registros."""
        try:
            self.state.update(
                method_name="configurar_tabla_mostrar_100",
                action="Configurando tabla para mostrar 100 registros"
            )
            
            self._registrar_estado("🔧 Configurando tabla para mostrar 100 registros")
            
            # JavaScript directo (método más confiable)
            resultado_js = await self.page.evaluate("""
                () => {
                    const select = document.querySelector('select[name="tablaRespuestaGlosa_length"]');
                    if (!select) {
                        return { success: false, error: 'Select no encontrado' };
                    }
                    
                    const option100 = select.querySelector('option[value="100"]');
                    if (!option100) {
                        return { success: false, error: 'Opción 100 no encontrada' };
                    }
                    
                    select.value = '100';
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    select.dispatchEvent(new Event('input', { bubbles: true }));
                    
                    return { 
                        success: true, 
                        valor: select.value,
                        textoOpcion: option100.textContent 
                    };
                }
            """)
            
            if resultado_js.get('success'):
                self._registrar_estado(f"✅ JavaScript exitoso - Valor: {resultado_js['valor']}")
                
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(3)
                
                info_total = await self._obtener_info_total_tabla()
                self._registrar_estado(f"✅ Tabla configurada - {info_total}")
                return True
            else:
                self._registrar_estado(f"❌ JavaScript falló: {resultado_js.get('error')}", "error")
                return False
                
        except Exception as e:
            self._registrar_estado(f"❌ Error configurando tabla: {e}", "error")
            return False
    
    async def extraer_datos_filas_tabla(self) -> List[Dict]:
        """Extrae datos de todas las filas de la tabla."""
        try:
            self.state.update(
                method_name="extraer_datos_filas_tabla",
                action="Extrayendo datos masivos de la tabla"
            )
            
            self._registrar_estado("📊 Extrayendo datos de todas las filas (máximo 100)")
            
            if not await self._verificar_pagina_activa():
                self._registrar_estado("❌ Página no activa", "error")
                return []
            
            filas = self.page.locator(self.selectores['filas_tabla'])
            total_filas = await filas.count()
            
            self._registrar_estado(f"📈 Total de filas encontradas: {total_filas}")
            
            datos_filas = []
            
            for i in range(total_filas):
                try:
                    # Verificar página activa cada 25 filas
                    if i % 25 == 0 and i > 0:
                        if not await self._verificar_pagina_activa():
                            self._registrar_estado(f"❌ Página cerrada en fila {i}", "error")
                            break
                    
                    fila = filas.nth(i)
                    celdas = fila.locator("td")
                    total_celdas = await celdas.count()
                    
                    if total_celdas >= 8:  # Verificar columnas mínimas
                        texto_celda_6 = await celdas.nth(6).text_content()
                        texto_celda_7 = await celdas.nth(7).text_content()
                        
                        datos_fila = {
                            'idcuenta': await celdas.nth(0).text_content(),
                            'numero_radicacion': await celdas.nth(1).text_content(),
                            'fecha_radicacion': await celdas.nth(2).text_content(),
                            'proveedor': await celdas.nth(3).text_content(),
                            'numero_factura': await celdas.nth(4).text_content(),
                            'fecha_factura': await celdas.nth(5).text_content(),
                            'valor_factura': self._parsear_moneda(texto_celda_6),
                            'valor_glosado': self._parsear_moneda(texto_celda_7),
                            'indice_fila': i
                        }
                        
                        # Limpiar espacios en blanco
                        for clave, valor in datos_fila.items():
                            if isinstance(valor, str):
                                datos_fila[clave] = valor.strip()
                        
                        datos_filas.append(datos_fila)
                        
                        # Log progreso cada 20 filas o las primeras 5
                        if i % 20 == 0 or i < 5:
                            self._registrar_estado(f"✅ Fila {i+1}: ID={datos_fila['idcuenta']}, Proveedor={datos_fila['proveedor'][:30]}...")
                    
                except Exception as e:
                    self._registrar_estado(f"❌ Error extrayendo datos de fila {i}: {e}", "error")
                    continue
            
            self._registrar_estado(f"📊 Extracción completada - {len(datos_filas)} filas válidas de {total_filas}")
            return datos_filas
            
        except Exception as e:
            self._registrar_estado(f"❌ Error extrayendo datos de tabla: {e}", "error")
            return []
    
    def _parsear_moneda(self, valor: str) -> float:
        """Convierte texto de moneda a float."""
        try:
            if not valor:
                return 0.0
            limpio = valor.replace('$', '').replace(',', '').replace(' ', '').strip()
            if not limpio:
                return 0.0
            return float(limpio)
        except Exception:
            return 0.0
    
    async def _verificar_pagina_activa(self) -> bool:
        """Verifica que la página de Playwright sigue activa."""
        try:
            if self.page.is_closed():
                return False
            await self.page.locator('body').count()
            return True
        except Exception:
            return False
    
    async def _obtener_info_total_tabla(self) -> str:
        """Obtiene información del total de registros de la tabla."""
        try:
            elemento_info = self.page.locator(self.selectores['info_tabla'])
            if await elemento_info.count() > 0:
                return await elemento_info.text_content()
            return "Información no disponible"
        except:
            return "Error obteniendo información"