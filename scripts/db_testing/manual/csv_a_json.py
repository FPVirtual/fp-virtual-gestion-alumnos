#!/usr/bin/env python3
"""
Convierte CSV de casos de test a JSON formato SIGAD.

Uso:
    python csv_a_json.py casos_test.csv --output test_casos.json
    python csv_a_json.py casos_test.csv --pretty

El CSV debe tener las columnas del archivo 02_plantilla_casos_test.csv
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_cursos(cursos_str: str) -> list:
    """Convierte string de cursos en lista de módulos."""
    if not cursos_str:
        return []
    
    cursos_list = [c.strip() for c in cursos_str.split(';') if c.strip()]
    modulos = []
    
    for i, sigla in enumerate(cursos_list):
        modulos.append({
            "idMateria": 10000 + i,
            "modulo": f"Módulo {sigla}",
            "siglasModulo": sigla
        })
    
    return modulos


def construir_ciclo(caso: dict) -> dict:
    """Construye el objeto ciclo a partir del caso."""
    cursos = caso.get('cursos_sigad', '')
    
    # Si no hay cursos, usar siglas genéricas
    siglas_ciclo = 'GEN101'
    if cursos:
        primera_sigla = cursos.split(';')[0].strip()
        siglas_ciclo = primera_sigla[:10]  # Máximo 10 chars
    
    # Convertir caso_id a int (viene como string del CSV)
    caso_id = int(caso.get('caso_id', 0) or 0)
    
    return {
        "idFicha": int(caso.get('sigad_idalumno', 90000) or 90000) - 90000 + 100,
        "codigoCiclo": f"CIC{caso_id:03d}",
        "ciclo": f"Ciclo caso {caso_id}",
        "siglasCiclo": siglas_ciclo,
        "modulos": parse_cursos(cursos)
    }


def construir_centro(caso: dict) -> dict:
    """Construye el objeto centro."""
    return {
        "codigoCentro": "50000001",
        "centro": "Centro de Pruebas",
        "ciclos": [construir_ciclo(caso)]
    }


def construir_alumno(caso: dict) -> dict:
    """Construye el objeto alumno completo."""
    # Convertir valores numéricos que vienen como string del CSV
    sigad_idalumno = int(caso.get('sigad_idalumno', 0) or 0)
    caso_id = int(caso.get('caso_id', 0) or 0)
    moodle_userid = caso.get('moodle_userid', '')
    moodle_userid_int = int(moodle_userid) if moodle_userid and moodle_userid.strip() else None
    
    alumno = {
        "idAlumno": sigad_idalumno,
        "idTipoDocumento": 1,
        "documento": caso.get('documento_sigad', ''),
        "nombre": caso.get('nombre_sigad', ''),
        "apellido1": caso.get('apellido1_sigad', ''),
        "apellido2": caso.get('apellido2_sigad', ''),
        "email": caso.get('email_sigad', ''),
        "centros": [construir_centro(caso)],
        "_meta_caso": {
            "caso_id": caso_id,
            "descripcion": caso.get('caso_descripcion', ''),
            "moodle_userid_original": moodle_userid_int,
            "moodle_username_original": caso.get('documento_moodle') or None,
            "moodle_nombre_original": caso.get('nombre_moodle') or None,
            "moodle_apellido_original": caso.get('apellido_moodle') or None,
            "moodle_email_original": caso.get('email_moodle') or None,
            "moodle_cursos_original": caso.get('cursos_moodle') or None,
            "estaba_suspendido": caso.get('esta_suspendido') == '1',
            "notas": caso.get('notas', '')
        }
    }
    
    # Limpiar None values en _meta_caso
    meta = alumno['_meta_caso']
    alumno['_meta_caso'] = {k: v for k, v in meta.items() if v is not None}
    
    return alumno


def csv_a_json(csv_file: str, output_file: str, pretty: bool = True) -> None:
    """Convierte CSV a JSON formato SIGAD."""
    
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"❌ Archivo no encontrado: {csv_file}")
        sys.exit(1)
    
    # Leer CSV
    casos = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            casos.append(row)
    
    print(f"✅ Leídos {len(casos)} casos del CSV")
    
    # Construir registro
    registro = {
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "hora": datetime.now().strftime("%H:%M:%S"),
        "comentario": "Casos de test generados manualmente desde CSV",
        "total_casos": len(casos),
        "alumnos": [construir_alumno(caso) for caso in casos]
    }
    
    # Guardar JSON
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(registro, f, ensure_ascii=False, indent=2)
        else:
            json.dump(registro, f, ensure_ascii=False)
    
    print(f"✅ JSON guardado: {output_path.absolute()}")
    
    # Mostrar resumen
    print("\n" + "="*70)
    print("RESUMEN DE CASOS")
    print("="*70)
    for caso in casos:
        cid = caso.get('caso_id', '?')
        desc = caso.get('caso_descripcion', 'Sin descripción')
        doc = caso.get('documento_sigad', 'N/A')
        print(f"  Caso {cid}: {desc[:50]}...")
        print(f"           Documento: {doc}")


def main():
    parser = argparse.ArgumentParser(
        description='Convierte CSV de casos de test a JSON formato SIGAD'
    )
    parser.add_argument(
        'csv_file',
        help='Archivo CSV con los casos de test'
    )
    parser.add_argument(
        '-o', '--output',
        default='test_casos_manual.json',
        help='Archivo JSON de salida (default: test_casos_manual.json)'
    )
    parser.add_argument(
        '--no-pretty',
        action='store_true',
        help='No formatear JSON (una sola línea)'
    )
    
    args = parser.parse_args()
    
    csv_a_json(args.csv_file, args.output, pretty=not args.no_pretty)
    
    print(f"\n📌 Próximos pasos:")
    print(f"   1. Copiar {args.output} a tests/data/ o data/")
    print(f"   2. Cargar con: Registro.model_validate(json.load(f))")
    print(f"   3. Probar sincronización con cada caso")


if __name__ == '__main__':
    main()
