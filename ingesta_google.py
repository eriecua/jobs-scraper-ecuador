r"""Prepara para el correo diario las ofertas que raspo el scraper de Google Jobs.

Google vive en otro proyecto (Google Scrapper/Scrape_google_opencode) porque necesita
Selenium y Chrome, tarda ~10 minutos y se bloquea si se le insiste. Corre por su cuenta,
deja un CSV, y esto lo ingiere. Asi un fallo suyo no puede tumbar el correo diario, que
tarda segundos y es lo que de verdad importa.

    uv run --python 3.12 --with-requirements requirements.txt --no-project ^
        python ingesta_google.py ofertas_google.csv

Las ofertas acaban en el MISMO data/historico.csv que linkedin, indeed y computrabajo,
con site='google', y salen en el siguiente correo diario como cualquier otra novedad.
Pero no las escribe esto: las deja en un buzon y las escribe el diario. Ver abajo.

Por que esto NO escribe en el historico: historico.actualizar() marca las ofertas como
vistas en cuanto escribe, y ejecutar_diario() arma el correo con lo que devuelve SU
llamada, no leyendo el historico. Escribir aqui gastaba la novedad antes de que nadie
avisara: las 71 primeras ofertas de Google entraron al CSV y no salieron en ningun
correo.

Asi que esto deja las ofertas en un buzon (data/google_pendientes.csv) y el diario las
recoge, las suma a su propio scrape y hace UNA sola llamada a actualizar(). Una escritura,
una marca de visto, un correo. El buzon se vacia solo cuando el diario escribio bien; si
falla, las ofertas siguen ahi y entran en la corrida siguiente.
"""
import os
import sys

import pandas as pd

import ubicaciones

# Las que el historico necesita para deduplicar y agrupar. El CSV de Google trae ademas
# 'portal' (BeBee, Multitrabajos...), que se conserva tal cual: las columnas de mas
# sobreviven al concat y el CSV ya paso de 8 a 31 columnas por este camino.
COLUMNAS_MINIMAS = ('id', 'site', 'title', 'company', 'location', 'date_posted',
                    'job_url')

# Google se toma las ciudades como una sugerencia: buscando "Santo Domingo" devuelve
# ofertas de Republica Dominicana, y "Punta Cana" no es Ecuador por mucho que el titulo
# diga "Ingeniero Industrial". Se descartan aqui y no en el scraper porque la tabla que
# sabe que es Ecuador es ubicaciones.py, y vive de este lado.
DESCARTAR_FUERA_DE_ECUADOR = True

# Lo que se descarta son los paises que Google cuela de verdad, NO todo lo que
# ubicaciones.py no reconozca. La diferencia importa: CANTONES solo tiene 24 de los 221
# cantones del pais, asi que "no lo reconozco" y "no es Ecuador" son cosas distintas.
# Ya paso: la primera version tiraba Sangolqui (canton Ruminahui, Pichincha) por no
# estar en la tabla. Ante la duda entra: una oferta de mas se ve y se ignora, una de
# menos no se ve nunca.
PAISES_AJENOS = (
    'republica dominicana', 'punta cana', 'santo domingo este', 'santo domingo norte',
    'colombia', 'peru', 'venezuela', 'chile', 'argentina', 'mexico', 'panama',
    'bolivia', 'brasil', 'uruguay', 'paraguay', 'costa rica', 'guatemala',
    'honduras', 'nicaragua', 'salvador', 'cuba', 'puerto rico', 'espana',
    'estados unidos', 'united states', 'bogota', 'lima', 'medellin', 'caracas',
    'buenos aires', 'santiago de chile', 'ciudad de mexico',
)

# Buzon donde se dejan las ofertas hasta que el diario las recoja. Se vacia solo cuando
# ejecutar_diario() consiguio escribir el historico. Si el diario no corre en varios
# dias, esto se va acumulando a proposito: mejor repetir una oferta que perderla.
PENDIENTES = os.path.join('data', 'google_pendientes.csv')

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


def _solo_ecuador(df):
    """Quita las ofertas de otros paises, conservando lo dudoso.

    Se descarta por lista de paises ajenos, no por "ubicaciones.py no lo reconoce". Esa
    tabla tiene 24 cantones de los 221 que hay, asi que tratar lo desconocido como
    extranjero tira ofertas buenas: Sangolqui (canton Ruminahui) se perdio asi.

    Una ubicacion que la tabla SI reconoce se acepta sin mirar la lista, porque entonces
    ya consta que es de aqui. 'Remoto' entra por esa via, que es lo que se quiere: una
    oferta remota publicada en la busqueda de Ecuador interesa aunque no diga ciudad.
    """
    location = df['location'].fillna('').map(ubicaciones._norm)
    conocida = (df['ciudad'].fillna('') != '') | (df['provincia'].fillna('') != '')
    ajena = location.apply(lambda t: any(p in t for p in PAISES_AJENOS))

    descartadas = df[ajena & ~conocida]
    for _, fila in descartadas.iterrows():
        print(f"   [FUERA] {fila['location']!r}: no es Ecuador, se descarta "
              f"({fila['title'][:40]})")
    if len(descartadas):
        print(f"   {len(descartadas)} oferta(s) descartada(s) por estar fuera de Ecuador")

    sin_ubicar = df[~ajena & ~conocida]
    if len(sin_ubicar):
        # No se tiran: puede ser un canton que falte en la tabla. Se avisa para poder
        # anadirlo a ubicaciones.CANTONES si resulta que sale a menudo.
        ubis = ', '.join(sorted(set(sin_ubicar['location']))[:5])
        print(f"   [AVISO] {len(sin_ubicar)} oferta(s) con ubicacion no catalogada "
              f"({ubis}): entran igual")

    return df[~(ajena & ~conocida)]


def _encolar(df, ruta=PENDIENTES):
    """Anade las ofertas al buzon, sin repetir las que ya estuvieran esperando.

    Dedup por 'id' y no por clave empresa+titulo+ciudad: de eso ya se encarga
    historico.actualizar() cuando el diario lo recoja, y hacerlo dos veces solo esconderia
    ofertas distintas que comparten titulo. Aqui basta con que dos corridas de Google
    seguidas no dupliquen la misma fila.
    """
    os.makedirs(os.path.dirname(ruta), exist_ok=True)

    if os.path.exists(ruta):
        previo = pd.read_csv(ruta, dtype=str).fillna('')
        df = pd.concat([previo, df], ignore_index=True)
        df = df[~df['id'].duplicated(keep='first')]

    # Atomica, como historico.actualizar: si revienta a medias, el buzon anterior queda
    # intacto y no se pierde lo que ya esperaba.
    tmp = ruta + '.tmp'
    df.to_csv(tmp, index=False, encoding='utf-8-sig')
    try:
        os.replace(tmp, ruta)
    except PermissionError:
        os.remove(tmp)
        raise RuntimeError(f"no se pudo escribir {ruta}: esta abierto en otra aplicacion")
    return df


def ingerir(ruta_csv, ruta_buzon=PENDIENTES):
    """Lee el CSV de Google, lo normaliza y lo deja en el buzon del diario.

    NO escribe en el historico: quien decide que es nuevo, y quien lo reporta, es
    ejecutar_diario(). Devuelve el DataFrame completo que quedo esperando.
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

    if DESCARTAR_FUERA_DE_ECUADOR:
        df = _solo_ecuador(df)
        if df.empty:
            print('[AVISO] Ninguna oferta era de Ecuador: no hay nada que ingerir')
            return df

    esperando = _encolar(df, ruta_buzon)
    print(f'[OK] {len(df)} ofertas al buzon ({len(esperando)} esperando al diario en '
          f'{ruta_buzon})')
    return esperando


def main():
    if len(sys.argv) < 2:
        print('Uso: python ingesta_google.py <csv de Google> [buzon.csv]',
              file=sys.stderr)
        return EXIT_SIN_ARCHIVO

    ruta_csv = sys.argv[1]
    ruta_buzon = sys.argv[2] if len(sys.argv) > 2 else PENDIENTES

    try:
        ingerir(ruta_csv, ruta_buzon)
    except FileNotFoundError:
        print(f'[ERROR] No existe {ruta_csv}. Corre el scraper de Google primero.',
              file=sys.stderr)
        return EXIT_SIN_ARCHIVO
    except RuntimeError as fallo:
        # _encolar() avisa asi cuando no puede escribir el buzon porque esta abierto en
        # Excel. Nada se pierde: el scraper de Google volvera a traerlas manana, y lo que
        # ya esperaba en el buzon sigue intacto porque la escritura es atomica.
        print(f'[ERROR] {fallo}', file=sys.stderr)
        return EXIT_ESCRITURA_FALLO

    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
