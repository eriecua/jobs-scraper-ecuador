r"""Scraper de Computrabajo, con la misma forma de salida que jobspy.

jobspy no soporta Computrabajo, asi que este modulo raspa el HTML por su cuenta y
devuelve un DataFrame con las columnas que espera main.py (id, site, title, company,
location, date_posted, job_url), para que se pueda concatenar con LinkedIn e Indeed sin
tratarlo como un caso especial mas alla de la llamada.

Promovido desde legacy/scraper_computrabajo.py, que seguia funcionando.
"""
import math
import random
import re
import time
import unicodedata
from datetime import date, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
    'Accept-Language': 'es-EC,es;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Columnas que se devuelven siempre, incluso sin resultados, para que un DataFrame vacio
# no reviente en el concat ni en la deduplicacion de main.py.
COLUMNAS = ['id', 'site', 'title', 'company', 'location', 'date_posted', 'job_url', 'salary']

DOMINIOS = {
    'ec': 'ec.computrabajo.com', 'co': 'co.computrabajo.com', 'mx': 'mx.computrabajo.com',
    'pe': 'pe.computrabajo.com', 'ar': 'ar.computrabajo.com', 'cl': 'cl.computrabajo.com',
    'bo': 'bo.computrabajo.com', 'uy': 'uy.computrabajo.com', 'pa': 'pa.computrabajo.com',
    'do': 'do.computrabajo.com',
}

# main.py habla de paises como 'ecuador' (lo que pide Indeed); aqui son codigos de dos letras.
PAIS_A_CODIGO = {
    'ecuador': 'ec', 'colombia': 'co', 'mexico': 'mx', 'peru': 'pe', 'argentina': 'ar',
    'chile': 'cl', 'bolivia': 'bo', 'uruguay': 'uy', 'panama': 'pa',
    'dominican republic': 'do',
}

# Computrabajo no acepta "Quito, Ecuador": la ciudad va en la ruta como
# <provincia>-en-<ciudad>. Sin una entrada aqui, la URL devuelve 200 con cero ofertas.
SLUGS_UBICACION = {
    'quito': 'pichincha-en-quito',
    'guayaquil': 'guayas-en-guayaquil',
    'santo domingo': 'santo-domingo-de-los-tsachilas',
    'santo domingo de los tsachilas': 'santo-domingo-de-los-tsachilas',
    'cuenca': 'azuay-en-cuenca',
    'ambato': 'tungurahua-en-ambato',
    'manta': 'manabi-en-manta',
    'machala': 'el-oro-en-machala',
    'loja': 'loja-en-loja',
    'ibarra': 'imbabura-en-ibarra',
    'riobamba': 'chimborazo-en-riobamba',
    'esmeraldas': 'esmeraldas-en-esmeraldas',
    'portoviejo': 'manabi-en-portoviejo',
    'duran': 'guayas-en-duran',
    # El pais entero no lleva sufijo de provincia.
    'ecuador': '',
}

OFERTAS_POR_PAGINA = 20

# Computrabajo NO tiene pagina de "todo el pais": /empleos, /trabajo y /ofertas-de-trabajo
# redirigen a la portada, y /empleos-en-ecuador responde 200 con cero ofertas. Para buscar
# en todo Ecuador hay que recorrer las provincias una por una. La pagina de una provincia
# ya incluye todas sus ciudades.
PROVINCIAS_EC = [
    'pichincha',
    'guayas',
    'azuay',
    'manabi',
    'tungurahua',
    'el-oro',
    'los-rios',
    'santo-domingo-de-los-tsachilas',
    'imbabura',
    'santa-elena',
    'chimborazo',
    'esmeraldas',
]


def _sin_acentos(texto):
    """Quita tildes y diacriticos: 'dias' -> 'dias', 'Mas' -> 'Mas'."""
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')


def _slug(texto):
    """Normaliza un termino a slug de URL: sin acentos, minusculas, guiones."""
    limpio = re.sub(r'[^a-z0-9\s-]', ' ', _sin_acentos(texto).lower())
    return '-'.join(limpio.split())


def _slug_ubicacion(ubicacion):
    """Traduce 'Quito, Ecuador' al slug que entiende Computrabajo.

    Devuelve (slug, reconocida). Si no esta en el mapa se intenta con la ciudad sola, pero
    se avisa: una ubicacion invalida no da error, da una pagina vacia.
    """
    if not ubicacion:
        return '', True

    ciudad = _sin_acentos(ubicacion.split(',')[0]).strip().lower()
    if ciudad in SLUGS_UBICACION:
        return SLUGS_UBICACION[ciudad], True

    completa = _sin_acentos(ubicacion).strip().lower()
    if completa in SLUGS_UBICACION:
        return SLUGS_UBICACION[completa], True

    return _slug(ciudad), False


def _crear_sesion():
    """Sesion con reintentos y backoff exponencial ante 429 y errores 5xx."""
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    reintentos = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET'],
    )
    sesion.mount('https://', HTTPAdapter(max_retries=reintentos))
    return sesion


MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
    'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11,
    'diciembre': 12,
}


def _dias_desde_fecha(dia, mes, hoy=None):
    """Dias transcurridos desde una fecha "25 de septiembre" que Computrabajo da SIN ano.

    dia y mes llegan como enteros (25, 9). Devuelve un int >= 0, o None si la fecha no
    existe (p.ej. 31 de febrero).
    """
    hoy = hoy or date.today()
    try:
        fecha = date(hoy.year, mes, dia)
    except ValueError:
        return None
    # Sin ano, una fecha "del futuro" solo puede ser del ano pasado: en enero,
    # "20 de diciembre" es el diciembre que acaba de terminar.
    if fecha > hoy:
        try:
            fecha = date(hoy.year - 1, mes, dia)
        except ValueError:  # 29 de febrero visto en un ano cuyo anterior no es bisiesto
            return None
    return (hoy - fecha).days


def _dias_desde(texto):
    """Convierte el texto de antiguedad de Computrabajo a dias aproximados."""
    if not texto:
        return None
    # Computrabajo escribe "Hace 3 dias" y "Mas de 30 dias": sin quitar las tildes
    # ningun patron de abajo coincide y todo devolveria None.
    t = _sin_acentos(texto).lower()
    # Pasados unos dias deja de escribir "Hace N dias" y pone la fecha: "25 de septiembre".
    # Medido el 05/10/2026: el 10% de las ofertas, justo las mas antiguas.
    m = re.fullmatch(r'(\d{1,2})\s+de\s+([a-z]+)', t.strip())
    if m and m.group(2) in MESES:
        return _dias_desde_fecha(int(m.group(1)), MESES[m.group(2)])
    if 'hoy' in t or 'minuto' in t or 'hora' in t:
        return 0
    if 'ayer' in t:
        return 1
    if 'mas de' in t and 'dias' in t:
        n = re.search(r'mas de\s+(\d+)\s+dias', t)
        return int(n.group(1)) + 1 if n else None
    if 'mas de' in t and 'mes' in t:
        n = re.search(r'mas de\s+(\d+)\s+mes', t)
        return int(n.group(1)) * 30 + 1 if n else None
    if 'hace' in t and 'dias' in t:
        n = re.search(r'hace\s+(\d+)\s+dias?', t)
        return int(n.group(1)) if n else None
    if 'hace' in t and 'semana' in t:
        n = re.search(r'hace\s+(\d+)\s+semana', t)
        return int(n.group(1)) * 7 if n else 7
    if 'hace' in t and 'mes' in t:
        n = re.search(r'hace\s+(\d+)\s+mes', t)
        return int(n.group(1)) * 30 if n else 30
    return None


def _id_de_url(url):
    """Saca un id estable del hash hexadecimal final de la URL de la oferta."""
    m = re.search(r'-([0-9A-F]{16,})$', url)
    return f'ct-{m.group(1)}' if m else f'ct-{abs(hash(url)):x}'


def _parsear_ofertas(html, dominio):
    """Extrae las ofertas de una pagina HTML de resultados."""
    soup = BeautifulSoup(html, 'html.parser')
    ofertas = []

    for articulo in soup.select('div#offersGridOfferContainer article.box_offer'):
        titulo_link = articulo.select_one('a.js-o-link')
        if not titulo_link:
            continue

        # Con perfil en Computrabajo la empresa es un enlace; sin perfil (el 20% medido el
        # 05/10, confidenciales incluidas: "Importante empresa del sector") es texto plano
        # en el mismo <p>. Leer solo el enlace las dejaba vacias.
        empresa = (articulo.select_one('a[offer-grid-article-company-url]')
                   or articulo.select_one('p.dFlex.fs16.fc_base.mt5'))
        ubicacion = articulo.select_one('p.fs16.fc_base.mt5:not(.dFlex) > span.mr10')
        fecha = articulo.select_one('p.fs13.fc_aux.mt15')
        salario = articulo.select_one('div.fs13.mt15 > span.dIB.mr10')

        href = titulo_link.get('href', '')
        if href.startswith('/'):
            href = f'https://{dominio}{href}'
        # El fragmento '#lc=ListOffers-Score-3' codifica la POSICION en los resultados,
        # asi que cambia entre corridas para la misma oferta y romperia el historico.
        href = href.split('#')[0]

        texto_fecha = fecha.get_text(' ', strip=True) if fecha else None
        dias = _dias_desde(texto_fecha)

        ofertas.append({
            'id': _id_de_url(href),
            'site': 'computrabajo',
            'title': titulo_link.get_text(strip=True),
            'company': empresa.get_text(strip=True) if empresa else None,
            'location': ubicacion.get_text(strip=True) if ubicacion else None,
            # Se guarda como fecha real, no como "Hace 3 dias": asi ordena y se compara
            # igual que lo que devuelven LinkedIn e Indeed.
            'date_posted': (date.today() - timedelta(days=dias)).isoformat()
                           if dias is not None else None,
            'job_url': href,
            'salary': salario.get_text(' ', strip=True) if salario else None,
            '_dias': dias,
        })

    return ofertas


def _avisar_si_hay_drift(ofertas):
    """Avisa si los selectores parecen haber dejado de coincidir.

    Dependen de clases utilitarias del sitio: si Computrabajo cambia el markup seguimos
    sacando titulos, pero el resto queda en None y nadie se entera.
    """
    if not ofertas:
        return
    for campo in ('company', 'location'):
        faltantes = sum(1 for o in ofertas if not o[campo])
        if faltantes > len(ofertas) / 2:
            print(f"   [AVISO] Posible cambio de estructura en Computrabajo: "
                  f"{faltantes}/{len(ofertas)} ofertas sin '{campo}'")


def _tiene_siguiente(html):
    """Indica si existe boton 'Siguiente' en la paginacion."""
    soup = BeautifulSoup(html, 'html.parser')
    boton = soup.select_one('div.dFlex.vm_fx.tj_fx.mtB span[title="Siguiente"]')
    return bool(boton and boton.get('data-path'))


def _recorrer_paginas(url_base, dominio, max_paginas, retraso, dias_max, sesion):
    """Recorre las paginas de una busqueda y devuelve las ofertas encontradas."""
    resultados = []
    sin_fecha = 0
    pagina = 1

    while pagina <= max_paginas:
        url = url_base if pagina == 1 else f'{url_base}?p={pagina}'

        try:
            respuesta = sesion.get(url, timeout=20)
            respuesta.raise_for_status()
        except Exception as e:
            print(f'   [AVISO] computrabajo pagina {pagina} fallo: {e}')
            print(f'   [AVISO] se conservan las {len(resultados)} ofertas ya obtenidas')
            break

        ofertas = _parsear_ofertas(respuesta.text, dominio)
        if not ofertas:
            break

        _avisar_si_hay_drift(ofertas)

        if dias_max is not None:
            # Las ofertas sin fecha legible se conservan: descartarlas en silencio
            # perderia ofertas validas solo porque cambio el texto de antiguedad.
            dentro = [o for o in ofertas if o['_dias'] is None or o['_dias'] <= dias_max]
            sin_fecha += sum(1 for o in ofertas if o['_dias'] is None)
            fuera = len(ofertas) - len(dentro)
            ofertas = dentro
            if fuera and not ofertas:
                # Vienen ordenadas por fecha: si la pagina entera es mas vieja que el
                # limite, las siguientes tambien lo seran.
                break

        resultados.extend(ofertas)

        if not _tiene_siguiente(respuesta.text):
            break

        pagina += 1
        time.sleep(retraso + random.uniform(0, 1))

    if sin_fecha:
        print(f'   [AVISO] {sin_fecha} ofertas sin fecha legible: se incluyeron igual')

    return resultados


def _a_dataframe(ofertas, resultados, por_fecha=False):
    """Construye el DataFrame final. Con la lista vacia sale vacio pero CON columnas,
    para que el concat de buscador.py no reviente.

    Con por_fecha se queda con las mas recientes en vez de con las primeras que llegaron.
    """
    if por_fecha:
        # Las que no traen fecha legible al final, no descartadas.
        ofertas = sorted(ofertas, key=lambda o: (o['_dias'] is None, o['_dias'] or 0))

    df = pd.DataFrame(ofertas, columns=COLUMNAS + ['_dias'])
    df = df.drop(columns=['_dias']).drop_duplicates(subset=['job_url'])
    return df.head(resultados).reset_index(drop=True)


def _recorrer_provincias(dominio, resultados, dias_max, retraso, sesion):
    """Recorre las provincias de Ecuador, para cubrir el pais entero sin termino.

    Es el unico camino: Computrabajo no publica una pagina de "todo el pais".

    Se visitan las 12 SIEMPRE, sin cortar al llegar al cupo: parando antes solo se
    recogian Pichincha, Guayas y Azuay, y las provincias pequenas no aparecian nunca.
    El recorte a `resultados` lo hace despues _a_dataframe(), quedandose con las mas
    recientes en vez de con las de las primeras provincias.
    """
    print(f'   computrabajo: recorriendo {len(PROVINCIAS_EC)} provincias '
          f'(no existe pagina de todo el pais)')

    por_provincia = max(1, math.ceil(resultados / len(PROVINCIAS_EC)))
    max_paginas = max(1, math.ceil(por_provincia / OFERTAS_POR_PAGINA))
    ofertas = []

    for provincia in PROVINCIAS_EC:
        ofertas.extend(_recorrer_paginas(
            f'https://{dominio}/empleos-en-{provincia}', dominio,
            max_paginas, retraso, dias_max, sesion,
        ))

    return ofertas


def scrape(termino='', ubicacion='Ecuador', resultados=100, dias_max=None,
           pais='ecuador', retraso=2):
    """Busca en Computrabajo y devuelve un DataFrame con las columnas de COLUMNAS.

    Con termino vacio trae todos los puestos de la ubicacion. `resultados` se traduce a
    paginas (~20 ofertas cada una) y luego se recorta, para que signifique lo mismo que
    en los demas sitios.
    """
    codigo = PAIS_A_CODIGO.get(str(pais).strip().lower(), 'ec')
    dominio = DOMINIOS.get(codigo, DOMINIOS['ec'])

    slug_ubi, reconocida = _slug_ubicacion(ubicacion)
    if not reconocida:
        print(f"   [AVISO] '{ubicacion}' no esta en el mapa de ubicaciones de Computrabajo; "
              f"se prueba con '{slug_ubi}' y puede no devolver nada. "
              f"Anadelo a SLUGS_UBICACION si es una ciudad valida")

    slug_term = _slug(termino) if termino else ''
    # Una sola sesion para toda la busqueda: reutiliza la conexion en vez de repetir el
    # saludo TLS en cada provincia.
    sesion = _crear_sesion()

    if slug_term and slug_ubi:
        ruta = f'trabajo-de-{slug_term}-en-{slug_ubi}'
    elif slug_term:
        # Sin ubicacion, la busqueda por termino ya cubre el pais entero.
        ruta = f'trabajo-de-{slug_term}'
    elif slug_ubi:
        ruta = f'empleos-en-{slug_ubi}'
    elif codigo == 'ec':
        # Ni termino ni ciudad: hay que ir provincia por provincia.
        ofertas = _recorrer_provincias(dominio, resultados, dias_max, retraso, sesion)
        return _a_dataframe(ofertas, resultados, por_fecha=True)
    else:
        print(f'   [AVISO] computrabajo necesita un puesto o una ciudad para buscar en '
              f'{pais}: solo hay lista de provincias para Ecuador')
        return _a_dataframe([], resultados)

    max_paginas = max(1, math.ceil(resultados / OFERTAS_POR_PAGINA))
    ofertas = _recorrer_paginas(
        f'https://{dominio}/{ruta}', dominio, max_paginas, retraso, dias_max, sesion
    )
    return _a_dataframe(ofertas, resultados)
