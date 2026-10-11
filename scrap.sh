#!/bin/sh
# Equivalente de scrap.cmd para Mac y Linux: corre main.py con Python 3.12 + jobspy
# gestionado por uv, sin tocar el Python del sistema.
#
#   ./scrap.sh "Data Analyst" --ubicacion "Quito, Ecuador"
#
# Para el reporte diario por correo, scrap_diario.sh (lee el .env).

# Desde la carpeta del script, como el pushd de scrap.cmd: si no, requirements.txt y
# data/ se buscarian donde estes parado.
cd "$(dirname "$0")" || exit 1

# exec: el proceso pasa a ser uv, asi que su codigo de salida (0/1/2/3) llega intacto a
# quien lo lance (cron incluido). "$@" con comillas deja "Data Analyst" como UN argumento.
exec uv run --python 3.12 --with-requirements requirements.txt --no-project python main.py "$@"
