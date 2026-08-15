import os
import subprocess
import glob
import time
import pandas as pd

def scrape_jobs(search_term, location, results_wanted=100,
                job_type=None, distance=50, hours_old=None,
                output_dir='data'):
    """
    Ejecuta jobsparser y retorna DataFrame con resultados.
    """
    # Construir comando
    cmd = [
        'jobsparser',
        '--search-term', search_term,
        '--location', location,
        '--site', 'linkedin',
        '--results-wanted', str(results_wanted),
        '--distance', str(distance),
        '--output-dir', output_dir,
    ]

    if job_type:
        cmd.extend(['--job-type', job_type])
    if hours_old:
        cmd.extend(['--hours-old', str(hours_old)])

    os.makedirs(output_dir, exist_ok=True)

    print(f"[BUSQUEDA] {search_term} en {location}...")
    inicio = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Error en jobsparser: {result.stderr}")

    # jobsparser reutiliza nombres (jobs_0.csv, jobs_1.csv...), asi que comparamos por
    # fecha de modificacion: si el CSV mas reciente es anterior a esta corrida, seria
    # el de una busqueda pasada y lo estariamos reportando como resultados nuevos.
    csvs = glob.glob(f"{output_dir}/*.csv")
    reciente = max(csvs, key=os.path.getmtime) if csvs else None
    if reciente is None or os.path.getmtime(reciente) < inicio:
        raise RuntimeError(f"jobsparser no escribio ningun CSV en '{output_dir}'")

    df = pd.read_csv(reciente)

    print(f"[OK] Encontrados {len(df)} empleos")
    return df
