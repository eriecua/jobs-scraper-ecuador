r"""Historico incremental: que ofertas ya se vieron y cuales son nuevas."""
import os
import re
import unicodedata
from datetime import date, datetime, timedelta

import pandas as pd

RUTA = os.path.join('data', 'historico.csv')

# Pasado este plazo una oferta deja de bloquear: si la vuelven a publicar, reaparece.
DIAS_CADUCIDAD = 60

# Columnas de las que depende la deduplicacion. jobspy no siempre las devuelve todas.
COLUMNAS_CLAVE = ('id', 'company', 'title', 'location')


def _clave(df):
    """Clave empresa+titulo+ciudad normalizada, para cazar el mismo empleo entre sitios.

    El mismo puesto publicado en LinkedIn y en Indeed llega con 'id' distinto, asi que
    el id solo no basta. Se calcula al vuelo, no se guarda en el CSV.

    La ubicacion va en la clave porque sin ella la misma vacante en Quito y en Guayaquil
    contaba como una sola. Pero solo la ciudad: cada sitio la escribe distinto
    ('Quito, Pichincha, Ecuador' en LinkedIn, 'Quito, Pichincha' en Computrabajo) y la
    oferta saldria repetida.
    """
    def limpiar(serie):
        texto = serie.fillna('').astype(str).str.lower()
        texto = texto.map(
            lambda s: unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
        )
        return texto.str.replace(r'\s+', ' ', regex=True).str.strip()

    ciudad = limpiar(df['location'].fillna('').astype(str).str.split(',').str[0])
    return limpiar(df['company']) + '|' + limpiar(df['title']) + '|' + ciudad


def _asegurar_columnas(df, columnas=COLUMNAS_CLAVE):
    """Crea vacias las columnas que falten, avisando.

    buscar() descarta las columnas 100% vacias de cada sitio, asi que el DataFrame final
    no siempre trae las mismas. Sin esto, un sitio con datos pobres da un KeyError seco
    en vez de un mensaje.
    """
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        print(f"   [AVISO] faltan columnas {', '.join(faltantes)}: se tratan como vacias")
        df = df.assign(**{c: '' for c in faltantes})
    return df


def _vigentes(viejo, dias=DIAS_CADUCIDAD):
    """Filas del historico lo bastante recientes como para seguir bloqueando duplicados.

    Las que no tienen fecha (historicos escritos antes de este cambio) se conservan: mejor
    callar una oferta repetida que inundar el correo la primera vez que se corre esto.
    """
    if 'visto_primera_vez' not in viejo.columns:
        return viejo

    corte = date.today() - timedelta(days=dias)
    visto = pd.to_datetime(viejo['visto_primera_vez'], errors='coerce')
    return viejo[visto.isna() | (visto.dt.date >= corte)]


def actualizar(df, busqueda, ruta=RUTA):
    """Anade al historico las filas no vistas antes y devuelve solo esas."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)

    if os.path.exists(ruta):
        # dtype=str es clave: sin forzarlo pandas puede leer 'id' como entero en una
        # corrida y como texto en otra, y la comparacion dejaria pasar duplicados.
        viejo = pd.read_csv(ruta, dtype=str)
    else:
        viejo = pd.DataFrame()

    df = _asegurar_columnas(df.copy())
    df['id'] = df['id'].astype(str)

    if viejo.empty:
        nuevos = df
    else:
        viejo = _asegurar_columnas(viejo)
        # Solo bloquea lo visto hace poco: pasado el plazo, un repost vuelve a ser noticia.
        vigente = _vigentes(viejo)
        ids = set(vigente['id'])
        claves = set(_clave(vigente))
        nuevos = df[~df['id'].isin(ids) & ~_clave(df).isin(claves)]

    # Dos ofertas identicas dentro de la misma corrida (una por sitio) cuentan como una.
    nuevos = nuevos[~_clave(nuevos).duplicated()]

    if nuevos.empty:
        return nuevos

    nuevos = nuevos.assign(busqueda=busqueda, visto_primera_vez=date.today().isoformat())

    # Escritura atomica: si algo revienta a mitad, el historico anterior sigue intacto.
    tmp = ruta + '.tmp'
    pd.concat([viejo, nuevos], ignore_index=True).to_csv(
        tmp, index=False, encoding='utf-8-sig'
    )
    os.replace(tmp, ruta)
    return nuevos


def guardar(df, etiqueta, output_dir='data'):
    """Guarda el DataFrame como CSV y devuelve la ruta."""
    os.makedirs(output_dir, exist_ok=True)
    nombre = re.sub(r'\s+', '_', re.sub(r'[^\w\s-]', '', etiqueta).strip()) or 'empleos'
    ruta = os.path.join(output_dir, f'{nombre}_{datetime.now():%Y%m%d_%H%M%S}.csv')
    # utf-8-sig para que Excel abra los acentos bien al doble clic.
    df.to_csv(ruta, index=False, encoding='utf-8-sig')
    print(f"[OK] Guardado: {ruta}")
    return ruta
