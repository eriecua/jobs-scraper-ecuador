r"""MVP: convierte data/historico.csv en una base SQLite para analizar en Power BI.

    .\scrap.cmd --help          (no, esto se corre aparte:)
    uv run --python 3.12 --with-requirements requirements.txt --no-project python a_sqlite.py

NO toca el scraper. Lee el CSV y escribe data/historico.db al lado. Se puede correr
las veces que haga falta: la base se reconstruye entera cada vez.

Escribe dos archivos con el MISMO contenido, porque cada uno sirve para algo:

    data/analisis.csv   para Power BI. Lo lee al doble clic, sin drivers.
    data/historico.db   para consultar en SQL con DB Browser for SQLite.

Por que los dos, y no solo la base: en esta maquina el ODBC de SQLite NO funciona.
Los tres drivers estan instalados y sus DLL existen, pero cualquier conexion muere
con 'HY000 connect failed', tambien desde PowerShell, asi que no es cosa de Power BI.
Se probaron las tres variantes del driver y rutas con y sin espacios: todas fallan
igual. Antes de volver a intentarlo por ahi, comprobar si falta el runtime de Visual
C++ o si el instalador metio un DLL de 32 bits registrado como de 64.

Lo que de verdad aporta esto sobre el historico.csv de siempre no es el formato: son
las columnas derivadas -familia, puntaje, nivel, motivo_exclusion-, que en Power BI
son segmentadores sin escribir una medida DAX. Y eso ya lo da el CSV.
"""
import os
import sqlite3

import pandas as pd

import perfil
import reporte

CSV = os.path.join('data', 'historico.csv')
BASE = os.path.join('data', 'historico.db')
PARA_BI = os.path.join('data', 'analisis.csv')

# Solo las columnas con datos de verdad. Las medidas sobre 392 ofertas reales dicen que
# job_level esta al 0%, min_amount/max_amount al 3% y company_industry al 3%: meterlas
# solo invita a construir un grafico encima de nada.
COLUMNAS = ['id', 'site', 'job_url', 'title', 'company', 'location', 'ciudad',
            'provincia', 'is_remote', 'date_posted', 'job_type', 'salary',
            'busqueda', 'visto_primera_vez']


def construir(csv=CSV, base=BASE):
    if not os.path.exists(csv):
        raise SystemExit(f'No existe {csv}. Corre el scraper primero.')

    df = pd.read_csv(csv, dtype=str)
    if df.empty:
        raise SystemExit(f'{csv} esta vacio: no hay nada que convertir.')

    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = ''
    df = df[COLUMNAS].copy()

    # Las derivadas son el motivo de que esto valga mas que importar el CSV a pelo:
    # en Power BI se convierten en segmentadores sin escribir una sola medida DAX.
    df['familia'] = df['title'].fillna('').map(reporte.familia_puesto)
    puntuados = df['title'].fillna('').map(perfil.puntuar)
    df['puntaje'] = [p for p, _ in puntuados]
    df['terminos'] = [', '.join(t) for _, t in puntuados]
    df['nivel'] = df['title'].fillna('').map(perfil.nivel)
    df['es_oferta_real'] = df['title'].fillna('').map(reporte.es_oferta_real).astype(int)
    df['motivo_exclusion'] = [perfil.excluir(t, f) or ''
                              for t, f in zip(df['title'].fillna(''), df['familia'])]

    # Fechas como texto ISO: es lo unico que SQLite y Power BI interpretan igual sin
    # discutir de zonas horarias.
    for columna in ('date_posted', 'visto_primera_vez'):
        df[columna] = pd.to_datetime(df[columna], errors='coerce').dt.strftime('%Y-%m-%d')

    # Power BI lee este CSV al doble clic, sin drivers. Se escribe siempre porque el
    # ODBC de SQLite fallo en esta maquina (HY000 connect failed con los tres drivers,
    # tambien fuera de Power BI), y las columnas derivadas son el 90% del valor.
    df.to_csv(PARA_BI, index=False, encoding='utf-8-sig')

    with sqlite3.connect(base) as conexion:
        df.to_sql('ofertas', conexion, if_exists='replace', index=False)
        # Aqui esta la idea de fondo: la deduplicacion deja de ser codigo y pasa a ser
        # una restriccion. Hoy solo documenta la clave; cuando historico.py escriba
        # aqui, un INSERT OR IGNORE hara solo el trabajo de _clave() y _vigentes().
        conexion.execute('CREATE INDEX IF NOT EXISTS idx_clave '
                         'ON ofertas(company, title, ciudad)')
        conexion.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON ofertas(date_posted)')

    return df, base


CONSULTAS = [
    ('Ofertas por ciudad',
     'SELECT ciudad, COUNT(*) AS ofertas FROM ofertas '
     "WHERE ciudad != '' GROUP BY ciudad ORDER BY ofertas DESC LIMIT 6"),
    ('Que estan buscando',
     'SELECT familia, COUNT(*) AS ofertas FROM ofertas '
     'GROUP BY familia ORDER BY ofertas DESC LIMIT 6'),
    ('Las que mas te encajan',
     'SELECT puntaje, title, company, ciudad FROM ofertas '
     'WHERE puntaje > 0 ORDER BY puntaje DESC LIMIT 5'),
    ('Empresas que mas repiten',
     'SELECT company, COUNT(*) AS ofertas FROM ofertas '
     "WHERE company != '' GROUP BY company HAVING ofertas > 1 "
     'ORDER BY ofertas DESC LIMIT 5'),
]


if __name__ == '__main__':
    df, base = construir()
    print(f'[OK] {len(df)} ofertas, {len(df.columns)} columnas')
    print(f'     {PARA_BI}  <- para Power BI (Obtener datos > Texto/CSV)')
    print(f'     {base}  <- para consultar en SQL (DB Browser for SQLite)')

    with sqlite3.connect(base) as conexion:
        for titulo, sql in CONSULTAS:
            print(f'\n--- {titulo}')
            resultado = pd.read_sql_query(sql, conexion)
            print(resultado.to_string(index=False) if len(resultado) else '   (sin datos)')
