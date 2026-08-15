# Búsquedas predefinidas
SEARCHES = [
    {
        'name': 'Ingeniero Industrial',
        'search_term': 'Ingeniero Industrial',
        'location': 'Santo Domingo, Ecuador',
        'results_wanted': 200,
        'job_type': 'fulltime',
        'hours_old': 168,
    },
    {
        'name': 'Analista de Datos',
        'search_term': 'Data Analyst',
        'location': 'Santo Domingo, Ecuador',
        'results_wanted': 150,
    },
    {
        'name': 'Procesos',
        'search_term': 'Procesos',
        'location': 'Santo Domingo, Ecuador',
        'results_wanted': 100,
        'distance': 25,
    },
    {
        'name': 'Python Ecuador (Computrabajo)',
        'search_term': 'Python',
        'site': 'computrabajo',
        'pais': 'ec',
        'max_paginas': 5,
        'retraso': 2,
    },
    {
        'name': 'Ingenieria Industrial (Computrabajo)',
        'search_term': 'ingeniero industrial',
        'site': 'computrabajo',
        'pais': 'ec',
        'max_paginas': 5,
        'retraso': 2,
    },
]

# Configuración por defecto
DEFAULT_CONFIG = {
    'site': 'linkedin',
    'results_wanted': 100,
    'distance': 50,
    'output_dir': 'data',
}