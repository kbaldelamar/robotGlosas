#!/usr/bin/env python3
"""
Script para configurar las tablas de glosas y insertar configuraciones iniciales.
Ejecutar una vez antes de usar el procesador completo.
"""

import sqlite3
import os
import logging

def setup_glosas_database():
    """Configura la base de datos con las tablas necesarias para glosas."""
    
    print("🔧 Configurando base de datos de glosas...")
    
    try:
        # Conectar a la base de datos
        db_path = "bootgestor.db"
        conn = sqlite3.connect(db_path)
        
        print(f"📂 Conectado a: {db_path}")
        
        # ===================================================
        # CREAR TABLAS
        # ===================================================
        
        print("📋 Creando tablas...")
        
        # 1. Tabla de configuración de respuestas automáticas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS glosas_respuestas_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo VARCHAR(100) NOT NULL,
                justificacion_patron VARCHAR(500) NOT NULL,
                respuesta_automatica TEXT NOT NULL,
                url_pdf VARCHAR(500),
                activo BOOLEAN DEFAULT 1,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(tipo, justificacion_patron)
            )
        """)
        
        # 2. Tabla de detalles de glosas procesadas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS glosa_items_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idcuenta VARCHAR(50) NOT NULL,
                id_glosa VARCHAR(20) NOT NULL,
                id_item VARCHAR(20),
                descripcion_item TEXT,
                tipo VARCHAR(100),
                descripcion VARCHAR(200),
                justificacion TEXT,
                valor_glosado DECIMAL(15,2),
                estado_original VARCHAR(50),
                
                respuesta_aplicada TEXT,
                config_id INTEGER,
                estado_procesamiento VARCHAR(50) DEFAULT 'PENDIENTE',
                fecha_procesamiento DATETIME,
                error_mensaje TEXT,
                
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (config_id) REFERENCES glosas_respuestas_config(id),
                UNIQUE(idcuenta, id_glosa)
            )
        """)
        
        # 3. Tabla de log de procesamiento
        conn.execute("""
            CREATE TABLE IF NOT EXISTS glosas_log_procesamiento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idcuenta VARCHAR(50) NOT NULL,
                id_glosa VARCHAR(20) NOT NULL,
                accion VARCHAR(100),
                detalle TEXT,
                fecha_accion DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ===================================================
        # CREAR ÍNDICES
        # ===================================================
        
        print("🔍 Creando índices...")
        
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_glosas_config_tipo ON glosas_respuestas_config(tipo)",
            "CREATE INDEX IF NOT EXISTS idx_glosas_config_activo ON glosas_respuestas_config(activo)",
            "CREATE INDEX IF NOT EXISTS idx_cuenta ON glosa_items_detalle(idcuenta)",
            "CREATE INDEX IF NOT EXISTS idx_estado ON glosa_items_detalle(estado_procesamiento)",
            "CREATE INDEX IF NOT EXISTS idx_tipo_justif ON glosa_items_detalle(tipo, justificacion)",
            "CREATE INDEX IF NOT EXISTS idx_cuenta_glosa ON glosas_log_procesamiento(idcuenta, id_glosa)"
        ]
        
        for indice in indices:
            conn.execute(indice)
        
        # ===================================================
        # INSERTAR CONFIGURACIONES INICIALES
        # ===================================================
        
        print("📝 Insertando configuraciones iniciales...")
        
        # Verificar si ya hay configuraciones
        cursor = conn.execute("SELECT COUNT(*) FROM glosas_respuestas_config")
        count = cursor.fetchone()[0]
        
        if count == 0:
            configuraciones = [
                (
                    'TARIFAS', 
                    '%MAYOR VALOR COBRADO EN%SERVICIO DE ALOJAMIENTO%', 
                    'El valor cobrado corresponde a la tarifa autorizada según contrato vigente y normatividad aplicable. Se adjunta soporte tarifario y autorización del servicio.',
                    r'C:\python\robotGlosas\contrato.pdf'
                ),
                (
                    'TARIFAS', 
                    '%MAYOR VALOR COBRADO EN%ALBERGUE ACOMPANANTE%', 
                    'El cobro del albergue para acompañante está justificado según tarifa contractual autorizada. Se cuenta con la debida autorización y documentación de soporte.',
                    r'C:\python\robotGlosas\contrato.pdf'
                ),
                (
                    'TARIFAS', 
                    '%MAYOR VALOR COBRADO%', 
                    'El valor facturado corresponde a las tarifas autorizadas y vigentes según contrato. Se adjunta documentación soporte.',
                    r'C:\python\robotGlosas\contrato.pdf'
                ),
                (
                    'MEDICAMENTOS', 
                    '%MEDICAMENTO NO AUTORIZADO%', 
                    'El medicamento fue suministrado por prescripción médica urgente. Se adjunta orden médica y justificación clínica.',
                    r'C:\python\robotGlosas\contrato.pdf'
                ),
                (
                    'PROCEDIMIENTOS', 
                    '%PROCEDIMIENTO NO AUTORIZADO%', 
                    'El procedimiento fue realizado por necesidad médica urgente con autorización verbal posterior. Se adjunta documentación clínica.',
                    r'C:\python\robotGlosas\contrato.pdf'
                )
            ]
            
            for config in configuraciones:
                conn.execute("""
                    INSERT INTO glosas_respuestas_config 
                    (tipo, justificacion_patron, respuesta_automatica, url_pdf) 
                    VALUES (?, ?, ?, ?)
                """, config)
            
            print(f"✅ Insertadas {len(configuraciones)} configuraciones")
        else:
            print(f"⚠️ Ya existen {count} configuraciones, saltando inserción")
        
        # ===================================================
        # VERIFICAR ARCHIVO PDF
        # ===================================================
        
        print("📄 Verificando archivo PDF...")
        
        pdf_path = r'C:\python\robotGlosas\contrato.pdf'
        
        if not os.path.exists(pdf_path):
            print(f"⚠️ IMPORTANTE: El archivo PDF no existe: {pdf_path}")
            print("   Crea un archivo PDF de ejemplo o actualiza las rutas en la BD")
            
            # Crear archivo de ejemplo
            try:
                with open(pdf_path, 'w') as f:
                    f.write("Archivo PDF de ejemplo - Reemplazar con documento real")
                print(f"📄 Archivo de ejemplo creado: {pdf_path}")
            except Exception as e:
                print(f"❌ No se pudo crear archivo de ejemplo: {e}")
        else:
            print(f"✅ Archivo PDF encontrado: {pdf_path}")
        
        # Confirmar cambios
        conn.commit()
        conn.close()
        
        print("\n🎉 CONFIGURACIÓN COMPLETADA")
        print("="*50)
        print("✅ Tablas creadas correctamente")
        print("✅ Índices creados")
        print("✅ Configuraciones insertadas")
        print("✅ Base de datos lista para usar")
        print("\n💡 Ahora puedes ejecutar el procesador completo de glosas")
        
    except Exception as e:
        print(f"❌ Error configurando base de datos: {e}")
        return False
    
    return True

def verificar_configuracion():
    """Verifica la configuración actual de la base de datos."""
    
    print("\n🔍 VERIFICANDO CONFIGURACIÓN ACTUAL")
    print("="*50)
    
    try:
        conn = sqlite3.connect("bootgestor.db")
        conn.row_factory = sqlite3.Row
        
        # Verificar tablas
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%glosa%'
        """)
        
        tablas = cursor.fetchall()
        print(f"📋 Tablas de glosas encontradas: {len(tablas)}")
        for tabla in tablas:
            print(f"   - {tabla['name']}")
        
        # Verificar configuraciones
        cursor = conn.execute("SELECT COUNT(*) as count FROM glosas_respuestas_config")
        count = cursor.fetchone()['count']
        print(f"\n⚙️ Configuraciones de respuesta: {count}")
        
        if count > 0:
            cursor = conn.execute("""
                SELECT tipo, justificacion_patron, activo 
                FROM glosas_respuestas_config 
                ORDER BY tipo
            """)
            
            for config in cursor.fetchall():
                estado = "✅" if config['activo'] else "❌"
                print(f"   {estado} {config['tipo']}: {config['justificacion_patron'][:50]}...")
        
        # Verificar datos de cuentas
        cursor = conn.execute("SELECT COUNT(*) as count FROM cuenta_glosas_principal")
        cuentas = cursor.fetchone()['count']
        print(f"\n🏢 Cuentas en BD: {cuentas}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")

if __name__ == "__main__":
    print("🚀 CONFIGURADOR DE BASE DE DATOS DE GLOSAS")
    print("="*50)
    
    # Configurar base de datos
    if setup_glosas_database():
        # Verificar configuración
        verificar_configuracion()
    else:
        print("❌ Falló la configuración de la base de datos")