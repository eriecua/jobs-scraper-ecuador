r"""Scraper de Multitrabajos (Bumeran Ecuador), con la misma forma de salida que computrabajo.py.

El HTML del sitio es un cascaron que se pinta en el cliente (ver TODO.md), pero la propia
web llama a una API JSON que responde con HTTP plano:

    POST https://www.multitrabajos.com/api/avisos/searchV2?pageSize=100&page=0&sort=RECIENTES
    x-site-id: BMEC
    {"filtros": [{"id": "localidad", "value": "ecuador|pichincha|quito"}], "query": "analista"}

Sin User-Agent de navegador completo devuelve cuerpo vacio. Los valores validos de los
filtros salen de GET /api/avisos/filtersV2 (campo idSemantico, no el id numerico).
"""
import math
import random
import re
import time
import unicodedata
from datetime import date, datetime

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import ubicaciones

URL_API = 'https://www.multitrabajos.com/api/avisos/searchV2'
URL_BASE = 'https://www.multitrabajos.com'

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
    'Accept-Language': 'es-EC,es;q=0.9',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Referer': 'https://www.multitrabajos.com/',
    'x-site-id': 'BMEC',
}

# Las de computrabajo.py mas las tres que esta API si trae y jobspy tambien usa.
COLUMNAS = ['id', 'site', 'title', 'company', 'location', 'date_posted', 'job_url', 'salary',
            'is_remote', 'job_type', 'description']

# La API acepta al menos 1000 por pagina (medido); 100 deja paginas pequenas y pocas.
OFERTAS_POR_PAGINA = 100

# Filtro dias_fecha_publicacion: (dias maximos que cubre, idSemantico). Se elige el
# primero que cubra dias_max; el recorte fino se hace despues con la fecha de cada oferta.
TRAMOS_FECHA = [
    (0, 'publicacion-hoy'),
    (1, 'publicacion-menor-a-2-dias'),
    (2, 'publicacion-menor-a-3-dias'),
    (3, 'publicacion-menor-a-4-dias'),
    (4, 'publicacion-menor-a-5-dias'),
    (5, 'publicacion-menor-a-6-dias'),
    (7, 'publicacion-menor-a-7-dias'),
    (15, 'publicacion-menor-a-15-dias'),
    (31, 'publicacion-menor-a-1-mes'),
]


def _slug(texto):
    """'Santo Domingo de los Tsachilas' -> 'santo-domingo-de-los-tsachilas'."""
    limpio = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode()
    limpio = re.sub(r'[^a-z0-9\s-]', ' ', limpio.lower())
    return '-'.join(limpio.split())


def _filtro_ubicacion(ubicacion):
    """Traduce 'Quito, Ecuador' al filtro de la API. Devuelve (filtro o None, reconocida).

    Se apoya en ubicaciones.normalizar(), la tabla unica de ciudades y provincias. Un valor
    invalido no da error: devuelve 0 ofertas, igual que Computrabajo.
    """
    if not ubicacion or _slug(ubicacion) == 'ecuador':
        return None, True
    ciudad, provincia = ubicaciones.normalizar(ubicacion)
    if ciudad and provincia:
        return {'id': 'localidad',
                'value': f'ecuador|{_slug(provincia)}|{_slug(ciudad)}'}, True
    if provincia:
        return {'id': 'provincia', 'value': f'ecuador|{_slug(provincia)}'}, True
    return None, False


def _filtro_fecha(dias_max):
    if dias_max is None:
        return None
    for tope, valor in TRAMOS_FECHA:
        if dias_max <= tope:
            return {'id': 'dias_fecha_publicacion', 'value': valor}
    return None  # mas de un mes: sin filtro, se recorta localmente


def _crear_sesion():
    """Sesion con reintentos y backoff ante 429 y 5xx. POST incluido: la busqueda es idempotente."""
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    reintentos = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'POST'],
    )
    sesion.mount('https://', HTTPAdapter(max_retries=reintentos))
    return sesion


def _fecha(texto):
    """'03-10-2026' (dd-mm-aaaa) -> date, o None."""
    try:
        return datetime.strptime(str(texto), '%d-%m-%Y').date()
    except (TypeError, ValueError):
        return None


def _url_oferta(aviso):
    """URL canonica de la ficha: /empleos/<titulo>[-<empresa>]-<id>.html.

    Es la que arma la propia web (makeFichaAvisoURL). El sitio resuelve por el id final,
    pero se usa la canonica para que el enlace no cambie de forma entre corridas.
    """
    partes = [_slug(aviso.get('titulo') or 'empleo')]
    if not aviso.get('confidencial') and aviso.get('empresa'):
        partes.append(_slug(aviso['empresa']))
    partes.append(str(aviso['id']))
    return f"{URL_BASE}/empleos/{'-'.join(p for p in partes if p)}.html"


def _a_oferta(aviso):
    publicada = _fecha(aviso.get('fechaPublicacion'))
    modalidad = (aviso.get('modalidadTrabajo') or '').strip().lower()
    return {
        'id': f"mt-{aviso['id']}",
        'site': 'multitrabajos',
        'title': aviso.get('titulo'),
        'company': 'Confidencial' if aviso.get('confidencial') else aviso.get('empresa'),
        'location': aviso.get('localizacion'),
        'date_posted': publicada.isoformat() if publicada else None,
        'job_url': _url_oferta(aviso),
        'salary': None,
        # 'Hibrido' no es remoto: solo cuenta la modalidad 100% remota.
        'is_remote': (modalidad == 'remoto') if modalidad else None,
        'job_type': aviso.get('tipoTrabajo'),
        # Viene gratis en la misma respuesta de la busqueda: es de donde salen las
        # habilidades que pide el puesto. historico.py la separa a descripciones.csv.
        'description': aviso.get('detalle'),
        '_dias': (date.today() - publicada).days if publicada else None,
    }


def _avisar_si_hay_drift(ofertas):
    """Avisa si la API dejo de mandar campos que siempre trae (renombrado silencioso)."""
    if not ofertas:
        return
    for campo in ('title', 'company', 'location', 'date_posted'):
        faltantes = sum(1 for o in ofertas if not o[campo])
        if faltantes > len(ofertas) / 2:
            print(f"   [AVISO] Posible cambio en la API de Multitrabajos: "
                  f"{faltantes}/{len(ofertas)} ofertas sin '{campo}'")


def scrape(termino='', ubicacion='Ecuador', resultados=100, dias_max=None,
           pais='ecuador', retraso=1):
    """Busca en Multitrabajos y devuelve un DataFrame con las columnas de COLUMNAS.

    Misma firma que computrabajo.scrape(). Solo existe para Ecuador (site BMEC).
    Las ofertas vienen ordenadas por recientes.
    """
    if str(pais).strip().lower() != 'ecuador':
        print(f'   [AVISO] multitrabajos solo cubre Ecuador, no {pais}')
        return pd.DataFrame(columns=COLUMNAS)

    filtros = []
    filtro_ubi, reconocida = _filtro_ubicacion(ubicacion)
    if not reconocida:
        print(f"   [AVISO] '{ubicacion}' no se reconoce como ciudad o provincia de Ecuador; "
              f"multitrabajos busca en todo el pais")
    if filtro_ubi:
        filtros.append(filtro_ubi)
    filtro_fecha = _filtro_fecha(dias_max)
    if filtro_fecha:
        filtros.append(filtro_fecha)

    sesion = _crear_sesion()
    cuerpo = {'filtros': filtros, 'query': termino or ''}
    por_pagina = min(OFERTAS_POR_PAGINA, max(1, resultados))
    max_paginas = max(1, math.ceil(resultados / por_pagina))
    ofertas = []

    for pagina in range(max_paginas):
        try:
            r = sesion.post(URL_API, json=cuerpo, timeout=20,
                            params={'pageSize': por_pagina, 'page': pagina,
                                    'sort': 'RECIENTES'})
            r.raise_for_status()
            datos = r.json()
        except Exception as e:
            if pagina == 0:
                raise  # nada obtenido: que buscador.py lo cuente como sitio fallido
            print(f'   [AVISO] multitrabajos pagina {pagina} fallo: {e}')
            print(f'   [AVISO] se conservan las {len(ofertas)} ofertas ya obtenidas')
            break

        lote = [_a_oferta(a) for a in datos.get('content') or []]
        _avisar_si_hay_drift(lote)
        ofertas.extend(lote)

        if not lote or (pagina + 1) * por_pagina >= (datos.get('total') or 0):
            break
        time.sleep(retraso + random.uniform(0, 0.5))

    if dias_max is not None:
        # Sin fecha legible se conserva, como en computrabajo.py.
        ofertas = [o for o in ofertas if o['_dias'] is None or o['_dias'] <= dias_max]

    df = pd.DataFrame(ofertas, columns=COLUMNAS + ['_dias'])
    df = df.drop(columns=['_dias']).drop_duplicates(subset=['id'])
    return df.head(resultados).reset_index(drop=True)
