r"""Que habilidades pide cada oferta, sacadas de su descripcion.

Lee data/descripciones.csv y escribe data/habilidades.csv en formato largo: una fila por
oferta y habilidad (id, habilidad, grupo). Para Power BI es una tabla puente relacionada
con el historico por id: "% de ofertas que piden SQL" es una medida directa, y anadir una
habilidad aqui no cambia la forma del archivo.

Se regenera entero en cada corrida (segundos): si se cambia la lista, el archivo refleja
la lista nueva sobre todas las descripciones guardadas, no solo sobre las de hoy.

Ojo al leerlo: solo cubre ofertas CON descripcion (Multitrabajos e Indeed). El
denominador de cualquier porcentaje es descripciones.csv, no el historico entero.
"""
import os

import pandas as pd

from perfil import _coincide, _norm

# Grupo -> habilidad -> como se escribe en las ofertas. Los sinonimos se escriben con
# naturalidad (mayusculas, tildes): se normalizan igual que el texto. Se buscan como
# palabra completa, asi que 'excel' no coincide con 'excelente'.
# Lista medida el 05/10/2026 sobre ofertas reales de las dos familias en Multitrabajos:
# las anadidas aparecen en el 7-70% de esas ofertas. "Eficiencia" y "productividad" salen
# mucho pero no son habilidades, por eso no estan.
HABILIDADES = {
    'Datos / BI': {
        'SQL': ['SQL', 'SQL Server', 'MySQL', 'PostgreSQL', 'T-SQL', 'PL/SQL'],
        'Power BI': ['Power BI', 'PowerBI', 'DAX', 'Power Query'],
        'Excel': ['Excel', 'tablas dinámicas', 'macros', 'VBA'],
        'Python': ['Python', 'pandas'],
        'Tableau': ['Tableau'],
        'ETL': ['ETL'],
        'Estadística': ['estadística', 'estadístico', 'statistics', 'statistical'],
        'Dashboards': ['dashboard', 'dashboards', 'tableros', 'tablero de control',
                       'visualización de datos'],
        'Reportería': ['reportes', 'reportería', 'informes de gestión'],
        'Bases de datos': ['base de datos', 'bases de datos', 'modelado de datos',
                           'data warehouse'],
    },
    'Procesos / mejora continua': {
        'Mejora continua': ['mejora continua', 'continuous improvement'],
        'Lean': ['Lean', 'Lean Manufacturing'],
        '5S': ['5S', '5 S'],
        'Kaizen': ['Kaizen'],
        'BPMN': ['BPMN', 'Bizagi', 'Visio'],
        # "Procedimientos" a secas tambien es "cumplir procedimientos": solo cuentan las
        # frases de documentar, que es la habilidad.
        'Documentación de procesos': [
            'documentación de procesos', 'documentar procesos', 'documentar procedimientos',
            'levantamiento de procesos', 'levantar procesos', 'mapeo de procesos',
            'flujogramas', 'diagramas de flujo', 'manual de procedimientos',
            'manuales de procedimientos', 'elaboración de procedimientos',
            'actualización de procedimientos', 'instructivos'],
        'Optimización de procesos': ['optimización de procesos', 'optimizar procesos',
                                     'rediseño de procesos'],
        'Gestión por procesos (BPM)': ['gestión por procesos', 'BPM',
                                       'business process management'],
        'Automatización': ['automatización', 'automatizar', 'RPA', 'Power Automate'],
        'Análisis de causa raíz': ['causa raíz', 'Ishikawa', '5 porqués', '5 por qués'],
        'Gestión de proyectos': ['gestión de proyectos', 'Scrum', 'metodologías ágiles'],
        'KPI': ['KPI', 'KPIs', 'indicadores'],
    },
    # Referencia: el usuario no lo trabaja, pero quiere ver cuanto lo pide el mercado
    # (en ofertas de procesos, Six Sigma ~23% e ISO 9001 ~19%). Filtrable en Power BI.
    'Calidad (referencia)': {
        'Six Sigma': ['Six Sigma', 'Seis Sigma', 'Green Belt', 'Black Belt'],
        'ISO 9001': ['ISO 9001', 'ISO 9001:2015'],
        'Sistema de gestión de calidad': ['sistema de gestión de calidad', 'SGC'],
        'BPM (manufactura)': ['buenas prácticas de manufactura'],
    },
}

# En Ecuador "BPM" tambien es Buenas Practicas de Manufactura (industria alimentaria).
# Medido: 1 de cada 7 "BPM" en ofertas de procesos. Si la oferta lo dice, BPM a secas no
# cuenta como gestion por procesos (va a 'BPM (manufactura)').
AMBIGUOS = {'BPM': 'buenas prácticas de manufactura'}

NOMBRE = 'habilidades.csv'
COLUMNAS = ['id', 'habilidad', 'grupo']


def detectar(texto):
    """[(habilidad, grupo), ...] que aparecen en el texto."""
    t = _norm(texto)
    ignorar = {s for s, aviso in AMBIGUOS.items() if _coincide(_norm(aviso), t)}
    return [(habilidad, grupo)
            for grupo, habilidades in HABILIDADES.items()
            for habilidad, sinonimos in habilidades.items()
            if any(_coincide(_norm(s), t) for s in sinonimos if s not in ignorar)]


def regenerar(dir_datos='data'):
    """Reescribe habilidades.csv a partir de descripciones.csv. Devuelve las filas escritas.

    Nunca falla: es un derivado, y un error aqui no debe dejar sin correo una corrida
    cuyo historico ya se escribio. Se puede rehacer en cualquier momento.
    """
    origen = os.path.join(dir_datos, 'descripciones.csv')
    destino = os.path.join(dir_datos, NOMBRE)
    try:
        if not os.path.exists(origen):
            return 0
        desc = pd.read_csv(origen, dtype=str).dropna(subset=['description'])
        filas = [(id_, h, g) for id_, texto in zip(desc['id'], desc['description'])
                 for h, g in detectar(texto)]
        tmp = destino + '.tmp'
        pd.DataFrame(filas, columns=COLUMNAS).to_csv(tmp, index=False, encoding='utf-8-sig')
        os.replace(tmp, destino)
        return len(filas)
    except Exception as e:
        print(f'[AVISO] no se pudo regenerar {destino}: {e}')
        return 0


if __name__ == '__main__':
    print(f'[OK] {regenerar()} filas en data/{NOMBRE}')
