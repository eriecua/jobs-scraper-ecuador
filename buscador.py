r"""Busqueda de empleos en todos los sitios, devolviendo un solo DataFrame."""
import logging
import math

import pandas as pd
from jobspy import scrape_jobs

import computrabajo
import multitrabajos
import ubicaciones

# jobspy loguea a stderr por su cuenta: ni verbose=0 ni silenciar el logger "JobSpy"
# bastan (sus loggers se crean tarde y se llaman "JobSpy:Linkedin", con dos puntos).
logging.disable(logging.INFO)

# Sitios que jobspy no cubre y raspa un modulo propio. Todos comparten la firma
# scrape(termino, ubicacion, resultados, dias_max, pais): anadir uno es una linea aqui.
FUENTES_PROPIAS = {
    'computrabajo': computrabajo.scrape,
    'multitrabajos': multitrabajos.scrape,
}

SITIOS_DEFECTO = ('linkedin', 'indeed', 'computrabajo', 'multitrabajos')

# La descripcion completa no se usa para nada: el indice de compatibilidad puntua con el
# titulo. Indeed la manda igual dentro de sus resultados, y son miles de caracteres por
# oferta que engordan el CSV sin aportar. Poner en False para conservarla.
DESCARTAR_DESCRIPCION = True


def buscar(termino='', ubicacion='Ecuador', resultados=100, horas=None, tipo=None,
           distancia=50, con_descripcion=False, sitios=SITIOS_DEFECTO,
           pais='ecuador'):
    """Scrapea cada sitio y devuelve (DataFrame con todo junto, lista de sitios fallidos).

    Con termino vacio trae todos los puestos de la ubicacion, sin filtrar por titulo.
    Va sitio por sitio a proposito: una sola llamada con varios sitios se cae entera si
    uno falla (p.ej. Glassdoor no existe para Ecuador), perdiendo tambien lo de los demas.

    Se devuelven los fallos aparte porque "cero empleos" y "todos los sitios reventaron"
    son cosas distintas y quien llama tiene que poder distinguirlas.
    """
    print(f"[BUSQUEDA] {termino or 'todos los puestos'} en {ubicacion}...")
    partes = []
    fallidos = []
    vacios = []

    for sitio in sitios:
        try:
            if sitio in FUENTES_PROPIAS:
                parcial = FUENTES_PROPIAS[sitio](
                    termino=termino,
                    ubicacion=ubicacion,
                    resultados=resultados,
                    # Los sitios propios solo publican la antiguedad en dias, no en horas.
                    dias_max=math.ceil(horas / 24) if horas else None,
                    pais=pais,
                )
            else:
                parcial = scrape_jobs(
                    site_name=[sitio],
                    search_term=termino,
                    location=ubicacion,
                    results_wanted=resultados,
                    hours_old=horas,
                    job_type=tipo,
                    distance=distancia,
                    country_indeed=pais,
                    # Con True, jobspy hace una peticion extra POR CADA empleo. Es la
                    # diferencia entre segundos y minutos, por eso el default es no traerla.
                    linkedin_fetch_description=con_descripcion,
                    verbose=0,
                )
            print(f"   {sitio}: {len(parcial)} empleos")
            if len(parcial):
                partes.append(parcial)
            else:
                vacios.append(sitio)
        except Exception as e:
            print(f"   [AVISO] {sitio} fallo: {e}")
            fallidos.append(sitio)

    # Los sitios propios devuelven 200 con cero ofertas cuando un slug o filtro no cuadra,
    # sin dar error. El motivo concreto lo sabe cada modulo, que ya avisa por su cuenta;
    # aqui solo se senala la discrepancia para que no pase inadvertida.
    for sitio in vacios:
        if sitio in FUENTES_PROPIAS and partes:
            print(f"   [AVISO] {sitio} no devolvio nada para '{ubicacion}' "
                  f"pero otros sitios si")

    if not partes:
        return pd.DataFrame(), fallidos
    # Sin quitar las columnas 100% vacias, concat avisa de un cambio futuro de dtypes.
    juntos = pd.concat([p.dropna(axis=1, how='all') for p in partes], ignore_index=True)

    # Cada sitio entrega la fecha a su manera (date, str, Timestamp). Sin unificarla,
    # ordenar por date_posted revienta al comparar str con date.
    if 'date_posted' in juntos.columns:
        juntos['date_posted'] = pd.to_datetime(juntos['date_posted'], errors='coerce')

    # Cada sitio escribe la ubicacion a su manera ('Quito, Pichincha, Ecuador',
    # 'Quito, P, EC'). Se normaliza aqui, el unico punto por donde pasan todos los sitios,
    # para que el CSV, el historico y el correo vean todos la misma ciudad. La guarda no
    # es adorno: si ningun sitio trajo 'location', sin ella es un KeyError seco.
    if 'location' in juntos.columns:
        pares = juntos['location'].map(ubicaciones.normalizar)
        juntos['ciudad'] = [c for c, _ in pares]
        juntos['provincia'] = [p for _, p in pares]

    if DESCARTAR_DESCRIPCION and not con_descripcion and 'description' in juntos.columns:
        juntos = juntos.drop(columns=['description'])

    return juntos, fallidos
