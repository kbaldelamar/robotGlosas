import asyncio
import logging
from typing import List, Dict, Tuple
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState

class ProcesadorTablaGlosas:
    """
    Procesador simplificado de la tabla principal de glosas.
    Versión básica que funciona sin dependencias complejas.
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
        
        # Selectores específicos de la tabla
        self.selectores = {
            'filas_tabla': "#tablaRespuestaGlosa tbody tr",
            'info_tabla': "#tablaRespuestaGlosa_info"
        }
        
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
        
        self._registrar_estado("ProcesadorTablaGlosas inicializado (versión simplificada)")
    
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
        MÉTODO PRINCIPAL: Procesa las filas de la tabla.
        Versión simplificada que extrae datos y los guarda en BD.
        
        Returns:
            Tuple[int, int]: (filas_procesadas, filas_saltadas)
        """
        try:
            self.state.update(
                method_name="procesar_filas_tabla",
                action="Procesando filas de tabla (versión simplificada)"
            )
            
            self.estadisticas['tiempo_inicio'] = asyncio.get_event_loop().time()
            
            self._registrar_estado("🚀 INICIANDO PROCESAMIENTO SIMPLIFICADO DE TABLA")
            self._registrar_estado("="*80)
            
            # PASO 1: Configurar tabla para mostrar más registros
            if not await self.configurar_tabla_mostrar_100():
                self._registrar_estado("⚠️ No se pudo configurar tabla para 100 registros", "warning")
            
            # PASO 2: Extraer datos de la tabla
            datos_extraidos = await self.extraer_datos_filas_tabla()
            
            if not datos_extraidos:
                self._registrar_estado("❌ No se extrajeron datos de la tabla", "error")
                return 0, 0
            
            # PASO 3: Procesar datos extraídos
            filas_procesadas, filas_saltadas = await self._procesar_datos_extraidos(datos_extraidos)
            
            self.estadisticas['tiempo_fin'] = asyncio.get_event_loop().time()
            
            # MOSTRAR ESTADÍSTICAS FINALES
            await self._mostrar_estadisticas_finales()
            
            self._registrar_estado("="*80)
            self._registrar_estado(f"📊 PROCESAMIENTO SIMPLIFICADO TERMINADO - Procesadas: {filas_procesadas}, Saltadas: {filas_saltadas}")
            
            return filas_procesadas, filas_saltadas
            
        except Exception as e:
            self._registrar_estado(f"❌ Error en procesamiento simplificado: {e}", "error")
            return 0, 0
    
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
                action="Extrayendo datos de la tabla"
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
    
    async def _procesar_datos_extraidos(self, datos_extraidos: List[Dict]) -> Tuple[int, int]:
        """
        Procesa los datos extraídos y los guarda en la base de datos.
        """
        try:
            self._registrar_estado(f"💾 Procesando {len(datos_extraidos)} cuentas extraídas")
            
            filas_procesadas = 0
            filas_saltadas = 0
            
            for i, datos_fila in enumerate(datos_extraidos):
                idcuenta = datos_fila['idcuenta']
                
                try:
                    # Verificar si debe procesarse esta cuenta
                    if self.db_manager.should_process_cuenta(idcuenta):
                        # Crear/actualizar registro en BD
                        cuenta_id = self.db_manager.create_or_update_cuenta(datos_fila)
                        
                        # Marcar como completado (procesamiento simplificado)
                        self.db_manager.update_cuenta_estado(
                            idcuenta, 
                            EstadoCuenta.COMPLETADO, 
                            "Procesado con método simplificado"
                        )
                        
                        filas_procesadas += 1
                        self.estadisticas['procesadas_exitosas'] += 1
                        
                        if i % 10 == 0 or i < 5:  # Log cada 10 cuentas o las primeras 5
                            self._registrar_estado(f"✅ Cuenta {idcuenta} procesada - BD ID: {cuenta_id}")
                    else:
                        filas_saltadas += 1
                        self.estadisticas['saltadas'] += 1
                        if filas_saltadas <= 5:  # Log solo las primeras 5 saltadas
                            self._registrar_estado(f"⏭️ Cuenta {idcuenta} saltada por estado")
                except Exception as e:
                    self._registrar_estado(f"❌ Error procesando cuenta {idcuenta}: {e}", "error")
                    filas_saltadas += 1
                    self.estadisticas['procesadas_fallidas'] += 1
                    
                    # Marcar como fallida en BD
                    try:
                        self.db_manager.update_cuenta_estado(
                            idcuenta, 
                            EstadoCuenta.FALLIDO, 
                            f"Error en procesamiento simplificado: {str(e)[:100]}"
                        )
                    except:
                        pass  # Si no se puede marcar, continuar
                    continue
            
            self.estadisticas['total_cuentas'] = len(datos_extraidos)
            
            self._registrar_estado("-"*50)
            self._registrar_estado(f"📊 PROCESAMIENTO DE DATOS COMPLETADO:")
            self._registrar_estado(f"   • Total extraídas: {len(datos_extraidos)}")
            self._registrar_estado(f"   • Procesadas exitosamente: {filas_procesadas}")
            self._registrar_estado(f"   • Saltadas: {filas_saltadas}")
            self._registrar_estado("-"*50)
            
            return filas_procesadas, filas_saltadas
            
        except Exception as e:
            self._registrar_estado(f"❌ Error procesando datos extraídos: {e}", "error")
            return 0, 0
    
    async def _mostrar_estadisticas_finales(self):
        """Muestra estadísticas detalladas del procesamiento."""
        try:
            tiempo_total = self.estadisticas['tiempo_fin'] - self.estadisticas['tiempo_inicio']
            
            self._registrar_estado("")
            self._registrar_estado("📊 ESTADÍSTICAS FINALES (PROCESAMIENTO SIMPLIFICADO)")
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
    
    def _parsear_moneda(self, valor: str) -> float:
        """Convierte texto de moneda a float."""
        try:
            if not valor:
                return 0.0
            limpio = valor.replace('', '').replace(',', '').replace(' ', '').strip()
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