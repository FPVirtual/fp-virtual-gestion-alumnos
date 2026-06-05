# Dockerfile mínimo para gestion-alumnos v0.3
# Uso:
#   docker build -t gestion-alumnos .
#   docker run --rm -v $(pwd)/.env.produccion:/app/.env:ro gestion-alumnos

FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias de runtime
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copiar solo el paquete y scripts necesarios
COPY gestion_alumnos/ ./gestion_alumnos/
COPY scripts/ ./scripts/
COPY .env.example .

# Crear usuario no root
RUN useradd appuser && chown -R appuser /app
USER appuser

# El comando por defecto muestra la ayuda.
# Sobrescribir en ejecución con el comando deseado, p. ej.:
#   docker run ... gestion-alumnos python -m gestion_alumnos sync --env-file /app/.env
CMD ["python", "-m", "gestion_alumnos", "--help"]
