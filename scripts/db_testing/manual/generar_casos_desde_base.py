#!/usr/bin/env python3
"""
Genera casos de test a partir de mis_datos_base.csv

Uso:
    python generar_casos_desde_base.py mis_datos_base.csv --output 02_casos_test.csv

Transformaciones aplicadas:
    Caso 1: Documento inventado (no existe en BD)
    Caso 2: Estaba suspendido (suspended=1)
    Caso 3: Email diferente
    Caso 4: Nombre modificado
    Caso 5: Username tipo NIE (X1234567L) vs DNI
    Caso 6: Agregó cursos (más cursos en SIGAD)
    Caso 7: Quitó cursos (menos cursos en SIGAD)
"""

import argparse
import csv
import random
import string
import sys
from pathlib import Path


def generar_documento_nuevo():
    """Genera un documento que no existe en BD."""
    numero = ''.join(random.choices(string.digits, k=8))
    letra = random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')
    return f"TEST{numero}{letra}"


def generar_nie():
    """Genera un NIE tipo X1234567L."""
    letra_ini = random.choice('XYZ')
    numero = ''.join(random.choices(string.digits, k=7))
    letra_fin = random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')
    return f"{letra_ini}{numero}{letra_fin}"


def parse_cursos(cursos_str):
    """Parsea string de cursos en lista."""
    if not cursos_str:
        return []
    return [c.strip() for c in cursos_str.split(',') if c.strip()]


def agregar_cursos(cursos_str):
    """Agrega 2 cursos nuevos a la lista."""
    cursos = parse_cursos(cursos_str)
    cursos_nuevos = ['NUEVO1', 'NUEVO2']
    return ';'.join(cursos + cursos_nuevos)


def quitar_cursos(cursos_str, quitar=3):
    """Quita algunos cursos, dejando al menos 1."""
    cursos = parse_cursos(cursos_str)
    if len(cursos) <= quitar:
        # Si tiene pocos cursos, dejar solo el primero
        return cursos[0] if cursos else ''
    return ';'.join(cursos[:-quitar])


def transformar_caso(usuario, caso_id):
    """Aplica transformación según el caso."""
    
    # Datos base del usuario
    caso = {
        'caso_id': caso_id,
        'moodle_userid': usuario.get('moodle_userid', ''),
        'sigad_idalumno': 90000 + caso_id,
        'documento_sigad': usuario.get('documento_actual', ''),
        'nombre_sigad': usuario.get('nombre', ''),
        'apellido1_sigad': usuario.get('apellido1', ''),
        'apellido2_sigad': usuario.get('apellido2', ''),
        'email_sigad': usuario.get('email_actual', ''),
        'cursos_sigad': usuario.get('cursos_actuales', '').replace(',', ';'),
        'documento_moodle': usuario.get('documento_actual', ''),
        'nombre_moodle': usuario.get('nombre', ''),
        'apellido_moodle': usuario.get('apellido1', ''),
        'email_moodle': usuario.get('email_actual', ''),
        'cursos_moodle': usuario.get('cursos_actuales', '').replace(',', ';'),
        'esta_suspendido': '0',
        'notas': ''
    }
    
    if caso_id == 1:
        # NUEVO: Documento inventado, no existe en Moodle
        caso['caso_descripcion'] = 'NUEVO - No existe en Moodle'
        caso['documento_sigad'] = generar_documento_nuevo()
        caso['moodle_userid'] = ''
        caso['documento_moodle'] = ''
        caso['nombre_moodle'] = ''
        caso['apellido_moodle'] = ''
        caso['email_moodle'] = ''
        caso['cursos_moodle'] = ''
        caso['notas'] = 'Usuario completamente nuevo, no existe en Moodle'
        
    elif caso_id == 2:
        # REACTIVAR: Estaba suspendido
        caso['caso_descripcion'] = 'REINCORPORACION - Estaba suspendido'
        caso['esta_suspendido'] = '1'
        caso['notas'] = 'Usuario existe pero está suspendido (suspended=1)'
        
    elif caso_id == 3:
        # CAMBIO EMAIL: Email diferente
        caso['caso_descripcion'] = 'CAMBIO_EMAIL - Email diferente'
        caso['email_sigad'] = f"nuevo.email.{caso['sigad_idalumno']}@cambiado.com"
        caso['notas'] = f"Email en Moodle: {caso['email_moodle']} → Email en SIGAD: {caso['email_sigad']}"
        
    elif caso_id == 4:
        # CAMBIO NOMBRE: Nombre modificado
        caso['caso_descripcion'] = 'CAMBIO_NOMBRE - Nombre modificado'
        caso['nombre_sigad'] = f"{caso['nombre_sigad']} Maria"  # Agregar segundo nombre
        caso['notas'] = f"Nombre en Moodle: {caso['nombre_moodle']} → Nombre en SIGAD: {caso['nombre_sigad']}"
        
    elif caso_id == 5:
        # CAMBIO NIE→DNI: Username es NIE pero SIGAD tiene DNI
        caso['caso_descripcion'] = 'CAMBIO_NIE_A_DNI - Cambio documento'
        nie = generar_nie()
        caso['documento_moodle'] = nie
        caso['notas'] = f"Username en Moodle es NIE ({nie}) pero SIGAD tiene DNI ({caso['documento_sigad']})"
        
    elif caso_id == 6:
        # NUEVAS MATRICULAS: Agregó cursos
        caso['caso_descripcion'] = 'NUEVAS_MATRICULAS - Agregó cursos'
        cursos_originales = caso['cursos_sigad']
        caso['cursos_sigad'] = agregar_cursos(cursos_originales)
        caso['notas'] = f"Cursos en Moodle: {caso['cursos_moodle']} → Cursos en SIGAD: {caso['cursos_sigad']}"
        
    elif caso_id == 7:
        # BAJA PARCIAL: Quitó cursos
        caso['caso_descripcion'] = 'BAJA_PARCIAL - Quitó cursos'
        cursos_originales = caso['cursos_sigad']
        caso['cursos_sigad'] = quitar_cursos(cursos_originales, quitar=2)
        caso['notas'] = f"Cursos en Moodle: {caso['cursos_moodle']} → Cursos en SIGAD: {caso['cursos_sigad']}"
    
    return caso


def leer_usuarios_base(csv_file):
    """Lee los usuarios del CSV base."""
    usuarios = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            usuarios.append(row)
    return usuarios


def generar_csv_casos(usuarios, output_file):
    """Genera CSV con los 7 casos de test."""
    
    if len(usuarios) < 7:
        print(f"⚠️  Advertencia: Solo hay {len(usuarios)} usuarios, se necesitan 7")
        print("   Se repetirán algunos usuarios para completar los casos")
        # Repetir usuarios si no hay suficientes
        while len(usuarios) < 7:
            usuarios.extend(usuarios[:7-len(usuarios)])
    
    # Tomar primeros 7 usuarios
    usuarios = usuarios[:7]
    
    # Generar casos
    casos = []
    for i, usuario in enumerate(usuarios, 1):
        caso = transformar_caso(usuario, i)
        casos.append(caso)
    
    # Escribir CSV
    fieldnames = [
        'caso_id', 'caso_descripcion', 'moodle_userid', 'sigad_idalumno',
        'documento_sigad', 'nombre_sigad', 'apellido1_sigad', 'apellido2_sigad',
        'email_sigad', 'cursos_sigad',
        'documento_moodle', 'nombre_moodle', 'apellido_moodle',
        'email_moodle', 'cursos_moodle', 'esta_suspendido', 'notas'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(casos)
    
    return casos


def mostrar_resumen(casos):
    """Muestra resumen de casos generados."""
    print("\n" + "=" * 80)
    print("CASOS DE TEST GENERADOS")
    print("=" * 80)
    
    for caso in casos:
        print(f"\n📋 CASO {caso['caso_id']}: {caso['caso_descripcion']}")
        print(f"   Documento SIGAD: {caso['documento_sigad']}")
        print(f"   Documento Moodle: {caso['documento_moodle'] or 'NO EXISTE'}")
        print(f"   Nombre: {caso['nombre_sigad']} {caso['apellido1_sigad']}")
        print(f"   Email SIGAD: {caso['email_sigad']}")
        print(f"   Email Moodle: {caso['email_moodle'] or 'N/A'}")
        print(f"   Cursos SIGAD: {caso['cursos_sigad']}")
        print(f"   Cursos Moodle: {caso['cursos_moodle'] or 'N/A'}")
        print(f"   Suspendido: {'SÍ' if caso['esta_suspendido'] == '1' else 'NO'}")


def main():
    parser = argparse.ArgumentParser(
        description='Genera casos de test a partir de mis_datos_base.csv'
    )
    parser.add_argument(
        'csv_base',
        help='Archivo CSV con datos base (mis_datos_base.csv)'
    )
    parser.add_argument(
        '-o', '--output',
        default='02_casos_test.csv',
        help='Archivo de salida (default: 02_casos_test.csv)'
    )
    
    args = parser.parse_args()
    
    # Verificar archivo existe
    if not Path(args.csv_base).exists():
        print(f"❌ Archivo no encontrado: {args.csv_base}")
        print("\nAsegúrate de haber:")
        print("  1. Ejecutado 01_extraer_datos_a_mano.sql en DBeaver")
        print("  2. Copiado los resultados a un archivo CSV")
        print("  3. Guardado como 'mis_datos_base.csv'")
        sys.exit(1)
    
    print("=" * 80)
    print("GENERADOR DE CASOS DE TEST DESDE DATOS BASE")
    print("=" * 80)
    
    # Leer usuarios
    print(f"\n📖 Leyendo: {args.csv_base}")
    usuarios = leer_usuarios_base(args.csv_base)
    print(f"✅ Encontrados {len(usuarios)} usuarios")
    
    # Generar casos
    print(f"\n🔧 Generando 7 casos de test...")
    casos = generar_csv_casos(usuarios, args.output)
    
    # Mostrar resumen
    mostrar_resumen(casos)
    
    # Guardar
    print(f"\n✅ CSV guardado: {args.output}")
    
    # Instrucciones siguientes
    print("\n" + "=" * 80)
    print("PRÓXIMOS PASOS")
    print("=" * 80)
    print("\n1. Revisa el archivo generado y ajusta si es necesario:")
    print(f"   - Abre {args.output} en Excel/editor")
    print("   - Verifica que las modificaciones sean correctas")
    print("   - Ajusta nombres, emails o cursos si lo necesitas")
    print("\n2. Convierte a JSON:")
    print(f"   python csv_a_json.py {args.output} --output test_casos.json")
    print("\n3. Verifica en BD:")
    print("   - Abre 03_queries_verificacion_manual.sql en DBeaver")
    print("   - Modifica los documentos con los valores generados")
    print("   - Ejecuta las queries de verificación")


if __name__ == '__main__':
    main()
