# Jobs Scraper Ecuador

[Leer en español](README.es.md)

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows | macOS | Linux](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
[![Tests](https://github.com/eriecua/jobs-scraper-ecuador/actions/workflows/pruebas.yml/badge.svg)](https://github.com/eriecua/jobs-scraper-ecuador/actions/workflows/pruebas.yml)

Searches LinkedIn, Indeed, Computrabajo and Multitrabajos at once and saves the job posts
to a single CSV file. It is built for Ecuador: the cities, provinces and site routes it
knows are Ecuadorian.

## What you can do with it

You only need the first use. The other two build on it.

| Use | What you get | Guide |
|---|---|---|
| 1. Search for jobs | A CSV of job posts that you open in Excel | [Below](#1-search-for-jobs), about 5 minutes |
| 2. Get a daily email | The new posts each day, ranked by how well they match your profile | [Daily email](#2-get-a-daily-email) |
| 3. Analyze the job market | SQL queries and Power BI: which skills are in demand, where, and who is hiring | [Analyze](#3-analyze-the-job-market) |

## Installation

1. Download the zip from the [latest release](https://github.com/eriecua/jobs-scraper-ecuador/releases/latest)
   (*Source code (zip)*) and unzip it into a folder whose path has no accented letters.

2. Install [uv](https://docs.astral.sh/uv/). It is the only thing you need: you don't
   install Python yourself, because uv downloads the right version on the first run. That
   takes a couple of minutes, once.

   Windows (PowerShell):
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Mac and Linux (Terminal):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Close the terminal and open it again so it finds `uv`.

3. Open a terminal in the project folder. On Windows, open the folder in File Explorer,
   type `powershell` in the address bar and press Enter. On a Mac, open Terminal, type `cd `
   followed by a space, drag the folder onto the window and press Enter.

## 1. Search for jobs

Windows:
```powershell
.\scrap.cmd "Data Analyst" --ubicacion "Quito, Ecuador" --resultados 20
```
Mac and Linux:
```bash
./scrap.sh "Data Analyst" --ubicacion "Quito, Ecuador" --resultados 20
```

The results go to the `data/` folder, in a file such as
`nuevos_Data_Analyst_20261010_204819.csv` (*nuevos* means "new"). Open it in Excel:

| site | title | company | ciudad | date_posted | job_url |
|---|---|---|---|---|---|
| linkedin | Marketing Analyst, New Business and M&A | Toptal | Quito | 2026-10-08 | linkedin.com/jobs/view/… |
| indeed | Senior Accounting Analyst | PayJoy | Quito | 2026-10-09 | ec.indeed.com/viewjob?… |
| computrabajo | Analista de marketing | CEO Marketing USA | Quito | 2026-10-07 | ec.computrabajo.com/… |
| multitrabajos | Junior Data Entry Analyst | Human Brand Consulting | Quito | 2026-10-02 | multitrabajos.com/… |

A job posted on two sites appears once.

### Only new posts, or all of them

The scraper remembers what it has already shown you, in `data/historico.csv`. If you repeat
a search, the CSV holds only what was posted since the previous run. When nothing is new it
prints `Nada nuevo` ("nothing new") and writes no file. To save every post it finds, seen
or not, add `--todas` ("all"):

```powershell
.\scrap.cmd "Data Analyst" --ubicacion "Quito, Ecuador" --todas
```

That file is named `todas_*.csv`.

### Options

The option names are in Spanish.

| Option | Default | What it does |
|---|---|---|
| `"puesto"` | none | The job title to search for (required). E.g. `"Data Analyst"`, `"Contador"` |
| `-t "p1" "p2"` | none | Several job titles in one run |
| `--ubicacion` | `Ecuador` | City, province or country. E.g. `"Guayaquil, Ecuador"` |
| `--resultados` | `100` | How many posts to fetch per site |
| `--todas` | off | Also save posts already seen in earlier runs |
| `--horas` | none | Only posts from the last N hours. E.g. `--horas 72` |
| `--tipo` | none | `fulltime`, `parttime`, `contract` or `internship` |
| `--sitios` | all four | Which sites to search. E.g. `--sitios linkedin,computrabajo` |
| `--distancia` | `50` | Radius in km around the city (LinkedIn and Indeed) |
| `--pais` | `ecuador` | Country for Indeed |
| `--descripcion` | off | Also fetch the full job description, which is slower; it goes to `data/descripciones.csv` |

More examples:
```powershell
.\scrap.cmd "Ingeniero Industrial" --horas 168 --tipo fulltime
.\scrap.cmd -t "Data Analyst" "Data Scientist" --ubicacion "Guayaquil, Ecuador"
```

## 2. Get a daily email

A few times a day, the scraper goes through your cities and sends you the new posts by
Gmail, ranked by how well they match what you are looking for, with charts and the CSV
attached.

1. Copy `.env.example` to `.env` and fill in your Gmail address and a Google app password
   ([how to get one](docs/correo.md#1-tus-datos-de-gmail)).
2. Edit `CIUDADES` (the cities) in `main.py` and your keywords in `perfil.py`. Both ship
   with an example profile: data and BI jobs in Quito, Guayaquil, Santo Domingo and Cuenca.
3. Test it with `.\scrap_diario.cmd` on Windows or `./scrap_diario.sh` on Mac and Linux.
   The email should arrive.
4. Schedule it so it runs on its own, on Windows or on Mac and Linux.

The full guide, in Spanish, is in [docs/correo.md](docs/correo.md).

## 3. Analyze the job market

Every post the scraper sees is added to `data/historico.csv`. One command turns that file
into a database you can query with SQL or open in Power BI.

1. Use the scraper for a few days (use 1 or 2). The more runs you have, the more of the
   market the data covers.
2. Run `.\analizar.cmd` on Windows or `./analizar.sh` on Mac and Linux. It creates
   `data/historico.db` for SQL and `data/analisis.csv` for Power BI.
3. Open `data/historico.db` in [DB Browser for SQLite](https://sqlitebrowser.org/), which is
   free, and paste a query from [`consultas.sql`](consultas.sql). The queries include the
   latest posts that match your keywords, the best matches for your profile, the most
   requested skills and the companies that post the most jobs.

The full guide, in Spanish and with the Power BI steps, is in
[docs/analisis.md](docs/analisis.md).

## Troubleshooting

| You see | What it means | What to do |
|---|---|---|
| `uv` is not recognized | The terminal does not see uv yet | Close and reopen the terminal. If it persists, reinstall uv |
| `Nada nuevo` | You had already seen all those posts | Nothing is wrong. Use `--todas` to save them anyway |
| `[AVISO] <sitio> fallo` | That site did not respond; the others carry on | Nothing, if other sites returned posts. If LinkedIn keeps failing, it has blocked you for sending too many requests: wait a few hours |
| `'X' no esta en el mapa de ubicaciones de Computrabajo` | That city is not set up for Computrabajo | See [adding a city](docs/configuracion.md#añadir-una-ciudad) |
| `Faltan GMAIL_USUARIO...` | The `.env` file is missing or incomplete | See [docs/correo.md](docs/correo.md#1-tus-datos-de-gmail) |
| `Posible cambio de estructura en Computrabajo` | The site changed its pages | `computrabajo.py` needs updating; open an issue |
| `permission denied` (Mac/Linux) | The zip lost the execute permission | Run `chmod +x *.sh` |
| Error saving `historico.csv` (exit code 3) | The file is open in Excel | Close it and run again |

Exit codes and the remaining messages are in
[docs/correo.md](docs/correo.md#códigos-de-salida).

## More documentation (in Spanish)

- [docs/correo.md](docs/correo.md): the daily email, and scheduling on Windows and on Mac and Linux.
- [docs/analisis.md](docs/analisis.md): SQL, Power BI, which data you have and what it cannot measure.
- [docs/configuracion.md](docs/configuracion.md): your profile, cities, sites and job categories.
- [docs/como-funciona.md](docs/como-funciona.md): the history file, each site, the project files and the tests.

> Don't run `pip install -r requirements.txt` with your own Python. `python-jobspy` requires
> `numpy==1.26.3`, which has no prebuilt package for Python 3.13 or later. The launchers
> (`.cmd` and `.sh`) use `uv` to avoid that.

## Legal notice

This is a personal, educational project. Using it means accepting the terms of use of each
site (LinkedIn, Indeed, Computrabajo, Multitrabajos), which may restrict automated access.
Use it in moderation: the sites temporarily block clients that send too many requests, and
the scraper already pauses between requests. The data belongs to whoever published it; do
not redistribute it.

LinkedIn and Indeed are scraped through [JobSpy](https://github.com/speedyapply/JobSpy).

## License

[MIT](LICENSE). You may use, modify and redistribute it as long as you keep the copyright
notice.
