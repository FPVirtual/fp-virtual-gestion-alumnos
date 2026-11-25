# Imagen PHP para tests del plugin: parte de una imagen con las extensiones
# que requiere Moodle (moodlehq/moodle-php-apache o derivada) y añade los
# locales que exige el entorno PHPUnit de Moodle.
ARG BASE_IMAGE=moodlehq/moodle-php-apache:8.2
FROM ${BASE_IMAGE}
RUN localedef -i en_AU -f UTF-8 en_AU.UTF-8 \
 && localedef -i es_ES -f UTF-8 es_ES.UTF-8 \
 && git config --system --add safe.directory '*'
