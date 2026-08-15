@echo off
REM Ejecuta main.py en un entorno con Python 3.12 + jobspy gestionado por uv.
REM El Python 3.14 del sistema no sirve: jobspy pinea numpy==1.26.3, sin wheel para 3.14.
setlocal
pushd "%~dp0"
uv run --python 3.12 --with-requirements requirements.txt --no-project python main.py %*
popd
endlocal
