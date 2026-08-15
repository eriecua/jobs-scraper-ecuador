@echo off
REM Abre la ventana para lanzar busquedas sin escribir el comando.
REM Mismo entorno que scrap.cmd: Python 3.12 gestionado por uv.
setlocal
pushd "%~dp0"
uv run --python 3.12 --with-requirements requirements.txt --no-project python ventana.py
popd
endlocal
