@echo off
REM Raspa Google Jobs y deja lo raspado en el buzon data/google_pendientes.csv.
REM
REM Son DOS entornos distintos a proposito:
REM   - Google necesita Selenium y Chrome, y vive en su propio proyecto con Poetry.
REM   - La ingesta corre aqui, con el mismo uv/Python 3.12 que el resto del scraper.
REM Mezclarlos obligaria a meter selenium en requirements.txt, que se resuelve en cada
REM corrida del reporte diario: si un dia no resolviera, se caeria el correo.
REM
REM No manda correo NI escribe el historico: deja las ofertas en el buzon y el reporte
REM diario de las 08:00 las recoge, las suma a su scrape y las reporta. Escribir el
REM historico aqui las marcaba como vistas antes de que nadie avisara, y no salian nunca.
REM Por eso esta tarea va ANTES que la del diario (07:30 vs 08:00).
setlocal
pushd "%~dp0"

set GOOGLE_DIR=..\..\Google Scrapper\Scrape_google_opencode
set CSV=%TEMP%\google_jobs_export.csv

if not exist "%GOOGLE_DIR%\pyproject.toml" (
    echo [ERROR] No se encuentra el scraper de Google en "%GOOGLE_DIR%"
    popd
    exit /b 1
)

REM Se borra el CSV de la corrida anterior ANTES de empezar. La ruta es fija, asi que si
REM el scraper muere sin escribir (la tarea lo mata por tiempo, Google bloquea), el
REM fichero viejo seguiria ahi: la ingesta lo tragaria, diria "0 nuevas" y saldria con 0.
REM Una caida total de Google se veria exactamente igual que un dia tranquilo.
if exist "%CSV%" del "%CSV%"

echo [1/2] Raspando Google Jobs...
pushd "%GOOGLE_DIR%"
poetry run python -m google_jobs_scraper --export "%CSV%"
set CODIGO=%ERRORLEVEL%
popd

REM Se sigue aunque Google devuelva error: puede haber muerto a mitad y aun asi haber
REM dejado el CSV con lo que alcanzo a raspar. Media corrida ingerida vale mas que nada.
if not exist "%CSV%" (
    echo [ERROR] Google no dejo ningun CSV en "%CSV%"
    popd
    exit /b 1
)
if not "%CODIGO%"=="0" echo [AVISO] Google salio con codigo %CODIGO%: se ingiere lo que haya

echo [2/2] Dejando en el buzon del diario...
uv run --python 3.12 --with-requirements requirements.txt --no-project python ingesta_google.py "%CSV%"
set CODIGO=%ERRORLEVEL%

REM Sin guardar el codigo aqui, el .cmd devuelve el de 'endlocal' y todo parece ir bien.
popd
endlocal & exit /b %CODIGO%
