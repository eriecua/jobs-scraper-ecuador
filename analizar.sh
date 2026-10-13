#!/bin/sh
# Equivalente de analizar.cmd para Mac y Linux: prepara data/historico.db (SQL, ver
# consultas.sql) y data/analisis.csv (Power BI / Excel). Lee data/historico.csv.
cd "$(dirname "$0")" || exit 1
exec uv run --python 3.12 --with-requirements requirements.txt --no-project python a_sqlite.py "$@"
