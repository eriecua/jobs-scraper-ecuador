r"""
Scraper de empleos (LinkedIn + Indeed + Computrabajo) con historico incremental.

Uso:  .\scrap "Data Analyst"
      .\scrap_diario.cmd          reporte diario por correo

jobspy exige numpy 1.26 y pandas 2.x, que no compilan en el Python 3.14 del sistema,
por eso scrap.cmd lo ejecuta en un entorno con Python 3.12 gestionado por uv.

Aqui solo viven la configuracion, la orquestacion y la linea de comandos. El trabajo de
verdad esta repartido:
    buscador.py     busca en los tres sitios
    computrabajo.py raspa Computrabajo (jobspy no lo cubre)
    historico.py    decide que es nuevo y guarda
    perfil.py       puntua cada oferta contra lo que buscas
    reporte.py      arma el correo
    correo.py       lo envia
"""
import argparse
import sys

import pandas as pd

import correo
import historico
import reporte
from buscador import SITIOS_DEFECTO, buscar

# --------------------------------------------------------------------------
# Configuracion del reporte diario (--diario). Editar a mano.
# --------------------------------------------------------------------------
CIUDADES = [
    'Quito, Ecuador',
    'Santo Domingo de los Tsachilas, Ecuador',
    'Guayaquil, Ecuador',
]
HORAS_DIARIO = 24        # ventana de la busqueda agendada
RESULTADOS_DIARIO = 100  # por sitio y por ciudad
ENVIAR_SI_VACIO = False  # si no hay nada nuevo, por defecto no manda correo

# Codigos de salida, para que la tarea agendada distinga que paso.
EXIT_OK = 0
EXIT_SCRAPE_FALLO = 1
EXIT_CORREO_FALLO = 2


def _ciudad_corta(ubicacion):
    """'Quito, Ecuador' -> 'Quito'. Para la columna ciudad_busqueda del CSV."""
    return ubicacion.split(',')[0].strip()


def ejecutar_diario():
    """Recorre CIUDADES, actualiza el historico y manda el correo. Devuelve exit code."""
    # Se comprueban ANTES de scrapear: si no, el historico ya marco las ofertas como
    # vistas y no volverian a salir en ningun correo futuro.
    faltan = correo.faltan_credenciales()
    if faltan:
        print(f"[ERROR] Faltan {', '.join(faltan)}: no se scrapea nada para no "
              f"marcar ofertas como vistas sin poder avisarte")
        return EXIT_CORREO_FALLO

    partes, fallos_por_ciudad = [], 0

    for ciudad in CIUDADES:
        df, fallidos = buscar(
            termino='',
            ubicacion=ciudad,
            resultados=RESULTADOS_DIARIO,
            horas=HORAS_DIARIO,
        )
        if fallidos and df.empty:
            fallos_por_ciudad += 1
        if not df.empty:
            partes.append(df.assign(ciudad_busqueda=_ciudad_corta(ciudad)))

    if fallos_por_ciudad == len(CIUDADES):
        print('[ERROR] Todos los sitios fallaron en todas las ciudades')
        return EXIT_SCRAPE_FALLO

    if not partes:
        print('[AVISO] Sin resultados en ninguna ciudad')
        return EXIT_OK

    df = pd.concat([p.dropna(axis=1, how='all') for p in partes], ignore_index=True)
    nuevos = historico.actualizar(df, 'diario')
    print(f'[OK] {len(df)} empleos ({len(nuevos)} nuevos desde la ultima corrida)')

    if nuevos.empty and not ENVIAR_SI_VACIO:
        print('[OK] Nada nuevo: no se envia correo')
        return EXIT_OK

    ruta = historico.guardar(nuevos, 'diario') if not nuevos.empty else None
    asunto, cuerpo = reporte.construir(nuevos, horas=HORAS_DIARIO)
    return EXIT_OK if correo.enviar(asunto, cuerpo, ruta) else EXIT_CORREO_FALLO


def main():
    parser = argparse.ArgumentParser(
        description='Scraper de empleos (LinkedIn + Indeed + Computrabajo)')
    parser.add_argument('termino', nargs='?', default='',
                        help='Puesto a buscar. Ej: "Data Analyst". '
                             'Si lo omites, trae todos los puestos de la ubicacion')
    parser.add_argument('--ubicacion', default='Ecuador', help='Ubicacion (default: Ecuador)')
    parser.add_argument('--resultados', type=int, default=100,
                        help='Cuantos empleos POR SITIO (default: 100)')
    parser.add_argument('--sitios', default=','.join(SITIOS_DEFECTO),
                        help=f"Sitios separados por coma (default: {','.join(SITIOS_DEFECTO)})")
    parser.add_argument('--pais', default='ecuador', help='Pais para Indeed (default: ecuador)')
    parser.add_argument('--horas', type=int, help='Solo ofertas de las ultimas N horas')
    parser.add_argument('--tipo', choices=['fulltime', 'parttime', 'contract', 'internship'],
                        help='Tipo de empleo')
    parser.add_argument('--distancia', type=int, default=50, help='Radio en km (default: 50)')
    parser.add_argument('--descripcion', action='store_true',
                        help='Incluir la descripcion completa (mucho mas lento)')
    parser.add_argument('--diario', action='store_true',
                        help='Reporte agendado: recorre CIUDADES y manda el correo. '
                             'Ignora el resto de opciones (usa la config del archivo)')
    args = parser.parse_args()

    if args.diario:
        return ejecutar_diario()

    df, fallidos = buscar(
        termino=args.termino,
        ubicacion=args.ubicacion,
        resultados=args.resultados,
        horas=args.horas,
        tipo=args.tipo,
        distancia=args.distancia,
        con_descripcion=args.descripcion,
        sitios=[s.strip() for s in args.sitios.split(',') if s.strip()],
        pais=args.pais,
    )

    if df.empty:
        # "Cero ofertas" sale 0; "todos los sitios reventaron" sale 1, para que una tarea
        # agendada pueda avisar de la averia en vez de tragarsela.
        if fallidos:
            print("[ERROR] Todos los sitios fallaron")
            return EXIT_SCRAPE_FALLO
        print("[AVISO] Sin resultados")
        return EXIT_OK

    # Sin puesto, la busqueda se identifica por la ubicacion.
    etiqueta = args.termino or args.ubicacion
    nuevos = historico.actualizar(df, etiqueta)
    print(f"[OK] {len(df)} empleos ({len(nuevos)} nuevos desde la ultima corrida)")

    if nuevos.empty:
        print("[OK] Nada nuevo: solo se actualizo el historico")
        return EXIT_OK

    historico.guardar(nuevos, f'nuevos_{etiqueta}')
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
