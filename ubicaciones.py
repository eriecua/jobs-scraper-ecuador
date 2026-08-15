r"""Ubicaciones de Ecuador: convierte el texto crudo de cada sitio en (ciudad, provincia).

Los tres sitios escriben la misma ciudad de forma distinta. Medido sobre el historico:
19 textos distintos para 6 ciudades reales.

    'Quito, Pichincha, Ecuador'   (LinkedIn)
    'Quito, Pichincha'            (Computrabajo)
    'Quito, P, EC'                (Indeed, provincia abreviada a una letra)
    'Quito Canton, Pichincha, Ecuador'
    'Eloy Alfaro, G, EC'          (parroquia, no canton)

Antes esto vivia repartido en tres tablas de reporte.py y solo servia para el grafico del
correo. Aqui es una sola tabla y el resultado se guarda en el CSV, que es donde hace falta
para poder filtrar en Excel.

CIUDAD Y PROVINCIA SON COSAS DISTINTAS. La version anterior fundia la provincia entera en
su capital, asi que Samborondon y Daule se contaban como Guayaquil. Son cantones aparte:
Guayaquil es la ciudad, Guayas la provincia. Cuando el texto solo nombra la provincia, la
ciudad queda vacia; no se inventa la capital.
"""
import re
import unicodedata

# Las 24 provincias. La clave es la forma normalizada; el valor, como se muestra.
PROVINCIAS = {
    'azuay': 'Azuay',
    'bolivar': 'Bolivar',
    'canar': 'Canar',
    'carchi': 'Carchi',
    'chimborazo': 'Chimborazo',
    'cotopaxi': 'Cotopaxi',
    'el oro': 'El Oro',
    'esmeraldas': 'Esmeraldas',
    'galapagos': 'Galapagos',
    'guayas': 'Guayas',
    'imbabura': 'Imbabura',
    'loja': 'Loja',
    'los rios': 'Los Rios',
    'manabi': 'Manabi',
    'morona santiago': 'Morona Santiago',
    'napo': 'Napo',
    'orellana': 'Orellana',
    'pastaza': 'Pastaza',
    'pichincha': 'Pichincha',
    'santa elena': 'Santa Elena',
    'santo domingo de los tsachilas': 'Santo Domingo de los Tsachilas',
    'sucumbios': 'Sucumbios',
    'tungurahua': 'Tungurahua',
    'zamora chinchipe': 'Zamora Chinchipe',
}

# Canton -> (nombre presentable, clave de su provincia). La provincia sale SIEMPRE de
# aqui, no del texto: asi 'Quito' es Pichincha aunque el sitio la escriba mal o la calle.
CANTONES = {
    'quito': ('Quito', 'pichincha'),
    'guayaquil': ('Guayaquil', 'guayas'),
    'cuenca': ('Cuenca', 'azuay'),
    'santo domingo': ('Santo Domingo', 'santo domingo de los tsachilas'),
    'la concordia': ('La Concordia', 'santo domingo de los tsachilas'),
    'ambato': ('Ambato', 'tungurahua'),
    'manta': ('Manta', 'manabi'),
    'machala': ('Machala', 'el oro'),
    'loja': ('Loja', 'loja'),
    'ibarra': ('Ibarra', 'imbabura'),
    'riobamba': ('Riobamba', 'chimborazo'),
    'esmeraldas': ('Esmeraldas', 'esmeraldas'),
    'portoviejo': ('Portoviejo', 'manabi'),
    'duran': ('Duran', 'guayas'),
    'samborondon': ('Samborondon', 'guayas'),
    'daule': ('Daule', 'guayas'),
    'quevedo': ('Quevedo', 'los rios'),
    'milagro': ('Milagro', 'guayas'),
    'latacunga': ('Latacunga', 'cotopaxi'),
    'babahoyo': ('Babahoyo', 'los rios'),
    'salinas': ('Salinas', 'santa elena'),
    'otavalo': ('Otavalo', 'imbabura'),
    'tulcan': ('Tulcan', 'carchi'),
    'azogues': ('Azogues', 'canar'),
}

# Parroquias y otros nombres que no son cantones. La clave lleva provincia porque el mismo
# nombre existe en varias: 'Eloy Alfaro' es parroquia de Duran en Guayas, canton propio en
# Esmeraldas y parroquia de Manta en Manabi. Sin la provincia no se puede desambiguar.
ALIAS = {
    ('eloy alfaro', 'guayas'): 'duran',
    ('comuna colorados de peripa', 'santo domingo de los tsachilas'): 'santo domingo',
    # Parroquias de Quito que LinkedIn antepone en vez del canton.
    ('cumbaya', 'pichincha'): 'quito',
    ('tumbaco', 'pichincha'): 'quito',
    ('calderon', 'pichincha'): 'quito',
    ('conocoto', 'pichincha'): 'quito',
}

# Indeed abrevia la PROVINCIA a una letra: 'Eloy Alfaro, G, EC'. Antes esta tabla mapeaba
# la letra directo a una ciudad ('g' -> 'Guayaquil'), que mezclaba los dos niveles y era
# justo lo que convertia Eloy Alfaro en Guayaquil.
ABREVIATURAS = {
    'p': 'pichincha', 'g': 'guayas', 'a': 'azuay', 't': 'tungurahua',
    'm': 'manabi', 'o': 'el oro', 'i': 'imbabura', 'h': 'chimborazo',
    'l': 'loja', 'sd': 'santo domingo de los tsachilas', 'c': 'cotopaxi',
    'r': 'los rios',
}

# Sufijos de pais que no aportan nada y estorban al buscar la provincia al final.
_PAIS = ('ecuador', 'ec', '')

_REMOTO = ('remoto', 'remote', 'desde casa', 'teletrabajo')

# Los cantones se prueban de mas largo a mas corto: 'la concordia' antes que 'concordia'
# si algun dia se anade, y en general para que un nombre compuesto no lo gane uno corto.
_CANTONES_POR_LARGO = sorted(CANTONES, key=len, reverse=True)


def _norm(texto):
    """Minusculas sin acentos y con espacios simples, para comparar sin sorpresas."""
    limpio = unicodedata.normalize('NFKD', str(texto).lower())
    limpio = limpio.encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', limpio).strip()


def _coincide(termino, texto):
    """Busca el termino como palabra completa, igual que perfil._coincide.

    Con 'in' a secas, 'loja' saltaria dentro de otra palabra y 'manta' dentro de
    'mantarraya'.
    """
    return re.search(rf'(?<![a-z0-9]){re.escape(termino)}(?![a-z0-9])', texto) is not None


def normalizar(location):
    """Devuelve (ciudad, provincia) a partir de la ubicacion cruda de cualquier sitio.

    Ambas pueden venir vacias, y eso es informacion, no un fallo: 'Pichincha, Ecuador' no
    nombra ningun canton, asi que la ciudad queda vacia en vez de inventar 'Quito'.

    Se trabaja por COMPONENTES separados por coma, no sobre la cadena entera. Escanear
    todo el texto rompe con 'Esmeraldas, Esmeraldas' (canton y provincia se llaman igual)
    y con 'La Concordia, Santo Domingo de los Tsachilas', donde el nombre de un canton
    esta contenido dentro del de la provincia y ganaria el canton equivocado.
    """
    texto = _norm(location)
    if not texto or texto == 'nan':
        return '', ''

    if any(marca in texto for marca in _REMOTO):
        return 'Remoto', ''

    partes = [p.strip() for p in texto.split(',')]
    while partes and partes[-1] in _PAIS:
        partes.pop()

    # La provincia se busca desde el final: es donde la escriben los tres sitios, y asi
    # 'Esmeraldas, Esmeraldas' entrega la segunda como provincia y deja libre la primera.
    provincia = ''
    for i in range(len(partes) - 1, -1, -1):
        if partes[i] in PROVINCIAS:
            provincia = partes[i]
        elif partes[i] in ABREVIATURAS:
            provincia = ABREVIATURAS[partes[i]]
        else:
            continue
        partes.pop(i)
        break

    for parte in partes:
        if parte in CANTONES:
            nombre, prov = CANTONES[parte]
            return nombre, PROVINCIAS[prov]

    if provincia:
        for parte in partes:
            destino = ALIAS.get((parte, provincia))
            if destino:
                nombre, prov = CANTONES[destino]
                return nombre, PROVINCIAS[prov]

    # Ultimo recurso: el canton nombrado dentro de un componente mas largo, como
    # 'Quito Canton'. Va al final para no ganarle a una coincidencia exacta.
    for parte in partes:
        for canton in _CANTONES_POR_LARGO:
            if _coincide(canton, parte):
                nombre, prov = CANTONES[canton]
                return nombre, PROVINCIAS[prov]

    return '', PROVINCIAS.get(provincia, '')


def etiqueta(ciudad, provincia):
    """Como se muestra la ubicacion en el correo.

    Cuando solo se conoce la provincia se dice '(prov.)' en vez de callarlo: agrupar una
    provincia entera bajo su capital es exactamente el error que este modulo corrige.
    """
    if ciudad:
        return ciudad
    if provincia:
        return f'{provincia} (prov.)'
    return 'Sin ubicacion'
