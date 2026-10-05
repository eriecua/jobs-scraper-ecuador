r"""Pruebas de humo: los scrapers propios contra los sitios REALES.

    .\test.cmd -m vivo

Las de test_offline.py prueban el codigo; estas prueban que Multitrabajos y Computrabajo
sigan respondiendo como el codigo espera. Si un sitio cambia su API o su HTML, el
correo llega sin sus ofertas y sin ningun error: esto es lo que lo detecta.

Solo lectura: no tocan el historico ni mandan correo. LinkedIn e Indeed no estan: los
raspa jobspy, no codigo de este repo.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import computrabajo  # noqa: E402
import multitrabajos  # noqa: E402

pytestmark = pytest.mark.vivo


def _lleno(df, columna):
    return df[columna].notna().mean() if len(df) else 0


@pytest.mark.parametrize('scraper', [multitrabajos, computrabajo], ids=['multitrabajos', 'computrabajo'])
def test_sitio_responde_con_ofertas_completas(scraper):
    # Quito, ultima semana: siempre hay decenas. Si da 0, el sitio cambio algo.
    df = scraper.scrape(ubicacion='Quito, Ecuador', resultados=40, dias_max=7)
    assert len(df) >= 10, f'{scraper.__name__}: solo {len(df)} ofertas en Quito en 7 dias'
    for columna in ('title', 'company', 'date_posted', 'job_url'):
        assert _lleno(df, columna) >= 0.9, f'{scraper.__name__}: {columna} al {_lleno(df, columna):.0%}'
    assert df['job_url'].str.startswith('https://').all()


def test_multitrabajos_trae_descripcion():
    df = multitrabajos.scrape(ubicacion='Quito, Ecuador', resultados=20, dias_max=7)
    assert _lleno(df, 'description') >= 0.9
