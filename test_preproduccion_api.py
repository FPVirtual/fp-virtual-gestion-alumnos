"""Script para probar la conexión API de Moodle en preproducción.

Uso:
    export MOODLE_PRE_URL=https://redestel.fpvirtualaragon.es/webservice/rest/server.php
    export MOODLE_PRE_TOKEN=49019fdf2e50b5faf71d9ec1a25b6b6a
    python test_preproduccion_api.py
"""

import os
import sys

import requests


def check_env():
    url = os.environ.get("MOODLE_PRE_URL")
    token = os.environ.get("MOODLE_PRE_TOKEN")
    if not url or not token:
        print("Faltan variables de entorno MOODLE_PRE_URL y/o MOODLE_PRE_TOKEN")
        sys.exit(1)
    return url, token


def call(url: str, token: str, wsfunction: str, params: dict | None = None, timeout: int = 60) -> dict | list | None:
    data = {
        "wstoken": token,
        "wsfunction": wsfunction,
        "moodlewsrestformat": "json",
    }
    if params:
        data.update(params)
    try:
        response = requests.post(url, data=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and "exception" in result:
            print(f"\n[ERROR API] {wsfunction}: {result.get('message')}")
            print(f"            errorcode: {result.get('errorcode')}")
            return result
        return result
    except requests.exceptions.Timeout:
        print(f"\n[TIMEOUT] {wsfunction} no respondió en {timeout}s")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR RED] {wsfunction}: {e}")
        return None


def main():
    url, token = check_env()
    print(f"URL: {url}")
    print(f"Token: {token[:8]}...")

    # 1. Información del sitio (valida token)
    print("\n[1] core_webservice_get_site_info")
    site_info = call(url, token, "core_webservice_get_site_info")
    if isinstance(site_info, dict) and "sitename" in site_info:
        print(f"  sitename: {site_info.get('sitename')}")
        print(f"  siteurl: {site_info.get('siteurl')}")
        print(f"  user: {site_info.get('username')} (id={site_info.get('userid')})")
        print(f"  functions: {len(site_info.get('functions', []))}")
    else:
        print(f"  Respuesta inesperada: {site_info}")
        return

    # 2. Datos del usuario propietario del token
    print("\n[2] core_user_get_users_by_field (username=api_manager)")
    user = call(url, token, "core_user_get_users_by_field", {
        "field": "username",
        "values[0]": "api_manager",
    })
    if isinstance(user, list) and user:
        print(f"  id: {user[0].get('id')}")
        print(f"  username: {user[0].get('username')}")
        print(f"  fullname: {user[0].get('fullname')}")
        print(f"  email: {user[0].get('email')}")

    # 3. Buscar un usuario (función usada por el repositorio)
    print("\n[3] core_user_get_users (búsqueda por username=api_manager)")
    users_search = call(url, token, "core_user_get_users", {
        "criteria[0][key]": "username",
        "criteria[0][value]": "api_manager",
    })
    if isinstance(users_search, dict) and "users" in users_search:
        print(f"  Encontrados: {len(users_search['users'])}")

    # 4. Cursos del usuario (función usada por el repositorio)
    print("\n[4] core_enrol_get_users_courses (userid=23754)")
    courses = call(url, token, "core_enrol_get_users_courses", {"userid": 23754})
    if isinstance(courses, list):
        print(f"  Total cursos matriculados: {len(courses)}")
        for c in courses[:5]:
            print(f"    - {c.get('id')}: {c.get('shortname')}")

    # 5. Listar cursos (puede ser lento en preproducción)
    print("\n[5] core_course_get_courses (timeout extendido a 120s)")
    all_courses = call(url, token, "core_course_get_courses", timeout=120)
    if isinstance(all_courses, list):
        print(f"  Total cursos en Moodle: {len(all_courses)}")
        for c in all_courses[:3]:
            print(f"    - {c.get('id')}: {c.get('shortname')} ({c.get('fullname')})")
        if len(all_courses) > 3:
            print(f"    ... y {len(all_courses) - 3} más")

    # 6. Funciones disponibles para este token
    print("\n[6] Funciones del servicio web habilitadas para este token")
    functions = site_info.get("functions", [])
    print(f"  Total: {len(functions)}")
    for f in functions:
        print(f"    - {f.get('name')} (v{f.get('version')})")


if __name__ == "__main__":
    main()
