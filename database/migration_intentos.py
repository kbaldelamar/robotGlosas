# database/migration_intentos.py
"""
Script de migración para añadir soporte al campo 'intentos' 
en el módulo Glosas en Pausa.
"""

import sqlite3
import os
import logging
from config.settings import Settings

def migrar_campo_intentos():
    """
    Migra la base de datos para soportar el campo 'intentos' 
    necesario para el módulo Glosas en Pausa.
    """
    
    print("🔧 === MIGRACIÓN CAMPO INTENTOS PARA GLOSAS EN PAUSA ===")
    print("✅ OBJETIVO: Añadir soporte completo para control de intentos")
    print("="*60)
    
    try:
        # Conectar a la base de datos
        db_path = Settings.DATABASE_PATH
        print(f"📂 Conectando a: {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print("✅ Conexión exitosa")
        print("-"*40)
        
        # ===================================
        # PASO 1: Verificar tabla principal
        # ===================================
        print("🔍 PASO 1: Verificando tabla principal")
        
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cuenta_glosas_principal'
        """)
        
        tabla_existe = cursor.fetchone()
        
        if not tabla_existe:
            print("❌ ERROR: Tabla 'cuenta_glosas_principal' no existe")
            print("   Ejecute primero el procesador principal para crear las tablas")
            return False
        
        print("✅ Tabla 'cuenta_glosas_principal' existe")
        
        # ===================================
        # PASO 2: Verificar campo intentos
        # ===================================
        print("\n🔧 PASO 2: Verificando campo 'intentos'")
        
        cursor = conn.execute("PRAGMA table_info(cuenta_glosas_principal)")
        columnas_actuales = {row['name']: row for row in cursor.fetchall()}
        
        print(f"📋 Columnas actuales: {len(columnas_actuales)}")
        
        if 'intentos' not in columnas_actuales:
            print("➕ Añadiendo campo 'intentos'...")
            
            conn.execute("""
                ALTER TABLE cuenta_glosas_principal 
                ADD COLUMN intentos INTEGER DEFAULT 0
            """)
            
            print("✅ Campo 'intentos' añadido exitosamente")
        else:
            print("✅ Campo 'intentos' ya existe")
        
        # ===================================
        # PASO 3: Inicializar valores
        # ===================================
        print("\n🔢 PASO 3: Inicializando valores de intentos")
        
        cursor = conn.execute("""
            UPDATE cuenta_glosas_principal 
            SET intentos = 0 
            WHERE intentos IS NULL
        """)
        
        if cursor.rowcount > 0:
            print(f"✅ Inicializados intentos para {cursor.rowcount} registros")
        else:
            print("✅ Todos los registros ya tienen intentos inicializados")
        
        # ===================================
        # PASO 4: Crear índices optimizados
        # ===================================
        print("\n🔍 PASO 4: Creando índices optimizados")
        
        indices_intentos = [
            ("CREATE INDEX IF NOT EXISTS idx_estado_intentos ON cuenta_glosas_principal(estado, intentos)", 
             "Índice para filtrar por estado e intentos"),
            ("CREATE INDEX IF NOT EXISTS idx_intentos ON cuenta_glosas_principal(intentos)", 
             "Índice para ordenar por intentos"),
            ("CREATE INDEX IF NOT EXISTS idx_fallidas_en_proceso ON cuenta_glosas_principal(estado) WHERE estado IN ('FALLIDO', 'EN_PROCESO')", 
             "Índice específico para EN PAUSA")
        ]
        
        for sql, descripcion in indices_intentos:
            try:
                conn.execute(sql)
                print(f"   ✅ {descripcion}")
            except Exception as e:
                print(f"   ⚠️ {descripcion}: {e}")
        
        # ===================================
        # PASO 5: Crear vista específica
        # ===================================
        print("\n👁️ PASO 5: Creando vista para Glosas en Pausa")
        
        conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_glosas_en_pausa AS
            SELECT 
                idcuenta,
                proveedor,
                estado,
                intentos,
                glosas_encontradas,
                glosas_procesadas,
                fecha_inicio,
                motivo_fallo,
                valor_glosado,
                CASE 
                    WHEN intentos >= 5 THEN 'NO_PROCESABLE'
                    WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos < 5 THEN 'PROCESABLE'
                    ELSE 'OTRO'
                END as procesabilidad,
                CASE 
                    WHEN intentos = 0 THEN 'PRIMER_INTENTO'
                    WHEN intentos BETWEEN 1 AND 2 THEN 'INTENTOS_TEMPRANOS'
                    WHEN intentos BETWEEN 3 AND 4 THEN 'INTENTOS_TARDIOS'
                    WHEN intentos >= 5 THEN 'LIMITE_ALCANZADO'
                    ELSE 'DESCONOCIDO'
                END as categoria_intentos
            FROM cuenta_glosas_principal 
            WHERE estado IN ('FALLIDO', 'EN_PROCESO')
            ORDER BY intentos ASC, fecha_inicio DESC
        """)
        
        print("✅ Vista 'vw_glosas_en_pausa' creada")
        
        # ===================================
        # PASO 6: Verificar datos existentes
        # ===================================
        print("\n📊 PASO 6: Verificando datos existentes")
        
        cursor = conn.execute("""
            SELECT 
                estado,
                COUNT(*) as total,
                AVG(COALESCE(intentos, 0)) as promedio_intentos,
                MAX(COALESCE(intentos, 0)) as max_intentos
            FROM cuenta_glosas_principal 
            GROUP BY estado
        """)
        
        print("Estado actual de la base de datos:")
        for row in cursor.fetchall():
            estado = row['estado']
            total = row['total']
            promedio = row['promedio_intentos']
            maximo = row['max_intentos']
            print(f"   • {estado}: {total} registros (promedio intentos: {promedio:.1f}, máx: {maximo})")
        
        # Verificar vista específica
        cursor = conn.execute("""
            SELECT 
                procesabilidad,
                COUNT(*) as count
            FROM vw_glosas_en_pausa 
            GROUP BY procesabilidad
        """)
        
        print("\nEstado de procesabilidad EN PAUSA:")
        for row in cursor.fetchall():
            print(f"   • {row['procesabilidad']}: {row['count']} cuentas")
        
        # ===================================
        # FINALIZAR MIGRACIÓN
        # ===================================
        conn.commit()
        conn.close()
        
        print("\n🎉 === MIGRACIÓN COMPLETADA EXITOSAMENTE ===")
        print("="*60)
        print("✅ Campo 'intentos' verificado/añadido")
        print("✅ Valores inicializados correctamente")
        print("✅ Índices optimizados creados")
        print("✅ Vista EN PAUSA creada")
        print("✅ Base de datos lista para módulo Glosas en Pausa")
        print("\n💡 Ahora puede usar el módulo Glosas en Pausa sin problemas")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR EN MIGRACIÓN: {e}")
        return False

def verificar_configuracion_glosas_en_pausa():
    """Verifica que la configuración esté correcta para Glosas en Pausa."""
    
    print("\n🔍 === VERIFICACIÓN GLOSAS EN PAUSA ===")
    print("-"*50)
    
    try:
        conn = sqlite3.connect(Settings.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        
        # Verificar estructura
        cursor = conn.execute("PRAGMA table_info(cuenta_glosas_principal)")
        columnas = [row['name'] for row in cursor.fetchall()]
        
        requisitos = ['intentos', 'estado', 'motivo_fallo']
        faltantes = [req for req in requisitos if req not in columnas]
        
        if faltantes:
            print(f"❌ FALTAN COLUMNAS: {faltantes}")
            return False
        
        print("✅ Estructura de tabla correcta")
        
        # Verificar datos específicos para EN PAUSA
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos < 5 THEN 1 ELSE 0 END) as procesables,
                SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos >= 5 THEN 1 ELSE 0 END) as no_procesables,
                SUM(CASE WHEN estado = 'COMPLETADO' THEN 1 ELSE 0 END) as completadas
            FROM cuenta_glosas_principal
        """)
        
        stats = cursor.fetchone()
        
        print(f"📊 ESTADÍSTICAS PARA GLOSAS EN PAUSA:")
        print(f"   • Total registros: {stats['total']}")
        print(f"   • Procesables EN PAUSA: {stats['procesables']}")
        print(f"   • No procesables (5+ intentos): {stats['no_procesables']}")
        print(f"   • Completadas: {stats['completadas']}")
        
        # Verificar vista
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM vw_glosas_en_pausa")
            vista_count = cursor.fetchone()[0]
            print(f"   • Registros en vista EN PAUSA: {vista_count}")
            print("✅ Vista EN PAUSA funcional")
        except Exception as e:
            print(f"❌ Error en vista EN PAUSA: {e}")
            return False
        
        conn.close()
        
        print("✅ CONFIGURACIÓN GLOSAS EN PAUSA VERIFICADA")
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def main():
    """Función principal de migración."""
    print("🚀 CONFIGURADOR GLOSAS EN PAUSA")
    print("="*50)
    
    # Migrar base de datos
    if migrar_campo_intentos():
        # Verificar configuración
        verificar_configuracion_glosas_en_pausa()
        
        print("\n🎯 PRÓXIMOS PASOS:")
        print("1. ✅ Migración completada")
        print("2. 🔄 Ejecutar módulo Glosas en Pausa desde la interfaz")
        print("3. 📊 Verificar reprocesamiento de cuentas fallidas")
        print("\n🎉 ¡Listo para usar Glosas en Pausa!")
    else:
        print("\n❌ MIGRACIÓN FALLIDA")
        print("Revise los errores anteriores antes de continuar")

if __name__ == "__main__":
    # Configurar logging básico
    logging.basicConfig(level=logging.INFO)
    main()