#!/usr/bin/env python3
# test_configuraciones_analysis.py
"""
Script para probar el análisis de configuraciones y glosas reales.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager_glosas import DatabaseManagerGlosas

def test_configuraciones_existentes():
    """Prueba las configuraciones existentes."""
    print("🔧 Probando configuraciones existentes...")
    
    db = DatabaseManagerGlosas()
    
    # Verificar configuraciones activas
    count = db.get_configuraciones_respuesta_count()
    print(f"📊 Configuraciones activas: {count}")
    
    # Obtener detalles
    detalle = db.get_configuraciones_respuesta_detalle()
    print(f"📊 Total configuraciones: {len(detalle)}")
    
    if detalle:
        print("📝 CONFIGURACIONES ENCONTRADAS:")
        for config in detalle:
            estado = "✅ ACTIVA" if config['activo'] else "❌ INACTIVA"
            print(f"   • {config['tipo']} - {config['justificacion_patron']} [{estado}]")
            print(f"     Respuesta: {config['respuesta_automatica'][:50]}...")
            if config['url_pdf']:
                print(f"     PDF: {config['url_pdf']}")
    else:
        print("📋 No hay configuraciones en la tabla")
    
    print()

def test_glosas_sin_procesar():
    """Prueba la consulta de glosas sin procesar."""
    print("🔍 Analizando glosas sin procesar...")
    
    db = DatabaseManagerGlosas()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT tipo, justificacion, descripcion, COUNT(*) as cantidad
                FROM glosa_items_detalle 
                WHERE fue_procesado = 0 OR fue_procesado IS NULL
                GROUP BY tipo, justificacion, descripcion
                ORDER BY cantidad DESC, tipo, justificacion
                LIMIT 10
            """)
            
            glosas_reales = cursor.fetchall()
        
        if glosas_reales:
            print(f"📊 Encontradas {len(glosas_reales)} tipos de glosas sin procesar:")
            print()
            
            for i, glosa in enumerate(glosas_reales):
                print(f"🏷️ GLOSA {i+1}:")
                print(f"   • Tipo: '{glosa['tipo']}'")
                print(f"   • Justificación: '{glosa['justificacion']}'")
                print(f"   • Descripción: '{glosa['descripcion']}'")
                print(f"   • Cantidad: {glosa['cantidad']} glosas")
                print(f"   📝 Configuración sugerida:")
                print(f"      - Tipo: {glosa['tipo']}")
                print(f"      - Patrón: {glosa['justificacion']}")
                print(f"      - Respuesta: [Definir respuesta personalizada]")
                print()
        else:
            print("📋 No se encontraron glosas sin procesar en la BD")
            
    except Exception as e:
        print(f"❌ Error consultando glosas: {e}")

def test_matching_logic():
    """Prueba la lógica de matching mejorada."""
    print("🧪 Probando lógica de matching...")
    
    # Simular configuraciones
    configuraciones = {
        'TARIFAS_dfsdfsdfsdfsdf': {
            'tipo': 'TARIFAS',
            'patron': 'dfsdfsdfsdfsdf',
            'respuesta': 'Respuesta de prueba',
            'pdf_path': None
        }
    }
    
    # Simular justificaciones de glosas reales
    glosas_test = [
        ('TARIFAS', 'dfsdfsdfsdfsdf'),
        ('TARIFAS', 'VALOR NO CUBIERTO'),
        ('TARIFAS', 'CODIGO INEXISTENTE'),
        ('GENERALES', 'DOCUMENTACION FALTANTE'),
    ]
    
    print("🔍 PRUEBAS DE MATCHING:")
    for tipo, justificacion in glosas_test:
        print(f"\n📄 Glosa: {tipo} - {justificacion}")
        
        # Buscar configuración compatible
        encontrada = False
        for key, config in configuraciones.items():
            if config['tipo'].upper() == tipo.upper():
                patron_limpio = config['patron'].replace('%', '').strip().upper()
                justificacion_limpia = justificacion.strip().upper()
                
                if patron_limpio in justificacion_limpia or justificacion_limpia in patron_limpio:
                    print(f"   ✅ COINCIDENCIA: {config['patron']}")
                    encontrada = True
                    break
        
        if not encontrada:
            print(f"   ❌ NO HAY CONFIGURACIÓN COMPATIBLE")
            print(f"   💡 Sugerencia: Crear configuración para '{tipo} - {justificacion}'")

def main():
    """Función principal de prueba."""
    print("🧪 ANÁLISIS DE CONFIGURACIONES Y GLOSAS")
    print("=" * 60)
    
    test_configuraciones_existentes()
    test_glosas_sin_procesar()
    test_matching_logic()
    
    print("🎉 ANÁLISIS COMPLETADO")

if __name__ == "__main__":
    main()
