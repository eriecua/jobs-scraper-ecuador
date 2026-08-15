import os
import re
import pandas as pd
from datetime import datetime
from config import DEFAULT_CONFIG

def _nombre_seguro(nombre):
    """Quita de un nombre de busqueda los caracteres invalidos en un nombre de archivo."""
    limpio = re.sub(r'[^\w\s-]', '', nombre).strip()
    return re.sub(r'\s+', '_', limpio) or 'reporte'

def generar_excel(df, metricas, nombre_busqueda, output_dir=None):
    """
    Genera reporte Excel con resultados del scraping.
    """
    output_dir = output_dir or DEFAULT_CONFIG['output_dir']
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_archivo = os.path.join(
        output_dir, f'reporte_{_nombre_seguro(nombre_busqueda)}_{timestamp}.xlsx'
    )

    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        # Hoja Resumen
        pd.DataFrame({
            'Métrica': ['Total Empleos', 'Empresas Únicas', 'Búsqueda'],
            'Valor': [metricas['total'], len(df['company'].unique()), nombre_busqueda]
        }).to_excel(writer, sheet_name='Resumen', index=False)

        # Hoja Por Empresa
        pd.DataFrame({
            'Empresa': list(metricas['por_empresa'].keys()),
            'Cantidad': list(metricas['por_empresa'].values())
        }).to_excel(writer, sheet_name='Por Empresa', index=False)

        # Hoja Por Ciudad
        pd.DataFrame({
            'Ciudad': list(metricas['por_ciudad'].keys()),
            'Cantidad': list(metricas['por_ciudad'].values())
        }).to_excel(writer, sheet_name='Por Ciudad', index=False)

        # Hoja Datos Completos
        df.to_excel(writer, sheet_name='Datos Completos', index=False)

    print(f"Reporte generado: {nombre_archivo}")
    return nombre_archivo
