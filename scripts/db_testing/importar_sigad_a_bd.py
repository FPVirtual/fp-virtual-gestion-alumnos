#!/usr/bin/env python3
"""
Script para importar datos de SIGAD (JSON) a la tabla auxiliar de MySQL.

Uso:
    python importar_sigad_a_bd.py --file datos_sigad.json --batch "20250301"
    python importar_sigad_a_bd.py --env .env.preproduccion

Requiere:
    - Acceso a la base de datos Moodle
    - Tabla sigad_alumnos_aux creada (ejecutar 01_esquema_tabla_auxiliar.sql)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pymysql
from pymysql.cursors import DictCursor


def cargar_configuracion(env_file: str | None = None) -> dict:
    """Carga configuración desde variables de entorno o archivo .env."""
    from dotenv import load_dotenv
    
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=True)
        print(f"✅ Configuración cargada desde: {env_file}")
    else:
        load_dotenv()
        print("✅ Configuración cargada desde variables de entorno")
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'admin'),
        'password': os.getenv('DB_PASS', ''),
        'database': os.getenv('DB_NAME', 'www_fpvirtualaragon_es')
    }


def conectar_bd(config: dict):
    """Establece conexión a la base de datos."""
    try:
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            cursorclass=DictCursor,
            charset='utf8mb4'
        )
        print(f"✅ Conectado a: {config['host']}:{config['port']}/{config['database']}")
        return conn
    except pymysql.Error as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)


def verificar_tabla(conn) -> bool:
    """Verifica que existe la tabla auxiliar."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'sigad_alumnos_aux'
        """)
        existe = cursor.fetchone() is not None
        
        if not existe:
            print("❌ Tabla 'sigad_alumnos_aux' no existe.")
            print("   Ejecuta primero: 01_esquema_tabla_auxiliar.sql")
        else:
            # Contar registros actuales
            cursor.execute("SELECT COUNT(*) as total FROM sigad_alumnos_aux")
            total = cursor.fetchone()['total']
            print(f"✅ Tabla lista. Registros actuales: {total}")
        
        return existe


def cargar_json(filepath: str) -> dict:
    """Carga el archivo JSON de SIGAD."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Archivo no encontrado: {filepath}")
        sys.exit(1)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        num_alumnos = len(datos.get('alumnos', []))
        print(f"✅ JSON cargado: {num_alumnos} alumnos")
        return datos
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
        sys.exit(1)


def extraer_primer_centro(alumno: dict) -> dict:
    """Extrae información del primer centro/ciclo del alumno."""
    centros = alumno.get('centros', [])
    if not centros:
        return {}
    
    centro = centros[0]
    ciclos = centro.get('ciclos', [])
    ciclo = ciclos[0] if ciclos else {}
    
    return {
        'codigo_centro': centro.get('codigoCentro', ''),
        'nombre_centro': centro.get('centro', ''),
        'codigo_ciclo': ciclo.get('codigoCiclo', ''),
        'nombre_ciclo': ciclo.get('ciclo', ''),
        'siglas_ciclo': ciclo.get('siglasCiclo', ''),
        'modulos': json.dumps(ciclo.get('modulos', []), ensure_ascii=False)
    }


def insertar_alumno(cursor, alumno: dict, batch_id: str) -> bool:
    """Inserta un alumno en la tabla auxiliar."""
    centro_info = extraer_primer_centro(alumno)
    
    sql = """
        INSERT INTO sigad_alumnos_aux (
            sigad_idalumno, sigad_documento, sigad_nombre,
            sigad_apellido1, sigad_apellido2, sigad_email,
            sigad_codigo_centro, sigad_nombre_centro,
            sigad_codigo_ciclo, sigad_nombre_ciclo, sigad_siglas_ciclo,
            sigad_modulos, import_batch
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            sigad_nombre = VALUES(sigad_nombre),
            sigad_apellido1 = VALUES(sigad_apellido1),
            sigad_apellido2 = VALUES(sigad_apellido2),
            sigad_email = VALUES(sigad_email),
            sigad_codigo_centro = VALUES(sigad_codigo_centro),
            sigad_nombre_centro = VALUES(sigad_nombre_centro),
            sigad_codigo_ciclo = VALUES(sigad_codigo_ciclo),
            sigad_nombre_ciclo = VALUES(sigad_nombre_ciclo),
            sigad_siglas_ciclo = VALUES(sigad_siglas_ciclo),
            sigad_modulos = VALUES(sigad_modulos),
            import_estado = 'PENDIENTE',
            import_batch = VALUES(import_batch)
    """
    
    params = (
        alumno.get('idAlumno'),
        alumno.get('documento'),
        alumno.get('nombre'),
        alumno.get('apellido1'),
        alumno.get('apellido2'),
        alumno.get('email'),
        centro_info.get('codigo_centro'),
        centro_info.get('nombre_centro'),
        centro_info.get('codigo_ciclo'),
        centro_info.get('nombre_ciclo'),
        centro_info.get('siglas_ciclo'),
        centro_info.get('modulos'),
        batch_id
    )
    
    try:
        cursor.execute(sql, params)
        return True
    except pymysql.Error as e:
        print(f"⚠️  Error insertando alumno {alumno.get('documento')}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Importa datos de SIGAD a tabla auxiliar de MySQL'
    )
    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Ruta al archivo JSON de SIGAD'
    )
    parser.add_argument(
        '--batch', '-b',
        default=datetime.now().strftime('%Y%m%d_%H%M%S'),
        help='Identificador del lote (default: fecha_actual)'
    )
    parser.add_argument(
        '--env', '-e',
        help='Archivo .env a cargar (ej: .env.preproduccion)'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Simular sin insertar (modo prueba)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("IMPORTACIÓN SIGAD → MySQL")
    print("=" * 60)
    
    # 1. Cargar configuración
    config = cargar_configuracion(args.env)
    
    # 2. Conectar a BD
    conn = conectar_bd(config)
    
    # 3. Verificar tabla
    if not verificar_tabla(conn):
        sys.exit(1)
    
    # 4. Cargar JSON
    datos = cargar_json(args.file)
    alumnos = datos.get('alumnos', [])
    
    if not alumnos:
        print("❌ No se encontraron alumnos en el JSON")
        sys.exit(1)
    
    # 5. Confirmar inserción
    if not args.dry_run:
        print(f"\n📥 Preparado para insertar {len(alumnos)} alumnos")
        print(f"   Batch ID: {args.batch}")
        respuesta = input("\n¿Continuar? (s/n): ")
        if respuesta.lower() != 's':
            print("❌ Cancelado por usuario")
            sys.exit(0)
    else:
        print("\n🔍 MODO DRY-RUN: No se insertarán datos")
    
    # 6. Procesar alumnos
    exitosos = 0
    fallidos = 0
    
    try:
        with conn.cursor() as cursor:
            for i, alumno in enumerate(alumnos, 1):
                doc = alumno.get('documento', 'N/A')
                nombre = f"{alumno.get('nombre', '')} {alumno.get('apellido1', '')}"
                
                if args.dry_run:
                    print(f"  [{i}/{len(alumnos)}] Simulado: {doc} - {nombre}")
                    exitosos += 1
                else:
                    if insertar_alumno(cursor, alumno, args.batch):
                        print(f"  [{i}/{len(alumnos)}] ✅ {doc} - {nombre}")
                        exitosos += 1
                    else:
                        fallidos += 1
                
                # Progress cada 100
                if i % 100 == 0:
                    print(f"   ... procesados {i} registros")
        
        if not args.dry_run:
            conn.commit()
            print(f"\n✅ Commit ejecutado")
        
    except Exception as e:
        print(f"\n❌ Error durante la inserción: {e}")
        conn.rollback()
        print("🔄 Rollback ejecutado")
        sys.exit(1)
    
    finally:
        conn.close()
    
    # 7. Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total alumnos en JSON: {len(alumnos)}")
    print(f"Insertados/Actualizados: {exitosos}")
    print(f"Fallidos: {fallidos}")
    print(f"Batch ID: {args.batch}")
    
    if not args.dry_run:
        print("\n📌 Próximos pasos:")
        print("   1. Ejecutar 04_queries_sincronizacion.sql en DBeaver")
        print("   2. Revisar la vista v_sigad_pendientes")
        print("   3. Ejecutar queries de actualización con precaución")


if __name__ == '__main__':
    main()
