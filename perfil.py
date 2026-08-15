r"""Indice de compatibilidad: que tanto encaja una oferta con lo que buscas.

Dos mecanismos con papeles distintos, y no conviene confundirlos:

    INTERES + DESEABLES  ORDENAN. Suben la oferta en la lista, nunca la eliminan.
    EXCLUIDOS + FAMILIAS_EXCLUIDAS  QUITAN. Vetan la oferta entera.

Exigir un termino de interes (como se hacia antes) mandaba a 0 el 68% de las ofertas y
enterraba cosas como "JEFE UNIDAD DE ESTADISTICA" o "Database Consultant" solo por no
decir la palabra exacta. En una busqueda dirigida el filtro ya lo hizo el propio sitio;
en el diario, exigirlo era perder ofertas sin saber cuales.

Se calcula SOLO con el titulo, a proposito. Solo el 26% de las ofertas trae descripcion
(y toda de Indeed), asi que puntuar con ella dejaria a ciegas a 3 de cada 4.

Para ajustarlo, edita las listas de abajo: son la unica parte que se toca.
"""
import re
import unicodedata

# --------------------------------------------------------------------------
# TUS TERMINOS. Esto es lo que se edita.
# --------------------------------------------------------------------------

# INTERES: de que va el puesto que buscas. Suma puntos y sube la oferta en la lista.
# NO es obligatorio: una oferta sin ninguno de estos sale igual, solo que mas abajo.
INTERES = {
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
    'optimización': 20,
    'inteligencia artificial': 20,
}

# DESEABLES: herramientas y detalles que suman encima.
DESEABLES = {
    'python': 15,
    'sql': 15,
    'power bi': 15,
    'tableau': 10,
    'etl': 12,
    'dashboard': 10,
    'reporteria': 10,
    # Los terminos se comparan como PALABRA COMPLETA, asi que una raiz como 'estadistic'
    # no coincide nunca: hay que escribir cada forma.
    'estadistica': 10,
    'estadistico': 10,
    'excel': 8,
    'automatizacion': 8,
    'kpi': 8,
    'indicadores': 8,
    'base de datos': 8,
    'VBA': 5,
    'Power Query': 5,
    'Project': 5,
}

# EXCLUIDOS: temas que no quieres ver. Vetan la oferta entera, no la puntuan bajo.
# Medido sobre el historico: quitan 86 ofertas y ni una sola tenia terminos de interes,
# asi que no hay riesgo de que se lleven por delante algo que si te servia.
EXCLUIDOS = [
    'ventas', 'vendedor', 'comercial', 'call center', 'cajero', 'cajera',
    'chofer', 'conductor', 'repartidor', 'seguridad', 'guardia', 'limpieza',
    'mesero', 'cocinero', 'empleada domestica',
    # LinkedIn publica mucho en ingles: sin esto se colaban 'Sales Development
    # Representative' y similares. No afecta a 'Salesforce Administrator', porque la
    # comparacion es por palabra completa y ahi 'sales' va pegado a 'force'.
    'sales',
]

# FAMILIAS_EXCLUIDAS: descarta categorias enteras, no palabra por palabra. Los nombres
# son los de FAMILIAS en reporte.py ('Ventas', 'Seguridad', 'Limpieza/Servicios',
# 'Salud', 'Educacion', 'Construccion'...). Vacia por defecto: EXCLUIDOS ya cubre lo
# que hoy molesta, y activar esto de golpe escondería mucho sin avisar.
FAMILIAS_EXCLUIDAS = []

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


def _normalizar(terminos, nombre):
    """Pasa las listas de arriba por _norm, para que se puedan escribir con naturalidad.

    Antes las claves se comparaban tal cual contra un titulo ya normalizado, asi que
    'Power BI', 'VBA' u 'optimizacion' con tilde no coincidian NUNCA y nadie se enteraba.
    Escribir los terminos como uno los diria es lo normal; normalizarlos es cosa del
    codigo, no del que edita la lista.
    """
    es_dict = isinstance(terminos, dict)
    salida = {} if es_dict else []
    vistos = {}

    for clave in terminos:
        limpia = _norm(clave)
        if not limpia:
            continue
        if limpia in vistos:
            print(f"   [AVISO] perfil.py: '{clave}' y '{vistos[limpia]}' son el mismo "
                  f"termino en {nombre}; se conserva el peso mas alto")
        if es_dict:
            salida[limpia] = max(salida.get(limpia, 0), terminos[clave])
        elif limpia not in salida:
            salida.append(limpia)
        vistos[limpia] = clave

    return salida


# Se normalizan una vez al cargar el modulo, no en cada comparacion.
_INTERES = _normalizar(INTERES, 'INTERES')
_DESEABLES = _normalizar(DESEABLES, 'DESEABLES')
_EXCLUIDOS = _normalizar(EXCLUIDOS, 'EXCLUIDOS')
# NIVELES no se normaliza: sus claves usan el espacio inicial (' jr', ' sr') para no
# coincidir dentro de otra palabra, y quitarselo las volveria imprecisas.


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


def excluir(titulo, familia=None):
    """Motivo por el que la oferta se veta, o None si no se veta.

    Devolver el motivo y no un simple True/False es lo que permite que el correo diga
    QUE termino esta recortando y cuanto. Sin eso, la exclusion es una caja negra.
    """
    t = _norm(titulo)
    for termino in _EXCLUIDOS:
        if _coincide(termino, t):
            return termino
    if familia and familia in FAMILIAS_EXCLUIDAS:
        return f'familia: {familia}'
    return None


def puntuar(titulo):
    """Devuelve (puntaje 0-100, lista de terminos que coincidieron).

    Puntaje 0 significa "no coincide con nada tuyo", NO "descartada": la oferta sale
    igual, mas abajo en la lista. Para descartar esta excluir().

    Los terminos devueltos son la explicacion: el correo los muestra para que se vea
    por que una oferta saco lo que saco, y puedas corregir las listas de arriba.
    """
    t = _norm(titulo)
    if not t:
        return 0, []

    del_interes = [(k, v) for k, v in _INTERES.items() if _coincide(k, t)]
    deseables = [(k, v) for k, v in _DESEABLES.items() if _coincide(k, t)]

    if not del_interes and not deseables:
        return 0, []

    puntos = 0
    if del_interes:
        pesos = sorted((v for _, v in del_interes), reverse=True)
        # El termino mas fuerte cuenta entero; los demas, a mitad de peso. Sumarlos todos
        # enteros dispararia 'Analista de Datos' a 60 solo por decir dos palabras del
        # mismo tema, por encima de ofertas mas especificas.
        puntos = pesos[0] + sum(pesos[1:]) // 2

    # Las herramientas suman aunque no haya termino de interes: un titulo que solo diga
    # 'Consultor Python SQL' merece estar por encima de uno que no dice nada.
    puntos += sum(v for _, v in deseables)

    terminos = [k for k, _ in del_interes] + [k for k, _ in deseables]
    return min(puntos, MAXIMO), terminos
