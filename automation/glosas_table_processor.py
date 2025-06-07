import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from playwright.async_api import Page
from database.db_manager_glosas import DatabaseManagerGlosas
from database.models_glosas import EstadoCuenta
from automation.navigation_handler import AutomationState, NavigationState

class GlosasTableProcessor:
    """
    Procesador de la tabla principal de glosas (Bolsa Respuesta).
    Maneja la configuración, iteración y lógica de decisión de procesamiento.
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
        self.selectors = {
            'tabla_length_select': "select[name='tablaRespuestaGlosa_length']",
            'option_todos': "option[value='-1']",
            'tabla_body': "#tablaRespuestaGlosa tbody",
            'filas_tabla': "#tablaRespuestaGlosa tbody tr",
            'boton_iniciar': ".btRespuestaStart",
            'tabla_info': "#tablaRespuestaGlosa_info"
        }
        
        self.state.update(
            class_name="GlosasTableProcessor",
            method_name="__init__"
        )
        
        self._log_state("GlosasTableProcessor inicializado")
    
    def _log_state(self, message: str, level: str = "info"):
        """Log con información de estado actual."""
        state_info = f"[{self.state.current_class}.{self.state.current_method}]"
        full_message = f"{state_info} {message}"
        
        if level == "info":
            self.logger.info(full_message)
        elif level == "warning":
            self.logger.warning(full_message)
        elif level == "error":
            self.logger.error(full_message)
    
    async def configure_table_show_all(self) -> bool:
        """
        Configura la tabla para mostrar todos los registros.
        
        Returns:
            bool: True si se configuró correctamente
        """
        try:
            self.state.update(
                method_name="configure_table_show_all",
                action="Configurando tabla para mostrar todos los registros"
            )
            
            self._log_state("Configurando tabla para mostrar todos los registros")
            
            # Buscar el select de cantidad de entradas
            length_select = self.page.locator(self.selectors['tabla_length_select'])
            
            if await length_select.count() == 0:
                self._log_state("No se encontró el select de cantidad de entradas", "error")
                return False
            
            self._log_state("Select de cantidad encontrado")
            
            # Hacer clic en el select para abrirlo
            await length_select.click()
            await asyncio.sleep(0.5)
            
            # Buscar y seleccionar la opción "Todos"
            option_todos = self.page.locator(self.selectors['option_todos'])
            
            if await option_todos.count() == 0:
                self._log_state("No se encontró la opción 'Todos'", "error")
                return False
            
            self._log_state("Opción 'Todos' encontrada")
            
            # Hacer clic en "Todos"
            await option_todos.click()
            self._log_state("Opción 'Todos' seleccionada")
            
            # Esperar a que la tabla se recargue
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)
            
            # Verificar que se aplicó el cambio
            total_info = await self._get_table_total_info()
            self._log_state(f"Tabla configurada - {total_info}")
            
            return True
            
        except Exception as e:
            self._log_state(f"Error configurando tabla: {e}", "error")
            return False
    
    async def _get_table_total_info(self) -> str:
        """Obtiene información del total de registros de la tabla."""
        try:
            info_element = self.page.locator(self.selectors['tabla_info'])
            if await info_element.count() > 0:
                return await info_element.text_content()
            return "Información no disponible"
        except:
            return "Error obteniendo información"
    
    async def extract_table_rows_data(self) -> List[Dict]:
        """
        Extrae datos de todas las filas de la tabla.
        
        Returns:
            List[Dict]: Lista de diccionarios con datos de cada fila
        """
        try:
            self.state.update(
                method_name="extract_table_rows_data",
                action="Extrayendo datos de filas de la tabla"
            )
            
            self._log_state("Extrayendo datos de todas las filas")
            
            # Obtener todas las filas
            filas = self.page.locator(self.selectors['filas_tabla'])
            total_filas = await filas.count()
            
            self._log_state(f"Total de filas encontradas: {total_filas}")
            
            rows_data = []
            
            for i in range(total_filas):
                try:
                    fila = filas.nth(i)
                    
                    # Extraer datos de cada columna
                    celdas = fila.locator("td")
                    total_celdas = await celdas.count()
                    
                    if total_celdas >= 8:  # Verificar que tenga las columnas esperadas
                        row_data = {
                            'idcuenta': await celdas.nth(0).text_content(),  # ID
                            'numero_radicacion': await celdas.nth(1).text_content(),  # Numero Radicacion
                            'fecha_radicacion': await celdas.nth(2).text_content(),  # Fecha Radicacion
                            'proveedor': await celdas.nth(3).text_content(),  # Proveedor
                            'numero_factura': await celdas.nth(4).text_content(),  # Numero Factura
                            'fecha_factura': await celdas.nth(5).text_content(),  # Fecha Factura
                            'valor_factura': await self._parse_currency(await celdas.nth(6).text_content()),  # Valor Factura
                            'valor_glosado': await self._parse_currency(await celdas.nth(7).text_content()),  # Valor Glosado
                            'fila_index': i  # Índice de la fila para referencia
                        }
                        
                        # Limpiar espacios en blanco
                        for key, value in row_data.items():
                            if isinstance(value, str):
                                row_data[key] = value.strip()
                        
                        rows_data.append(row_data)
                        
                        self._log_state(f"Fila {i+1}: ID={row_data['idcuenta']}, Proveedor={row_data['proveedor'][:30]}...")
                    
                except Exception as e:
                    self._log_state(f"Error extrayendo datos de fila {i}: {e}", "error")
                    continue
            
            self._log_state(f"Extracción completada - {len(rows_data)} filas válidas")
            return rows_data
            
        except Exception as e:
            self._log_state(f"Error extrayendo datos de tabla: {e}", "error")
            return []
    
    def _parse_currency(self, value: str) -> float:
        """
        Convierte texto de moneda a float.
        
        Args:
            value (str): Valor como texto (ej: "2,666,040.00")
            
        Returns:
            float: Valor numérico
        """
        try:
            # Remover símbolos de moneda y espacios
            cleaned = value.replace('$', '').replace(',', '').replace(' ', '')
            return float(cleaned)
        except:
            return 0.0
    
    async def process_table_rows(self) -> Tuple[int, int]:
        """
        Procesa todas las filas de la tabla según la lógica de estados.
        
        Returns:
            Tuple[int, int]: (filas_procesadas, filas_saltadas)
        """
        try:
            self.state.update(
                method_name="process_table_rows",
                action="Procesando filas de la tabla principal"
            )
            
            self._log_state("Iniciando procesamiento de filas")
            
            # Configurar tabla para mostrar todos
            if not await self.configure_table_show_all():
                self._log_state("Error configurando tabla", "error")
                return 0, 0
            
            # Extraer datos de todas las filas
            rows_data = await self.extract_table_rows_data()
            
            if not rows_data:
                self._log_state("No se encontraron filas para procesar", "warning")
                return 0, 0
            
            filas_procesadas = 0
            filas_saltadas = 0
            
            # Procesar cada fila
            for row_data in rows_data:
                idcuenta = row_data['idcuenta']
                
                # Verificar si debe procesarse esta cuenta
                if self.db_manager.should_process_cuenta(idcuenta):
                    # Crear/actualizar registro en BD
                    cuenta_id = self.db_manager.create_or_update_cuenta(row_data)
                    
                    # Hacer clic en el botón de la fila
                    if await self._click_row_button(row_data['fila_index']):
                        self._log_state(f"Cuenta {idcuenta} procesada - ID BD: {cuenta_id}")
                        filas_procesadas += 1
                        
                        # AQUÍ se continuará con el procesamiento de glosas específicas
                        # Por ahora retornamos para continuar con la siguiente fila
                        
                    else:
                        # Error haciendo clic, marcar como fallido
                        self.db_manager.update_cuenta_estado(
                            idcuenta, 
                            EstadoCuenta.FALLIDO, 
                            "Error haciendo clic en botón"
                        )
                        self._log_state(f"Error procesando cuenta {idcuenta}", "error")
                
                else:
                    # Saltar esta cuenta
                    self._log_state(f"Cuenta {idcuenta} saltada por estado")
                    filas_saltadas += 1
            
            self._log_state(f"Procesamiento completado - Procesadas: {filas_procesadas}, Saltadas: {filas_saltadas}")
            return filas_procesadas, filas_saltadas
            
        except Exception as e:
            self._log_state(f"Error en procesamiento de filas: {e}", "error")
            return 0, 0
    
    async def _click_row_button(self, fila_index: int) -> bool:
        """
        Hace clic en el botón "Iniciar Respuesta Glosa" de una fila específica.
        
        Args:
            fila_index (int): Índice de la fila
            
        Returns:
            bool: True si se hizo clic correctamente
        """
        try:
            self._log_state(f"Haciendo clic en botón de fila {fila_index}")
            
            # Obtener la fila específica
            fila = self.page.locator(self.selectors['filas_tabla']).nth(fila_index)
            
            # Buscar el botón dentro de la fila
            boton = fila.locator(self.selectors['boton_iniciar'])
            
            if await boton.count() == 0:
                self._log_state(f"No se encontró botón en fila {fila_index}", "error")
                return False
            
            # Hacer scroll al botón si es necesario
            await boton.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # Hacer clic
            await boton.click()
            self._log_state(f"Clic realizado en botón de fila {fila_index}")
            
            # Esperar a que cargue la nueva página
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            self._log_state(f"Error haciendo clic en fila {fila_index}: {e}", "error")
            return False