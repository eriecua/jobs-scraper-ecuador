# Cómo funciona

Detalles internos, para quien quiera entender o modificar el scraper. Para usarlo no hace
falta leer esto.

- [Histórico: cómo sabe qué es nuevo](#histórico-cómo-sabe-qué-es-nuevo)
- [Qué guarda cada archivo de `data/`](#qué-guarda-cada-archivo-de-data)
- [Cada sitio](#cada-sitio)
- [Archivos del proyecto](#archivos-del-proyecto)
- [Windows, Mac y Linux](#windows-mac-y-linux)
- [Pruebas](#pruebas)
- [Extra: ofertas de Google Jobs](#extra-ofertas-de-google-jobs)

## Histórico: cómo sabe qué es nuevo

Todo lo visto se acumula en `data/historico.csv`. Una oferta se considera repetida si
coinciden **empresa + título + ciudad** (así la misma vacante en Quito y en Guayaquil
cuenta como dos, y la misma vacante en LinkedIn e Indeed cuenta como una) y si se vio hace
menos de `DIAS_CADUCIDAD` días (60 por defecto, en `historico.py`): pasado ese plazo, un
repost vuelve a aparecer.

- Cada búsqueda escribe **solo las ofertas nuevas** en `data/nuevos_<puesto>_<fecha>.csv`.
- Con `--todas`, escribe **todas las encontradas** en `data/todas_<puesto>_<fecha>.csv`,
  vistas o no, igual sin repetir la misma vacante entre sitios. El histórico se actualiza
  igual.
- **Si borras `historico.csv`**, la próxima corrida devuelve todo como nuevo, y el correo
  también. Es el estado del scraper: no lo borres salvo que quieras empezar de cero.

Los CSV se guardan en `utf-8-sig` para que Excel abra los acentos bien al doble clic.

### Columnas del CSV

Las de jobspy, más las que añade el scraper. Las principales:

`site`, `title`, `company`, `location`, `ciudad`, `provincia`, `date_posted`, `job_type`,
`job_url`, `is_remote`, `min_amount`, `max_amount`, `currency`, `company_industry`,
`salary`, `busqueda`, `visto_primera_vez`.

`ciudad` y `provincia` las añade `ubicaciones.py` a partir de `location`, que se conserva
cruda por si hay que depurar un caso raro. Son las columnas por las que se filtra en
Excel: `location` trae 19 formas distintas de escribir 6 ciudades
([ver ubicaciones](configuracion.md#ciudades-y-provincias--ubicacionespy)).

Cada sitio llena las que puede: LinkedIn e Indeed dan el salario en `min_amount`/
`max_amount` (pocas veces); Computrabajo lo da como texto en `salary`. `date_posted` sí
queda unificada como fecha en todos.

La columna `description` **no entra en el histórico ni en el CSV**: son ~1.800 caracteres
por oferta. Se guarda aparte en `data/descripciones.csv` (`id`, `description`, una línea
por oferta), solo para las ofertas nuevas que la traen: Multitrabajos e Indeed, que la
mandan en la misma búsqueda. `--descripcion` pide además la de LinkedIn en una búsqueda
suelta (una petición más por oferta: 7 s → 22 s para 20 ofertas).

## Qué guarda cada archivo de `data/`

| Archivo | Qué es |
|---|---|
| `historico.csv` | Todo lo visto. Es el **estado**: decide qué es nuevo |
| `nuevos_*.csv` / `todas_*.csv` | Resultado de cada búsqueda suelta |
| `diario_*.csv` | Lo que mandó cada correo diario (el adjunto) |
| `descripciones.csv` | Descripción completa de las ofertas que la traen, por `id` |
| `habilidades.csv` | Qué habilidades pide cada oferta, sacadas de su descripción |
| `corridas.csv` | Una fila por sitio y búsqueda: ofertas, error y segundos. Sirve para ver si un sitio lleva días fallando |
| `correo_pendiente.csv` | Ofertas de un correo que no se pudo enviar; se reenvían ([ver correo](correo.md#si-el-correo-falla)) |
| `historico.db` / `analisis.csv` | Los crea `analizar` ([ver análisis](analisis.md)) |

## Cada sitio

LinkedIn e Indeed van por [JobSpy](https://github.com/speedyapply/JobSpy). Computrabajo y
Multitrabajos no los cubre jobspy, así que tienen módulo propio y devuelven las mismas
columnas que los demás.

### Computrabajo

`computrabajo.py` raspa el HTML directamente. Diferencias a tener en cuenta:

- **La ubicación va por un mapa de slugs.** Computrabajo no entiende `"Quito, Ecuador"`:
  la ruta es `pichincha-en-quito`. El mapa `SLUGS_UBICACION` trae las ciudades grandes de
  Ecuador. Una ciudad que no esté ahí devuelve **200 con cero ofertas**, sin error, así
  que el scraper avisa cuando eso pasa y los demás sitios sí trajeron algo
  ([añadir una ciudad](configuracion.md#añadir-una-ciudad)).
- **No existe página de "todo el país".** `/empleos`, `/trabajo` y `/ofertas-de-trabajo`
  redirigen a la portada, y `/empleos-en-ecuador` responde 200 con cero ofertas. Si se le
  pide sin puesto y sin ciudad, **recorre las 12 provincias** una por una y se queda con
  las más recientes (verás `computrabajo: recorriendo 12 provincias`; tarda ~16 s frente a
  ~2 s). Con un puesto sí hay URL de país (`trabajo-de-<puesto>`), así que las búsquedas
  normales son rápidas.
- **`--horas` se redondea a días.** Computrabajo solo publica la antigüedad como "Hace 3
  días", no la hora exacta. `--horas 24` se traduce a "último 1 día".
- **El salario viene como texto** (`"790,00 US$ (Mensual)"`) en la columna `salary`, no
  como `min_amount`/`max_amount` numéricos.
- Va con reintentos, backoff y una pausa de ~2 s entre páginas para no hacerse bloquear;
  por eso es más lento que los otros.
- Si Computrabajo cambia su HTML, los selectores dejarían de coincidir. El scraper avisa
  (`Posible cambio de estructura`) cuando más de la mitad de las ofertas salen sin
  empresa o sin ubicación, en vez de devolver filas vacías en silencio.

### Multitrabajos

`multitrabajos.py` no raspa HTML: la página se dibuja en el navegador, pero la propia web
consulta una API JSON, y el scraper usa esa misma API. Trae la descripción completa
siempre. La ciudad se traduce sola con `ubicaciones.py`; un filtro mal formado también
devuelve 200 con cero ofertas.

## Archivos del proyecto

Cada uno hace un solo trabajo:

| Archivo | Qué hace |
|---|---|
| `main.py` | Configuración del diario, orquestación y línea de comandos |
| `buscador.py` | Busca en todos los sitios y junta los resultados |
| `computrabajo.py` | Raspa Computrabajo (jobspy no lo cubre) |
| `multitrabajos.py` | Consulta Multitrabajos por su API JSON (jobspy no lo cubre) |
| `historico.py` | Decide qué es nuevo y guarda los CSV |
| `ubicaciones.py` | Convierte la ubicación cruda de cada sitio en ciudad + provincia |
| `perfil.py` | Puntúa cada oferta contra lo que buscas |
| `habilidades.py` | Saca de las descripciones qué habilidades pide cada oferta |
| `reporte.py` | Arma el correo |
| `graficos.py` | Las barras y cifras del correo, en HTML |
| `correo.py` | Lo envía por Gmail |
| `a_sqlite.py` | Prepara la base para analizar (lo lanza `analizar`) |
| `consultas.sql` | Consultas SQL listas para `historico.db` |
| `scrap` / `scrap_diario` / `analizar` / `test` (`.cmd` y `.sh`) | Lanzadores |
| `scrap_diario_oculto.vbs` | Lanza el diario sin abrir ventana (agendado en Windows) |
| `tests/` | Pruebas |
| `ingesta_google.py`, `scrap_google.cmd` | [Extra opcional](#extra-ofertas-de-google-jobs) |

## Windows, Mac y Linux

El código Python es el mismo en los tres sistemas; solo cambian los lanzadores, que llevan
el mismo comando `uv`:

| Windows | Mac / Linux | Qué hace |
|---|---|---|
| `.\scrap.cmd` | `./scrap.sh` | Búsqueda suelta |
| `.\scrap_diario.cmd` | `./scrap_diario.sh` | Correo diario; lee el `.env` |
| `.\analizar.cmd` | `./analizar.sh` | Prepara la base para analizar |
| `.\test.cmd` | `./test.sh` | Pruebas |
| `scrap_diario_oculto.vbs` | — | No hace falta: `cron` no abre ventana |

En Windows, córrelos desde **PowerShell o cmd**, no desde Git Bash: la invocación del
`.cmd` falla ahí.

**Por qué `uv` y un Python aparte:** `python-jobspy` exige `numpy==1.26.3` y `pandas 2.x`.
Esa versión de numpy no tiene versión precompilada para Python 3.13 o superior, así que
`pip` intentaría compilarla y fallaría. Los lanzadores piden a `uv` un Python 3.12 aislado,
sin tocar el que tengas instalado.

## Pruebas

```powershell
.\test.cmd             # sin red, ~2 s: índice, ubicaciones, fechas, histórico...
.\test.cmd -m vivo     # de humo contra los sitios reales (lentas, necesitan internet)
```

En Mac y Linux, `./test.sh` con las mismas opciones. GitHub Actions corre las de sin red
en Windows, macOS y Linux en cada push (`.github/workflows/pruebas.yml`).

Si las de `vivo` fallan, lo más probable es que un sitio haya cambiado su HTML o su API.

## Extra: ofertas de Google Jobs

`ingesta_google.py` y `scrap_google.cmd` ingieren el CSV de un scraper de Google Jobs
**aparte, que no viene en este repo** (necesita Selenium y Chrome). Sin ese scraper no
sirven y puedes ignorarlos: el diario funciona igual. `scrap_google.cmd` es solo para
Windows.
