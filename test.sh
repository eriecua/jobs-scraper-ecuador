#!/bin/sh
# Pruebas sin red (tests/) en Mac y Linux. Equivalente de test.cmd: mismo entorno que
# scrap.sh, mas pytest, que solo hace falta aqui y por eso no va en requirements.txt.
#
#   ./test.sh            solo las de sin red
#   ./test.sh -m vivo    solo las de humo contra los sitios reales
cd "$(dirname "$0")" || exit 1
exec uv run --python 3.12 --with-requirements requirements.txt --with pytest --no-project python -m pytest tests -q "$@"
