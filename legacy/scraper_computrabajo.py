import random
import re
import time
import unicodedata

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept-Language': 'es-EC,es;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Columnas del DataFrame resultante. Se pasan explicitamente a pd.DataFrame para que
# una busqueda sin resultados produzca un DataFrame vacio pero CON columnas, y no
# reviente en drop_duplicates() ni en el analisis posterior.
COLUMNS = ['title', 'company', 'location', 'date_published', 'salary', 'url', 'fecha_scrape']

# Dominios por país
PAISES = {
    'ec': 'ec.computrabajo.com',
    'co': 'co.computrabajo.com',
    'mx': 'mx.computrabajo.com',
    'pe': 'pe.computrabajo.com',
    'ar': 'ar.computrabajo.com',
    'cl': 'cl.computrabajo.com',
    'bo': 'bo.computrabajo.com',
    'uy': 'uy.computrabajo.com',
    'pa': 'pa.computrabajo.com',
    'do': 'do.computrabajo.com',
}

# Provincias de Ecuador (la página de provincia incluye todas sus ciudades)
LOCALIDADES_EC = [
    'azuay',
    'chimborazo',
    'el-oro',
    'esmeraldas',
    'guayas',
    'imbabura',
    'los-rios',
    'manabi',
    'pichincha',
    'santa-elena',
    'santo-domingo-de-los-tsachilas',
    'tungurahua',
]


def _sin_acentos(texto):
    """Quita tildes y diacriticos: 'días' -> 'dias', 'Más' -> 'Mas'."""
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')


def _slug(texto):
    """Normaliza un termino a slug de URL: sin acentos, minusculas, guiones."""
    return '-'.join(_sin_acentos(texto).strip().lower().split())


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


def _dias_desde(texto):
    """Convierte el texto de antigüedad de Computrabajo a días aproximados."""
    if not texto:
        return None
    # Computrabajo escribe "Hace 3 días" y "Más de 30 días": sin quitar las tildes
    # ningun patron de abajo coincide y todo devolveria None.
    t = _sin_acentos(texto).lower()
    if 'hoy' in t:
        return 0
    if 'ayer' in t:
        return 1
    if 'minuto' in t or 'hora' in t:
        return 0
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


def _parsear_ofertas(html, dominio):
    """Extrae las ofertas de una página HTML de resultados."""
    soup = BeautifulSoup(html, 'html.parser')
    ofertas = []

    for articulo in soup.select('div#offersGridOfferContainer article.box_offer'):
        titulo_link = articulo.select_one('a.js-o-link')
        if not titulo_link:
            continue

        empresa = articulo.select_one('a[offer-grid-article-company-url]')
        ubicacion = articulo.select_one('p.fs16.fc_base.mt5:not(.dFlex) > span.mr10')
        fecha = articulo.select_one('p.fs13.fc_aux.mt15')
        salario = articulo.select_one('div.fs13.mt15 > span.dIB.mr10')

        href = titulo_link.get('href', '')
        if href.startswith('/'):
            href = f"https://{dominio}{href}"

        ofertas.append({
            'title': titulo_link.get_text(strip=True),
            'company': empresa.get_text(strip=True) if empresa else None,
            'location': ubicacion.get_text(strip=True) if ubicacion else None,
            'date_published': fecha.get_text(' ', strip=True) if fecha else None,
            'salary': salario.get_text(' ', strip=True) if salario else None,
            'url': href,
            'fecha_scrape': date.today().isoformat(),
        })

    return ofertas


def _avisar_si_hay_drift(ofertas):
    """
    Los selectores dependen de clases utilitarias del sitio. Si Computrabajo cambia el
    markup seguimos extrayendo titulos, pero el resto queda en None y el reporte sale
    vacio sin ningun error. Avisamos si mas de la mitad viene incompleta.
    """
    if not ofertas:
        return

    for campo in ('company', 'location'):
        faltantes = sum(1 for o in ofertas if not o[campo])
        if faltantes > len(ofertas) / 2:
            print(f"[ADVERTENCIA] Posible cambio de estructura en Computrabajo: "
                  f"{faltantes}/{len(ofertas)} ofertas sin '{campo}'")


def _tiene_siguiente(html):
    """Indica si existe botón 'Siguiente' en la paginación."""
    soup = BeautifulSoup(html, 'html.parser')
    boton = soup.select_one('div.dFlex.vm_fx.tj_fx.mtB span[title="Siguiente"]')
    return bool(boton and boton.get('data-path'))


def _a_dataframe(resultados, etiqueta='Computrabajo'):
    """Construye el DataFrame final, deduplicando por url (la clave natural)."""
    df = pd.DataFrame(resultados, columns=COLUMNS).drop_duplicates(subset=['url'])
    print(f"[OK] Total: {len(df)} empleos unicos de {etiqueta}")
    return df


def _recorrer_paginas(url_base, dominio, max_paginas, retraso, dias_max=None, sesion=None):
    """Recorre todas las páginas de una URL base de Computrabajo y devuelve las ofertas.

    Si dias_max se indica, descarta ofertas publicadas hace más de N días.
    """
    sesion = sesion or _crear_sesion()
    resultados = []
    pagina = 1

    while pagina <= max_paginas:
        url = url_base if pagina == 1 else f"{url_base}?p={pagina}"
        print(f"[Pagina {pagina}] {url}")

        try:
            response = sesion.get(url, timeout=20)
            response.raise_for_status()
        except Exception as e:
            print(f"[ERROR] En pagina {pagina}: {e}")
            print(f"[ERROR] Se conservan las {len(resultados)} ofertas obtenidas hasta ahora")
            break

        ofertas = _parsear_ofertas(response.text, dominio)
        if not ofertas:
            print("[OK] Sin mas ofertas disponibles")
            break

        _avisar_si_hay_drift(ofertas)

        if dias_max is not None:
            filtradas = [
                o for o in ofertas
                if (d := _dias_desde(o['date_published'])) is not None and d <= dias_max
            ]
            descartadas = len(ofertas) - len(filtradas)
            ofertas = filtradas
            print(f"   -> {len(ofertas)} ofertas de los ultimos {dias_max} dias ({descartadas} descartadas)")
            if not ofertas:
                # Los resultados vienen ordenados por fecha: si esta pagina entera es
                # mas vieja que el limite, las siguientes tambien lo seran.
                print("[OK] Sin mas ofertas dentro del rango de fechas")
                break
        else:
            print(f"   -> {len(ofertas)} ofertas encontradas")

        resultados.extend(ofertas)

        if not _tiene_siguiente(response.text):
            print("[OK] Ultima pagina alcanzada")
            break

        pagina += 1
        time.sleep(retraso + random.uniform(0, 1))

    return resultados


def _scrape(prefijo, termino, pais, max_paginas, retraso):
    """Recorre una busqueda de Computrabajo y devuelve un DataFrame de ofertas unicas."""
    dominio = PAISES.get(pais, PAISES['ec'])
    url_base = f"https://{dominio}/{prefijo}{_slug(termino)}"

    resultados = _recorrer_paginas(url_base, dominio, max_paginas, retraso)
    return _a_dataframe(resultados)


def scrape_todo_ecuador(dias_max=7, max_paginas=10, retraso=2):
    """
    Ejecuta scraping de TODOS los empleos de Ecuador (todas las provincias, sin puesto).

    Args:
        dias_max: Solo ofertas publicadas en los últimos N días (None = todas)
        max_paginas: Máximo de páginas por provincia (~20 ofertas por página)
        retraso: Segundos de espera entre requests (anti-bloqueo)
    """
    dominio = PAISES['ec']
    sesion = _crear_sesion()
    resultados = []

    for provincia in LOCALIDADES_EC:
        url_base = f"https://{dominio}/empleos-en-{provincia}"
        print(f"\n[PROVINCIA] {provincia.replace('-', ' ').title()}")
        prov = _recorrer_paginas(url_base, dominio, max_paginas, retraso, dias_max, sesion)
        resultados.extend(prov)
        print(f"   -> {len(prov)} empleos en {provincia}")

    print()
    return _a_dataframe(resultados, 'Ecuador')


def scrape_computrabajo(palabra_clave, pais='ec', max_paginas=10, retraso=2):
    """
    Ejecuta scraping de Computrabajo por palabra clave y retorna DataFrame con resultados.

    Args:
        palabra_clave: Término de búsqueda (ej: "Python")
        pais: Código de país ('ec', 'co', 'mx', ...)
        max_paginas: Máximo de páginas a recorrer (~20 ofertas por página)
        retraso: Segundos de espera entre requests (anti-bloqueo)
    """
    print(f"[BUSQUEDA POR PALABRA CLAVE] {palabra_clave}")
    return _scrape('trabajo-de-', palabra_clave, pais, max_paginas, retraso)


def scrape_computrabajo_localidad(localidad, pais='ec', max_paginas=10, retraso=2):
    """
    Ejecuta scraping de TODOS los empleos de una localidad (sin palabra clave).

    Args:
        localidad: Provincia y/o ciudad. Ejemplos:
            "pichincha-en-quito", "guayas-en-guayaquil", "santo-domingo-de-los-tsachilas"
        pais: Código de país ('ec', 'co', 'mx', ...)
        max_paginas: Máximo de páginas a recorrer (~20 ofertas por página)
        retraso: Segundos de espera entre requests (anti-bloqueo)
    """
    print(f"[BUSQUEDA POR LOCALIDAD] {localidad}")
    return _scrape('empleos-en-', localidad, pais, max_paginas, retraso)
