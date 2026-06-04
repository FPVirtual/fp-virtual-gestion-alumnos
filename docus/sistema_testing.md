# Sistema de Testing

> **Última actualización:** Junio 2026  
> **Tests totales:** 35  
> **Estado:** 35/35 ✅

---

## Índice

- [Ejecutar todos los tests](#ejecutar-todos-los-tests)
- [1. Tests de Configuración (`test_core_config.py`)](#1-tests-de-configuración)
- [2. Tests del DI Container (`test_core_container.py`)](#2-tests-del-di-container)
- [3. Tests de Modelos (`test_models.py`)](#3-tests-de-modelos)
- [4. Tests del Repositorio Moosh (`test_repositories_moosh.py`)](#4-tests-del-repositorio-moosh)
- [5. Tests del Repositorio SIGAD (`test_repositories_sigad.py`)](#5-tests-del-repositorio-sigad)
- [6. Tests de Integración Moodle API (`test_moodle_api_integration.py`)](#6-tests-de-integración-moodle-api)

---

## Ejecutar todos los tests

```bash
# Todos los tests
pytest tests/ -v

# Todos con resumen
pytest tests/ -v --tb=short

# Con cobertura
pytest tests/ --cov=gestion_alumnos
```

---

## 1. Tests de Configuración

**Archivo:** `tests/test_core_config.py`  
**Tests:** 3

Validan que `Pydantic Settings` carga correctamente las variables de entorno y calcula propiedades derivadas.

| Test | Descripción | Comando |
|------|-------------|---------|
| `test_config_default` | Valores por defecto: `environment=dev`, `moodle_driver=moosh`, `email_limit=10` | `pytest tests/test_core_config.py::test_config_default -v` |
| `test_config_produccion` | Con `SUBDOMAIN=www` activa `is_produccion=True` y `email_limit=1000` | `pytest tests/test_core_config.py::test_config_produccion -v` |
| `test_config_api_driver` | Con `MOODLE_DRIVER=api` el driver se resuelve correctamente | `pytest tests/test_core_config.py::test_config_api_driver -v` |

**Ejecutar todos:**
```bash
pytest tests/test_core_config.py -v
```

---

## 2. Tests del DI Container

**Archivo:** `tests/test_core_container.py`  
**Tests:** 3

Validan que el contenedor de inyección de dependencias resuelve la implementación correcta de `MoodleRepository` según la configuración.

| Test | Descripción | Comando |
|------|-------------|---------|
| `test_container_resuelve_moosh_por_defecto` | Con `moodle_driver=moosh` devuelve `MooshMoodleRepository` | `pytest tests/test_core_container.py::test_container_resuelve_moosh_por_defecto -v` |
| `test_container_resuelve_api` | Con `moodle_driver=api` devuelve `APIMoodleRepository` | `pytest tests/test_core_container.py::test_container_resuelve_api -v` |
| `test_container_override_moodle_repo` | Permite reemplazar la implementación en runtime (útil para mocks) | `pytest tests/test_core_container.py::test_container_override_moodle_repo -v` |

**Ejecutar todos:**
```bash
pytest tests/test_core_container.py -v
```

---

## 3. Tests de Modelos

**Archivo:** `tests/test_models.py`  
**Tests:** 10

Validan la creación, validación y propiedades calculadas de los modelos Pydantic.

| Test | Descripción | Comando |
|------|-------------|---------|
| `test_modulo_str` | `__str__` de `Modulo` devuelve "SIGLAS - Nombre" | `pytest tests/test_models.py::test_modulo_str -v` |
| `test_ciclo_str` | `__str__` de `Ciclo` devuelve "SIGLAS (código)" | `pytest tests/test_models.py::test_ciclo_str -v` |
| `test_centro_str` | `__str__` de `Centro` devuelve "código - nombre" | `pytest tests/test_models.py::test_centro_str -v` |
| `test_alumno_nombre_completo` | Propiedad `nombre_completo` concatena nombre + apellidos | `pytest tests/test_models.py::test_alumno_nombre_completo -v` |
| `test_alumno_username_moodle` | Propiedad `username_moodle` es documento en minúsculas | `pytest tests/test_models.py::test_alumno_username_moodle -v` |
| `test_alumno_email_institucional` | Propiedad `email_institucional` genera email del dominio | `pytest tests/test_models.py::test_alumno_email_institucional -v` |
| `test_alumno_obtener_todos_modulos` | Obtiene todos los módulos de todos los ciclos/centros | `pytest tests/test_models.py::test_alumno_obtener_todos_modulos -v` |
| `test_registro_total_alumnos` | `total_alumnos` devuelve la cantidad correcta | `pytest tests/test_models.py::test_registro_total_alumnos -v` |
| `test_registro_buscar_por_documento` | `buscar_por_documento` encuentra alumno por DNI/NIE | `pytest tests/test_models.py::test_registro_buscar_por_documento -v` |
| `test_registro_buscar_por_documento_no_existe` | Devuelve `None` si el documento no existe | `pytest tests/test_models.py::test_registro_buscar_por_documento_no_existe -v` |
| `test_alumno_normaliza_documento` | Valida y normaliza documento a mayúsculas | `pytest tests/test_models.py::test_alumno_normaliza_documento -v` |

**Ejecutar todos:**
```bash
pytest tests/test_models.py -v
```

---

## 4. Tests del Repositorio Moosh

**Archivo:** `tests/test_repositories_moosh.py`  
**Tests:** 3

Validan `MooshMoodleRepository` usando mocks de `subprocess.run`. No requieren Moodle real.

| Test | Descripción | Comando |
|------|-------------|---------|
| `test_moosh_usuario_existe` | `usuario_existe` devuelve `True` cuando moosh encuentra el usuario | `pytest tests/test_repositories_moosh.py::test_moosh_usuario_existe -v` |
| `test_moosh_crear_usuario` | `crear_usuario` devuelve el ID parseado de la salida de moosh | `pytest tests/test_repositories_moosh.py::test_moosh_crear_usuario -v` |
| `test_moosh_error_comando` | `MoodleError` se lanza cuando moosh retorna código de error != 0 | `pytest tests/test_repositories_moosh.py::test_moosh_error_comando -v` |

**Ejecutar todos:**
```bash
pytest tests/test_repositories_moosh.py -v
```

---

## 5. Tests del Repositorio SIGAD

**Archivo:** `tests/test_repositories_sigad.py`  
**Tests:** 6

Validan `SIGADRepository` usando `requests_mock` para simular la API REST de SIGAD.

| Test | Descripción | Comando |
|------|-------------|---------|
| `test_obtener_registro_desde_api` | Flujo completo: solicitud → descarga → parseo a `Registro` con estructura anidada | `pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_obtener_registro_desde_api -v` |
| `test_obtener_registro_desde_test` | Modo test: carga desde `tests/data/test_estudiantes_data.json` sin llamar a la API | `pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_obtener_registro_desde_test -v` |
| `test_reintentos_api` | Cuando SIGAD retorna `codigo=-1` (no listo), reintenta hasta obtener `codigo=0` | `pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_reintentos_api -v` |
| `test_error_credenciales` | Lanza `APIError` si faltan `API_USER` o `API_PASSWORD` | `pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_error_credenciales -v` |
| `test_buscar_por_documento` | `buscar_por_documento` encuentra alumno en registro de test | `pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_buscar_por_documento -v` |
| `test_estructura_completa_json` | Valida que todos los campos del JSON SIGAD se parsean a modelos Pydantic | `pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_estructura_completa_json -v` |

**Ejecutar todos:**
```bash
pytest tests/test_repositories_sigad.py -v
```

---

## 6. Tests de Integración Moodle API

**Archivo:** `tests/test_moodle_api_integration.py`  
**Tests:** 9  
**Requisitos:** Instancia de Moodle real accesible en `192.168.2.253:8087` con token válido.

> ⚠️ **Advertencia:** Estos tests tocan datos reales en Moodle. Usan el usuario `prof_cd_daw` para operaciones de suspensión. **Nunca suspender `moodle-api`** (propietario del token).

| Test | Descripción | Comando |
|------|-------------|---------|
| `test_endpoint_responde` | El endpoint REST responde HTTP 200 | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIConexion::test_endpoint_responde -v` |
| `test_token_valido` | El token permite llamar a `core_webservice_get_site_info` | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIConexion::test_token_valido -v` |
| `test_listar_usuarios` | `obtener_todos_usuarios()` devuelve lista con al menos 1 usuario | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIUsuarios::test_listar_usuarios -v` |
| `test_usuario_existe_moodle_api` | `usuario_existe("moodle-api")` es `True` | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIUsuarios::test_usuario_existe_moodle_api -v` |
| `test_usuario_no_existe` | Username aleatorio no existe | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIUsuarios::test_usuario_no_existe -v` |
| `test_crear_usuario` | Crea usuario vía API, devuelve ID > 0 | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIUsuarios::test_crear_usuario -v` |
| `test_suspender_y_reactivar_usuario` | Suspender y reactivar `prof_cd_daw`; verifica campo `suspended` | `pytest tests/test_moodle_api_integration.py::TestMoodleAPIUsuarios::test_suspender_y_reactivar_usuario -v` |
| `test_obtener_matriculas_moodle_api` | Obtiene matrículas del usuario `moodle-api` | `pytest tests/test_moodle_api_integration.py::TestMoodleAPICursos::test_obtener_matriculas_moodle_api -v` |
| `test_obtener_matriculas_usuario_inexistente` | Devuelve lista vacía para usuario inexistente | `pytest tests/test_moodle_api_integration.py::TestMoodleAPICursos::test_obtener_matriculas_usuario_inexistente -v` |

**Ejecutar todos:**
```bash
pytest tests/test_moodle_api_integration.py -v
```

**Si Moodle no está disponible**, todos los tests de este archivo se saltan automáticamente (`pytestmark.skipif`).

---

## Fixtures Principales (`tests/conftest.py`)

| Fixture | Alcance | Descripción |
|---------|---------|-------------|
| `settings_test` | función | Configuración de test (`ENVIRONMENT=test`, `MOODLE_DRIVER=moosh`) |
| `sample_modulo` | función | Instancia de `Modulo` de prueba |
| `sample_ciclo` | función | Instancia de `Ciclo` con 1 módulo |
| `sample_centro` | función | Instancia de `Centro` con 1 ciclo |
| `sample_alumno` | función | Instancia de `Alumno` con 1 centro |
| `sample_registro` | función | Instancia de `Registro` con 1 alumno |
| `mock_moosh` | función | Mock de `subprocess.run` que simula éxito de moosh |

---

## Comandos Rápidos

```bash
# Todos
pytest tests/ -v

# Solo unitarios (sin integración)
pytest tests/ -v --ignore=tests/test_moodle_api_integration.py

# Solo integración Moodle
pytest tests/test_moodle_api_integration.py -v

# Un test específico
pytest tests/test_repositories_sigad.py::TestSIGADRepository::test_obtener_registro_desde_api -v

# Con cobertura
pytest tests/ --cov=gestion_alumnos --cov-report=html
```
