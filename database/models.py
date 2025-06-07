from dataclasses import dataclass
from typing import Optional

@dataclass
class Cliente:
    """
    Modelo de datos para la tabla Cliente.
    Representa la estructura de un cliente en la base de datos.
    """
    id: Optional[int] = None
    nombre: str = ""
    nit: str = ""
    correo: str = ""
    telefono: str = ""
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para facilitar serialización."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'nit': self.nit,
            'correo': self.correo,
            'telefono': self.telefono
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Cliente':
        """Crea una instancia de Cliente desde un diccionario."""
        return cls(
            id=data.get('id'),
            nombre=data.get('nombre', ''),
            nit=data.get('nit', ''),
            correo=data.get('correo', ''),
            telefono=data.get('telefono', '')
        )