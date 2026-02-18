#!/usr/bin/env python3
"""
Script de ejemplo para sincronizar datos SIGAD con Moodle.

Este script muestra cómo:
1. Insertar datos de SIGAD en tabla auxiliar
2. Comparar contra tablas reales de Moodle
3. Detectar cambios necesarios

Uso:
    python scripts/ejemplo_uso_sigad_sync.py
    
Requiere:
    - Variables de entorno configuradas en .env
    - Tablas y vistas creadas (ejecutar scripts/crear_tabla_auxiliar_sigad_v2.sql)
"""

import os
import sys

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gestion_alumnos.utils.sigad_db_sync import (
    SigadDatabaseSync, 
    sincronizar_y_detectar,
    solo_detectar_cambios
)
from gestion_alumnos.logger_config import logger


# =============================================================================
# DATOS DE EJEMPLO (normalmente vendrían de la API de SIGAD)
# =============================================================================

ejemplo_registro_sigad = {
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
            "email": "valeria.torres.medina@ejemplo.com",
            "centros": [
                {
                    "codigoCentro": "50009348",
                    "centro": "AVEMPACE",
                    "ciclos": [
                        {
                            "idFicha": 22,
                            "codigoCiclo": "12242301",
                            "ciclo": "Educación Infantil (Formación Profesional)",
                            "siglasCiclo": "SSC302",
                            "modulos": [
                                {
                                    "idMateria": 18599,
                                    "modulo": "Itinerario personal para la empleabilidad I",
                                    "siglasModulo": "IPPE1"
                                },
                                {
                                    "idMateria": 18601,
                                    "modulo": "Primeros auxilios",
                                    "siglasModulo": "PA"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "idAlumno": 16920,
            "idTipoDocumento": 1,
            "documento": "73106923C",
            "nombre": "Bruno",
            "apellido1": "Rojas",
            "apellido2": None,
            "email": "bruno.rojas@ejemplo.com",
            "centros": [
                {
                    "codigoCentro": "50009348",
                    "centro": "AVEMPACE",
                    "ciclos": [
                        {
                            "idFicha": 19,
                            "codigoCiclo": "12242301",
                            "ciclo": "Educación Infantil (Formación Profesional)",
                            "siglasCiclo": "SSC302",
                            "modulos": [
                                {
                                    "idMateria": 18586,
                                    "modulo": "Autonomía personal y salud infantil",
                                    "siglasModulo": "APSI"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


def ejemplo_rapido():
    """Ejemplo más simple: una sola función que hace todo."""
    print("\n" + "=" * 70)
    print("EJEMPLO 1: Sincronización completa en una llamada")
    print("=" * 70)
    
    # Esta función hace todo: limpia tabla, inserta datos, detecta cambios
    filas, cambios = sincronizar_y_detectar(ejemplo_registro_sigad)
    
    print(f"\n✓ Filas insertadas: {filas}")
    print(f"✓ Cambios detectados por categoría:")
    for categoria, cantidad in cambios.get('resumen', {}).items():
        print(f"    - {categoria}: {cantidad}")


def ejemplo_paso_a_paso():
    """Ejemplo con control detallado de cada paso."""
    print("\n" + "=" * 70)
    print("EJEMPLO 2: Control paso a paso")
    print("=" * 70)
    
    sync = SigadDatabaseSync()
    
    try:
        # Paso 1: Conectar
        print("\n1. Conectando a la base de datos...")
        if not sync.conectar():
            print("   ✗ Error de conexión")
            return
        print("   ✓ Conectado")
        
        # Paso 2: Limpiar tabla auxiliar
        print("\n2. Limpiando tabla auxiliar...")
        sync.truncate_tabla_auxiliar()
        
        # Paso 3: Insertar datos de SIGAD
        print("\n3. Insertando datos de SIGAD...")
        filas = sync.insertar_registro_sigad(ejemplo_registro_sigad)
        print(f"   ✓ Insertadas {filas} filas")
        
        # Paso 4: Detectar cambios vs Moodle
        print("\n4. Detectando cambios contra tablas de Moodle...")
        cambios = sync.detectar_cambios_vs_moodle()
        
        # Paso 5: Mostrar resultados detallados
        print("\n5. RESULTADOS:")
        print("-" * 50)
        
        resumen = cambios.get('resumen', {})
        print(f"\n   Alumnos nuevos (crear): {resumen.get('ALUMNOS_NUEVOS', 0)}")
        for a in cambios['alumnos_nuevos'][:3]:
            print(f"      + {a['sigad_nombre']} {a['sigad_apellido1']} ({a['sigad_documento']})")
        
        print(f"\n   Alumnos de baja (suspender): {resumen.get('ALUMNOS_BAJA', 0)}")
        for a in cambios['alumnos_baja'][:3]:
            print(f"      - {a['moodle_nombre']} {a['moodle_apellidos']} ({a['moodle_documento']})")
        
        print(f"\n   Alumnos a reactivar: {resumen.get('ALUMNOS_REACTIVAR', 0)}")
        
        print(f"\n   Emails a actualizar: {resumen.get('EMAILS_ACTUALIZAR', 0)}")
        for e in cambios['cambios_email'][:3]:
            print(f"      ~ {e['sigad_nombre']}: {e['email_en_moodle']} -> {e['email_en_sigad']}")
        
        print(f"\n   Matrículas nuevas: {resumen.get('MATRICULAS_NUEVAS', 0)}")
        print(f"   Matrículas a dar de baja: {resumen.get('MATRICULAS_BAJA', 0)}")
        
        # Paso 6: Consultar vistas directamente
        print("\n6. Consultando vista comparativa...")
        vista_data = sync.obtener_vista_comparativa('v_comp_alumnos_sigad_vs_moodle')
        print(f"   ✓ Vista devolvió {len(vista_data)} registros")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sync.desconectar()


def ejemplo_sin_insertar():
    """Ejemplo que solo detecta cambios (sin modificar tabla auxiliar)."""
    print("\n" + "=" * 70)
    print("EJEMPLO 3: Solo detectar cambios (sin insertar)")
    print("=" * 70)
    print("\nÚtil cuando la tabla auxiliar ya tiene los datos de SIGAD")
    print("y solo quieres ver qué cambios hay pendientes.")
    
    cambios = solo_detectar_cambios()
    print(f"\n✓ Cambios detectados: {len(cambios)}")


# =============================================================================
# SCRIPT PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DEMO: Sincronización SIGAD vs Moodle (Tablas reales)")
    print("=" * 70)
    
    # Verificar variables de entorno
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME']
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"\n⚠️  Error: Faltan variables de entorno: {', '.join(missing)}")
        print("Asegúrate de tener el archivo .env configurado correctamente.")
        sys.exit(1)
    
    print("\n✓ Variables de entorno configuradas")
    print(f"  BD: {os.getenv('DB_NAME')} @ {os.getenv('DB_HOST')}")
    
    # Menú de opciones
    print("\n" + "-" * 70)
    print("OPCIONES:")
    print("  1 - Ejemplo rápido (todo en uno)")
    print("  2 - Ejemplo paso a paso (control detallado)")
    print("  3 - Solo detectar cambios (sin insertar)")
    print("  0 - Salir")
    print("-" * 70)
    
    opcion = input("\nSelecciona una opción [1]: ").strip() or "1"
    
    try:
        if opcion == "1":
            ejemplo_rapido()
        elif opcion == "2":
            ejemplo_paso_a_paso()
        elif opcion == "3":
            ejemplo_sin_insertar()
        elif opcion == "0":
            print("\nSaliendo...")
            sys.exit(0)
        else:
            print("\nOpción no válida")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("Demo completado ✓")
    print("=" * 70)
