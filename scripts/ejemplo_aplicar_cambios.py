#!/usr/bin/env python3
"""
Script de ejemplo completo: Detectar y aplicar cambios SIGAD -> Moodle

Este script muestra el flujo completo:
1. Insertar datos de SIGAD en tabla auxiliar
2. Detectar diferencias contra Moodle
3. Aplicar cambios (SQL para datos personales, moosh para matrículas)

Uso:
    # Simulación (no aplica cambios reales)
    python scripts/ejemplo_aplicar_cambios.py --dry-run
    
    # Ejecución real
    python scripts/ejemplo_aplicar_cambios.py --apply
    
    # Solo detectar sin aplicar
    python scripts/ejemplo_aplicar_cambios.py --detect-only
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gestion_alumnos.utils.sigad_db_sync import sincronizar_y_detectar, solo_detectar_cambios
from gestion_alumnos.utils.sigad_aplicar_cambios import aplicar_cambios_sigad
from gestion_alumnos.logger_config import logger


def ejemplo_completo(dry_run: bool = True, detect_only: bool = False):
    """
    Ejemplo completo del flujo: sincronizar, detectar y aplicar cambios.
    """
    
    # =================================================================
    # CONFIGURACIÓN
    # =================================================================
    MOODLE_CONTAINER = os.getenv("MOODLE_CONTAINER", "wwwfpvirtualaragones-moodle-1")
    
    # Mapeo de siglas de módulos a course IDs de Moodle
    # Esto debería venir de una tabla de configuración o base de datos
    MAPEO_CURSOS_EJEMPLO = {
        'IPPE1': 123,
        'PA': 124,
        'APSI': 125,
        'DCM': 126,
        'DASP': 127,
        'HS': 128,
        'IN': 129,
    }
    
    print("\n" + "="*70)
    print("DEMO COMPLETO: Sincronización y Aplicación de Cambios")
    print("="*70)
    print(f"\nModo: {'SIMULACIÓN (DRY-RUN)' if dry_run else 'EJECUCIÓN REAL'}")
    print(f"Contenedor Moodle: {MOODLE_CONTAINER}")
    
    # =================================================================
    # PASO 1: DATOS DE EJEMPLO (en producción vendrían de la API SIGAD)
    # =================================================================
    
    # Simulamos datos de SIGAD
    registro_sigad_ejemplo = {
        "fecha": "18/02/2026",
        "hora": "15:30:00",
        "alumnos": [
            {
                "idAlumno": 16839,
                "idTipoDocumento": 1,
                "documento": "78842153Q",
                "nombre": "Valeria",
                "apellido1": "Torres",
                "apellido2": "Medina",
                "email": "valeria.torres.nueva@ejemplo.com",  # Email cambiado
                "centros": [
                    {
                        "codigoCentro": "50009348",
                        "centro": "AVEMPACE",
                        "ciclos": [
                            {
                                "idFicha": 22,
                                "codigoCiclo": "12242301",
                                "ciclo": "Educación Infantil",
                                "siglasCiclo": "SSC302",
                                "modulos": [
                                    {"idMateria": 18599, "modulo": "IPPE1", "siglasModulo": "IPPE1"},
                                    {"idMateria": 18601, "modulo": "Primeros auxilios", "siglasModulo": "PA"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "idAlumno": 99999,  # Nuevo alumno
                "idTipoDocumento": 1,
                "documento": "12345678A",
                "nombre": "Nuevo",
                "apellido1": "Alumno",
                "apellido2": "Test",
                "email": "nuevo.alumno@test.com",
                "centros": [
                    {
                        "codigoCentro": "50009348",
                        "centro": "AVEMPACE",
                        "ciclos": [
                            {
                                "idFicha": 25,
                                "codigoCiclo": "12242301",
                                "ciclo": "Educación Infantil",
                                "siglasCiclo": "SSC302",
                                "modulos": [
                                    {"idMateria": 18599, "modulo": "IPPE1", "siglasModulo": "IPPE1"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # =================================================================
    # PASO 2: SINCRONIZAR Y DETECTAR CAMBIOS
    # =================================================================
    
    print("\n" + "-"*70)
    print("PASO 1: Sincronizando datos de SIGAD y detectando cambios...")
    print("-"*70)
    
    try:
        filas_insertadas, cambios = sincronizar_y_detectar(registro_sigad_ejemplo)
        
        print(f"\n✓ Filas insertadas en tabla auxiliar: {filas_insertadas}")
        print(f"\nResumen de cambios detectados:")
        for categoria, cantidad in cambios.get('resumen', {}).items():
            print(f"  • {categoria}: {cantidad}")
        
        # Si solo queremos detectar, terminamos aquí
        if detect_only:
            print("\n" + "="*70)
            print("Modo DETECCIÓN ONLY - No se aplicaron cambios")
            print("="*70)
            return
        
    except Exception as e:
        print(f"\n✗ Error en detección de cambios: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # =================================================================
    # PASO 3: APLICAR CAMBIOS
    # =================================================================
    
    print("\n" + "-"*70)
    print(f"PASO 2: Aplicando cambios ({'SIMULACIÓN' if dry_run else 'REAL'})...")
    print("-"*70)
    
    print("\n📋 Operaciones que se realizarán:")
    print("  • Datos personales: UPDATE SQL directo (rápido)")
    print("  • Altas/Bajas/Reactivaciones: Comandos moosh")
    print("  • Matrículas: Comandos moosh")
    
    try:
        resultado = aplicar_cambios_sigad(
            cambios=cambios,
            moodle_container=MOODLE_CONTAINER,
            mapeo_cursos=MAPEO_CURSOS_EJEMPLO,
            dry_run=dry_run
        )
        
        # Mostrar resultados detallados
        print("\n" + "="*70)
        print("RESULTADO DE LA APLICACIÓN")
        print("="*70)
        
        stats = resultado['estadisticas']
        print(f"\nEstadísticas:")
        print(f"  ✓ Datos personales actualizados: {stats['datos_personales_actualizados']}")
        print(f"  ✓ Usuarios creados: {stats['usuarios_creados']}")
        print(f"  ✓ Usuarios suspendidos: {stats['usuarios_suspendidos']}")
        print(f"  ✓ Usuarios reactivados: {stats['usuarios_reactivados']}")
        print(f"  ✓ Matrículas creadas: {stats['matriculas_creadas']}")
        print(f"  ✓ Matrículas suspendidas: {stats['matriculas_suspendidas']}")
        print(f"  ✗ Errores: {stats['errores']}")
        
        print(f"\nResumen:")
        print(f"  • Total operaciones: {resultado['exitosos'] + resultado['fallidos']}")
        print(f"  • Exitosas: {resultado['exitosos']}")
        print(f"  • Fallidas: {resultado['fallidos']}")
        print(f"  • Modo: {resultado['modo']}")
        
        # Mostrar algunos resultados detallados
        if resultado['resultados']:
            print(f"\nDetalle de operaciones (primeras 5):")
            for i, res in enumerate(resultado['resultados'][:5]):
                icono = "✓" if res.exito else "✗"
                print(f"  {icono} {res.tipo}: {res.documento} - {res.mensaje[:50]}")
        
        print("\n" + "="*70)
        
        if dry_run:
            print("⚠️  ESTO FUE UNA SIMULACIÓN (DRY-RUN)")
            print("    Para aplicar cambios reales, ejecuta con --apply")
        else:
            print("✓ CAMBIOS APLICADOS EN MOODLE")
        
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Error aplicando cambios: {e}")
        import traceback
        traceback.print_exc()
        return


def main():
    parser = argparse.ArgumentParser(
        description='Sincroniza datos de SIGAD con Moodle y aplica cambios'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Simula las operaciones sin aplicar cambios reales (default)'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Aplica los cambios reales en Moodle'
    )
    parser.add_argument(
        '--detect-only',
        action='store_true',
        help='Solo detecta cambios sin aplicarlos'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.apply and args.detect_only:
        print("Error: No puedes usar --apply y --detect-only al mismo tiempo")
        sys.exit(1)
    
    # Por defecto, dry-run a menos que se especifique --apply
    dry_run = not args.apply
    detect_only = args.detect_only
    
    # Verificar variables de entorno
    required = ['DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME']
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Error: Faltan variables de entorno: {', '.join(missing)}")
        sys.exit(1)
    
    # Ejecutar
    try:
        ejemplo_completo(dry_run=dry_run, detect_only=detect_only)
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()
