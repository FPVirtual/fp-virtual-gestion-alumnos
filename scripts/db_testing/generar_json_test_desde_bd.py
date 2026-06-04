#!/usr/bin/env python3
"""
Genera JSON de test a partir de casos creados en la base de datos.

Uso:
    python generar_json_test_desde_bd.py --output test_casos.json
    python generar_json_test_desde_bd.py --env .env.preproduccion
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pymysql
from pymysql.cursors import DictCursor


def conectar_bd(env_file: str | None = None) -> pymysql.Connection:
    """Conecta a la base de datos."""
    from dotenv import load_dotenv
    
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=True)
    else:
        load_dotenv()
    
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'admin'),
        'password': os.getenv('DB_PASS', ''),
        'database': os.getenv('DB_NAME', 'www_fpvirtualaragon_es')
    }
    
    try:
        return pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            cursorclass=DictCursor,
            charset='utf8mb4'
        )
    except pymysql.Error as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)


def crear_tabla_casos(conn: pymysql.Connection) -> None:
    """Crea la tabla de casos de test si no existe."""
    sql = """
    CREATE TABLE IF NOT EXISTS tmp_casos_test (
        caso_id INT PRIMARY KEY,
        caso_descripcion VARCHAR(100),
        sigad_idalumno INT,
        sigad_documento VARCHAR(20),
        sigad_nombre VARCHAR(100),
        sigad_apellido1 VARCHAR(100),
        sigad_apellido2 VARCHAR(100),
        sigad_email VARCHAR(200),
        sigad_cursos VARCHAR(500),
        moodle_userid INT,
        moodle_username VARCHAR(100),
        moodle_nombre_original VARCHAR(100),
        moodle_apellido_original VARCHAR(100),
        moodle_email_original VARCHAR(200),
        moodle_cursos_original VARCHAR(500),
        moodle_suspended INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)


def obtener_casos(conn: pymysql.Connection) -> list[dict]:
    """Obtiene los casos de test de la BD."""
    sql = """
        SELECT 
            caso_id,
            caso_descripcion,
            sigad_idalumno,
            sigad_documento,
            sigad_nombre,
            sigad_apellido1,
            sigad_apellido2,
            sigad_email,
            sigad_cursos,
            moodle_userid,
            moodle_username,
            moodle_nombre_original,
            moodle_apellido_original,
            moodle_email_original,
            moodle_cursos_original,
            moodle_suspended
        FROM tmp_casos_test
        ORDER BY caso_id
    """
    
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def construir_alumno_json(caso: dict) -> dict:
    """Construye el objeto alumno en formato SIGAD."""
    # Parsear cursos
    cursos_siglas = caso['sigad_cursos'].split(', ') if caso['sigad_cursos'] else []
    
    # Construir módulos para cada curso
    modulos = []
    for i, sigla in enumerate(cursos_siglas[:3]):  # Máximo 3 cursos
        modulos.append({
            "idMateria": 10000 + caso['caso_id'] * 100 + i,
            "modulo": f"Módulo de prueba {sigla}",
            "siglasModulo": sigla
        })
    
    # Construir ciclo
    ciclo = {
        "idFicha": 100 + caso['caso_id'],
        "codigoCiclo": f"CIC{caso['caso_id']:03d}",
        "ciclo": f"Ciclo de prueba caso {caso['caso_id']}",
        "siglasCiclo": f"CIC{caso['caso_id']:03d}",
        "modulos": modulos
    }
    
    # Construir centro
    centro = {
        "codigoCentro": "50000000",
        "centro": "Centro de Pruebas",
        "ciclos": [ciclo]
    }
    
    # Construir alumno completo
    alumno = {
        "idAlumno": caso['sigad_idalumno'],
        "idTipoDocumento": 1,
        "documento": caso['sigad_documento'],
        "nombre": caso['sigad_nombre'],
        "apellido1": caso['sigad_apellido1'],
        "apellido2": caso['sigad_apellido2'] or "",
        "email": caso['sigad_email'],
        "centros": [centro],
        "_meta_caso": {
            "caso_id": caso['caso_id'],
            "descripcion": caso['caso_descripcion'],
            "moodle_userid_original": caso['moodle_userid'],
            "moodle_username_original": caso['moodle_username'],
            "moodle_nombre_original": caso['moodle_nombre_original'],
            "moodle_apellido_original": caso['moodle_apellido_original'],
            "moodle_email_original": caso['moodle_email_original'],
            "moodle_cursos_original": caso['moodle_cursos_original'],
            "estaba_suspendido": caso['moodle_suspended'] == 1
        }
    }
    
    return alumno


def generar_json(casos: list[dict], output_file: str) -> None:
    """Genera el archivo JSON de test."""
    
    registro = {
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "hora": datetime.now().strftime("%H:%M:%S"),
        "comentario": "Casos de test generados desde datos reales de Moodle",
        "total_casos": len(casos),
        "alumnos": [construir_alumno_json(caso) for caso in casos]
    }
    
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ JSON generado: {output_path.absolute()}")
    print(f"   Total alumnos: {len(casos)}")


def mostrar_resumen(casos: list[dict]) -> None:
    """Muestra resumen de casos en consola."""
    print("\n" + "=" * 80)
    print("CASOS DE TEST GENERADOS")
    print("=" * 80)
    
    for caso in casos:
        print(f"\n📋 CASO {caso['caso_id']}: {caso['caso_descripcion']}")
        print(f"   Documento SIGAD: {caso['sigad_documento']}")
        print(f"   Nombre: {caso['sigad_nombre']} {caso['sigad_apellido1']}")
        print(f"   Email SIGAD: {caso['sigad_email']}")
        print(f"   Cursos: {caso['sigad_cursos']}")
        
        if caso['moodle_username']:
            print(f"   ↳ Moodle original: {caso['moodle_username']}")
            print(f"   ↳ Email original: {caso['moodle_email_original']}")
            print(f"   ↳ Cursos originales: {caso['moodle_cursos_original']}")
            
            # Detectar diferencias
            diferencias = []
            if caso['sigad_email'] != caso['moodle_email_original']:
                diferencias.append("EMAIL")
            if caso['sigad_nombre'] != caso['moodle_nombre_original']:
                diferencias.append("NOMBRE")
            if caso['sigad_documento'] != caso['moodle_username']:
                diferencias.append("DOCUMENTO")
            if caso['sigad_cursos'] != caso['moodle_cursos_original']:
                diferencias.append("CURSOS")
            if caso['moodle_suspended'] == 1:
                diferencias.append("SUSPENDIDO")
            
            if diferencias:
                print(f"   ⚠️  Diferencias detectadas: {', '.join(diferencias)}")
        else:
            print(f"   ↳ NUEVO: No existe en Moodle")


def main():
    parser = argparse.ArgumentParser(
        description='Genera JSON de test desde casos creados en BD'
    )
    parser.add_argument(
        '--output', '-o',
        default='test_casos_desde_bd.json',
        help='Archivo de salida (default: test_casos_desde_bd.json)'
    )
    parser.add_argument(
        '--env', '-e',
        help='Archivo .env (ej: .env.preproduccion)'
    )
    parser.add_argument(
        '--crear-casos', '-c',
        action='store_true',
        help='Primero ejecutar script SQL para crear casos'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("GENERADOR DE JSON DE TEST DESDE BD")
    print("=" * 80)
    
    # Conectar
    conn = conectar_bd(args.env)
    
    if args.crear_casos:
        print("\n📌 Para crear casos, primero ejecuta en DBeaver:")
        print("   07_extraer_casos_test.sql")
        resp = input("\n¿Ya ejecutaste el script SQL? (s/n): ")
        if resp.lower() != 's':
            print("❌ Cancelado. Ejecuta el SQL primero.")
            return
    
    # Verificar tabla existe
    try:
        casos = obtener_casos(conn)
    except pymysql.Error as e:
        print(f"\n❌ Error: {e}")
        print("\n📌 La tabla tmp_casos_test no existe.")
        print("   Ejecuta primero en DBeaver: 07_extraer_casos_test.sql")
        return
    
    if not casos:
        print("\n⚠️  No hay casos en tmp_casos_test")
        print("   Ejecuta primero: 07_extraer_casos_test.sql")
        return
    
    # Mostrar resumen
    mostrar_resumen(casos)
    
    # Generar JSON
    generar_json(casos, args.output)
    
    conn.close()
    
    print("\n📌 Próximos pasos:")
    print(f"   1. Copiar {args.output} a tests/data/")
    print("   2. Usar en tests: cargar con json_parser")
    print("   3. Probar sincronización con cada caso")


if __name__ == '__main__':
    main()
