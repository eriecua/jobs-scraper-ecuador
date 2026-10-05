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
# Calidad (ISO 9001, Six Sigma, 5S) fuera a proposito: no le interesa al usuario.
HABILIDADES = {
    'Datos / BI': {
        'SQL': ['SQL', 'SQL Server', 'MySQL', 'PostgreSQL', 'T-SQL', 'PL/SQL'],
        'Power BI': ['Power BI', 'PowerBI', 'DAX', 'Power Query'],
        'Excel': ['Excel', 'tablas dinámicas', 'macros', 'VBA'],
        'Python': ['Python', 'pandas'],
        'Tableau': ['Tableau'],
        'ETL': ['ETL'],
        'Estadística': ['estadística', 'estadístico', 'statistics', 'statistical'],
    },
    'Procesos / mejora continua': {
        'Lean': ['Lean', 'Lean Manufacturing'],
        'Kaizen': ['Kaizen'],
        'BPMN': ['BPMN', 'Bizagi'],
        'KPI': ['KPI', 'KPIs', 'indicadores de gestión'],
    },
}

NOMBRE = 'habilidades.csv'
COLUMNAS = ['id', 'habilidad', 'grupo']


def detectar(texto):
    """[(habilidad, grupo), ...] que aparecen en el texto."""
    t = _norm(texto)
    return [(habilidad, grupo)
            for grupo, habilidades in HABILIDADES.items()
            for habilidad, sinonimos in habilidades.items()
            if any(_coincide(_norm(s), t) for s in sinonimos)]


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
