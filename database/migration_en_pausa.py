# database/migration_en_pausa.py
"""
Script de migración para añadir soporte completo al módulo EN PAUSA.
Ejecutar UNA VEZ antes de usar el módulo EN PAUSA.
"""

import sqlite3
import os
import logging
from config.settings import Settings

def migrar_bd_para_en_pausa():
    """
    Migra la base de datos para soportar funcionalidad EN PAUSA.
    Añade columna 'intentos' y estado 'FALLA_TOTAL'.
    """
    
    print("🔧 === MIGRACIÓN BD PARA MÓDULO EN PAUSA ===")
    print("✅ OBJETIVO: Añadir soporte completo para reprocesamiento")
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
        # PASO 1: Verificar estructura actual
        # ===================================
        print("🔍 PASO 1: Verificando estructura actual")
        
        # Verificar si existe tabla principal
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
        
        # Verificar columnas actuales
        cursor = conn.execute("PRAGMA table_info(cuenta_glosas_principal)")
        columnas_actuales = {row['name']: row for row in cursor.fetchall()}
        
        print(f"📋 Columnas actuales: {len(columnas_actuales)}")
        for nombre in columnas_actuales.keys():
            print(f"   • {nombre}")
        
        # ===================================
        # PASO 2: Añadir columna 'intentos' si no existe
        # ===================================
        print("\n🔧 PASO 2: Verificando columna 'intentos'")
        
        if 'intentos' not in columnas_actuales:
            print("➕ Añadiendo columna 'intentos'...")
            
            conn.execute("""
                ALTER TABLE cuenta_glosas_principal 
                ADD COLUMN intentos INTEGER DEFAULT 0
            """)
            
            print("✅ Columna 'intentos' añadida exitosamente")
        else:
            print("✅ Columna 'intentos' ya existe")
        
        # ===================================
        # PASO 3: Verificar estados existentes
        # ===================================
        print("\n📊 PASO 3: Verificando estados existentes")
        
        cursor = conn.execute("""
            SELECT estado, COUNT(*) as count 
            FROM cuenta_glosas_principal 
            GROUP BY estado
        """)
        
        estados_actuales = cursor.fetchall()
        
        print("Estados encontrados:")
        for row in estados_actuales:
            print(f"   • {row['estado']}: {row['count']} registros")
        
        # ===================================
        # PASO 4: Actualizar modelo de estados (si es necesario)
        # ===================================
        print("\n🔄 PASO 4: Verificando consistencia de estados")
        
        # Verificar si hay estados inconsistentes que necesiten limpieza
        cursor = conn.execute("""
            SELECT COUNT(*) as count 
            FROM cuenta_glosas_principal 
            WHERE estado NOT IN ('PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'FALLIDO', 'FALLA_TOTAL')
        """)
        
        inconsistentes = cursor.fetchone()['count']
        
        if inconsistentes > 0:
            print(f"⚠️ Encontrados {inconsistentes} registros con estados inconsistentes")
            print("🔧 Normalizando estados...")
            
            # Normalizar estados conocidos comunes
            normalizaciones = [
                ("UPDATE cuenta_glosas_principal SET estado = 'COMPLETADO' WHERE estado = 'COMPLETE'", "COMPLETE -> COMPLETADO"),
                ("UPDATE cuenta_glosas_principal SET estado = 'FALLIDO' WHERE estado = 'FAILED'", "FAILED -> FALLIDO"),
                ("UPDATE cuenta_glosas_principal SET estado = 'PENDIENTE' WHERE estado = 'PENDING'", "PENDING -> PENDIENTE"),
            ]
            
            for sql, descripcion in normalizaciones:
                try:
                    cursor = conn.execute(sql)
                    if cursor.rowcount > 0:
                        print(f"   ✅ {descripcion}: {cursor.rowcount} registros")
                except Exception as e:
                    print(f"   ⚠️ {descripcion}: {e}")
        else:
            print("✅ Todos los estados son consistentes")
        
        # ===================================
        # PASO 5: Inicializar intentos para registros existentes
        # ===================================
        print("\n🔢 PASO 5: Inicializando intentos para registros existentes")
        
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
        # PASO 6: Crear índices optimizados para EN PAUSA
        # ===================================
        print("\n🔍 PASO 6: Creando índices optimizados para EN PAUSA")
        
        indices_en_pausa = [
            ("CREATE INDEX IF NOT EXISTS idx_estado_intentos ON cuenta_glosas_principal(estado, intentos)", 
             "Índice para filtrar por estado e intentos"),
            ("CREATE INDEX IF NOT EXISTS idx_intentos ON cuenta_glosas_principal(intentos)", 
             "Índice para ordenar por intentos"),
            ("CREATE INDEX IF NOT EXISTS idx_fecha_intentos ON cuenta_glosas_principal(fecha_inicio, intentos)", 
             "Índice para ordenar por fecha e intentos")
        ]
        
        for sql, descripcion in indices_en_pausa:
            try:
                conn.execute(sql)
                print(f"   ✅ {descripcion}")
            except Exception as e:
                print(f"   ⚠️ {descripcion}: {e}")
        
        # ===================================
        # PASO 7: Crear vista para EN PAUSA
        # ===================================
        print("\n👁️ PASO 7: Creando vista específica para EN PAUSA")
        
        conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_cuentas_en_pausa AS
            SELECT 
                idcuenta,
                proveedor,
                estado,
                intentos,
                glosas_encontradas,
                glosas_procesadas,
                fecha_inicio,
                motivo_fallo,
                CASE 
                    WHEN intentos >= 5 THEN 'NO_PROCESABLE'
                    WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos < 5 THEN 'PROCESABLE'
                    ELSE 'OTRO'
                END as procesabilidad
            FROM cuenta_glosas_principal 
            WHERE estado IN ('FALLIDO', 'EN_PROCESO', 'FALLA_TOTAL')
            ORDER BY intentos DESC, fecha_inicio DESC
        """)
        
        print("✅ Vista 'vw_cuentas_en_pausa' creada")
        
        # ===================================
        # FINALIZAR MIGRACIÓN
        # ===================================
        conn.commit()
        conn.close()
        
        print("\n🎉 === MIGRACIÓN COMPLETADA EXITOSAMENTE ===")
        print("="*60)
        print("✅ Columna 'intentos' verificada/añadida")
        print("✅ Estados normalizados")
        print("✅ Índices optimizados creados")
        print("✅ Vista EN PAUSA creada")
        print("✅ Base de datos lista para módulo EN PAUSA")
        print("\n💡 Ahora puede usar el módulo EN PAUSA sin problemas")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR EN MIGRACIÓN: {e}")
        return False

def verificar_configuracion_en_pausa():
    """Verifica que la configuración EN PAUSA esté correcta."""
    
    print("\n🔍 === VERIFICACIÓN DE CONFIGURACIÓN EN PAUSA ===")
    print("-"*50)
    
    try:
        conn = sqlite3.connect(Settings.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        
        # Verificar estructura
        cursor = conn.execute("PRAGMA table_info(cuenta_glosas_principal)")
        columnas = [row['name'] for row in cursor.fetchall()]
        
        requisitos = ['intentos', 'estado', 'motivo_fallo', 'fecha_inicio']
        faltantes = [req for req in requisitos if req not in columnas]
        
        if faltantes:
            print(f"❌ FALTAN COLUMNAS: {faltantes}")
            return False
        
        print("✅ Estructura de tabla correcta")
        
        # Verificar datos
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN estado IN ('FALLIDO', 'EN_PROCESO') AND intentos < 5 THEN 1 ELSE 0 END) as procesables,
                SUM(CASE WHEN estado = 'FALLA_TOTAL' OR intentos >= 5 THEN 1 ELSE 0 END) as no_procesables
            FROM cuenta_glosas_principal
        """)
        
        stats = cursor.fetchone()
        
        print(f"📊 ESTADÍSTICAS ACTUALES:")
        print(f"   • Total registros: {stats['total']}")
        print(f"   • Procesables EN PAUSA: {stats['procesables']}")
        print(f"   • No procesables: {stats['no_procesables']}")
        
        # Verificar vista
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM vw_cuentas_en_pausa")
            vista_count = cursor.fetchone()[0]
            print(f"   • Registros en vista EN PAUSA: {vista_count}")
            print("✅ Vista EN PAUSA funcional")
        except Exception as e:
            print(f"❌ Error en vista EN PAUSA: {e}")
            return False
        
        conn.close()
        
        print("✅ CONFIGURACIÓN EN PAUSA VERIFICADA CORRECTAMENTE")
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def main():
    """Función principal de migración."""
    print("🚀 CONFIGURADOR DE MÓDULO EN PAUSA")
    print("="*50)
    
    # Migrar base de datos
    if migrar_bd_para_en_pausa():
        # Verificar configuración
        verificar_configuracion_en_pausa()
        
        print("\n🎯 PRÓXIMOS PASOS:")
        print("1. ✅ Migración completada")
        print("2. 🔄 Ejecutar módulo EN PAUSA desde la interfaz")
        print("3. 📊 Verificar procesamiento de cuentas fallidas")
        print("\n🎉 ¡Listo para usar el módulo EN PAUSA!")
    else:
        print("\n❌ MIGRACIÓN FALLIDA")
        print("Revise los errores anteriores antes de continuar")

if __name__ == "__main__":
    # Configurar logging básico
    logging.basicConfig(level=logging.INFO)
    main()