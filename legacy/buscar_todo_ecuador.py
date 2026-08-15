"""
Busca TODOS los empleos de Computrabajo Ecuador (sin puesto, por ciudades/provincias)
publicados en los ultimos 7 dias y genera el reporte Excel.
"""
import argparse
from scraper_computrabajo import scrape_todo_ecuador
from analisis import analizar
from generar_excel import generar_excel


def main():
    parser = argparse.ArgumentParser(description='Todos los empleos de Ecuador (ultimos 7 dias)')
    parser.add_argument('--dias', type=int, default=7, help='Solo ofertas de los ultimos N dias (default: 7)')
    parser.add_argument('--pages', type=int, default=10, help='Maximo de paginas por provincia (~20 ofertas c/u)')
    parser.add_argument('--retraso', type=int, default=2, help='Segundos entre peticiones')
    args = parser.parse_args()

    df = scrape_todo_ecuador(dias_max=args.dias, max_paginas=args.pages, retraso=args.retraso)

    if df.empty:
        print("[ERROR] No se encontraron empleos")
        return

    metricas = analizar(df)
    generar_excel(df, metricas, f'Todos Ecuador ultimos {args.dias} dias')


if __name__ == "__main__":
    main()