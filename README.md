# Jobs Scraper Ecuador

![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows | macOS | Linux](https://img.shields.io/badge/plataforma-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
[![Pruebas](https://github.com/eriecua/jobs-scraper-ecuador/actions/workflows/pruebas.yml/badge.svg)](https://github.com/eriecua/jobs-scraper-ecuador/actions/workflows/pruebas.yml)

Busca empleos en **LinkedIn, Indeed, Computrabajo y Multitrabajos** a la vez y los guarda
en un solo CSV. Hecho para **Ecuador**.

## ¿Qué quieres hacer?

Son tres usos independientes. Solo necesitas el primero; los otros dos se suman encima.

| Quiero... | Qué obtienes | Guía |
|---|---|---|
| **1. Buscar empleos** | Un CSV con las ofertas, que abres en Excel | [Aquí abajo](#1-buscar-empleos) (5 min) |
| **2. Recibir un correo diario** | Cada día, las ofertas nuevas ordenadas según tu perfil | [Correo diario](#2-recibir-un-correo-diario) |
| **3. Analizar el mercado** | Consultas SQL y Power BI: qué se pide, dónde, quién contrata | [Analizar](#3-analizar-el-mercado) |

## Instalación

1. **Descarga** el zip de la [última versión](https://github.com/eriecua/jobs-scraper-ecuador/releases/latest)
   (*Source code (zip)*) y descomprímelo en una carpeta sin acentos.

2. **Instala [uv](https://docs.astral.sh/uv/)**, lo único que hace falta. No tienes que
   instalar Python: uv descarga la versión correcta la primera vez (tarda un par de
   minutos, solo esa vez).

   Windows (PowerShell):
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Mac y Linux (Terminal):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Cierra y vuelve a abrir la terminal para que reconozca `uv`.

3. **Abre la terminal en la carpeta del proyecto.** En Windows: abre la carpeta en el
   Explorador, escribe `powershell` en la barra de direcciones y pulsa Enter. En Mac: abre
   la Terminal, escribe `cd ` (con un espacio), arrastra la carpeta a la ventana y pulsa
   Enter.

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

Si la misma vacante sale en dos sitios, aparece una sola vez.

### Solo ofertas nuevas (y cómo ver todas)

El scraper **recuerda lo que ya te mostró** (en `data/historico.csv`). Si repites la misma
búsqueda, el CSV trae solo lo que salió desde la vez anterior, y si no hay nada nuevo verás
`Nada nuevo` y no se crea archivo. Para guardar **todas** las ofertas encontradas, vistas o
no, añade `--todas`:

```powershell
.\scrap.cmd "Data Analyst" --ubicacion "Quito, Ecuador" --todas
```

Ese archivo se llama `todas_*.csv`.

### Opciones

| Opción | Por defecto | Qué hace |
|---|---|---|
| `"puesto"` | — | Qué buscar. Obligatorio. Ej: `"Data Analyst"`, `"Contador"` |
| `-t "p1" "p2"` | — | Varios puestos en una corrida, en vez de uno |
| `--ubicacion` | `Ecuador` | Ciudad, provincia o país. Ej: `"Guayaquil, Ecuador"` |
| `--resultados` | `100` | Cuántas ofertas **por sitio** |
| `--todas` | no | Guarda también las ofertas ya vistas en corridas anteriores |
| `--horas` | — | Solo ofertas de las últimas N horas. Ej: `--horas 72` |
| `--tipo` | — | `fulltime`, `parttime`, `contract` o `internship` |
| `--sitios` | los cuatro | Ej: `--sitios linkedin,computrabajo` |
| `--distancia` | `50` | Radio en km alrededor de la ciudad (LinkedIn e Indeed) |
| `--pais` | `ecuador` | País para Indeed |
| `--descripcion` | no | Pide también la descripción completa (más lento); va a `data/descripciones.csv` |

Más ejemplos:
```powershell
.\scrap.cmd "Ingeniero Industrial" --horas 168 --tipo fulltime
.\scrap.cmd -t "Data Analyst" "Data Scientist" --ubicacion "Guayaquil, Ecuador"
```

## 2. Recibir un correo diario

El scraper recorre tus ciudades varias veces al día y te manda por Gmail las ofertas
nuevas, ordenadas según lo bien que encajan con lo que buscas, con gráficos y el CSV
adjunto.

1. **Pon tus datos de Gmail.** Copia `.env.example` como `.env` y rellénalo con tu correo y
   una *contraseña de aplicación* de Google ([cómo sacarla](docs/correo.md#1-tus-datos-de-gmail)).
2. **Di qué buscas.** Edita `CIUDADES` en `main.py` y tus palabras clave en `perfil.py`.
   Vienen con un perfil de ejemplo (Datos/BI en Quito, Guayaquil, Santo Domingo y Cuenca).
3. **Pruébalo:** `.\scrap_diario.cmd` (Windows) o `./scrap_diario.sh` (Mac/Linux). Te debe
   llegar el correo.
4. **Agéndalo** para que corra solo, en Windows o en Mac/Linux.

Guía completa paso a paso: **[docs/correo.md](docs/correo.md)**.

## 3. Analizar el mercado

Todo lo que el scraper ve se acumula en `data/historico.csv`. Con un comando lo conviertes
en una base de datos para consultar con SQL o abrir en Power BI.

1. **Junta datos:** usa el scraper unos días (uso 1 o 2). Cuantas más corridas, más
   mercado ves.
2. **Prepara la base:** `.\analizar.cmd` (Windows) o `./analizar.sh` (Mac/Linux). Crea
   `data/historico.db` (SQL) y `data/analisis.csv` (Power BI).
3. **Consulta:** abre `data/historico.db` con [DB Browser for SQLite](https://sqlitebrowser.org/)
   (gratis) y pega una consulta de [`consultas.sql`](consultas.sql): las ofertas más
   recientes que coinciden con tus palabras, las que mejor te encajan, qué habilidades
   piden, qué empresas contratan más, por ciudad, por semana...

Guía completa paso a paso, con Power BI: **[docs/analisis.md](docs/analisis.md)**.

## Problemas frecuentes

| Ves esto | Qué significa | Qué hacer |
|---|---|---|
| `uv` no se reconoce | La terminal no ve uv todavía | Cierra y abre la terminal. Si sigue, reinstala uv |
| `Nada nuevo` | Ya habías visto todas esas ofertas | Normal. Usa `--todas` para guardarlas igual |
| `[AVISO] <sitio> fallo` | Ese sitio no respondió; los demás siguen | Nada, si otros trajeron datos. Si LinkedIn falla seguido, te bloqueó por pedir mucho: espera unas horas |
| `'X' no esta en el mapa de ubicaciones de Computrabajo` | Esa ciudad no está configurada para Computrabajo | Ver [añadir una ciudad](docs/configuracion.md#añadir-una-ciudad) |
| `Faltan GMAIL_USUARIO...` | No hay `.env` o está incompleto | Ver [docs/correo.md](docs/correo.md#1-tus-datos-de-gmail) |
| `Posible cambio de estructura en Computrabajo` | El sitio cambió su página | Hay que actualizar `computrabajo.py`; abre un *issue* |
| `permission denied` (Mac/Linux) | El zip perdió el permiso de ejecución | `chmod +x *.sh` |
| Error al guardar `historico.csv` (código 3) | Lo tienes abierto en Excel | Ciérralo y repite |

Los códigos de salida y el resto de mensajes están en [docs/correo.md](docs/correo.md#códigos-de-salida).

## Más documentación

- [docs/correo.md](docs/correo.md): correo diario, agendado en Windows y Mac/Linux.
- [docs/analisis.md](docs/analisis.md): SQL, Power BI, qué datos hay y qué no se puede medir.
- [docs/configuracion.md](docs/configuracion.md): tu perfil, ciudades, sitios y categorías.
- [docs/como-funciona.md](docs/como-funciona.md): histórico, cada sitio, archivos del proyecto, pruebas.

> No uses `pip install -r requirements.txt` con tu Python: `python-jobspy` exige
> `numpy==1.26.3`, que no tiene versión precompilada para Python 3.13 o superior. Los
> lanzadores (`.cmd` / `.sh`) usan `uv` justamente para evitarlo.

## Aviso legal

Proyecto personal y educativo. Usarlo implica aceptar los términos de uso de cada sitio
(LinkedIn, Indeed, Computrabajo, Multitrabajos), que pueden limitar el acceso automatizado.
Úsalo con moderación: los sitios bloquean temporalmente a quien hace demasiadas
peticiones, y el scraper ya incluye pausas para evitarlo. Los datos pertenecen a sus
publicadores; no los redistribuyas.

Se apoya en [JobSpy](https://github.com/speedyapply/JobSpy) para LinkedIn e Indeed.

## Licencia

[MIT](LICENSE): puedes usarlo, modificarlo y redistribuirlo, manteniendo el aviso de
copyright.
