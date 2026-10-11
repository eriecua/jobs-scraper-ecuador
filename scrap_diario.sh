#!/bin/sh
# Reporte diario por correo en Mac y Linux. Equivalente de scrap_diario.cmd: pensado para
# cron. Lee las credenciales de .env (no versionado) con lineas CLAVE=valor.
cd "$(dirname "$0")" || exit 1

if [ ! -f .env ]; then
    echo "[ERROR] Falta .env con GMAIL_USUARIO, GMAIL_APP_PASSWORD y CORREO_DESTINO" >&2
    exit 2
fi

# Linea a linea y no con '. ./.env': Google muestra la contrasena de aplicacion con
# espacios ("abcd efgh ijkl mnop") y, sin comillas, sh ejecutaria 'efgh' como comando.
# Se quitan ademas el \r de un .env guardado en Windows y el BOM de Notepad, que
# dejarian la credencial con un caracter invisible y Gmail la rechazaria. Se limpia la
# linea ENTERA antes de mirarla: una linea en blanco de Windows es "\r", no "", y un
# export invalido aborta el script (en sh es un error fatal).
BOM=$(printf '\357\273\277')
while IFS= read -r linea || [ -n "$linea" ]; do
    linea=$(printf '%s' "$linea" | tr -d '\r')
    linea=${linea#"$BOM"}
    case "$linea" in
        \#*) continue ;;
        [A-Za-z_]*=*) export "$linea" ;;
    esac
done < .env

exec uv run --python 3.12 --with-requirements requirements.txt --no-project python main.py --diario
