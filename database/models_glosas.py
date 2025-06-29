from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum

class EstadoCuenta(Enum):
    """Estados posibles de una cuenta de glosas."""
    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"
    FALLA_TOTAL = "FALLA_TOTAL"  # ✅ NUEVO: Para 5+ intentos


class TipoProcesabilidad(Enum):
    """
    Tipos de procesabilidad para módulo EN PAUSA.
    ✅ NUEVO: Para categorizar cuentas según su elegibilidad de reprocesamiento.
    """
    PROCESABLE = "PROCESABLE"          # FALLIDO/EN_PROCESO con < 5 intentos
    NO_PROCESABLE = "NO_PROCESABLE"    # FALLA_TOTAL o >= 5 intentos
    COMPLETADO = "COMPLETADO"          # Ya procesado exitosamente
    OTRO = "OTRO"  

@dataclass
class CuentaGlosasPrincipal:
    """
    Modelo de datos para la tabla principal de cuentas de glosas.
    Representa una fila de la tabla 'Bolsa Respuesta'.
    """
    id: Optional[int] = None
    idcuenta: str = ""                    # ID único de la cuenta (ej: 174713)
    numero_radicacion: str = ""           # RAD-38465_20250311_233131
    fecha_radicacion: str = ""            # 2025-03-11
    proveedor: str = ""                   # HOGAR DE REPOSO BETANIA S.A.S.
    numero_factura: str = ""              # FEM40102
    fecha_factura: str = ""               # 2025-02-28 00:00:00
    valor_factura: float = 0.0            # 3,058,552.00
    valor_glosado: float = 0.0            # 3,058,552.00
    
    # Campos de control
    estado: EstadoCuenta = EstadoCuenta.PENDIENTE
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    glosas_encontradas: int = 0           # Total de glosas en la cuenta
    glosas_tarifas: int = 0              # Glosas de tipo TARIFAS encontradas
    glosas_procesadas: int = 0           # Glosas efectivamente procesadas
    motivo_fallo: str = ""               # Si falló, descripción
    intentos: int = 0                    # Número de intentos de procesamiento
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para BD."""
        return {
            'id': self.id,
            'idcuenta': self.idcuenta,
            'numero_radicacion': self.numero_radicacion,
            'fecha_radicacion': self.fecha_radicacion,
            'proveedor': self.proveedor,
            'numero_factura': self.numero_factura,
            'fecha_factura': self.fecha_factura,
            'valor_factura': self.valor_factura,
            'valor_glosado': self.valor_glosado,
            'estado': self.estado.value,
            'fecha_inicio': self.fecha_inicio,
            'fecha_fin': self.fecha_fin,
            'glosas_encontradas': self.glosas_encontradas,
            'glosas_tarifas': self.glosas_tarifas,
            'glosas_procesadas': self.glosas_procesadas,
            'motivo_fallo': self.motivo_fallo,
            'intentos': self.intentos
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CuentaGlosasPrincipal':
        """Crea una instancia desde diccionario de BD."""
        return cls(
            id=data.get('id'),
            idcuenta=data.get('idcuenta', ''),
            numero_radicacion=data.get('numero_radicacion', ''),
            fecha_radicacion=data.get('fecha_radicacion', ''),
            proveedor=data.get('proveedor', ''),
            numero_factura=data.get('numero_factura', ''),
            fecha_factura=data.get('fecha_factura', ''),
            valor_factura=data.get('valor_factura', 0.0),
            valor_glosado=data.get('valor_glosado', 0.0),
            estado=EstadoCuenta(data.get('estado', 'PENDIENTE')),
            fecha_inicio=data.get('fecha_inicio'),
            fecha_fin=data.get('fecha_fin'),
            glosas_encontradas=data.get('glosas_encontradas', 0),
            glosas_tarifas=data.get('glosas_tarifas', 0),
            glosas_procesadas=data.get('glosas_procesadas', 0),
            motivo_fallo=data.get('motivo_fallo', ''),
            intentos=data.get('intentos', 0)
        )
    
    def es_procesable_en_pausa(self) -> bool:
        """
        Determina si esta cuenta es procesable en el módulo EN PAUSA.
        
        Returns:
            bool: True si puede ser reprocesada
        """
        return (
            self.estado in [EstadoCuenta.FALLIDO, EstadoCuenta.EN_PROCESO] and 
            self.intentos < 5
        )
    
    def get_procesabilidad(self) -> TipoProcesabilidad:
        """
        Obtiene el tipo de procesabilidad para módulo EN PAUSA.
        
        Returns:
            TipoProcesabilidad: Tipo de procesabilidad
        """
        if self.estado == EstadoCuenta.COMPLETADO:
            return TipoProcesabilidad.COMPLETADO
        elif self.estado == EstadoCuenta.FALLA_TOTAL or self.intentos >= 5:
            return TipoProcesabilidad.NO_PROCESABLE
        elif self.estado in [EstadoCuenta.FALLIDO, EstadoCuenta.EN_PROCESO]:
            return TipoProcesabilidad.PROCESABLE
        else:
            return TipoProcesabilidad.OTRO
    
    def incrementar_intentos(self) -> None:
        """
        Incrementa el número de intentos y actualiza estado si es necesario.
        """
        self.intentos += 1
        
        if self.intentos >= 5:
            self.estado = EstadoCuenta.FALLA_TOTAL
            self.motivo_fallo = f"Superó 5 intentos de procesamiento (intento {self.intentos})"
        else:
            self.estado = EstadoCuenta.EN_PROCESO
    
    def marcar_como_recuperada(self, glosas_procesadas: int = 0) -> None:
        """
        Marca la cuenta como recuperada exitosamente.
        
        Args:
            glosas_procesadas (int): Número de glosas procesadas
        """
        self.estado = EstadoCuenta.COMPLETADO
        self.fecha_fin = datetime.now()
        self.glosas_procesadas = glosas_procesadas
        self.motivo_fallo = f"Recuperada en intento {self.intentos} - {glosas_procesadas} glosas procesadas"
    
    def get_info_resumen(self) -> str:
        """
        Obtiene información resumida de la cuenta para logs.
        
        Returns:
            str: Resumen de la cuenta
        """
        procesabilidad = self.get_procesabilidad()
        return (
            f"Cuenta {self.idcuenta}: {self.estado.value} "
            f"(intentos: {self.intentos}, procesabilidad: {procesabilidad.value})"
        )

@dataclass
class GlosaItemDetalle:
    """
    Modelo de datos para glosas individuales dentro de una cuenta.
    Representa una fila de la tabla de glosas específicas.
    """
    id: Optional[int] = None
    cuenta_principal_id: int = 0          # FK a cuenta_glosas_principal
    
    # Datos de la glosa individual
    id_glosa: str = ""                    # 2671480, 545704, etc.
    id_item: str = ""                     # 1530357, 1530358, etc.
    descripcion_item: str = ""            # 890105 ATENCION (VISITA) DOMICILIARIA...
    tipo: str = ""                        # TARIFAS, AUTORIZACION
    descripcion: str = ""                 # 223 PROCEDIMIENTO O ACTIVIDAD
    justificacion: str = ""               # MAYOR VALOR COBRADO EN SERVICIO...
    valor_glosado: float = 0.0            # $ 573.480,00
    estado_original: str = ""             # SIN RESPUESTA
    
    # Campos de procesamiento
    es_procesable: bool = False           # Si cumple criterios (TARIFAS + MAYOR VALOR)
    fue_procesado: bool = False           # Si se procesó exitosamente
    fecha_procesamiento: Optional[datetime] = None
    respuesta_enviada: str = ""           # Respuesta que se envió
    archivo_subido: str = ""              # Path del PDF subido
    error_procesamiento: str = ""         # Si hubo error, descripción
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para BD."""
        return {
            'id': self.id,
            'cuenta_principal_id': self.cuenta_principal_id,
            'id_glosa': self.id_glosa,
            'id_item': self.id_item,
            'descripcion_item': self.descripcion_item,
            'tipo': self.tipo,
            'descripcion': self.descripcion,
            'justificacion': self.justificacion,
            'valor_glosado': self.valor_glosado,
            'estado_original': self.estado_original,
            'es_procesable': self.es_procesable,
            'fue_procesado': self.fue_procesado,
            'fecha_procesamiento': self.fecha_procesamiento,
            'respuesta_enviada': self.respuesta_enviada,
            'archivo_subido': self.archivo_subido,
            'error_procesamiento': self.error_procesamiento
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GlosaItemDetalle':
        """Crea una instancia desde diccionario de BD."""
        return cls(
            id=data.get('id'),
            cuenta_principal_id=data.get('cuenta_principal_id', 0),
            id_glosa=data.get('id_glosa', ''),
            id_item=data.get('id_item', ''),
            descripcion_item=data.get('descripcion_item', ''),
            tipo=data.get('tipo', ''),
            descripcion=data.get('descripcion', ''),
            justificacion=data.get('justificacion', ''),
            valor_glosado=data.get('valor_glosado', 0.0),
            estado_original=data.get('estado_original', ''),
            es_procesable=data.get('es_procesable', False),
            fue_procesado=data.get('fue_procesado', False),
            fecha_procesamiento=data.get('fecha_procesamiento'),
            respuesta_enviada=data.get('respuesta_enviada', ''),
            archivo_subido=data.get('archivo_subido', ''),
            error_procesamiento=data.get('error_procesamiento', '')
        )
@dataclass
class EstadisticasEnPausa:
    """
    Modelo para estadísticas específicas del módulo EN PAUSA.
    """
    total_fallidas: int = 0
    total_en_proceso: int = 0
    total_falla_total: int = 0
    total_procesables: int = 0
    total_no_procesables: int = 0
    total_recuperadas_hoy: int = 0
    
    def get_tasa_recuperacion(self) -> float:
        """Calcula la tasa de recuperación."""
        total_intentadas = self.total_fallidas + self.total_en_proceso
        if total_intentadas == 0:
            return 0.0
        return (self.total_recuperadas_hoy / total_intentadas) * 100
    
    def get_resumen(self) -> str:
        """Obtiene resumen de estadísticas."""
        return (
            f"EN PAUSA: {self.total_procesables} procesables, "
            f"{self.total_falla_total} falla total, "
            f"tasa recuperación: {self.get_tasa_recuperacion():.1f}%"
        )

@dataclass 
class ResultadoReprocesamiento:
    """
    Modelo para resultados de reprocesamiento EN PAUSA.
    """
    cuentas_procesadas: int = 0
    cuentas_recuperadas: int = 0
    cuentas_falla_total: int = 0
    tiempo_total: float = 0.0
    errores: List[str] = None
    
    def __post_init__(self):
        if self.errores is None:
            self.errores = []
    
    def get_tasa_exito(self) -> float:
        """Calcula la tasa de éxito del reprocesamiento."""
        if self.cuentas_procesadas == 0:
            return 0.0
        return (self.cuentas_recuperadas / self.cuentas_procesadas) * 100
    
    def agregar_error(self, error: str) -> None:
        """Agrega un error al resultado."""
        self.errores.append(error)
    
    def get_resumen_final(self) -> str:
        """Obtiene resumen final del reprocesamiento."""
        return (
            f"Reprocesamiento: {self.cuentas_recuperadas}/{self.cuentas_procesadas} "
            f"({self.get_tasa_exito():.1f}% éxito) en {self.tiempo_total:.1f}s"
        )