# Jobs Scraper Ecuador

[Read in English](README.md)

![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows | macOS | Linux](https://img.shields.io/badge/plataforma-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
[![Pruebas](https://github.com/eriecua/jobs-scraper-ecuador/actions/workflows/pruebas.yml/badge.svg)](https://github.com/eriecua/jobs-scraper-ecuador/actions/workflows/pruebas.yml)

Busca empleos en LinkedIn, Indeed, Computrabajo y Multitrabajos a la vez y guarda las
ofertas en un solo archivo CSV. Está hecho para Ecuador: las ciudades, provincias y rutas
de cada sitio que conoce son las de Ecuador.

## Qué puedes hacer

Solo necesitas el primer uso. Los otros dos se apoyan en él.

| Uso | Qué obtienes | Guía |
|---|---|---|
| 1. Buscar empleos | Un CSV con las ofertas, que abres en Excel | [Aquí abajo](#1-buscar-empleos), unos 5 minutos |
| 2. Recibir un correo diario | Las ofertas nuevas de cada día, ordenadas según lo bien que encajan con tu perfil | [Correo diario](#2-recibir-un-correo-diario) |
| 3. Analizar el mercado | Consultas SQL y Power BI: qué habilidades se piden, dónde y quién contrata | [Analizar](#3-analizar-el-mercado) |

## Instalación

1. Descarga el zip de la [última versión](https://github.com/eriecua/jobs-scraper-ecuador/releases/latest)
   (*Source code (zip)*) y descomprímelo en una carpeta cuya ruta no tenga tildes.

2. Instala [uv](https://docs.astral.sh/uv/). Es lo único que necesitas: no instalas Python
   tú, porque uv descarga la versión correcta en la primera corrida. Eso tarda un par de
   minutos, una sola vez.

   Windows (PowerShell):
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Mac y Linux (Terminal):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Cierra la terminal y vuelve a abrirla para que encuentre `uv`.

3. Abre una terminal en la carpeta del proyecto. En Windows, abre la carpeta en el
   Explorador, escribe `powershell` en la barra de direcciones y pulsa Enter. En Mac, abre
   la Terminal, escribe `cd ` seguido de un espacio, arrastra la carpeta a la ventana y
   pulsa Enter.

## 1. Buscar empleos

Windows:
```powershell
.\scrap.cmd "Data Analyst" --ubicacion "Quito, Ecuador" --resultados 20
```
Mac y Linux:
```bash
./scrap.sh "Data Analyst" --ubicacion "Quito, Ecuador" --resultados 20
```

El resultado queda en la carpeta `data/`, en un archivo como
`nuevos_Data_Analyst_20261010_204819.csv`. Ábrelo con Excel:

| site | title | company | ciudad | date_posted | job_url |
|---|---|---|---|---|---|
| linkedin | Marketing Analyst, New Business and M&A | Toptal | Quito | 2026-10-08 | linkedin.com/jobs/view/… |
| indeed | Senior Accounting Analyst | PayJoy | Quito | 2026-10-09 | ec.indeed.com/viewjob?… |
| computrabajo | Analista de marketing | CEO Marketing USA | Quito | 2026-10-07 | ec.computrabajo.com/… |
| multitrabajos | Junior Data Entry Analyst | Human Brand Consulting | Quito | 2026-10-02 | multitrabajos.com/… |

Una vacante publicada en dos sitios aparece una sola vez.

### Solo ofertas nuevas, o todas

El scraper recuerda lo que ya te mostró, en `data/historico.csv`. Si repites una búsqueda,
el CSV trae solo lo que se publicó desde la corrida anterior. Cuando no hay nada nuevo,
muestra `Nada nuevo` y no crea archivo. Para guardar todas las ofertas que encuentre,
vistas o no, añade `--todas`:

```powershell
.\scrap.cmd "Data Analyst" --ubicacion "Quito, Ecuador" --todas
```

Ese archivo se llama `todas_*.csv`.

### Opciones

| Opción | Por defecto | Qué hace |
|---|---|---|
| `"puesto"` | ninguno | El puesto a buscar (obligatorio). Ej: `"Data Analyst"`, `"Contador"` |
| `-t "p1" "p2"` | ninguno | Varios puestos en una corrida |
| `--ubicacion` | `Ecuador` | Ciudad, provincia o país. Ej: `"Guayaquil, Ecuador"` |
| `--resultados` | `100` | Cuántas ofertas traer de cada sitio |
| `--todas` | no | Guarda también las ofertas ya vistas en corridas anteriores |
| `--horas` | ninguno | Solo ofertas de las últimas N horas. Ej: `--horas 72` |
| `--tipo` | ninguno | `fulltime`, `parttime`, `contract` o `internship` |
| `--sitios` | los cuatro | En qué sitios buscar. Ej: `--sitios linkedin,computrabajo` |
| `--distancia` | `50` | Radio en km alrededor de la ciudad (LinkedIn e Indeed) |
| `--pais` | `ecuador` | País para Indeed |
| `--descripcion` | no | Pide también la descripción completa de la oferta, que es más lento; va a `data/descripciones.csv` |

Más ejemplos:
```powershell
.\scrap.cmd "Ingeniero Industrial" --horas 168 --tipo fulltime
.\scrap.cmd -t "Data Analyst" "Data Scientist" --ubicacion "Guayaquil, Ecuador"
```

## 2. Recibir un correo diario

Varias veces al día, el scraper recorre tus ciudades y te manda por Gmail las ofertas
nuevas, ordenadas según lo bien que encajan con lo que buscas, con gráficos y el CSV
adjunto.

1. Copia `.env.example` como `.env` y rellénalo con tu dirección de Gmail y una contraseña
   de aplicación de Google ([cómo sacarla](docs/correo.md#1-tus-datos-de-gmail)).
2. Edita `CIUDADES` en `main.py` y tus palabras clave en `perfil.py`. Los dos vienen con un
   perfil de ejemplo: puestos de datos y BI en Quito, Guayaquil, Santo Domingo y Cuenca.
3. Pruébalo con `.\scrap_diario.cmd` en Windows o `./scrap_diario.sh` en Mac y Linux. Te
   debe llegar el correo.
4. Agéndalo para que corra solo, en Windows o en Mac y Linux.

La guía completa está en [docs/correo.md](docs/correo.md).

## 3. Analizar el mercado

Cada oferta que el scraper ve se suma a `data/historico.csv`. Un comando convierte ese
archivo en una base de datos que puedes consultar con SQL o abrir en Power BI.

1. Usa el scraper unos días (uso 1 o 2). Cuantas más corridas tengas, más parte del
   mercado cubren los datos.
2. Corre `.\analizar.cmd` en Windows o `./analizar.sh` en Mac y Linux. Crea
   `data/historico.db` para SQL y `data/analisis.csv` para Power BI.
3. Abre `data/historico.db` en [DB Browser for SQLite](https://sqlitebrowser.org/), que es
   gratis, y pega una consulta de [`consultas.sql`](consultas.sql). Las consultas incluyen
   las ofertas más recientes que coinciden con tus palabras clave, las que mejor encajan
   con tu perfil, las habilidades más pedidas y las empresas que más publican.

La guía completa, con los pasos de Power BI, está en [docs/analisis.md](docs/analisis.md).

## Problemas frecuentes

| Ves esto | Qué significa | Qué hacer |
|---|---|---|
| `uv` no se reconoce | La terminal todavía no ve uv | Cierra y abre la terminal. Si sigue, reinstala uv |
| `Nada nuevo` | Ya habías visto todas esas ofertas | No es un error. Usa `--todas` para guardarlas igual |
| `[AVISO] <sitio> fallo` | Ese sitio no respondió; los demás siguen | Nada, si otros sitios trajeron ofertas. Si LinkedIn falla seguido, te bloqueó por hacer demasiadas peticiones: espera unas horas |
| `'X' no esta en el mapa de ubicaciones de Computrabajo` | Esa ciudad no está configurada para Computrabajo | Ver [añadir una ciudad](docs/configuracion.md#añadir-una-ciudad) |
| `Faltan GMAIL_USUARIO...` | Falta el archivo `.env` o está incompleto | Ver [docs/correo.md](docs/correo.md#1-tus-datos-de-gmail) |
| `Posible cambio de estructura en Computrabajo` | El sitio cambió sus páginas | Hay que actualizar `computrabajo.py`; abre un *issue* |
| `permission denied` (Mac/Linux) | El zip perdió el permiso de ejecución | Corre `chmod +x *.sh` |
| Error al guardar `historico.csv` (código de salida 3) | El archivo está abierto en Excel | Ciérralo y vuelve a correr |

Los códigos de salida y el resto de mensajes están en
[docs/correo.md](docs/correo.md#códigos-de-salida).

## Más documentación

- [docs/correo.md](docs/correo.md): el correo diario y cómo agendarlo en Windows y en Mac y Linux.
- [docs/analisis.md](docs/analisis.md): SQL, Power BI, qué datos tienes y qué no se puede medir.
- [docs/configuracion.md](docs/configuracion.md): tu perfil, ciudades, sitios y categorías de puesto.
- [docs/como-funciona.md](docs/como-funciona.md): el histórico, cada sitio, los archivos del proyecto y las pruebas.

> No corras `pip install -r requirements.txt` con tu propio Python. `python-jobspy` exige
> `numpy==1.26.3`, que no tiene paquete precompilado para Python 3.13 o superior. Los
> lanzadores (`.cmd` y `.sh`) usan `uv` para evitarlo.

## Aviso legal

Es un proyecto personal y educativo. Usarlo implica aceptar los términos de uso de cada
sitio (LinkedIn, Indeed, Computrabajo, Multitrabajos), que pueden limitar el acceso
automatizado. Úsalo con moderación: los sitios bloquean temporalmente a quien hace
demasiadas peticiones, y el scraper ya hace pausas entre peticiones. Los datos pertenecen
a quien los publicó; no los redistribuyas.

LinkedIn e Indeed se consultan a través de [JobSpy](https://github.com/speedyapply/JobSpy).

## Licencia

[MIT](LICENSE). Puedes usarlo, modificarlo y redistribuirlo siempre que mantengas el aviso
de copyright.
