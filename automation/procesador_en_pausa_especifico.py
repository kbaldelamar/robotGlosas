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
import os 
import traceback



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

                # ✅ NUEVO: Inicializar configuraciones vacías
        self.configuraciones_respuesta = {}

        # ✅ MANTENER: Selectores específicos para EN PAUSA
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
            'boton_confirmar_terminar': ".swal2-confirm",
            'campo_tipo_glosa': "#glosaTipo",
            'campo_justificacion_glosa': "#glosaJustificacion"
        }

        # Selector para las filas de la tabla EN PAUSA (ajusta según tu HTML real)
        self.url_tabla_principal = "https://vco.ctamedicas.com/app/respuestaGlosaPause"

        self.url_tabla_en_pausa = None
        
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
        """Procesa las cuentas en pausa usando implementación independiente."""
        try:
            self.state.update(
                method_name="procesar_cuentas_en_pausa",
                action="Procesando cuentas en pausa de forma independiente"
            )
            self._log(f"🔄 Procesando {len(cuentas_en_pausa)} cuentas EN PAUSA (INDEPENDIENTE)")
            
            # Preparar sistema independiente
            if not await self._preparar_sistema():
                return 0, 0

            procesadas = 0
            fallidas = 0

            for i, cuenta_data in enumerate(cuentas_en_pausa):
                idcuenta = cuenta_data['idcuenta']
                intentos_actuales = cuenta_data.get('intentos', 0)

                self._log(f"🎯 PROCESANDO {i + 1}/{len(cuentas_en_pausa)}: {idcuenta}")

                try:
                    # Límite de intentos
                    if intentos_actuales >= 5:
                        self._log(f"🚫 Cuenta {idcuenta} excede 5 intentos, saltando")
                        fallidas += 1
                        continue
                    
                    # Incrementar intentos
                    await self._incrementar_intentos(idcuenta)

                    # Hacer clic en cuenta EN PAUSA
                    if not await self._hacer_clic_cuenta_en_pausa(idcuenta):
                        self._log(f"❌ No se pudo hacer clic en cuenta {idcuenta}")
                        fallidas += 1
                        continue
                    
                    # Procesar con implementación independiente
                    resultado = await self._procesar_cuenta_completa_independiente(idcuenta)

                    if resultado['exito']:
                        procesadas += 1
                        self._log(f"✅ CUENTA {idcuenta} COMPLETADA")
                        if self.worker:
                            self.worker.emit_cuenta_processed(idcuenta, 'COMPLETADO')
                    else:
                        fallidas += 1
                        if self.worker:
                            self.worker.emit_cuenta_processed(idcuenta, 'FALLIDO')

                except Exception as e:
                    fallidas += 1
                    await self._marcar_error_procesamiento(idcuenta, f"Error general: {e}")
                    self._log(f"❌ Error procesando {idcuenta}: {e}", "error")

                # Regresar a tabla principal después de cada cuenta
                await self._regresar_tabla_principal()
                await asyncio.sleep(3)
                await self._configurar_tabla_500_registros()
                await asyncio.sleep(2)

            return procesadas, fallidas

        except Exception as e:
            self._log(f"❌ Error en procesamiento EN PAUSA independiente: {e}", "error")
            return 0, 0

    async def procesar_cuentas_en_pausa_especificas(self, cuentas_en_pausa: List[Dict]) -> Tuple[int, int]:
        """REFACTORIZADO: Usar procesar_cuentas_en_pausa en lugar de lógica propia."""
        return await self.procesar_cuentas_en_pausa(cuentas_en_pausa)

    def _debug_metodos_heredados(self):
        """
        🔍 DEBUG: Mostrar métodos disponibles de la clase padre.
        """
        try:
            self._log("🔍 === DEBUGGING MÉTODOS HEREDADOS ===")

            # Obtener todos los métodos disponibles
            metodos_disponibles = []
            for nombre in dir(self):
                if not nombre.startswith('_') and callable(getattr(self, nombre)):
                    metodos_disponibles.append(nombre)

            # Filtrar métodos relevantes para procesamiento
            palabras_clave = ['proces', 'glosa', 'ejecutar', 'run', 'handle', 'manage', 'completa']
            metodos_procesamiento = []

            for metodo in metodos_disponibles:
                for palabra in palabras_clave:
                    if palabra.lower() in metodo.lower():
                        metodos_procesamiento.append(metodo)
                        break
                    
            self._log(f"📋 Métodos de procesamiento disponibles ({len(metodos_procesamiento)}):")
            for metodo in metodos_procesamiento:
                self._log(f"   • {metodo}")

            # Verificar métodos específicos comunes
            metodos_comunes = [
                'procesar_cuenta_completa',
                'procesar_glosas_cuenta', 
                'ejecutar_procesamiento',
                'run_automation',
                'process_account',
                'handle_account',
                '_procesar_cuenta_completa',
                'procesar_glosas',
                'ejecutar_glosas',
                'manejar_glosas'
            ]

            self._log("🎯 Verificando métodos comunes:")
            metodos_encontrados = []
            for metodo in metodos_comunes:
                if hasattr(self, metodo):
                    metodos_encontrados.append(metodo)
                    self._log(f"   ✅ {metodo} - DISPONIBLE")
                else:
                    self._log(f"   ❌ {metodo} - NO DISPONIBLE")

            self._log(f"🔥 Métodos heredados encontrados: {metodos_encontrados}")
            self._log("🔍 === FIN DEBUG MÉTODOS ===")

        except Exception as e:
            self._log(f"❌ Error en debug métodos: {e}", "error")

    
    
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
        ✅ MEJORADO: Guarda las cuentas extraídas en la base de datos como PENDIENTE.
        Cambiado de FALLIDO a PENDIENTE para que sean procesables.
        """
        self._log(f"💾 Guardando {len(cuentas_extraidas)} cuentas EN PAUSA en base de datos como PENDIENTE")
        try:
            cuentas_guardadas = 0

            for cuenta in cuentas_extraidas:
                try:
                    # ✅ VERIFICAR si ya existe para evitar duplicados
                    if self.db_manager.should_process_cuenta(cuenta['idcuenta']):

                        # ✅ USAR el método correcto del db_manager
                        cuenta_data = {
                            'idcuenta': cuenta['idcuenta'],
                            'proveedor': cuenta['proveedor'],
                            'valor_glosado': self._parsear_moneda(cuenta['valor_glosado']),
                            'fecha_radicacion': cuenta['fecha_radicacion'],
                            'numero_radicacion': '',  # Completar si tienes este dato
                            'numero_factura': '',     # Completar si tienes este dato  
                            'fecha_factura': '',      # Completar si tienes este dato
                            'valor_factura': 0.0      # Completar si tienes este dato
                        }

                        cuenta_bd_id = self.db_manager.create_or_update_cuenta(cuenta_data)
                        cuentas_guardadas += 1

                        if cuentas_guardadas <= 5:  # Log solo primeras 5
                            self._log(f"✅ Cuenta {cuenta['idcuenta']} guardada como PENDIENTE - ID: {cuenta_bd_id}")

                    else:
                        self._log(f"⏭️ Cuenta {cuenta['idcuenta']} saltada (ya procesada o en proceso)")

                except Exception as e:
                    self._log(f"❌ Error guardando cuenta {cuenta['idcuenta']}: {e}", "error")
                    continue

            self._log(f"✅ Guardado completado. Total cuentas nuevas guardadas: {cuentas_guardadas}/{len(cuentas_extraidas)}")

            # ✅ EMITIR SIGNAL si hay worker
            if self.worker and cuentas_guardadas > 0:
                self.worker.emit_data_imported(cuentas_guardadas)
                self.worker.emit_tabla_refresh()

        except Exception as e:
            self._log(f"❌ Error guardando cuentas en base de datos: {e}", "error")
    async def ejecutar(self):
        """
        ✅ FUNCIONALIDAD RECUPERADA: BD primero, luego importar tabla si es necesario.
        1. Busca cuentas pendientes en BD
        2. Si no hay nada en BD, importa desde tabla web
        3. Procesa lo que encuentra/importa
        """
        self._log("▶️ Iniciando procesamiento de cuentas EN PAUSA (BD PRIMERO)")
        try:
            # ✅ PASO 1: Buscar primero en BD
            self._log("🔍 Buscando cuentas pendientes en BD...")
            cuentas_pendientes_bd = await self._obtener_cuentas_en_pausa()

            if cuentas_pendientes_bd:
                # ✅ HAY CUENTAS EN BD: Procesar directamente
                self._log(f"📋 Encontradas {len(cuentas_pendientes_bd)} cuentas pendientes en BD")
                self._log("🚀 Procesando cuentas existentes en BD...")

                procesadas, fallidas = await self.procesar_cuentas_en_pausa(cuentas_pendientes_bd)
                self._log(f"✅ Procesamiento BD completado - Procesadas: {procesadas}, Fallidas: {fallidas}")

            else:
                # ✅ NO HAY CUENTAS EN BD: Importar desde tabla web
                self._log("⚠️ No hay cuentas pendientes en BD")
                self._log("📥 Importando cuentas desde tabla web EN PAUSA...")

                # Extraer de la tabla web
                cuentas_en_tabla = await self.extraer_datos_filas_tabla()

                if cuentas_en_tabla:
                    self._log(f"📋 Encontradas {len(cuentas_en_tabla)} cuentas en tabla web")

                    # Guardar en BD como PENDIENTE
                    await self.procesar_y_guardar_cuentas(cuentas_en_tabla)
                    self._log("💾 Cuentas guardadas en BD")

                    # Buscar las recién importadas
                    cuentas_recien_importadas = await self._obtener_cuentas_en_pausa()

                    if cuentas_recien_importadas:
                        self._log(f"🚀 Procesando {len(cuentas_recien_importadas)} cuentas recién importadas...")
                        procesadas, fallidas = await self.procesar_cuentas_en_pausa(cuentas_recien_importadas)
                        self._log(f"✅ Procesamiento importación completado - Procesadas: {procesadas}, Fallidas: {fallidas}")
                    else:
                        self._log("❌ Error: No se pudieron recuperar cuentas después de importar", "error")
                else:
                    self._log("⚠️ No hay cuentas en tabla web para importar")

            self._log("✅ Proceso de cuentas EN PAUSA completado")

        except Exception as e:
            self._log(f"❌ Error en el proceso de cuentas EN PAUSA: {e}", "error")
    async def verificar_estado_sistema(self):
        """
        🔍 DIAGNÓSTICO: Verifica el estado actual de BD y tabla web.
        Útil para debuggear y entender qué hay disponible.
        """
        try:
            self._log("🔍 === VERIFICANDO ESTADO DEL SISTEMA ===")

            # 1. Verificar BD
            cuentas_bd = await self._obtener_cuentas_en_pausa()
            self._log(f"📊 Cuentas pendientes en BD: {len(cuentas_bd)}")

            if cuentas_bd:
                estados = {}
                for cuenta in cuentas_bd[:5]:  # Solo primeras 5
                    estado = cuenta.get('estado', 'N/A')
                    intentos = cuenta.get('intentos', 0)
                    estados[cuenta['idcuenta']] = f"{estado} ({intentos} intentos)"
                self._log(f"📋 Muestra BD: {estados}")

            # 2. Verificar tabla web
            cuentas_web = await self.extraer_datos_filas_tabla()
            self._log(f"📊 Cuentas en tabla web: {len(cuentas_web)}")

            if cuentas_web:
                muestra_web = {}
                for cuenta in cuentas_web[:5]:  # Solo primeras 5
                    muestra_web[cuenta['idcuenta']] = cuenta.get('estado', 'N/A')
                self._log(f"📋 Muestra Web: {muestra_web}")

            # 3. Recomendación
            if cuentas_bd:
                self._log("💡 RECOMENDACIÓN: Procesar cuentas existentes en BD")
            elif cuentas_web:
                self._log("💡 RECOMENDACIÓN: Importar cuentas desde tabla web")
            else:
                self._log("⚠️ RECOMENDACIÓN: No hay cuentas disponibles para procesar")

            self._log("🔍 === FIN VERIFICACIÓN ===")

            return {
                'cuentas_bd': len(cuentas_bd),
                'cuentas_web': len(cuentas_web),
                'tiene_pendientes_bd': len(cuentas_bd) > 0,
                'tiene_tabla_web': len(cuentas_web) > 0
            }

        except Exception as e:
            self._log(f"❌ Error verificando estado: {e}", "error")
            return {
                'cuentas_bd': 0,
                'cuentas_web': 0,
                'tiene_pendientes_bd': False,
                'tiene_tabla_web': False
            }
    
    async def _navegar_y_hacer_clic_cuenta(self, idcuenta: str) -> bool:
        """
        ✅ SOBRESCRITO: Detecta si ya estamos en pantalla de glosas.
        Reutiliza _hacer_clic_cuenta_en_pausa() que ya tienes y funciona.
        """
        try:
            url_actual = self.page.url
            self._log(f"🔍 _navegar_y_hacer_clic_cuenta EN PAUSA - URL: {url_actual}")

            # ✅ DETECCIÓN INTELIGENTE: ¿Ya estamos en pantalla de glosas?
            if "respuestaGlosastart" in url_actual:
                self._log(f"✅ YA ESTAMOS en pantalla de glosas para cuenta {idcuenta}")
                self._log("🎯 SALTANDO navegación - continuando con procesamiento")
                return True

            # ✅ Si no, usar tu método existente que YA FUNCIONA
            self._log(f"📋 Usando método existente _hacer_clic_cuenta_en_pausa")
            return await self._hacer_clic_cuenta_en_pausa(idcuenta)

        except Exception as e:
            self._log(f"❌ Error en _navegar_y_hacer_clic_cuenta EN PAUSA: {e}", "error")
            return False
    async def _regresar_tabla_principal(self):
        """REFACTORIZADO: Usar navegación directa más simple."""
        try:
            self._log("↩️ Regresando a tabla EN PAUSA")
            await self.page.goto(self.url_tabla_principal)
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(3)
            self._log("✅ Regreso a EN PAUSA exitoso")
            return True
        except Exception as e:
            self._log(f"❌ Error regresando a tabla EN PAUSA: {e}", "error")
            return False
    
    async def _marcar_como_fallida_definitiva(self, idcuenta: str, motivo: str):
        """Solo agregar si no existe ya."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,
                f"Fallida definitiva después de 5 intentos: {motivo[:200]}"
            )
            self._log(f"🚫 Cuenta {idcuenta} marcada como fallida definitiva")
        except Exception as e:
            self._log(f"❌ Error marcando como fallida definitiva {idcuenta}: {e}", "error")

    async def _marcar_error_procesamiento(self, idcuenta: str, error: str):
        """Solo agregar si no existe ya."""
        try:
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.FALLIDO,
                f"Error en procesamiento: {error[:200]}"
            )
        except Exception as e:
            self._log(f"❌ Error marcando error de procesamiento {idcuenta}: {e}", "error")
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

    # ✅ NUEVO: Preparar sistema independiente  
    async def _preparar_sistema(self) -> bool:
        """Prepara el sistema para el procesamiento independiente."""
        try:
            self._log("🔧 Preparando sistema independiente para EN PAUSA")

            # Ya tienes _cargar_configuraciones_respuesta() - solo llamarlo
            await self._cargar_configuraciones_respuesta()

            # Usar NavigationHandler para configurar a 500 (ya lo tienes implementado)
            if hasattr(self, 'navigation_handler') and self.navigation_handler:
                # Tu NavigationHandler ya configura EN PAUSA para 500 automáticamente
                self._log("✅ Configuración de tabla delegada a NavigationHandler")
            else:
                # Fallback: configurar manualmente para 500 (como ya lo tienes)
                await self._configurar_tabla_500_registros()

            self._log("✅ Sistema independiente preparado")
            return True

        except Exception as e:
            self._log(f"❌ Error preparando sistema: {e}", "error")
            return False

    # ✅ NUEVO: Configurar tabla para 500 registros (tu estándar actual)
    async def _configurar_tabla_500_registros(self):
        """Configura la tabla EN PAUSA para mostrar 500 registros (o Todos si no hay 500)."""
        try:
            self._log("🔧 Configurando tabla EN PAUSA para 500 registros")
            resultado_js = await self.page.evaluate("""
                () => {
                    const select = document.querySelector('select[name="tablaRespuestaGlosaPause_length"]');
                    if (!select) return { success: false, error: 'Select no encontrado' };
                    const opcion500 = select.querySelector('option[value="500"]');
                    if (opcion500) {
                        select.value = '500';
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        return { success: true, valor: '500' };
                    }
                    const opcionTodos = select.querySelector('option[value="-1"]');
                    if (opcionTodos) {
                        select.value = '-1';
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        return { success: true, valor: '-1' };
                    }
                    return { success: false, error: 'No hay opción 500 ni Todos' };
                }
            """)
            if resultado_js.get('success'):
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                await asyncio.sleep(2)
                self._log(f"✅ Tabla EN PAUSA configurada para {resultado_js['valor']} registros")
            else:
                self._log(f"⚠️ No se pudo configurar la tabla: {resultado_js.get('error')}", "warning")
        except Exception as e:
            self._log(f"⚠️ Error configurando tabla: {e}", "warning")

    # ✅ NUEVO: Procesar cuenta completa independiente
    async def _procesar_cuenta_completa_independiente(self, idcuenta: str) -> Dict:
        """Procesa una cuenta completa de forma independiente."""
        try:
            self._log(f"🔄 Procesando cuenta completa independiente: {idcuenta}")

            # Marcar como EN_PROCESO
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.EN_PROCESO,
                "Iniciando procesamiento independiente EN PAUSA"
            )

            if self.worker:
                self.worker.emit_cuenta_processed(idcuenta, 'EN_PROCESO')

            # Procesar todas las glosas
            resultado_glosas = await self._procesar_todas_las_glosas_cuenta(idcuenta)

            if not resultado_glosas['exito']:
                await self._marcar_cuenta_fallida(idcuenta, f"Error procesando glosas: {resultado_glosas['error']}")
                return resultado_glosas

            # Terminar cuenta
            if not await self._terminar_cuenta():
                await self._marcar_cuenta_fallida(idcuenta, "No se pudo terminar la cuenta")
                return {'exito': False, 'error': 'No se pudo terminar la cuenta'}

            # Marcar como COMPLETADO
            self.db_manager.update_cuenta_estado(
                idcuenta, 
                EstadoCuenta.COMPLETADO,
                f"Procesada independiente EN PAUSA - {resultado_glosas['glosas_procesadas']} glosas"
            )

            return {
                'exito': True,
                'glosas_procesadas': resultado_glosas['glosas_procesadas'],
                'glosas_fallidas': resultado_glosas['glosas_fallidas']
            }

        except Exception as e:
            error_msg = f"Error procesando cuenta independiente {idcuenta}: {e}"
            self._log(error_msg, "error")
            await self._marcar_cuenta_fallida(idcuenta, error_msg)
            return {'exito': False, 'error': error_msg}

    # ✅ NUEVO: Procesar todas las glosas de una cuenta
    async def _procesar_todas_las_glosas_cuenta(self, idcuenta: str) -> Dict:
        """Procesa todas las glosas de una cuenta."""
        try:
            self._log(f"📋 Procesando todas las glosas de cuenta {idcuenta}")

            # Hacer scroll hasta tabla de glosas
            if not await self._hacer_scroll_hasta_tabla_glosas():
                return {'exito': False, 'error': 'No se pudo hacer scroll hasta tabla de glosas'}

            # Extraer glosas de la tabla
            glosas_extraidas = await self._extraer_glosas_de_tabla(idcuenta)

            if not glosas_extraidas:
                return {'exito': False, 'error': 'No se encontraron glosas para procesar'}

            self._log(f"📊 Encontradas {len(glosas_extraidas)} glosas para procesar")

            # Procesar cada glosa
            glosas_procesadas = 0
            glosas_fallidas = 0

            for i, glosa in enumerate(glosas_extraidas):
                self._log(f"   🔄 Procesando glosa {i+1}/{len(glosas_extraidas)}: {glosa['id_glosa']}")

                try:
                    # Buscar configuración
                    tipo_glosa = glosa.get('tipo', '')
                    justificacion_glosa = glosa.get('justificacion', '')
                    configuracion = self._buscar_configuracion_glosa(tipo_glosa, justificacion_glosa)

                    if not configuracion:
                        await self._guardar_glosa_sin_configuracion(idcuenta, glosa)
                        self._log(f"   ⚠️ Glosa {glosa['id_glosa']}: SIN configuración")
                        continue

                    # Procesar glosa
                    glosa['configuracion'] = configuracion
                    resultado = await self._procesar_glosa_individual(glosa)

                    if resultado['exito']:
                        glosas_procesadas += 1
                        self._log(f"   ✅ Glosa {glosa['id_glosa']} procesada exitosamente")
                    else:
                        glosas_fallidas += 1
                        self._log(f"   ❌ Glosa {glosa['id_glosa']} falló")

                except Exception as e:
                    glosas_fallidas += 1
                    self._log(f"   ❌ Error procesando glosa {glosa['id_glosa']}: {e}", "error")

                await asyncio.sleep(2)

            return {
                'exito': True,
                'glosas_procesadas': glosas_procesadas,
                'glosas_fallidas': glosas_fallidas
            }

        except Exception as e:
            error_msg = f"Error procesando glosas de cuenta {idcuenta}: {e}"
            self._log(error_msg, "error")
            return {'exito': False, 'error': error_msg}

    # ✅ NUEVO: Hacer scroll hasta tabla de glosas
    async def _hacer_scroll_hasta_tabla_glosas(self) -> bool:
        """Hace scroll hasta la tabla de glosas."""
        try:
            # Buscar tabla de glosas
            tabla_glosas = self.page.locator("#tableAuditGlosas")
            if await tabla_glosas.count() > 0:
                await tabla_glosas.scroll_into_view_if_needed()
                await asyncio.sleep(2)
                self._log("✅ Scroll hasta tabla de glosas realizado")
                return True

            # Fallback: scroll general
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
            await asyncio.sleep(3)
            return True

        except Exception as e:
            self._log(f"⚠️ Error haciendo scroll: {e}", "warning")
            return False

    # ✅ NUEVO: Extraer glosas de la tabla
    async def _extraer_glosas_de_tabla(self, idcuenta: str) -> List[Dict]:
        """Extrae información de todas las glosas de la tabla."""
        try:
            glosas = []
            filas = self.page.locator("#tableAuditGlosas tbody tr")
            total_filas = await filas.count()

            if total_filas == 0:
                self._log("❌ No se encontró tabla de glosas", "error")
                return []

            self._log(f"📊 Extrayendo {total_filas} glosas de la tabla")

            for i in range(total_filas):
                try:
                    fila = filas.nth(i)
                    celdas = fila.locator("td")
                    total_celdas = await celdas.count()

                    if total_celdas >= 8:
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

                        # Limpiar datos
                        for key, value in glosa_info.items():
                            if isinstance(value, str):
                                glosa_info[key] = value.strip()

                        # Guardar en BD usando método que ya tienes
                        cuenta_id = await self._obtener_cuenta_id(idcuenta)
                        if cuenta_id:
                            self._guardar_glosa_en_detalle(cuenta_id, glosa_info)

                        glosas.append(glosa_info)

                except Exception as e:
                    self._log(f"⚠️ Error extrayendo glosa en fila {i}: {e}", "warning")
                    continue
                
            self._log(f"📊 Extracción completada: {len(glosas)} glosas")
            return glosas

        except Exception as e:
            self._log(f"❌ Error extrayendo glosas de tabla: {e}", "error")
            return []

    # ✅ NUEVO: Buscar configuración para glosa
    def _buscar_configuracion_glosa(self, tipo: str, justificacion: str) -> Optional[Dict]:
        """Busca configuración para una glosa específica."""
        try:
            for key, config in self.configuraciones_respuesta.items():
                if config['tipo'].upper() == tipo.upper():
                    patron = config['patron'].replace('%', '').upper()
                    if patron in justificacion.upper():
                        return config
            return None
        except Exception as e:
            self._log(f"❌ Error buscando configuración: {e}", "error")
            return None

    # ✅ NUEVO: Procesar glosa individual
    async def _procesar_glosa_individual(self, glosa_info: Dict) -> Dict:
        """Procesa una glosa individual."""
        try:
            id_glosa = glosa_info.get('id_glosa', '')

            # Hacer clic en botón de la glosa
            if not await self._hacer_clic_boton_glosa(id_glosa):
                return {'exito': False, 'error': 'No se pudo hacer clic en botón de glosa'}

            # Esperar que el modal se abra
            if not await self._esperar_modal_abierto(id_glosa):
                return {'exito': False, 'error': 'Modal no se abrió correctamente'}

            # Llenar modal
            configuracion = glosa_info.get('configuracion')
            if not configuracion:
                await self._cerrar_modal()
                return {'exito': False, 'error': 'Sin configuración disponible'}

            if not await self._llenar_modal_respuesta(configuracion, glosa_info):
                await self._cerrar_modal()
                return {'exito': False, 'error': 'Error llenando modal'}

            # Guardar respuesta
            if not await self._guardar_respuesta_modal():
                await self._cerrar_modal()
                return {'exito': False, 'error': 'Error guardando respuesta'}

            await asyncio.sleep(3)
            await self._guardar_glosa_procesada(glosa_info.get('idcuenta', ''), glosa_info, configuracion)
            return {'exito': True}

        except Exception as e:
            try:
                await self._cerrar_modal()
            except:
                pass
            await self._guardar_glosa_fallida(glosa_info.get('idcuenta', ''), glosa_info, str(e))
            return {'exito': False, 'error': str(e)}

    # ✅ NUEVO: Hacer clic en botón de glosa
    async def _hacer_clic_boton_glosa(self, id_glosa: str) -> bool:
        """Hace clic en el botón de una glosa específica."""
        try:
            boton_glosa = self.page.locator(f'button.btnAnswerGlosaModal[idglosa="{id_glosa}"]')
            if await boton_glosa.count() > 0:
                await boton_glosa.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                await boton_glosa.click()
                return True
            return False
        except Exception as e:
            self._log(f"❌ Error haciendo clic en botón glosa {id_glosa}: {e}", "error")
            return False

    # ✅ NUEVO: Esperar modal abierto
    async def _esperar_modal_abierto(self, id_glosa: str) -> bool:
        """Espera a que el modal se abra correctamente."""
        try:
            titulo_modal = self.page.locator("#titleModalAnswerGlosa")
            await titulo_modal.wait_for(state="visible", timeout=10000)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            self._log(f"❌ Error esperando modal para glosa {id_glosa}: {e}", "error")
            return False

    # ✅ NUEVO: Llenar modal de respuesta
    async def _llenar_modal_respuesta(self, configuracion: Dict, glosa_info: Dict) -> bool:
        """Llena el modal de respuesta, validando existencia de PDF según configuración."""
        try:
            self._log("🟢 [PDF] Iniciando llenado de modal de respuesta")

            # Seleccionar dropdown
            self._log("🟢 [PDF] Seleccionando respuesta en dropdown...")
            if not await self._seleccionar_respuesta_dropdown():
                self._log("🔴 [PDF] Falló selección de respuesta en dropdown")
                return False

            # Llenar justificación
            self._log("🟢 [PDF] Llenando justificación...")
            if not await self._llenar_justificacion(configuracion['respuesta']):
                self._log("🔴 [PDF] Falló llenado de justificación")
                return False

            pdf_path = configuracion.get('pdf_path', '')
            tipo = glosa_info.get('tipo', '')
            num_factura = glosa_info.get('num_factura', '')
            idcuenta = glosa_info.get('idcuenta', '')

            # Si NO hay ruta PDF configurada, procesa sin subir PDF
            if not pdf_path:
                self._log("🟡 [PDF] No hay ruta PDF configurada, procesando sin subir PDF")
                self._log("✅ Modal llenado correctamente (sin PDF)")
                return True

            # Si es AUTORIZACION, ajusta la ruta
            if tipo.upper() == "AUTORIZACION" and num_factura:
                ruta_final = os.path.normpath(os.path.join(pdf_path, num_factura, "OTROS.PDF"))
                self._log(f"🟢 [PDF] Ruta PDF ajustada por AUTORIZACION: {ruta_final}")
            else:
                ruta_final = os.path.normpath(pdf_path)
                self._log(f"🟢 [PDF] Ruta PDF a usar: {ruta_final}")

            # Si hay ruta PDF y el archivo NO existe, marca como fallida y retorna False
            if not os.path.exists(ruta_final):
                self._log(f"🔴 [PDF] PDF no encontrado: {ruta_final}", "error")
                await self._guardar_glosa_fallida(idcuenta, glosa_info, f"PDF no encontrado: {ruta_final}")
                await self._marcar_cuenta_fallida(idcuenta, f"PDF no encontrado: {ruta_final}")
                self._log("🔴 [PDF] Glosa y cuenta marcadas como fallidas por falta de PDF")
                return False

            # Si existe, sube el archivo
            self._log(f"🟢 [PDF] Subiendo archivo PDF: {ruta_final}")
            if not await self._subir_archivo_pdf(ruta_final):
                self._log("🔴 [PDF] Falló la subida del archivo PDF")
                return False

            self._log("✅ Modal llenado correctamente (con PDF)")
            return True
        except Exception as e:
            self._log(f"❌ Error llenando modal: {e}", "error")
            return False

    # ✅ NUEVO: Seleccionar respuesta en dropdown
    async def _seleccionar_respuesta_dropdown(self) -> bool:
        """Selecciona la respuesta en el dropdown."""
        try:
            select2_container = self.page.locator("#select2-glosaRespTipo-container")
            await select2_container.click()
            await asyncio.sleep(2)

            opcion_999 = self.page.locator("li.select2-results__option:has-text('999 SUBSANADA')")
            await opcion_999.first.click()
            await asyncio.sleep(1)
            return True
        except Exception as e:
            self._log(f"❌ Error seleccionando dropdown: {e}", "error")
            return False

    # ✅ NUEVO: Llenar justificación
    async def _llenar_justificacion(self, respuesta_texto: str) -> bool:
        """
        ✅ MEJORADO: Llena el campo de justificación simulando escritura humana.
        Copiado desde ProcesadorCompletoGlosasImplementado con simulación de espacios.
        """
        try:
            texto_mayuscula = respuesta_texto.upper()
            textarea = self.page.locator(self.selectores['textarea_justificacion'])
            await textarea.scroll_into_view_if_needed()
            await textarea.click()
            await asyncio.sleep(0.5)

            # Limpiar campo completamente
            await textarea.press('Control+a')
            await textarea.press('Delete')
            await asyncio.sleep(0.5)

            # Pegar texto con JS
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

            # Simulación humana: espacios al final
            self._log("📝 Agregando espacios finales...")
            await textarea.press_sequentially("   ", delay=120)
            await asyncio.sleep(0.2)

            # Simular Tab para salir del campo
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
                # Fallback JS
                self._log("🔄 Aplicando fallback con JavaScript...")
                await self.page.evaluate("""
                    (texto) => {
                        const textarea = document.getElementById('glosaRespObs');
                        if (textarea) {
                            textarea.value = texto;
                            textarea.focus();
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            textarea.dispatchEvent(new Event('change', { bubbles: true }));
                            textarea.dispatchEvent(new Event('blur', { bubbles: true }));
                            textarea.classList.remove('is-invalid');
                            textarea.classList.add('is-valid');
                            const errorMsg = document.getElementById('glosaRespObsHelp');
                            if errorMsg) errorMsg.style.display = 'none';
                        }
                    }
                """, texto_mayuscula)
                self._log("✅ Justificación llenada con JavaScript")
                return True

        except Exception as e:
            self._log(f"❌ Error llenando justificación: {e}", "error")
            return False

    # ✅ NUEVO: Subir archivo PDF
    async def _subir_archivo_pdf(self, pdf_path: str) -> bool:
        """Sube el archivo PDF."""
        try:
            input_file = self.page.locator("#glosaRespFile")
            if await input_file.count() > 0:
                await input_file.set_input_files(pdf_path)
                await asyncio.sleep(2)
            return True
        except Exception as e:
            self._log(f"⚠️ Error subiendo PDF: {e}", "warning")
            return True

    # ✅ NUEVO: Guardar respuesta del modal
    async def _guardar_respuesta_modal(self) -> bool:
        """Hace clic en el botón para guardar la respuesta."""
        try:
            boton_responder = self.page.locator("#btnAnswerGlosa")
            await boton_responder.scroll_into_view_if_needed()
            await boton_responder.click()
            return True
        except Exception as e:
            self._log(f"❌ Error guardando respuesta: {e}", "error")
            return False

    # ✅ NUEVO: Terminar cuenta
    async def _terminar_cuenta(self) -> bool:
        """Termina el procesamiento de la cuenta."""
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            boton_terminar = self.page.locator("#btRespuestaFinish").filter(has_not=self.page.locator('[disabled]'))
            if await boton_terminar.count() > 0:
                await boton_terminar.click()
                await asyncio.sleep(3)

                # Confirmar
                boton_confirmar = self.page.locator(".swal2-confirm")
                await boton_confirmar.wait_for(state="visible", timeout=10000)
                await boton_confirmar.click()
                await asyncio.sleep(2)

                await self.page.wait_for_load_state('networkidle', timeout=15000)
                return True
            return False
        except Exception as e:
            self._log(f"❌ Error terminando cuenta: {e}", "error")
            return False

    # ✅ NUEVO: Cerrar modal
    async def _cerrar_modal(self) -> bool:
        """Cierra el modal."""
        try:
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            return True
        except:
            return False

    # =========================== MÉTODOS DE BASE DE DATOS (NUEVOS) ===========================

    # ✅ NUEVO: Obtener ID de cuenta
    async def _obtener_cuenta_id(self, idcuenta: str) -> Optional[int]:
        """Obtiene el ID interno de la cuenta desde la BD."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("SELECT id FROM cuenta_glosas_principal WHERE idcuenta = ?", (idcuenta,))
                row = cursor.fetchone()
                return row['id'] if row else None
        except Exception as e:
            self._log(f"❌ Error obteniendo ID de cuenta: {e}", "error")
            return None

    # ✅ NUEVO: Guardar glosa en detalle
    def _guardar_glosa_en_detalle(self, cuenta_id: int, glosa_info: Dict):
        """Guarda una glosa en la tabla de detalle."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id FROM glosa_items_detalle 
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (cuenta_id, glosa_info.get('id_glosa', '')))

                if cursor.fetchone():
                    # Actualizar
                    conn.execute("""
                        UPDATE glosa_items_detalle 
                        SET tipo = ?, justificacion = ?, valor_glosado = ?, 
                            estado_original = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE cuenta_principal_id = ? AND id_glosa = ?
                    """, (
                        glosa_info.get('tipo', ''),
                        glosa_info.get('justificacion', ''),
                        self._parsear_moneda(glosa_info.get('valor_glosado', '0')),
                        glosa_info.get('estado', 'SIN RESPUESTA'),
                        cuenta_id,
                        glosa_info['id_glosa']
                    ))
                else:
                    # Insertar nueva
                    conn.execute("""
                        INSERT INTO glosa_items_detalle 
                        (cuenta_principal_id, id_glosa, tipo, justificacion, valor_glosado, 
                         estado_original, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        cuenta_id,
                        glosa_info.get('id_glosa', ''),
                        glosa_info.get('tipo', ''),
                        glosa_info.get('justificacion', ''),
                        self._parsear_moneda(glosa_info.get('valor_glosado', '0')),
                        glosa_info.get('estado', 'SIN RESPUESTA')
                    ))

                conn.commit()

        except Exception as e:
            self._log(f"❌ Error guardando glosa en detalle: {e}", "error")

    # ✅ NUEVO: Parsear moneda
    def _parsear_moneda(self, valor: str) -> float:
        """Convierte texto de moneda a float."""
        try:
            if not valor:
                return 0.0
            limpio = valor.replace('$', '').replace(',', '').replace(' ', '').strip()
            return float(limpio) if limpio else 0.0
        except Exception as e:
            self._log(f"⚠️ Error parseando moneda '{valor}': {e}", "warning")
            return 0.0

    # ✅ NUEVO: Guardar glosa procesada
    async def _guardar_glosa_procesada(self, idcuenta: str, glosa_info: Dict, configuracion: Dict):
        """Guarda una glosa como procesada."""
        try:
            cuenta_id = await self._obtener_cuenta_id(idcuenta)
            if not cuenta_id:
                return
    
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 1 FROM glosas_detalles_procesadas WHERE idcuenta = ? AND id_glosa = ?
                """, (idcuenta, glosa_info['id_glosa']))
                if cursor.fetchone():
                    # Ya existe, actualiza el estado
                    conn.execute("""
                        UPDATE glosas_detalles_procesadas
                        SET estado_procesamiento = 'EXITOSO'
                        WHERE idcuenta = ? AND id_glosa = ?
                    """, (idcuenta, glosa_info['id_glosa']))
                else:
                    # No existe, inserta nuevo
                    conn.execute("""
                        INSERT INTO glosas_detalles_procesadas 
                        (idcuenta, id_glosa, estado_procesamiento)
                        VALUES (?, ?, 'EXITOSO')
                    """, (idcuenta, glosa_info['id_glosa']))
    
                # Actualizar detalle
                conn.execute("""
                    UPDATE glosa_items_detalle
                    SET fue_procesado = TRUE, fecha_procesamiento = CURRENT_TIMESTAMP
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (cuenta_id, glosa_info.get('id_glosa', '')))
    
                conn.commit()
    
        except Exception as e:
            self._log(f"⚠️ Error guardando glosa procesada: {e}", "warning")
    # ✅ NUEVO: Guardar glosa fallida
    async def _guardar_glosa_fallida(self, idcuenta: str, glosa_info: Dict, error: str):
        """Guarda una glosa como fallida."""
        try:
            cuenta_id = await self._obtener_cuenta_id(idcuenta)
            if not cuenta_id:
                return
    
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    INSERT INTO glosas_detalles_procesadas 
                    (idcuenta, id_glosa, estado_procesamiento, error_mensaje)
                    VALUES (?, ?, 'ERROR', ?)
                """, (idcuenta, glosa_info['id_glosa'], error))
    
                conn.execute("""
                    UPDATE glosa_items_detalle 
                    SET error_procesamiento = ?, fecha_procesamiento = CURRENT_TIMESTAMP
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (error, cuenta_id, glosa_info['id_glosa']))
    
                conn.commit()
    
        except Exception as e:
            self._log(f"⚠️ Error guardando glosa fallida: {e}", "warning")

    # ✅ NUEVO: Guardar glosa sin configuración
    async def _guardar_glosa_sin_configuracion(self, idcuenta: str, glosa_info: Dict):
        """Guarda una glosa como sin configuración."""
        try:
            cuenta_id = await self._obtener_cuenta_id(idcuenta)
            if not cuenta_id:
                return

            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE glosa_items_detalle 
                    SET error_procesamiento = 'SIN_CONFIGURACION',
                        fecha_procesamiento = CURRENT_TIMESTAMP
                    WHERE cuenta_principal_id = ? AND id_glosa = ?
                """, (cuenta_id, glosa_info['id_glosa']))

                conn.commit()

        except Exception as e:
            self._log(f"❌ Error guardando glosa sin configuración: {e}", "error")

    # ✅ NUEVO: Obtener cuentas EN PAUSA desde BD
    async def _obtener_cuentas_en_pausa(self) -> List[Dict]:
        """Obtiene cuentas EN PAUSA desde la base de datos."""
        try:
            self._log("🟢🟢🟢 ENTRANDO a _obtener_cuentas_en_pausa", "info")
            self._log(f"🟢 Stack trace:\n{''.join(traceback.format_stack(limit=5))}", "info")
            self._log("📋 Obteniendo cuentas EN PAUSA desde BD")

            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT idcuenta, proveedor, estado, valor_glosado, fecha_radicacion, 
                           COALESCE(intentos, 0) as intentos
                    FROM cuenta_glosas_principal 
                    WHERE estado IN ('PENDIENTE', 'FALLIDO') 
                    AND COALESCE(intentos, 0) < 5
                    ORDER BY created_at ASC
                """)

                cuentas = []
                for row in cursor.fetchall():
                    cuentas.append({
                        'idcuenta': row['idcuenta'],
                        'proveedor': row['proveedor'],
                        'estado': row['estado'],
                        'valor_glosado': row['valor_glosado'],
                        'fecha_radicacion': row['fecha_radicacion'],
                        'intentos': row['intentos']
                    })

                if cuentas:
                    self._log(f"✅ Encontradas {len(cuentas)} cuentas EN PAUSA")
                    # Imprime la información de las cuentas encontradas (solo primeras 5 para no saturar el log)
                    self._log(f"🔎 Primeras cuentas encontradas: {cuentas[:5]}")
                else:
                    self._log("⚠️ No se encontraron cuentas EN PAUSA en la BD")
                return cuentas

        except Exception as e:
            self._log(f"❌ Error obteniendo cuentas EN PAUSA desde BD: {e}", "error")
            return []