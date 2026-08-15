# CLAUDE.md

Scraper de empleos (LinkedIn + Indeed + Computrabajo) con histórico incremental y reporte
diario por correo. El uso detallado está en `README.md`; aquí solo lo que muerde.

## Ejecutar

```powershell
.\scrap.cmd "Data Analyst"     # búsqueda suelta
.\scrap_diario.cmd             # reporte diario por correo
```

La tarea `ScraperEmpleos` lanza el diario a las 08:00, 14:00 y 20:00 vía
`scrap_diario_oculto.vbs`, que lo corre sin ventana y propaga el código de salida.

Desde **PowerShell o cmd**, no desde Git Bash (la invocación del `.cmd` falla ahí).

**Nunca** `pip install -r requirements.txt` con el Python del sistema: `python-jobspy`
fija `numpy==1.26.3`, que no tiene wheel para el Python 3.14 instalado e intentaría
compilarlo. `scrap.cmd` usa `uv` para provisionar Python 3.12 aparte.

## No tocar

- `.env` — credenciales de Gmail, fuera de git.
- `data/historico.csv` — es el **estado** que decide qué oferta es nueva. Si se borra,
  la siguiente corrida reporta todo otra vez como novedad.
- `legacy/` — código viejo que se conserva a propósito.

## Verificar un cambio

Prueba por `scrap.cmd`, **no** con `uv run --with paquete ...` a mano. Ese atajo enmascara
dependencias que faltan en `requirements.txt` (ya pasó con `requests` y `beautifulsoup4`).

Lo que no necesita red (`reporte.py`, `perfil.py`, `historico.py`) se prueba offline
contra `data/historico.csv`.

Códigos de salida: `0` ok · `1` todos los sitios fallaron · `2` no se pudo enviar el correo.

## Los datos, medidos — no supuestos

Sobre 392 ofertas reales del histórico:

```
site 100% · location 96% · company 93% · date_posted 79% · is_remote 76%
salary (texto, solo Computrabajo) 16% · job_type 9%
min_amount / max_amount 3% · company_industry 3% · job_level 0%
```

Consecuencias, antes de diseñar nada encima:

- **No se puede analizar sueldos.** El 3% no sostiene ningún gráfico ni promedio.
- **`description` se descarta a propósito** (`DESCARTAR_DESCRIPCION` en `buscador.py`).
  Solo la traía Indeed; el índice de compatibilidad puntúa con el título.
- **Las ubicaciones no coinciden entre sitios**: `"Quito, Pichincha, Ecuador"` (LinkedIn),
  `"Quito, P, EC"` (Indeed), `"Quito, Pichincha"` (Computrabajo). Hay que normalizarlas
  (`ciudad_normalizada` en `reporte.py`) o los conteos por ciudad salen partidos.
- **LinkedIn publica spam real** ("Trabaja con nosotros", clickbait tipo "MOVIES FROM THE
  80S"). No es un fallo del scraper: son ofertas con URL válida. Se filtran en el reporte
  (`NO_OFERTAS`), no en el origen.

## Dónde se ajusta la configuración

| Qué | Dónde |
|---|---|
| Ciudades del diario | `CIUDADES` en `main.py` **y** `SLUGS_UBICACION` en `computrabajo.py` |
| Términos del índice de compatibilidad | `INTERES` / `DESEABLES` (ordenan) y `EXCLUIDOS` / `FAMILIAS_EXCLUIDAS` (quitan) en `perfil.py` |
| Familias de puesto del gráfico | `FAMILIAS` en `reporte.py` |
| Descartar la descripción | `DESCARTAR_DESCRIPCION` en `buscador.py` |

Añadir una ciudad exige tocar **dos** archivos. Computrabajo no entiende `"Quito, Ecuador"`:
su ruta es `pichincha-en-quito`, y un slug inválido devuelve **200 con cero ofertas sin
dar error**, así que hay que comprobarlo contra el sitio.

## Git

El repo vive en esta carpeta (`git init` hecho aquí, no en `Proyectos varios`, que
arrastra `node_modules` y cosas ajenas). El `.git` de la carpeta padre está **vacío** y no
funciona: ignóralo.

## Decisiones ya tomadas

- **Sin skill.** Evaluado y descartado: los procedimientos candidatos son de dos pasos.
  El único con recorrido —ajustar `perfil.py` y re-medir— aún no se ha hecho ni una vez.
- **Gráficos del correo en HTML/CSS, no imágenes.** Un correo no ejecuta JS ni dibuja SVG,
  y un PNG se lee mal en el celular y arrastra su fondo blanco al modo oscuro.
