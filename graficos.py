r"""Piezas visuales del correo: barras, KPIs e insignias.

Por que barras en HTML y no imagenes: un correo no ejecuta JavaScript ni renderiza SVG,
y un PNG tiene tamano fijo (se lee mal en el celular y arrastra su fondo blanco al modo
oscuro). Una barra hecha con una celda de tabla y un color de fondo se ve igual en Gmail
web, Gmail movil y Outlook, se reajusta al ancho y admite links al lado.

Por eso todo el HTML de aqui usa tablas con estilos en linea: nada de flexbox, grid,
<style> en el head, SVG ni imagenes.

Este modulo no sabe nada de empleos: recibe etiquetas y numeros ya ordenados y devuelve
HTML. Que va en cada grafico y en que orden lo decide reporte.py.
"""
import html

# Paleta con contraste suficiente en fondo claro y oscuro.
AZUL = "#67b6e4"
AZUL_SUAVE = '#dbeafe'
VERDE = "#7BE79D"
GRIS = '#6b7280'
GRIS_BORDE = '#e5e7eb'
TEXTO = '#111827'
FONDO = '#ffffff'

MAX_BARRAS = 8  # mas de esto y el grafico se vuelve una lista larga


def barra(etiqueta, valor, maximo, color=AZUL):
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


def grafico(titulo, conteos, color=AZUL, limite=MAX_BARRAS):
    """Bloque de titulo + barras a partir de un Series de conteos YA ORDENADO.

    No reordena nada: se queda con las `limite` primeras tal como llegan. Quien llama
    decide el criterio (ver _postergar_cajones en reporte.py).
    """
    if not len(conteos):
        return ''

    serie = conteos.head(limite)
    maximo = int(serie.max())

    filas = ''.join(barra(k, int(v), maximo, color) for k, v in serie.items())
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


def kpis(pares):
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


def insignia(puntaje):
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
