@echo off
REM Reporte diario por correo. Pensado para el Programador de tareas de Windows.
REM Lee las credenciales de .env (no versionado) con lineas CLAVE=valor.
setlocal
pushd "%~dp0"

if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
) else (
    echo [ERROR] Falta .env con GMAIL_USUARIO, GMAIL_APP_PASSWORD y CORREO_DESTINO
    popd
    exit /b 2
)

uv run --python 3.12 --with-requirements requirements.txt --no-project python main.py --diario
set CODIGO=%ERRORLEVEL%

popd
endlocal & exit /b %CODIGO%
