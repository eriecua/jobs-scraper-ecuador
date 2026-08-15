r"""Construye el correo diario: graficos de barras y listado de ofertas.

Por que barras en HTML y no imagenes: un correo no ejecuta JavaScript ni renderiza SVG,
y un PNG tiene tamano fijo (se lee mal en el celular y arrastra su fondo blanco al modo
oscuro). Una barra hecha con una celda de tabla y un color de fondo se ve igual en Gmail
web, Gmail movil y Outlook, se reajusta al ancho y admite links al lado.

Por eso todo el HTML de aqui usa tablas con estilos en linea: nada de flexbox, grid,
<style> en el head, SVG ni imagenes.
"""
import html
import unicodedata
from collections import Counter
from datetime import date

import pandas as pd

import perfil

# Paleta con contraste suficiente en fondo claro y oscuro.
AZUL = '#2563eb'
AZUL_SUAVE = '#dbeafe'
VERDE = '#059669'
GRIS = '#6b7280'
GRIS_BORDE = '#e5e7eb'
TEXTO = '#111827'
FONDO = '#ffffff'

MAX_BARRAS = 8  # mas de esto y el grafico se vuelve una lista larga

# Ciudades de Ecuador que se buscan en CUALQUIER parte de la ubicacion: LinkedIn antepone
# la parroquia ('19 de Marzo, Esmeraldas, Ecuador'), asi que mirar solo el primer
# componente daba categorias como 'Eloy Alfaro' o 'c'.
CIUDADES = [
    'quito', 'guayaquil', 'cuenca', 'santo domingo', 'ambato', 'manta', 'machala',
    'loja', 'ibarra', 'riobamba', 'esmeraldas', 'portoviejo', 'duran', 'quevedo',
    'milagro', 'latacunga', 'babahoyo', 'salinas', 'otavalo', 'tulcan', 'azogues',
]

# Si no aparece la ciudad, la provincia sirve de aproximacion. Se funden con la ciudad
# (no '(prov.)' aparte) o Guayaquil saldria partido en dos barras.
PROVINCIAS = {
    'pichincha': 'Quito', 'guayas': 'Guayaquil', 'azuay': 'Cuenca',
    'tungurahua': 'Ambato', 'manabi': 'Manta', 'el oro': 'Machala',
    'imbabura': 'Ibarra', 'chimborazo': 'Riobamba', 'loja': 'Loja',
    'santo domingo de los tsachilas': 'Santo Domingo', 'cotopaxi': 'Latacunga',
    'los rios': 'Babahoyo', 'santa elena': 'Salinas', 'carchi': 'Tulcan',
    'canar': 'Azogues',
}

# Indeed abrevia la provincia a una letra: 'Eloy Alfaro, G, EC'.
CODIGOS_INDEED = {
    'p': 'Quito', 'g': 'Guayaquil', 'a': 'Cuenca', 't': 'Ambato',
    'm': 'Manta', 'o': 'Machala', 'i': 'Ibarra', 'h': 'Riobamba',
    'l': 'Loja', 'sd': 'Santo Domingo', 'c': 'Latacunga', 'r': 'Babahoyo',
}

# Familias de puesto. El orden importa: gana la primera que coincida, asi que las mas
# especificas van antes que las genericas ('desarrollador' antes que 'ingeniero').
FAMILIAS = {
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
AL_FINAL = (OTROS, 'Otras', 'Sin ubicacion')

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
    """Devuelve una ciudad presentable a partir de la ubicacion cruda del sitio.

    Cada sitio la escribe distinto ('Quito, Pichincha, Ecuador', 'Quito, P, EC',
    'Quito, Pichincha'), y LinkedIn a veces manda la parroquia. Sin esto el grafico sale
    con categorias como 'c', 'G' o 'Eloy Alfaro'.
    """
    n = _norm(location).strip()
    if not n or n == 'nan':
        return 'Sin ubicacion'

    if 'desde casa' in n or 'remote' in n or 'remoto' in n:
        return 'Remoto'

    for ciudad in CIUDADES:
        if ciudad in n:
            return ciudad.title()

    for provincia, capital in PROVINCIAS.items():
        if provincia in n:
            return capital

    # Ultimo recurso: la abreviatura de provincia de Indeed, siempre el penultimo campo.
    partes = [p.strip() for p in n.split(',')]
    if len(partes) >= 2 and partes[-1] in ('ec', 'ecuador'):
        if partes[-2] in CODIGOS_INDEED:
            return CODIGOS_INDEED[partes[-2]]

    return 'Otras'


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


def _barra(etiqueta, valor, maximo, color=AZUL):
    """Una fila del grafico: etiqueta, barra proporcional y numero."""
    # El ancho es relativo al maximo de la serie, no al total: con 14/6/3 la barra mas
    # larga llena la fila y las demas se leen en proporcion a ella.
    ancho = max(2, round(100 * valor / maximo)) if maximo else 2
    return (
        '<tr>'
        f'<td style="padding:3px 10px 3px 0;font-size:13px;color:{TEXTO};'
        f'white-space:nowrap;vertical-align:middle">{html.escape(str(etiqueta))}</td>'
        '<td style="width:99%;padding:3px 0;vertical-align:middle">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;table-layout:fixed">'
        f'<tr><td style="width:{ancho}%;background-color:{color};height:14px;'
        f'border-radius:3px;font-size:0;line-height:14px">&nbsp;</td>'
        '<td style="font-size:0;line-height:14px">&nbsp;</td></tr>'
        '</table></td>'
        f'<td style="padding:3px 0 3px 10px;font-size:13px;font-weight:bold;'
        f'color:{TEXTO};text-align:right;vertical-align:middle">{valor}</td>'
        '</tr>'
    )


def _postergar_cajones(conteos):
    """Manda 'Otros' / 'Otras' / 'Sin ubicacion' al final, conservando el resto del orden."""
    presentes = [c for c in AL_FINAL if c in conteos.index]
    if not presentes:
        return conteos
    return pd.concat([conteos.drop(presentes), conteos[presentes]])


def _grafico(titulo, conteos, color=AZUL, limite=MAX_BARRAS):
    """Bloque de titulo + barras a partir de un Series de conteos ya ordenado."""
    if not len(conteos):
        return ''

    serie = _postergar_cajones(conteos).head(limite)
    maximo = int(serie.max())

    filas = ''.join(_barra(k, int(v), maximo, color) for k, v in serie.items())
    resto = len(conteos) - len(serie)
    pie = (f'<div style="font-size:11px;color:{GRIS};padding-top:4px">'
           f'+{resto} categorias mas</div>') if resto > 0 else ''

    return (
        f'<div style="margin:22px 0 0">'
        f'<div style="font-size:11px;font-weight:bold;letter-spacing:.08em;'
        f'color:{GRIS};text-transform:uppercase;padding-bottom:6px">'
        f'{html.escape(titulo)}</div>'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;border-collapse:collapse">'
        f'{filas}</table>{pie}</div>'
    )


def _kpis(pares):
    """Fila de numeros grandes: [(valor, etiqueta), ...]."""
    celdas = ''.join(
        f'<td style="padding:12px 8px;text-align:center;background-color:{AZUL_SUAVE};'
        f'border-radius:6px" width="{100 // len(pares)}%">'
        f'<div style="font-size:26px;font-weight:bold;color:{AZUL};line-height:1.1">{v}</div>'
        f'<div style="font-size:11px;color:{GRIS};text-transform:uppercase;'
        f'letter-spacing:.05em;padding-top:2px">{html.escape(e)}</div></td>'
        + ('<td style="width:8px"></td>' if i < len(pares) - 1 else '')
        for i, (v, e) in enumerate(pares)
    )
    return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            f'style="width:100%;border-collapse:separate"><tr>{celdas}</tr></table>')


def _insignia(puntaje):
    """Color del puntaje: verde si encaja, gris si no. Mismo tamano siempre."""
    if puntaje >= 60:
        fondo, texto = '#059669', '#ffffff'
    elif puntaje >= 30:
        fondo, texto = '#d1fae5', '#065f46'
    else:
        fondo, texto = '#f3f4f6', GRIS
    return (f'<span style="display:inline-block;min-width:26px;padding:1px 5px;'
            f'background-color:{fondo};color:{texto};border-radius:4px;font-size:11px;'
            f'font-weight:bold;text-align:center">{puntaje}</span>')


def _listado(df):
    """Las ofertas agrupadas por ciudad, con link. Es lo que hace el correo accionable."""
    bloques = []

    # Las ciudades con mas ofertas primero; 'Otras' y 'Sin ubicacion' al final.
    orden = df['ciudad'].value_counts()
    postergadas = [c for c in ('Otras', 'Sin ubicacion') if c in orden.index]
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
                f'vertical-align:top;width:34px">{_insignia(int(fila.puntaje))}</td>'
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

    `nuevos` es el DataFrame de ofertas nuevas. Se le anaden al vuelo las columnas
    'ciudad' y 'familia'; no se guardan en el CSV.
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

    df['ciudad'] = df['location'].map(ciudad_normalizada) if 'location' in df.columns \
        else 'Sin ubicacion'
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

        _kpis([(total, 'ofertas'), (interesantes, 'te encajan'),
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
