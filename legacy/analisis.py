def analizar(df):
    """
    Analiza DataFrame de empleos y retorna métricas.
    """
    resultados = {
        'total': len(df),
        'por_empresa': df['company'].value_counts().head(10).to_dict(),
        'por_ciudad': df['location'].value_counts().head(10).to_dict(),
    }

    if 'job_type' in df.columns:
        resultados['por_tipo'] = df['job_type'].value_counts().to_dict()

    return resultados
