#!/usr/bin/env python3
# test_configuraciones.py
"""
Script de prueba para verificar el funcionamiento del sistema de configuraciones.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from database.db_manager_glosas import DatabaseManagerGlosas
from ui.components.configuraciones_respuesta_dialog import ConfiguracionesRespuestaDialog

def test_database():
    """Prueba la funcionalidad de la base de datos."""
    print("🔧 Probando funcionalidad de base de datos...")
    
    db = DatabaseManagerGlosas()
    
    # Crear tablas
    db.create_glosas_tables()
    print("✅ Tablas creadas correctamente")
    
    # Verificar configuraciones
    count = db.get_configuraciones_respuesta_count()
    print(f"📊 Configuraciones activas: {count}")
    
    detalle = db.get_configuraciones_respuesta_detalle()
    print(f"📊 Total configuraciones: {len(detalle)}")
    
    if detalle:
        print("📝 CONFIGURACIONES ENCONTRADAS:")
        for config in detalle:
            estado = "✅ ACTIVA" if config['activo'] else "❌ INACTIVA"
            print(f"   • {config['tipo']} - {config['justificacion_patron']} [{estado}]")
    else:
        print("📋 No hay configuraciones en la tabla (esto es esperado)")
    
    print("✅ Prueba de base de datos completada\n")

def test_ui():
    """Prueba la interfaz de usuario."""
    print("🖥️ Probando interfaz de usuario...")
    
    app = QApplication(sys.argv)
    
    dialog = ConfiguracionesRespuestaDialog()
    dialog.show()
    
    print("✅ Dialog abierto correctamente")
    print("💡 Puede probar crear configuraciones manualmente")
    print("💡 Cierre el dialog cuando termine")
    
    app.exec()
    
    print("✅ Prueba de interfaz completada")

def main():
    """Función principal de prueba."""
    print("🧪 INICIANDO PRUEBAS DEL SISTEMA DE CONFIGURACIONES")
    print("=" * 60)
    
    # Prueba 1: Base de datos
    test_database()
    
    # Prueba 2: Interfaz de usuario
    respuesta = input("¿Desea probar la interfaz de usuario? (s/n): ")
    if respuesta.lower() in ['s', 'si', 'y', 'yes']:
        test_ui()
    
    print("🎉 PRUEBAS COMPLETADAS")

if __name__ == "__main__":
    main()
