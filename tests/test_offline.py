r"""Pruebas sin red de lo que decide que te llega y como se guarda.

    .\test.cmd

Cada prueba fija un caso que ya fallo de verdad o una decision tomada con el usuario: si
alguien la rompe sin querer, aqui salta antes que en el correo de las 08:00.
"""
import os
import sys
from datetime import date

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import computrabajo  # noqa: E402
import habilidades  # noqa: E402
import historico  # noqa: E402
import multitrabajos  # noqa: E402
import perfil  # noqa: E402
import reporte  # noqa: E402
import ubicaciones  # noqa: E402


# --- perfil.py: el indice que ordena el correo -----------------------------------------

@pytest.mark.parametrize('titulo, minimo', [
    ('Analista de Datos', 30),
    ('Analista de Procesos', 30),
    ('Coordinador de Mejora Continua', 30),
    ('Senior Business Analyst', 30),
    ('Científico de datos', 30),
])
def test_tus_puestos_encajan(titulo, minimo):
    assert perfil.puntuar(titulo)[0] >= minimo


@pytest.mark.parametrize('titulo', ['Analista contable', 'Analista de bienestar',
                                    'Ingeniero industrial'])
def test_analista_sin_tema_e_industrial_no_encajan(titulo):
    assert perfil.puntuar(titulo)[0] < 30


@pytest.mark.parametrize('titulo', ['Pasante de ingeniería industrial',
                                    'Pasante de Mejora Continua',
                                    'Practicas Preprofesionales en Datos', 'Data Intern'])
def test_pasantias_fuera_del_correo(titulo):
    assert perfil.excluir(titulo) == 'nivel: Practicas'


@pytest.mark.parametrize('titulo', ['Auditor Interno', 'Comercio Internacional',
                                    'Analista de Calidad'])
def test_no_excluye_por_subcadena(titulo):
    # 'intern' esta dentro de "interno" e "internacional".
    assert perfil.excluir(titulo) is None


def test_excluidos_por_palabra_completa():
    assert perfil.excluir('Vendedor de mostrador') == 'vendedor'
    assert perfil.excluir('Salesforce Administrator') is None


# --- reporte.py: familias, empresas y el correo ----------------------------------------

@pytest.mark.parametrize('titulo, familia', [
    ('Analista de Procesos', 'Procesos/Mejora continua'),
    ('Lean Manager', 'Procesos/Mejora continua'),
    ('Ingeniero de Calidad', 'Calidad'),
    ('Analista de Calidad y Procesos', 'Calidad'),  # dice "calidad": manda la regla
    ('Analista de Datos', 'Datos/BI'),
    ('Contract Processor', 'Otros'),  # 'process' dentro de 'processor'
])
def test_familia_puesto(titulo, familia):
    assert reporte.familia_puesto(titulo) == familia


@pytest.mark.parametrize('empresa, esperado', [
    ('Empresa Confidencial', 'Confidencial'),
    ('Confidential Careers', 'Confidencial'),
    ('Importante empresa del sector Automotriz', 'Confidencial'),
    ('Grupo Empresarial Dinova', 'Grupo Empresarial Dinova'),
    ('Hitss Ecuador', 'Hitss Ecuador'),
    (None, None),
])
def test_empresa_normalizada(empresa, esperado):
    assert reporte.empresa_normalizada(empresa) == esperado


def test_correo_sin_nan_ni_pasantias():
    # El NaN solo aparece si en el mismo correo hay ofertas CON nivel (Jefe -> Jefatura)
    # y SIN nivel: con todas sin nivel pandas guarda None, que si es falso. Sin la de
    # Jefe, esta prueba pasaba aunque el fallo estuviera.
    titulos = ['Científico de datos', 'Jefe de Procesos', 'Pasante de ingeniería industrial',
               'Analista contable']
    n = len(titulos)
    df = pd.DataFrame({
        'title': titulos, 'company': ['Hitss Ecuador', 'Pronaca', 'Ecuasal', 'ACME'],
        'location': ['Quito, Pichincha, Ecuador'] * n,
        'ciudad': ['Quito'] * n, 'provincia': ['Pichincha'] * n,
        'site': ['linkedin'] * n, 'job_url': [f'https://x/{i}' for i in range(n)],
    })
    asunto, cuerpo = reporte.construir(df, horas=24)
    assert asunto.startswith('2 de 3 ')
    assert '· nan' not in cuerpo  # el fallo real: "Hitss Ecuador · nan · datos"
    assert 'Pasante' not in cuerpo.split('Se ocultaron')[0]


# --- habilidades.py --------------------------------------------------------------------

def _habilidades(texto):
    return {h for h, _ in habilidades.detectar(texto)}


def test_habilidades_basicas():
    assert _habilidades('Dashboards en Power BI con SQL Server') == {'Dashboards', 'Power BI', 'SQL'}
    assert _habilidades('Excelente actitud, cumplir procedimientos internos') == set()


def test_bpm_ambiguo():
    assert _habilidades('Normas BPM (buenas prácticas de manufactura)') == {'BPM (manufactura)'}
    assert 'Gestión por procesos (BPM)' in _habilidades('metodologías como lean, six sigma, bpm')


# --- computrabajo.py: la fecha sin ano -------------------------------------------------

@pytest.mark.parametrize('dia, mes, hoy, esperado', [
    (25, 9, date(2026, 10, 5), 10),
    (20, 12, date(2027, 1, 10), 21),   # en enero, diciembre es el del ano pasado
    (31, 2, date(2026, 10, 5), None),  # no existe
    (29, 2, date(2028, 3, 1), 1),
])
def test_dias_desde_fecha(dia, mes, hoy, esperado):
    assert computrabajo._dias_desde_fecha(dia, mes, hoy) == esperado


@pytest.mark.parametrize('texto, dias', [
    ('Hace  8  horas', 0), ('Ayer', 1), ('Hace 3 días', 3), ('Más de 30 días', 31),
])
def test_dias_desde_texto(texto, dias):
    assert computrabajo._dias_desde(texto) == dias


def test_computrabajo_empresa_sin_perfil():
    # Sin perfil en el sitio la empresa es texto plano, no enlace (20% de las ofertas).
    html = '''<div id="offersGridOfferContainer"><article class="box_offer">
      <h2><a class="js-o-link" href="/ofertas-de-trabajo/x-E4EF7F3BE8677F0F61373E686DCF3405">Ejecutivo B2B</a></h2>
      <p class="dFlex vm_fx fs16 fc_base mt5">AYUPREST S.A.</p>
      <p class="fs16 fc_base mt5"><span class="mr10">Guayaquil, Guayas</span></p>
      <p class="fs13 fc_aux mt15">25 de septiembre</p></article></div>'''
    oferta = computrabajo._parsear_ofertas(html, 'ec.computrabajo.com')[0]
    assert oferta['company'] == 'AYUPREST S.A.'
    assert oferta['date_posted'] is not None


# --- multitrabajos.py ------------------------------------------------------------------

def test_multitrabajos_mapeo():
    aviso = {'id': 1118466990, 'titulo': 'Ingeniera Industrial - Área de Producción',
             'empresa': 'Productos Pesqueros', 'confidencial': False,
             'localizacion': 'Montecristi, Manabí', 'fechaPublicacion': '03-10-2026',
             'modalidadTrabajo': 'Presencial', 'tipoTrabajo': 'Full-time',
             'detalle': 'Requisitos: Excel'}
    o = multitrabajos._a_oferta(aviso)
    assert o['id'] == 'mt-1118466990'
    assert o['date_posted'] == '2026-10-03'
    assert o['is_remote'] is False
    assert o['description'] == 'Requisitos: Excel'
    assert o['job_url'].endswith('-1118466990.html')
    assert multitrabajos._a_oferta({**aviso, 'confidencial': True})['company'] == 'Confidencial'


# --- ubicaciones.py --------------------------------------------------------------------

@pytest.mark.parametrize('location, par', [
    ('Quito, Pichincha, Ecuador', ('Quito', 'Pichincha')),
    ('Quito, P, EC', ('Quito', 'Pichincha')),
    ('Pifo, Pichincha', ('Quito', 'Pichincha')),
    ('Pichincha, Ecuador', ('', 'Pichincha')),  # solo provincia: no inventa la capital
])
def test_normalizar_ubicacion(location, par):
    assert ubicaciones.normalizar(location) == par


# --- historico.py: que es nuevo y donde va la descripcion ------------------------------

def _ofertas(*ids):
    return pd.DataFrame({
        'id': list(ids), 'site': 'multitrabajos', 'title': [f'Analista {i}' for i in ids],
        'company': 'ACME', 'location': 'Quito, Pichincha', 'date_posted': '2026-10-05',
        'job_url': [f'https://x/{i}' for i in ids],
        'description': [f'Se requiere SQL\ny Power BI ({i})' for i in ids],
    })


def test_historico_nuevos_y_descripciones(tmp_path):
    ruta = str(tmp_path / 'historico.csv')
    nuevos = historico.actualizar(_ofertas('mt-1', 'mt-2'), 'prueba', ruta=ruta)
    assert len(nuevos) == 2
    assert 'description' not in nuevos.columns

    guardado = pd.read_csv(ruta, dtype=str)
    assert 'description' not in guardado.columns
    desc = pd.read_csv(tmp_path / 'descripciones.csv', dtype=str)
    assert list(desc['id']) == ['mt-1', 'mt-2']
    assert not desc['description'].str.contains('\n').any()  # una linea por oferta

    # Segunda corrida: una repetida y una nueva. Ni ofertas ni descripciones duplicadas.
    nuevos = historico.actualizar(_ofertas('mt-2', 'mt-3'), 'prueba', ruta=ruta)
    assert list(nuevos['id']) == ['mt-3']
    desc = pd.read_csv(tmp_path / 'descripciones.csv', dtype=str)
    assert list(desc['id']) == ['mt-1', 'mt-2', 'mt-3']


def test_habilidades_se_regeneran(tmp_path):
    historico.actualizar(_ofertas('mt-1'), 'prueba', ruta=str(tmp_path / 'historico.csv'))
    assert habilidades.regenerar(str(tmp_path)) == 2
    filas = pd.read_csv(tmp_path / 'habilidades.csv')
    assert set(filas['habilidad']) == {'SQL', 'Power BI'}


def test_descripciones_rotas_no_tumban_el_correo(tmp_path):
    # Corren DESPUES de escribir el historico: si revientan, las ofertas quedan vistas y
    # sin correo. Un descripciones.csv sin columna 'id' hace fallar su lectura.
    (tmp_path / 'descripciones.csv').write_text('basura,sin,clave\n1,2,3\n', encoding='utf-8')
    nuevos = historico.actualizar(_ofertas('mt-1'), 'prueba', ruta=str(tmp_path / 'historico.csv'))
    assert list(nuevos['id']) == ['mt-1']


# --- main.py: outbox del correo diario --------------------------------------------------

import main  # noqa: E402


@pytest.fixture
def diario(tmp_path, monkeypatch):
    """Corre ejecutar_diario() en una carpeta temporal, sin red y con un correo falso.

    Devuelve correr(ids, envio_ok) -> (codigo, ids del adjunto o None).
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    monkeypatch.setattr(main, 'CIUDADES', ['Quito, Ecuador'])
    monkeypatch.setattr(main.correo, 'faltan_credenciales', lambda: [])
    monkeypatch.setattr(main.habilidades, 'regenerar', lambda *a, **k: 0)
    monkeypatch.setattr(historico, 'RUTA', os.path.join('data', 'historico.csv'))
    monkeypatch.setattr(historico.actualizar, '__defaults__',
                        (os.path.join('data', 'historico.csv'),))
    enviados = []

    def correr(ids, envio_ok=True):
        # Con los tipos que de verdad devuelve buscar() (fecha y booleano), no todo texto:
        # el reintento mezcla esto con el outbox, que se relee como texto.
        oferta = _ofertas(*ids).drop(columns=['description']).assign(
            ciudad='Quito', provincia='Pichincha', is_remote=False,
            date_posted=pd.to_datetime('2026-10-05'))
        monkeypatch.setattr(main, 'buscar', lambda **k: (oferta, []))

        def enviar(asunto, cuerpo, ruta):
            enviados.append(sorted(pd.read_csv(ruta, dtype=str)['id']) if ruta else None)
            return envio_ok
        monkeypatch.setattr(main.correo, 'enviar', enviar)
        antes = len(enviados)
        codigo = main.ejecutar_diario()
        # Solo el correo de ESTA corrida: devolver el de la anterior hacia pasar una
        # prueba de reintento aunque no se reintentara nada.
        return codigo, enviados[-1] if len(enviados) > antes else None

    return correr


def test_correo_fallido_se_reintenta(diario):
    codigo, adjunto = diario(['mt-1', 'mt-2'], envio_ok=False)
    assert codigo == main.EXIT_CORREO_FALLO
    assert os.path.exists(main.CORREO_PENDIENTE)

    # mt-1 y mt-2 ya estan en el historico (vistas): sin outbox no volverian a salir.
    codigo, adjunto = diario(['mt-2', 'mt-3'], envio_ok=True)
    assert codigo == main.EXIT_OK
    assert adjunto == ['mt-1', 'mt-2', 'mt-3']  # sin duplicar mt-2
    assert not os.path.exists(main.CORREO_PENDIENTE)


def test_correo_bueno_no_deja_pendientes(diario):
    codigo, adjunto = diario(['mt-1'])
    assert (codigo, adjunto) == (main.EXIT_OK, ['mt-1'])
    assert not os.path.exists(main.CORREO_PENDIENTE)
    # La siguiente corrida sin nada nuevo no reenvia nada.
    assert diario(['mt-1'])[0] == main.EXIT_OK


def test_dia_sin_novedades_reintenta_lo_pendiente(diario):
    diario(['mt-1'], envio_ok=False)
    codigo, adjunto = diario(['mt-1'])  # nada nuevo hoy
    assert adjunto == ['mt-1']


def test_busqueda_suelta_no_toca_el_outbox(diario, monkeypatch):
    diario(['mt-1'], envio_ok=False)
    antes = open(main.CORREO_PENDIENTE, encoding='utf-8-sig').read()
    monkeypatch.setattr(sys, 'argv', ['main.py', 'analista'])
    monkeypatch.setattr(main, 'buscar', lambda **k: (_ofertas('mt-9').drop(columns=['description']), []))
    assert main.main() == main.EXIT_OK
    assert open(main.CORREO_PENDIENTE, encoding='utf-8-sig').read() == antes


def test_todas_guarda_tambien_las_ya_vistas(diario, monkeypatch):
    oferta = _ofertas('mt-1', 'mt-2').drop(columns=['description'])
    # La misma vacante que mt-2 publicada en otro sitio: otro id, otra URL, misma clave.
    doble = oferta.iloc[[1]].assign(id='in-2', site='indeed', job_url='https://y/2')
    monkeypatch.setattr(main, 'buscar', lambda **k: (pd.concat([oferta, doble]), []))

    monkeypatch.setattr(sys, 'argv', ['main.py', 'analista'])
    assert main.main() == main.EXIT_OK
    # Segunda corrida igual: sin --todas no habria CSV, porque nada es nuevo.
    monkeypatch.setattr(sys, 'argv', ['main.py', 'analista', '--todas'])
    assert main.main() == main.EXIT_OK

    archivos = [f for f in os.listdir('data') if f.startswith('todas_')]
    assert len(archivos) == 1
    guardado = pd.read_csv(os.path.join('data', archivos[0]), dtype=str)
    assert sorted(guardado['id']) == ['mt-1', 'mt-2']  # la doble, una sola vez
    assert {'ciudad', 'provincia'} <= set(guardado.columns)


# --- buscador.py: registro de corridas ---------------------------------------------------

import buscador  # noqa: E402


def test_corridas_anota_cada_sitio(tmp_path, monkeypatch):
    def bien(**k):
        return _ofertas('mt-1', 'mt-2').drop(columns=['description'])

    def mal(**k):
        raise ConnectionError('429 Too Many Requests')

    monkeypatch.setattr(buscador, 'FUENTES_PROPIAS', {'bien': bien, 'mal': mal})
    monkeypatch.setattr(buscador, 'RUTA_CORRIDAS', str(tmp_path / 'corridas.csv'))
    df, fallidos = buscador.buscar(ubicacion='Quito, Ecuador', sitios=['bien', 'mal'])
    assert (len(df), fallidos) == (2, ['mal'])

    filas = pd.read_csv(tmp_path / 'corridas.csv', dtype=str).set_index('sitio')
    assert filas.loc['bien', 'ofertas'] == '2' and pd.isna(filas.loc['bien', 'error'])
    assert filas.loc['mal', 'ofertas'] == '0' and '429' in filas.loc['mal', 'error']


def test_corridas_rota_no_tumba_la_busqueda(tmp_path, monkeypatch):
    monkeypatch.setattr(buscador, 'FUENTES_PROPIAS',
                        {'bien': lambda **k: _ofertas('mt-1').drop(columns=['description'])})
    (tmp_path / 'corridas.csv').mkdir()  # una carpeta donde va el archivo: no se puede escribir
    monkeypatch.setattr(buscador, 'RUTA_CORRIDAS', str(tmp_path / 'corridas.csv'))
    df, fallidos = buscador.buscar(sitios=['bien'])
    assert (len(df), fallidos) == (1, [])


def test_correo_que_revienta_al_armarse_no_pierde_ofertas(diario, monkeypatch):
    construir = main.reporte.construir

    def revienta(*a, **k):
        raise ValueError('fallo al armar el correo')
    monkeypatch.setattr(main.reporte, 'construir', revienta)
    with pytest.raises(ValueError):
        diario(['mt-1', 'mt-2'])
    assert os.path.exists(main.CORREO_PENDIENTE)

    # Arreglado el fallo, la siguiente corrida las manda junto con las nuevas: fecha y
    # booleano reales mezclados con lo que el outbox relee como texto.
    monkeypatch.setattr(main.reporte, 'construir', construir)
    codigo, adjunto = diario(['mt-3'])
    assert (codigo, adjunto) == (main.EXIT_OK, ['mt-1', 'mt-2', 'mt-3'])
