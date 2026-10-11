r"""Opcional: convierte data/historico.csv en una base SQLite para analizar en Power BI.

Se corre aparte del scraper:

    uv run --python 3.12 --with-requirements requirements.txt --no-project python a_sqlite.py

NO toca el scraper. Lee el CSV y escribe data/historico.db al lado. Se puede correr
las veces que haga falta: la base se reconstruye entera cada vez.

Escribe dos archivos con el MISMO contenido, porque cada uno sirve para algo:

    data/analisis.csv   para Power BI. Lo lee al doble clic, sin drivers.
    data/historico.db   para consultar en SQL con DB Browser for SQLite.

Por que los dos, y no solo la base: Power BI solo lee SQLite a traves de un driver
ODBC, que hay que instalar aparte y no siempre conecta (en la maquina donde se hizo
esto fallaba con 'HY000 connect failed'). El CSV no necesita nada.

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
# Lo escribe habilidades.py en cada corrida con ofertas nuevas: una fila por oferta y
# habilidad (id, habilidad, grupo). Solo cubre las ofertas que traen descripcion.
HABILIDADES = os.path.join('data', 'habilidades.csv')

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
    # Las ~20 formas de "empresa oculta" en una sola, para contar y agrupar empresas.
    df['empresa'] = df['company'].map(reporte.empresa_normalizada)
    df['empresa_confidencial'] = (df['empresa'] == reporte.CONFIDENCIAL).astype(int)
    puntuados = df['title'].fillna('').map(perfil.puntuar)
    df['puntaje'] = [p for p, _ in puntuados]
    df['terminos'] = [', '.join(t) for _, t in puntuados]
    df['nivel'] = df['title'].fillna('').map(perfil.nivel)
    # Para buscar por palabras en SQL: el LIKE de SQLite solo ignora mayusculas en letras
    # sin tilde, asi que '%analisis%' no encontraria "ANALISIS" escrito con tilde. Con
    # el titulo en minusculas y sin tildes, basta escribir la palabra igual.
    df['titulo_normalizado'] = df['title'].fillna('').map(perfil._norm)
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
        # Segunda tabla, ligada por id: "que habilidades pide el mercado" es la metrica
        # que el titulo solo no da. Si aun no hay descripciones, la tabla queda vacia
        # en vez de faltar, para que las consultas de consultas.sql no revienten.
        if os.path.exists(HABILIDADES):
            pedidas = pd.read_csv(HABILIDADES, dtype=str)
        else:
            pedidas = pd.DataFrame(columns=['id', 'habilidad', 'grupo'])
        pedidas.to_sql('habilidades', conexion, if_exists='replace', index=False)
        conexion.execute('CREATE INDEX IF NOT EXISTS idx_habilidad_id ON habilidades(id)')

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
     'SELECT empresa, COUNT(*) AS ofertas FROM ofertas '
     "WHERE empresa != '' AND empresa_confidencial = 0 GROUP BY empresa HAVING ofertas > 1 "
     'ORDER BY ofertas DESC LIMIT 5'),
]


if __name__ == '__main__':
    df, base = construir()
    print(f'[OK] {len(df)} ofertas, {len(df.columns)} columnas')
    print(f'     {PARA_BI}  <- para Power BI (Obtener datos > Texto/CSV)')
    print(f'     {base}  <- para consultar en SQL (DB Browser for SQLite);'
          ' consultas listas en consultas.sql')

    with sqlite3.connect(base) as conexion:
        for titulo, sql in CONSULTAS:
            print(f'\n--- {titulo}')
            resultado = pd.read_sql_query(sql, conexion)
            print(resultado.to_string(index=False) if len(resultado) else '   (sin datos)')
