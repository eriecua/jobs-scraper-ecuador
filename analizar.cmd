@echo off
REM Prepara lo raspado para analizarlo: data\historico.db (SQL, ver consultas.sql) y
REM data\analisis.csv (Power BI / Excel). No raspa nada: lee data\historico.csv.
setlocal
pushd "%~dp0"
uv run --python 3.12 --with-requirements requirements.txt --no-project python a_sqlite.py %*
set CODIGO=%ERRORLEVEL%
popd
endlocal & exit /b %CODIGO%
