r"""Construye el correo diario: clasifica las ofertas y arma el cuerpo HTML.

Aqui vive QUE se dice: como se agrupan los titulos en familias, que publicaciones no son
ofertas de verdad, en que orden va cada cosa y que se oculta. COMO se pinta una barra, un
KPI o una insignia esta en graficos.py, que no sabe nada de empleos.

El HTML de aqui tambien usa tablas con estilos en linea: un correo no admite flexbox,
grid, <style> en el head, SVG ni imagenes.
"""
import html
import unicodedata
from collections import Counter
from datetime import date

import pandas as pd

import graficos
import perfil
import ubicaciones
from graficos import AZUL, FONDO, GRIS, GRIS_BORDE, TEXTO, VERDE

# Las tablas de ciudades, provincias y abreviaturas de Indeed vivian aqui. Se mudaron a
# ubicaciones.py: el mismo dato hace falta ahora en el CSV, y tenerlo en dos sitios
# garantizaba que el correo y el archivo acabaran diciendo cosas distintas.

# Familias de puesto. El orden importa: gana la primera que coincida, asi que las mas
# especificas van antes que las genericas ('desarrollador' antes que 'ingeniero').
FAMILIAS = {
    # Gana la PRIMERA familia que coincide: estas dos van antes que TI, Produccion e
    # Ingenieria para que "Ingeniero de Calidad" o "Analista de Procesos de Produccion" no
    # se pierdan alli. Calidad solo por la palabra en el titulo (decision del usuario: los
    # titulos de procesos y calidad se mezclan, y la palabra es lo unico inequivoco).
    'Calidad': ['calidad'],
    # Se compara por subcadena: los terminos cortos llevan espacios para ser palabra
    # completa ('lean' esta dentro de 'cleaning', 'process' dentro de 'processor').
    'Procesos/Mejora continua': ['procesos', 'mejora continua', 'excelencia operacional',
                                 'excelencia operativa', ' lean ', 'kaizen', ' process ',
                                 'continuous improvement', ' bpm '],
    'Desarrollador/TI': ['desarrollador', 'developer', 'programador', 'software', 'fullstack',
                         'full stack', 'backend', 'frontend', 'devops', 'qa ', 'sre',
                         'scrum master', 'tech lead', 'quality assurance', 'help desk',
                         'database', 'infrastructure', 'ciberseguridad', 'redes y ',
                         'soporte tecnico', 'sistemas', 'automatizacion'],
    'Datos/BI': ['analista de datos', 'data analyst', 'data scientist', 'business intelligence',
                 ' bi ', 'analista bi', 'datos', 'data engineer'],
    'Contabilidad/Finanzas': ['contador', 'contable', 'contabilidad', 'accountant',
                              'finanzas', 'financiero', 'financial', 'tesoreria', 'auditor',
                              'credito', 'cobranza', 'cobrador', 'facturacion',
                              'oficial de cumplimiento', 'riesgos', 'siniestros'],
    'Recursos Humanos': ['recursos humanos', 'talento humano', 'talent', 'recruiter',
                         'reclutador', 'seleccion de personal', 'nomina'],
    'Marketing': ['marketing', 'community manager', 'publicidad', 'redes sociales',
                  'contenido', 'branding', 'trade marketing'],
    'Diseno': ['disenador', 'diseno grafico', 'designer', 'ux', 'ui '],
    'Ventas': ['vendedor', 'ventas', 'comercial', 'sales', 'impulsador', 'promotor',
               'preventista', 'perchero', 'mercaderista', 'merchandiser',
               'business development', 'comercio exterior', 'venta'],
    'Atencion al Cliente': ['atencion al cliente', 'call center', 'contact center',
                            'servicio al cliente', 'cajero', 'cajera', 'recepcionista',
                            'customer', 'agendador', 'telefonic'],
    'Logistica': ['logistica', 'logistico', 'bodega', 'bodeguero', 'almacen', 'inventario',
                  'inventory', 'despacho', 'distribucion', 'transporte', 'chofer',
                  'conductor', 'repartidor', 'mensajero', 'motorizado', 'empacador',
                  'estibador', 'montacarguista', 'planificador', 'planner', 'supply',
                  'tripulante'],
    'Salud': ['medico', 'enfermer', 'odontolog', 'psicolog', 'farmac', 'laboratorista',
              'nutricion', 'fisioterap', 'veterinari'],
    'Educacion': ['docente', 'profesor', 'maestro', 'teacher', 'tutor', 'capacitador'],
    'Seguridad': ['seguridad', 'guardia', 'vigilante'],
    'Limpieza/Servicios': ['limpieza', 'conserje', 'camarer', 'mesero', 'cocinero',
                           'chef', 'ayudante de cocina', 'barista', 'bartender',
                           'saloner', 'reposter', 'panader', 'jardiner', 'barberia',
                           'empleada domestica', 'estilista', 'peluquer'],
    'Produccion/Operario': ['operario', 'operador', 'obrero', 'produccion', 'mantenimiento',
                            'soldador', 'mecanico', 'electricista', 'montaje', 'tornero',
                            'fresador', 'armador', 'ensamblador', 'costurer'],
    'Construccion': ['construccion', 'albanil', 'topografo', 'residente de obra', 'arquitect'],
    'Ingenieria': ['ingenier', 'engineer'],
    'Analista': ['analista', 'analyst'],
    'Asesor': ['asesor', 'consultor', 'advisor'],
    'Ejecutivo': ['ejecutiv', 'executive'],
    'Jefatura/Gerencia': ['jefe', 'gerente', 'manager', 'director', 'coordinador',
                          'supervisor', 'lider', 'head of', 'encargado', 'gestor',
                          'administrador', 'principal '],
    'Asistente/Auxiliar': ['asistente', 'auxiliar', 'assistant', 'secretari', 'ayudante',
                           'agente de', 'asociad'],
    'Tecnico': ['tecnico', 'technician', 'inspector', 'geomensor', 'topograf'],
    'Especialista': ['especialista', 'specialist', 'expert'],
    'Practicas': ['practicante', 'pasante', 'pasantia', 'intern', 'trainee',
                  'en practicas'],
}

OTROS = 'Otros'

# Cajones de sastre: se muestran, pero nunca por delante de una categoria de verdad,
# aunque tengan mas ofertas.
AL_FINAL = (OTROS, 'Sin ubicacion')

# Sufijo de las ubicaciones de las que solo se supo la provincia ('Pichincha (prov.)').
# No es un cajon fijo como los de arriba: hay una etiqueta distinta por provincia, asi que
# se reconocen por el sufijo y no por una lista.
SUFIJO_PROVINCIA = ' (prov.)'

# Titulos que LinkedIn acepta pero no describen un puesto. Son publicaciones reales
# (spam o perezosas), no un fallo del scraper: se ocultan del reporte, no del CSV.
NO_OFERTAS = [
    'trabaja con nosotros', 'trabaje con nosotros', 'postula aqui', 'postulate',
    'unete a nuestro equipo', 'unete al equipo', 'equipo familiar', 'agente asociado',
    'vacantes disponibles', 'oportunidades laborales', 'bolsa de empleo',
    'forma parte de', 'estudios del sector',
]


def _norm(texto):
    """Minusculas sin acentos, para comparar sin sorpresas."""
    limpio = unicodedata.normalize('NFKD', str(texto).lower())
    return limpio.encode('ascii', 'ignore').decode()


def ciudad_normalizada(location):
    """Etiqueta de ciudad presentable a partir de la ubicacion cruda del sitio.

    La logica esta en ubicaciones.py; aqui solo se convierte el par (ciudad, provincia)
    en la etiqueta que va en el grafico. Se mantiene esta funcion porque es la que usa el
    comando de comprobacion del README.
    """
    return ubicaciones.etiqueta(*ubicaciones.normalizar(location))


def familia_puesto(titulo):
    """Agrupa el titulo en una familia de puesto (Analista, Ventas, Logistica...)."""
    n = f' {_norm(titulo)} '
    for familia, claves in FAMILIAS.items():
        if any(clave in n for clave in claves):
            return familia
    return OTROS


def es_oferta_real(titulo):
    """False para llamados genericos de reclutamiento y titulos vacios de contenido."""
    n = _norm(titulo).strip()
    if len(n) < 4:
        return False
    return not any(frase in n for frase in NO_OFERTAS)


def _es_cajon(nombre):
    """True si la categoria es un cajon de sastre y no una ciudad o familia de verdad."""
    return nombre in AL_FINAL or str(nombre).endswith(SUFIJO_PROVINCIA)


def _postergar_cajones(conteos):
    """Manda los cajones de sastre al final, conservando el resto del orden."""
    presentes = [c for c in conteos.index if _es_cajon(c)]
    if not presentes:
        return conteos
    return pd.concat([conteos.drop(presentes), conteos[presentes]])


def _grafico(titulo, conteos, color=AZUL, limite=graficos.MAX_BARRAS):
    """Grafico de barras, con los cajones de sastre mandados al final.

    graficos.grafico() dibuja en el orden que le llega; el criterio es cosa de aqui.
    """
    return graficos.grafico(titulo, _postergar_cajones(conteos), color, limite)


def _listado(df):
    """Las ofertas agrupadas por ciudad, con link. Es lo que hace el correo accionable."""
    bloques = []

    # Las ciudades con mas ofertas primero; los cajones de sastre al final.
    orden = df['ciudad'].value_counts()
    postergadas = [c for c in orden.index if _es_cajon(c)]
    ciudades = [c for c in orden.index if c not in postergadas] + postergadas

    for ciudad in ciudades:
        grupo = df[df['ciudad'] == ciudad]
        # Las que tocan tus terminos arriba; el resto debajo por fecha. El puntaje ordena,
        # no filtra: las de 0 siguen ahi, solo que despues.
        criterios = ['puntaje'] + (['date_posted'] if 'date_posted' in grupo.columns else [])
        grupo = grupo.sort_values(criterios, ascending=False, na_position='last')

        filas = []
        for fila in grupo.itertuples():
            titulo = html.escape(str(getattr(fila, 'title', '') or 'Sin titulo'))
            empresa = html.escape(str(getattr(fila, 'company', '') or 'Sin empresa'))
            url = str(getattr(fila, 'job_url', '') or '')
            enlace = (f'<a href="{html.escape(url, quote=True)}" '
                      f'style="color:{AZUL};text-decoration:none;font-weight:600">{titulo}</a>'
                      if url else f'<span style="font-weight:600">{titulo}</span>')

            # Por que puntuo asi: los terminos que coincidieron, y el nivel si el titulo
            # lo dice. El nivel es solo etiqueta, no entra en el puntaje.
            detalle = [empresa]
            if getattr(fila, 'nivel', None):
                detalle.append(html.escape(str(fila.nivel)))
            if getattr(fila, 'terminos', None):
                detalle.append(html.escape(', '.join(fila.terminos)))

            filas.append(
                f'<tr>'
                f'<td style="padding:7px 8px 7px 0;border-bottom:1px solid {GRIS_BORDE};'
                f'vertical-align:top;width:34px">{graficos.insignia(int(fila.puntaje))}</td>'
                f'<td style="padding:7px 0;border-bottom:1px solid {GRIS_BORDE};'
                f'font-size:14px;color:{TEXTO}">{enlace}'
                f'<div style="font-size:12px;color:{GRIS};padding-top:1px">'
                f'{" · ".join(detalle)}</div>'
                '</td></tr>'
            )

        bloques.append(
            f'<div style="margin:26px 0 0">'
            f'<div style="font-size:15px;font-weight:bold;color:{TEXTO};'
            f'border-bottom:2px solid {AZUL};padding-bottom:5px">'
            f'{html.escape(ciudad)} '
            f'<span style="color:{GRIS};font-weight:normal">· {len(grupo)} ofertas</span>'
            '</div>'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            f'style="width:100%;border-collapse:collapse">{"".join(filas)}</table></div>'
        )

    return ''.join(bloques)


def _pie_ocultadas(no_ofertas, motivos):
    """Dice cuantas ofertas se ocultaron y por que termino exacto.

    Es lo que evita que el filtro sea una caja negra: viendo que 'comercial' recorta 37
    ofertas se puede decidir con criterio si esa palabra sobra en EXCLUIDOS.
    """
    excluidas = sum(motivos.values())
    if not (excluidas or no_ofertas):
        return ''

    lineas = []
    if excluidas:
        desglose = ' · '.join(f'{t} {n}' for t, n in motivos.most_common(6))
        resto = len(motivos) - 6
        if resto > 0:
            desglose += f' · otros {resto}'
        lineas.append(f'<b>{excluidas}</b> por tus exclusiones — {html.escape(desglose)}')
    if no_ofertas:
        lineas.append(f'<b>{no_ofertas}</b> que no describen un puesto '
                      f'(tipo "Trabaja con nosotros")')

    return (
        f'<div style="font-size:11px;color:{GRIS};padding-top:16px;'
        f'border-top:1px solid {GRIS_BORDE};margin-top:22px;line-height:1.6">'
        f'Se ocultaron {excluidas + no_ofertas} publicaciones:<br>'
        + '<br>'.join(f'&nbsp;&nbsp;{l}' for l in lineas) +
        '<br>Todas siguen en el CSV adjunto. Para cambiar esto, edita '
        '<code>EXCLUIDOS</code> en perfil.py.</div>'
    )


def construir(nuevos, horas=24):
    """Devuelve (asunto, cuerpo_html) del reporte diario.

    `nuevos` es el DataFrame de ofertas nuevas. Se trabaja sobre una copia porque aqui
    'ciudad' se reescribe con la ETIQUETA del grafico ('Pichincha (prov.)' donde el dato
    guardado es la ciudad vacia). Sin la copia, esa etiqueta se colaria en el CSV, que
    debe llevar el valor crudo de ubicaciones.normalizar().
    """
    df = nuevos.copy()

    # Se guarda POR QUE se oculto cada fila, para poder decirlo al pie del correo. Sin
    # eso, el filtro es una caja negra y no hay forma de saber que se esta perdiendo.
    no_ofertas = 0
    motivos_exclusion = Counter()

    if len(df) and 'title' in df.columns:
        real = df['title'].map(es_oferta_real)
        no_ofertas = int((~real).sum())
        df = df[real]

        familias = df['title'].map(familia_puesto)
        motivos = [perfil.excluir(t, f) for t, f in zip(df['title'], familias)]
        motivos_exclusion.update(m for m in motivos if m)
        df = df[[m is None for m in motivos]]

    total = len(df)
    fecha = date.today().strftime('%d/%m/%Y')

    if not total:
        asunto = 'Sin puestos nuevos hoy'
        cuerpo = (
            f'<div style="font-family:Segoe UI,Arial,sans-serif;background-color:{FONDO};'
            f'color:{TEXTO};padding:20px">'
            f'<p style="font-size:15px">Erick, hoy no hay puestos nuevos '
            f'en las ultimas {horas} horas.</p></div>'
        )
        return asunto, cuerpo

    # buscador.py ya deja ciudad y provincia puestas; aqui solo se les da la etiqueta que
    # va en el grafico. Recalcular desde 'location' es el respaldo para un DataFrame que
    # no venga de buscar() (un CSV viejo, una prueba suelta).
    if 'ciudad' in df.columns and 'provincia' in df.columns:
        df['ciudad'] = [ubicaciones.etiqueta(c, p)
                        for c, p in zip(df['ciudad'].fillna(''), df['provincia'].fillna(''))]
    elif 'location' in df.columns:
        df['ciudad'] = df['location'].map(ciudad_normalizada)
    else:
        df['ciudad'] = 'Sin ubicacion'
    df['familia'] = df['title'].map(familia_puesto) if 'title' in df.columns else OTROS

    # Compatibilidad segun perfil.py. Ordena el listado; no oculta nada.
    titulos = df['title'].fillna('') if 'title' in df.columns else pd.Series([''] * len(df))
    puntuados = titulos.map(perfil.puntuar)
    df['puntaje'] = [p for p, _ in puntuados]
    df['terminos'] = [t for _, t in puntuados]
    df['nivel'] = titulos.map(perfil.nivel)

    interesantes = int((df['puntaje'] >= 30).sum())

    # _grafico() ya manda los cajones de sastre al final de cada serie.
    por_ciudad = df['ciudad'].value_counts()
    por_familia = df['familia'].value_counts()

    empresas = df['company'].nunique() if 'company' in df.columns else 0

    # El asunto dice lo unico que decide si abres el correo: cuantas te encajan.
    if interesantes:
        asunto = f'{interesantes} de {total} puestos nuevos te encajan'
    else:
        # Sin coincidencias, al menos que se vea donde esta el movimiento.
        lider = _postergar_cajones(por_ciudad)
        asunto = f'{total} puestos nuevos · {lider.index[0]} lidera con {int(lider.iloc[0])}'

    partes = [
        f'<div style="font-family:Segoe UI,Arial,sans-serif;background-color:{FONDO};'
        f'color:{TEXTO};padding:20px;max-width:640px">',

        f'<div style="font-size:19px;font-weight:bold;color:{TEXTO}">'
        f'Erick, {total} puestos nuevos</div>'
        f'<div style="font-size:12px;color:{GRIS};padding:2px 0 16px">'
        f'Ultimas {horas} horas · {fecha}</div>',

        graficos.kpis([(total, 'ofertas'), (interesantes, 'te encajan'),
                       (len(por_ciudad), 'ciudades'), (empresas, 'empresas')]),

        _grafico('Ofertas por ciudad', por_ciudad, AZUL),
        _grafico('Que estan buscando', por_familia, VERDE),
    ]

    if 'site' in df.columns:
        partes.append(_grafico('Por sitio', df['site'].value_counts(), GRIS, limite=5))

    partes.append(_listado(df))

    partes.append(_pie_ocultadas(no_ofertas, motivos_exclusion))

    partes.append('</div>')
    return asunto, '\n'.join(partes)
