r"""Historico incremental: que ofertas ya se vieron y cuales son nuevas."""
import os
import re
import unicodedata
from datetime import date, datetime, timedelta

import pandas as pd

import ubicaciones

RUTA = os.path.join('data', 'historico.csv')

# Pasado este plazo una oferta deja de bloquear: si la vuelven a publicar, reaparece.
DIAS_CADUCIDAD = 60

# Columnas de las que depende la deduplicacion. jobspy no siempre las devuelve todas.
COLUMNAS_CLAVE = ('id', 'company', 'title', 'location')
# date_posted tambien se persiste para conservar la fecha real del aviso, y ciudad/
# provincia para poder agrupar en Excel sin pelearse con las 19 formas de escribir
# 'location'. Ninguna de las dos entra en COLUMNAS_CLAVE: la deduplicacion no cambia.
COLUMNAS_HISTORICO = COLUMNAS_CLAVE + ('date_posted', 'ciudad', 'provincia')

# La descripcion (~1.500 caracteres por oferta) vive aparte, al lado del historico, y se
# liga por id: asi historico.csv sigue siendo ligero y en Power BI es una tabla relacionada.
NOMBRE_DESCRIPCIONES = 'descripciones.csv'


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


def _rellenar_ubicacion(df):
    """Deriva ciudad/provincia de 'location' donde falten.

    No hace falta migrar el CSV a mano: 'location' siempre se guardo, asi que el dato se
    reconstruye al leer y queda escrito en la siguiente pasada. Va ANTES de
    _asegurar_columnas a proposito; si fuera despues, esa ya las habria creado vacias y
    esto no dispararia nunca.

    Rellena fila a fila, no solo cuando falta la columna entera: al anadir una parroquia a
    ubicaciones.ALIAS, las filas viejas que quedaron sin ciudad se arreglan solas en la
    siguiente corrida. Las que de verdad no tienen ciudad (una ubicacion que solo nombra
    la provincia) se recalculan a vacio, que es lo correcto.
    """
    if 'location' not in df.columns or df.empty:
        return df

    df = df.copy()
    for columna in ('ciudad', 'provincia'):
        if columna not in df.columns:
            df[columna] = ''

    location = df['location'].fillna('')
    pendientes = (df['ciudad'].fillna('') == '') & (location != '')
    if not pendientes.any():
        return df

    pares = location[pendientes].map(ubicaciones.normalizar)
    df.loc[pendientes, 'ciudad'] = [c for c, _ in pares]
    df.loc[pendientes, 'provincia'] = [p for _, p in pares]
    return df


def _asegurar_columnas(df, columnas=COLUMNAS_HISTORICO):
    """Crea vacias las columnas que falten, avisando.

    buscar() descarta las columnas 100% vacias de cada sitio, asi que el DataFrame final
    no siempre trae las mismas. Sin esto, un sitio con datos pobres da un KeyError seco
    en vez de un mensaje.
    """
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        print(f"   [AVISO] faltan columnas {', '.join(faltantes)}: se tratan como vacias")
        df = df.assign(**{c: '' for c in faltantes})

    if 'date_posted' in df.columns:
        df['date_posted'] = pd.to_datetime(df['date_posted'], errors='coerce')
        df['date_posted'] = df['date_posted'].dt.strftime('%Y-%m-%d')
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
        viejo = _rellenar_ubicacion(viejo)
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
    descripciones = None
    if 'description' in nuevos.columns:
        descripciones = nuevos[['id', 'description']]
        nuevos = nuevos.drop(columns=['description'])

    # Escritura atomica: si algo revienta a mitad, el historico anterior sigue intacto.
    tmp = ruta + '.tmp'
    pd.concat([viejo, nuevos], ignore_index=True).to_csv(
        tmp, index=False, encoding='utf-8-sig'
    )

    try:
        os.replace(tmp, ruta)
    except PermissionError:
        # Windows bloquea el archivo mientras Excel o LibreOffice lo tienen abierto, y
        # os.replace revienta con un traceback crudo que no dice ni cual es el archivo.
        #
        # Se falla a proposito en vez de seguir: la tarea agendada corre sin que nadie
        # mire la consola, y solo una excepcion la deja marcada en rojo en el Programador
        # de tareas. Nada se pierde, porque al no escribirse el historico estas ofertas
        # siguen contando como no vistas y volveran a salir en la proxima corrida.
        os.remove(tmp)
        raise RuntimeError(
            f"no se pudo actualizar {ruta}: esta abierto en otra aplicacion"
        )

    # Despues del historico, no antes: si este no se pudo escribir, las ofertas vuelven en
    # la proxima corrida y sus descripciones se habrian guardado dos veces.
    if descripciones is not None:
        _guardar_descripciones(
            descripciones, os.path.join(os.path.dirname(ruta), NOMBRE_DESCRIPCIONES))

    return nuevos


def _guardar_descripciones(df, ruta):
    """Anade a descripciones.csv las de las ofertas nuevas que la traen. Nunca falla.

    Es un dato secundario: si el archivo esta abierto en Excel se avisa y se sigue, porque
    reventar aqui dejaria sin correo un historico que ya se escribio bien.
    """
    df = df.dropna(subset=['description'])
    # Una sola linea por descripcion: con saltos de linea dentro de un campo, Excel y
    # algunas importaciones de Power BI parten la fila. Para buscar habilidades da igual.
    df = df.assign(description=df['description'].astype(str)
                   .str.replace(r'\s+', ' ', regex=True).str.strip())
    df = df[df['description'] != '']
    if os.path.exists(ruta):
        # Un repost pasado el plazo de caducidad vuelve con el mismo id: no se duplica.
        ya = set(pd.read_csv(ruta, dtype=str, usecols=['id'])['id'])
        df = df[~df['id'].isin(ya)]
    if df.empty:
        return
    try:
        df.to_csv(ruta, mode='a', index=False, header=not os.path.exists(ruta),
                  encoding='utf-8-sig' if not os.path.exists(ruta) else 'utf-8')
    except PermissionError:
        print(f'[AVISO] no se pudo escribir {ruta} (abierto en otra aplicacion): '
              f'{len(df)} descripciones se pierden en esta corrida')


def guardar(df, etiqueta, output_dir='data'):
    """Guarda el DataFrame como CSV y devuelve la ruta."""
    os.makedirs(output_dir, exist_ok=True)
    nombre = re.sub(r'\s+', '_', re.sub(r'[^\w\s-]', '', etiqueta).strip()) or 'empleos'
    ruta = os.path.join(output_dir, f'{nombre}_{datetime.now():%Y%m%d_%H%M%S}.csv')
    # utf-8-sig para que Excel abra los acentos bien al doble clic.
    df.to_csv(ruta, index=False, encoding='utf-8-sig')
    print(f"[OK] Guardado: {ruta}")
    return ruta
