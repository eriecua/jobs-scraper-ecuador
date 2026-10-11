r"""
Scraper de empleos (LinkedIn + Indeed + Computrabajo + Multitrabajos) con historico incremental.

Uso:  .\scrap.cmd "Data Analyst"       (Mac/Linux: ./scrap.sh "Data Analyst")
      .\scrap_diario.cmd               reporte diario por correo (./scrap_diario.sh)

jobspy exige numpy 1.26 y pandas 2.x, sin version precompilada para Python 3.13+,
por eso los lanzadores lo ejecutan en un entorno con Python 3.12 gestionado por uv.

Aqui solo viven la configuracion, la orquestacion y la linea de comandos. El trabajo de
verdad esta repartido:
    buscador.py     busca en todos los sitios
    computrabajo.py raspa Computrabajo (jobspy no lo cubre)
    multitrabajos.py raspa Multitrabajos por su API JSON (jobspy no lo cubre)
    historico.py    decide que es nuevo y guarda
    habilidades.py  que habilidades pide cada oferta, desde su descripcion
    perfil.py       puntua cada oferta contra lo que buscas
    ubicaciones.py  normaliza las 19 formas de escribir una ciudad
    reporte.py      decide que dice el correo y en que orden
    graficos.py     dibuja las barras, los KPIs y las insignias
    correo.py       lo envia
"""
import argparse
import os
import sys

import pandas as pd

import correo
import habilidades
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
    'Cuenca, Ecuador',
]
HORAS_DIARIO = 24        # ventana de la busqueda agendada
RESULTADOS_DIARIO = 100  # por sitio y por ciudad
# Radio de LinkedIn e Indeed alrededor de cada ciudad. Con 50 km la busqueda de Quito
# traia Latacunga (17 ofertas el 05/10, casi todas pasantias). 25 km deja Quito y sus
# valles (Sangolqui, Tumbaco, Cumbaya). Computrabajo y Multitrabajos no usan radio.
DISTANCIA_DIARIO = 25
ENVIAR_SI_VACIO = False  # si no hay nada nuevo, por defecto no manda correo

# Buzon que deja ingesta_google.py. Google corre aparte (Selenium, ~13 min) y no puede
# escribir el historico por su cuenta: actualizar() marca las ofertas como vistas, y el
# correo se arma con lo que devuelve la llamada de AQUI, no leyendo el CSV. Si Google
# escribiera antes, sus ofertas quedarian marcadas sin que nadie las reporte, que es
# justo lo que pasaba con las 71 primeras.
PENDIENTES_GOOGLE = os.path.join('data', 'google_pendientes.csv')

# Outbox del correo diario. historico.actualizar() marca las ofertas como vistas ANTES de
# enviar: si Gmail fallaba, esas ofertas no volvian a salir nunca. Ahora quedan aqui hasta
# que un envio sale bien, y la siguiente corrida las suma a sus nuevas. Archivo aparte y no
# una columna del historico: una columna obligaria a rellenar las filas viejas.
CORREO_PENDIENTE = os.path.join('data', 'correo_pendiente.csv')

# Codigos de salida, para que la tarea agendada distinga que paso.
EXIT_OK = 0
EXIT_SCRAPE_FALLO = 1
EXIT_CORREO_FALLO = 2
EXIT_ESCRITURA_FALLO = 3  # el historico estaba bloqueado (abierto en Excel)


def _ciudad_corta(ubicacion):
    """'Quito, Ecuador' -> 'Quito'. Para la columna ciudad_busqueda del CSV."""
    return ubicacion.split(',')[0].strip()


def _consolidar(piezas):
    """Une los DataFrames de varias busquedas en uno solo, sin URLs repetidas.

    dropna(axis=1) por pieza porque cada sitio devuelve columnas distintas y las que
    vienen 100% vacias solo estorban al concatenar.
    """
    df = pd.concat([p.dropna(axis=1, how='all') for p in piezas], ignore_index=True)
    return df.drop_duplicates(subset=['job_url'], keep='first').reset_index(drop=True)


def _registrar(df, etiqueta):
    """Actualiza el historico y avisa por consola. Devuelve solo las ofertas nuevas."""
    nuevos = historico.actualizar(df, etiqueta)
    print(f'[OK] {len(df)} empleos ({len(nuevos)} nuevos desde la ultima corrida)')
    if not nuevos.empty:
        habilidades.regenerar()
    return nuevos


def _google_pendientes(ruta=PENDIENTES_GOOGLE):
    """Reclama el buzon y devuelve lo que Google dejo esperando.

    Reclamar = renombrarlo antes de leerlo, no leerlo y ya. Google arranca a las 07:30 y
    tarda ~13 min, asi que normalmente termina mucho antes que el diario de las 08:00 --
    pero la tarea lleva StartWhenAvailable, y si el PC arranca tarde su ingesta puede caer
    DENTRO de esta corrida. Sin reclamar:

        08:00:01  el diario lee el buzon        -> [A, B]
        08:00:20  Google anade C                -> [A, B, C]
        08:00:45  el diario borra el buzon      -> C desaparece, sin error ni aviso

    Renombrando primero, lo que Google escriba va a un buzon nuevo y entra manana.

    El .enproceso que quedo de una corrida anterior tambien se recoge: si el historico
    estaba bloqueado (Excel abierto), esas ofertas se reclamaron y nunca se escribieron.
    Sin esto, reclamar cambiaria una carrera rara por una perdida frecuente.
    """
    reclamado = ruta + '.enproceso'

    piezas, leidos = [], []
    for origen in (reclamado, ruta):  # el reclamado primero: es lo mas viejo
        if not os.path.exists(origen):
            continue
        try:
            piezas.append(pd.read_csv(origen, dtype=str).fillna(''))
            leidos.append(origen)
        except Exception as fallo:
            # Un buzon ilegible no puede tumbar el correo: es un extra, no el plato
            # principal. No se borra, para poder mirarlo despues.
            print(f'   [AVISO] no se pudo leer {origen} ({fallo}): se sigue sin eso')

    if not piezas:
        return pd.DataFrame()

    df = pd.concat(piezas, ignore_index=True)
    df = df[~df['id'].duplicated(keep='first')]

    try:
        df.to_csv(reclamado, index=False, encoding='utf-8-sig')
        if ruta in leidos:
            os.remove(ruta)
    except OSError as fallo:
        # No se pudo reclamar. Se devuelven igual: perder la carrera es raro, perder el
        # correo entero es hoy. La proxima corrida las vera repetidas y las descartara.
        print(f'   [AVISO] no se pudo reclamar el buzon ({fallo}): entran sin reclamar')

    print(f'[GOOGLE] {len(df)} oferta(s) esperando en el buzon')
    return df


def _vaciar_buzon_google(ruta=PENDIENTES_GOOGLE):
    """Borra el buzon reclamado. Solo DESPUES de escribir el historico con exito.

    Se borra el .enproceso y no el buzon: lo que Google haya dejado mientras corriamos es
    de manana y no se ha reportado a nadie.
    """
    reclamado = ruta + '.enproceso'
    try:
        os.remove(reclamado)
    except FileNotFoundError:
        pass
    except OSError as fallo:
        # El historico ya se escribio: la proxima corrida lo volvera a leer y
        # actualizar() las descartara por repetidas. Ruido, no perdida.
        print(f'   [AVISO] no se pudo vaciar {reclamado} ({fallo})')


def _sumar_correo_pendiente(nuevos, ruta=CORREO_PENDIENTE):
    """Las ofertas de un correo que no salio, sumadas a las nuevas de hoy.

    Si no se puede leer, se avisa y se sigue: no puede tumbar el correo de hoy, y el
    archivo se queda para mirarlo.
    """
    if not os.path.exists(ruta):
        return nuevos
    try:
        atrasadas = pd.read_csv(ruta, dtype=str)
    except Exception as fallo:
        print(f'   [AVISO] no se pudo leer {ruta} ({fallo}): se sigue sin eso')
        return nuevos
    print(f'[CORREO] {len(atrasadas)} oferta(s) de un correo anterior que no salio')
    juntas = pd.concat([atrasadas, nuevos], ignore_index=True)
    return juntas[~juntas['id'].astype(str).duplicated(keep='first')].reset_index(drop=True)


def _guardar_correo_pendiente(nuevos, ruta=CORREO_PENDIENTE):
    """Deja las ofertas del correo en el outbox ANTES de enviarlo."""
    try:
        tmp = ruta + '.tmp'
        nuevos.to_csv(tmp, index=False, encoding='utf-8-sig')
        os.replace(tmp, ruta)
    except OSError as fallo:
        # Sin outbox se envia igual: es lo que pasaba antes de existir.
        print(f'   [AVISO] no se pudo guardar {ruta} ({fallo}): si el correo falla, '
              f'estas ofertas no se reintentan')


def _vaciar_correo_pendiente(ruta=CORREO_PENDIENTE):
    """Borra el outbox. Solo DESPUES de un envio que salio bien."""
    try:
        os.remove(ruta)
    except FileNotFoundError:
        pass
    except OSError as fallo:
        # Peor caso: la proxima corrida reenvia estas ofertas. Duplicado, no perdida.
        print(f'   [AVISO] no se pudo vaciar {ruta} ({fallo}): se reenviaran')


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
            distancia=DISTANCIA_DIARIO,
        )
        if fallidos and df.empty:
            fallos_por_ciudad += 1
        if not df.empty:
            partes.append(df.assign(ciudad_busqueda=_ciudad_corta(ciudad)))

    if fallos_por_ciudad == len(CIUDADES):
        # Se sale ANTES de tocar el buzon: si todos los sitios estan caidos, lo de Google
        # sigue esperando y entra en la proxima corrida en vez de gastarse en un correo
        # que no se va a mandar.
        print('[ERROR] Todos los sitios fallaron en todas las ciudades')
        return EXIT_SCRAPE_FALLO

    # Va antes del 'if not partes': un dia en que los sitios no devuelvan nada pero
    # Google si, el correo debe salir igual.
    pendientes = _google_pendientes()
    if not pendientes.empty:
        partes.append(pendientes)

    if not partes:
        print('[AVISO] Sin resultados en ninguna ciudad')
        return EXIT_OK

    nuevos = _registrar(_consolidar(partes), 'diario')

    # El historico ya esta escrito: lo del buzon quedo dentro y no hace falta guardarlo.
    if not pendientes.empty:
        _vaciar_buzon_google()

    # Antes del 'nada nuevo': un dia sin novedades igual debe reintentar lo que no salio.
    nuevos = _sumar_correo_pendiente(nuevos)

    if nuevos.empty and not ENVIAR_SI_VACIO:
        print('[OK] Nada nuevo: no se envia correo')
        return EXIT_OK

    # Lo PRIMERO tras saber que hay algo que avisar: el historico ya las marco como vistas,
    # y si guardar() o construir() revientan, sin outbox se perderian.
    if not nuevos.empty:
        _guardar_correo_pendiente(nuevos)
    ruta = historico.guardar(nuevos, 'diario') if not nuevos.empty else None
    asunto, cuerpo = reporte.construir(nuevos, horas=HORAS_DIARIO)
    if not correo.enviar(asunto, cuerpo, ruta):
        print(f'[AVISO] el correo no salio: sus ofertas quedan en {CORREO_PENDIENTE} '
              f'y se reintentan en la proxima corrida')
        return EXIT_CORREO_FALLO
    # Entre un envio bueno y este borrado, un corte reenviaria el correo manana: se
    # prefiere un duplicado a una perdida.
    _vaciar_correo_pendiente()
    return EXIT_OK


def _terminos(args):
    """Los terminos a buscar, juntando --termino y el argumento posicional."""
    crudos = list(args.terminos) + [args.termino_posicional]
    return [t.strip() for t in crudos if t and t.strip()]


def main():
    parser = argparse.ArgumentParser(
        description='Scraper de empleos (LinkedIn + Indeed + Computrabajo + Multitrabajos)')
    parser.add_argument('termino_posicional', nargs='?', default='',
                        help='Puesto a buscar. Ej: "Data Analyst". '
                             'Hace falta al menos uno, aqui o en --termino')
    parser.add_argument('-t', '--termino', dest='terminos', nargs='+', default=[],
                        help='Uno o varios puestos a buscar. Ej: --termino "Data Analyst" "Data Scientist"')
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

    terminos = _terminos(args)
    if not terminos:
        print('[ERROR] Indica al menos un termino, como argumento o con --termino. '
              'Ej: .\\scrap.cmd "Data Analyst"  (Mac/Linux: ./scrap.sh "Data Analyst")',
              file=sys.stderr)
        return EXIT_SCRAPE_FALLO

    piezas, fallidos = [], []
    for termino in terminos:
        df_parcial, fallidos_parcial = buscar(
            termino=termino,
            ubicacion=args.ubicacion,
            resultados=args.resultados,
            horas=args.horas,
            tipo=args.tipo,
            distancia=args.distancia,
            con_descripcion=args.descripcion,
            sitios=[s.strip() for s in args.sitios.split(',') if s.strip()],
            pais=args.pais,
        )
        if not df_parcial.empty:
            piezas.append(df_parcial)
        fallidos.extend(fallidos_parcial)

    if not piezas:
        # "Cero ofertas" sale 0; "todos los sitios reventaron" sale 1, para que una tarea
        # agendada pueda avisar de la averia en vez de tragarsela.
        if fallidos:
            print("[ERROR] Todos los sitios fallaron")
            return EXIT_SCRAPE_FALLO
        print("[AVISO] Sin resultados")
        return EXIT_OK

    etiqueta = ', '.join(terminos) if len(terminos) > 1 else terminos[0]
    nuevos = _registrar(_consolidar(piezas), etiqueta)

    if nuevos.empty:
        print("[OK] Nada nuevo: solo se actualizo el historico")
        return EXIT_OK

    historico.guardar(nuevos, f'nuevos_{etiqueta}')
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as fallo:
        # historico.actualizar() avisa asi cuando no puede escribir el CSV. Se atrapa
        # aqui para que en la terminal salga el mensaje y no un traceback de diez lineas;
        # el codigo de salida sigue siendo distinto de cero para la tarea agendada.
        print(f'[ERROR] {fallo}', file=sys.stderr)
        sys.exit(EXIT_ESCRITURA_FALLO)
