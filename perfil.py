r"""Indice de compatibilidad: que tanto encaja una oferta con lo que buscas.

Se calcula SOLO con el titulo, a proposito. Solo el 26% de las ofertas trae descripcion
(y toda de Indeed), asi que puntuar con ella dejaria fuera a 3 de cada 4. El titulo esta
siempre.

Para ajustarlo, edita las listas de abajo: son la unica parte que se toca.
"""
import re
import unicodedata

# --------------------------------------------------------------------------
# TUS TERMINOS. Esto es lo que se edita.
# --------------------------------------------------------------------------

# NUCLEO: de que va el puesto. Sin al menos uno de estos, la oferta no interesa
# y saca 0 por mucho que coincidan los deseables.
NUCLEO = {
    'business intelligence': 30,
    'inteligencia de negocios': 30,
    'ingeniero industrial': 30,
    'ingenieria industrial': 30,
    'analista': 30,
    'analyst': 30,
    'datos': 30,
    'data': 30,
    'mejora continua': 25,
    'procesos': 25,
    'bi': 25,
    'planificacion': 20,
    'planner': 20,
    'planificador': 20,
}

# DESEABLES: suman encima del nucleo, pero por si solos no valen nada.
DESEABLES = {
    'python': 15,
    'sql': 15,
    'power bi': 15,
    'tableau': 10,
    'etl': 12,
    'dashboard': 10,
    'reporteria': 10,
    'estadistic': 10,
    'excel': 8,
    'automatizacion': 8,
    'kpi': 8,
}

# EXCLUIDOS: temas que no te interesan. Mandan sobre todo lo demas: la oferta saca 0.
EXCLUIDOS = [
    'ventas', 'vendedor', 'comercial', 'call center', 'cajero', 'cajera',
    'chofer', 'conductor', 'repartidor', 'seguridad', 'guardia', 'limpieza',
    'mesero', 'cocinero', 'empleada domestica',
]

# NIVEL: solo etiqueta lo que el titulo deja ver. NO suma ni resta al puntaje: muchos
# titulos no dicen el nivel, y castigarlos por callarlo seria inventar informacion.
NIVELES = {
    'Practicas': ['practicante', 'pasante', 'pasantia', 'intern', 'trainee'],
    'Junior': ['junior', ' jr', 'jr.', 'auxiliar', 'asistente'],
    'Senior': ['senior', ' sr', 'sr.', 'especialista', 'lead', 'experto'],
    'Jefatura': ['jefe', 'gerente', 'director', 'manager', 'coordinador',
                 'supervisor', 'head of'],
}

MAXIMO = 100


def _norm(texto):
    """Minusculas sin acentos y con espacios simples, para comparar sin sorpresas."""
    limpio = unicodedata.normalize('NFKD', str(texto).lower())
    limpio = limpio.encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', limpio).strip()


def _coincide(termino, texto):
    """Busca el termino como palabra completa.

    Con 'in' a secas, 'bi' coincidiria dentro de 'combinado' y 'data' dentro de
    'datacenter', inflando el puntaje con falsos positivos.
    """
    return re.search(rf'(?<![a-z0-9]){re.escape(termino)}(?![a-z0-9])', texto) is not None


def nivel(titulo):
    """Etiqueta de nivel segun el titulo, o None si no lo dice. Solo informativo."""
    t = f' {_norm(titulo)} '
    for etiqueta, claves in NIVELES.items():
        if any(clave.strip() and clave in t for clave in claves):
            return etiqueta
    return None


def puntuar(titulo):
    """Devuelve (puntaje 0-100, lista de terminos que coincidieron).

    Los terminos devueltos son la explicacion: el correo los muestra para que se vea
    por que una oferta saco lo que saco, y puedas corregir las listas de arriba.
    """
    t = _norm(titulo)
    if not t:
        return 0, []

    excluido = [e for e in EXCLUIDOS if _coincide(e, t)]
    if excluido:
        return 0, [f'-{excluido[0]}']

    del_nucleo = [(k, v) for k, v in NUCLEO.items() if _coincide(k, t)]
    if not del_nucleo:
        return 0, []

    deseables = [(k, v) for k, v in DESEABLES.items() if _coincide(k, t)]

    pesos = sorted((v for _, v in del_nucleo), reverse=True)
    # El termino mas fuerte del nucleo cuenta entero; los demas, a mitad de peso. Sumarlos
    # todos enteros haria que 'Analista de Datos' saliera disparado a 60 solo por decir
    # dos palabras del mismo tema, quedando por encima de ofertas mas especificas.
    puntos = pesos[0] + sum(pesos[1:]) // 2
    puntos += sum(v for _, v in deseables)

    terminos = [k for k, _ in del_nucleo] + [k for k, _ in deseables]
    return min(puntos, MAXIMO), terminos
