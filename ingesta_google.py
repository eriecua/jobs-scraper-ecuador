r"""Mete en el historico las ofertas que raspo el scraper de Google Jobs.

Google vive en otro proyecto (Google Scrapper/Scrape_google_opencode) porque necesita
Selenium y Chrome, tarda ~10 minutos y se bloquea si se le insiste. Corre por su cuenta,
deja un CSV, y esto lo ingiere. Asi un fallo suyo no puede tumbar el correo diario, que
tarda segundos y es lo que de verdad importa.

    uv run --python 3.12 --with-requirements requirements.txt --no-project ^
        python ingesta_google.py ofertas_google.csv

Las ofertas entran al MISMO data/historico.csv que linkedin, indeed y computrabajo, con
site='google', y salen en el siguiente correo diario como cualquier otra novedad.

Por que no manda el correo el mismo: historico.actualizar() marca las ofertas como vistas
en cuanto escribe. Si esto avisara por su cuenta, habria dos correos; y si escribiera sin
avisar a nadie, esas ofertas quedarian marcadas y no saldrian NUNCA. Escribir aqui y
dejar que el diario las reporte es lo unico que las hace aparecer una vez y solo una.
"""
import sys

import pandas as pd

import historico
import ubicaciones

# Las que el historico necesita para deduplicar y agrupar. El CSV de Google trae ademas
# 'portal' (BeBee, Multitrabajos...), que se conserva tal cual: las columnas de mas
# sobreviven al concat y el CSV ya paso de 8 a 31 columnas por este camino.
COLUMNAS_MINIMAS = ('id', 'site', 'title', 'company', 'location', 'date_posted',
                    'job_url')

EXIT_OK = 0
EXIT_SIN_ARCHIVO = 1
EXIT_ESCRITURA_FALLO = 3  # mismo codigo que main.py: el historico estaba bloqueado


def _validar(df):
    """Comprueba lo que el historico da por sentado. Devuelve lista de problemas."""
    problemas = []

    faltan = [c for c in COLUMNAS_MINIMAS if c not in df.columns]
    if faltan:
        problemas.append(f"faltan columnas: {', '.join(faltan)}")

    if 'location' in df.columns:
        # La deduplicacion saca la ciudad con location.split(',')[0]. Si el portal sigue
        # pegado ('Quito - a traves de BeBee'), la clave queda 'quito a traves de bebee'
        # y NO cruza con la misma oferta vista por LinkedIn, que da 'quito'. No da error:
        # simplemente entran duplicados. Por eso se comprueba aqui y se para.
        sucias = df['location'].fillna('').str.contains(r'[•·]|a trav[eé]s de', case=False)
        if sucias.any():
            problemas.append(
                f"{sucias.sum()} ubicaciones traen el portal pegado "
                f"(ej: {df.loc[sucias, 'location'].iloc[0]!r}): la deduplicacion fallaria"
            )

    return problemas


def ingerir(ruta_csv, ruta_historico=historico.RUTA):
    """Lee el CSV de Google y anade al historico lo que no se hubiera visto ya.

    Devuelve el DataFrame de ofertas nuevas (vacio si no habia ninguna).
    """
    df = pd.read_csv(ruta_csv, dtype=str).fillna('')
    print(f"[LEIDO] {len(df)} ofertas en {ruta_csv}")

    if df.empty:
        print('[OK] El CSV no traia ofertas: no hay nada que ingerir')
        return df

    problemas = _validar(df)
    if problemas:
        for p in problemas:
            print(f'[ERROR] {p}', file=sys.stderr)
        raise SystemExit(
            'El CSV no cumple lo que el historico espera. Se para antes de escribir.'
        )

    # ciudad/provincia con la misma tabla que usan los otros tres sitios. Es la unica
    # forma de que 'Quito' de Google y 'Quito, Pichincha, Ecuador' de LinkedIn se agrupen
    # juntos en el correo.
    pares = df['location'].map(ubicaciones.normalizar)
    df['ciudad'] = [c for c, _ in pares]
    df['provincia'] = [p for _, p in pares]

    nuevos = historico.actualizar(df, 'google', ruta=ruta_historico)
    print(f'[OK] {len(df)} ofertas ({len(nuevos)} nuevas desde la ultima corrida)')
    return nuevos


def main():
    if len(sys.argv) < 2:
        print('Uso: python ingesta_google.py <csv de Google> [historico.csv]',
              file=sys.stderr)
        return EXIT_SIN_ARCHIVO

    ruta_csv = sys.argv[1]
    ruta_historico = sys.argv[2] if len(sys.argv) > 2 else historico.RUTA

    try:
        ingerir(ruta_csv, ruta_historico)
    except FileNotFoundError:
        print(f'[ERROR] No existe {ruta_csv}. Corre el scraper de Google primero.',
              file=sys.stderr)
        return EXIT_SIN_ARCHIVO
    except RuntimeError as fallo:
        # historico.actualizar() avisa asi cuando no puede escribir el CSV porque esta
        # abierto en Excel. Nada se pierde: al no escribirse, esas ofertas siguen
        # contando como no vistas y volveran a salir en la proxima corrida.
        print(f'[ERROR] {fallo}', file=sys.stderr)
        return EXIT_ESCRITURA_FALLO

    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
