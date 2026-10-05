@echo off
REM Pruebas sin red (tests\). Mismo entorno que scrap.cmd, mas pytest, que solo hace falta
REM aqui y por eso no va en requirements.txt.
setlocal
pushd "%~dp0"
uv run --python 3.12 --with-requirements requirements.txt --with pytest --no-project python -m pytest tests -q %*
set CODIGO=%ERRORLEVEL%
popd
endlocal & exit /b %CODIGO%
