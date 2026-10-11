# Analizar el mercado

Cada oferta que el scraper ve, en cualquier búsqueda o en el correo diario, se guarda en
`data/historico.csv`. Con el tiempo ese archivo es una foto del mercado laboral: qué
puestos se piden, dónde, qué empresas contratan y qué herramientas exigen.

Esta guía lo convierte en una base de datos que consultas con SQL o abres en Power BI.

- [Paso 1: juntar datos](#paso-1-juntar-datos)
- [Paso 2: preparar la base](#paso-2-preparar-la-base)
- [Paso 3a: consultar con SQL](#paso-3a-consultar-con-sql)
- [Paso 3b: abrirlo en Power BI](#paso-3b-abrirlo-en-power-bi)
- [Qué columnas hay](#qué-columnas-hay)
- [Qué se puede medir y qué no](#qué-se-puede-medir-y-qué-no)

## Paso 1: juntar datos

Usa el scraper unos días: búsquedas sueltas (uso 1) o, mejor, el
[correo diario](correo.md), que recorre ciudades enteras sin filtrar por puesto y da una
muestra más completa del mercado. Cuantas más corridas, más fiable la foto.

## Paso 2: preparar la base

Windows:
```powershell
.\analizar.cmd
```
Mac y Linux:
```bash
./analizar.sh
```

No busca nada en internet: lee lo que ya tienes y crea dos archivos con el mismo
contenido, cada uno para una herramienta:

| Archivo | Para qué |
|---|---|
| `data/historico.db` | Consultar con SQL (DB Browser for SQLite) |
| `data/analisis.csv` | Power BI o Excel, sin instalar nada más |

Puedes correrlo las veces que quieras: se reconstruye entero cada vez. Hazlo de nuevo
cuando quieras ver los datos más recientes. Al terminar imprime un resumen (ofertas por
ciudad, qué se busca, las que más te encajan, empresas que más publican).

Además de las columnas que trae cada sitio, añade otras ya calculadas, listas para
filtrar: familia de puesto, puntaje de compatibilidad, nivel, motivo de exclusión y
empresa normalizada (ver [qué columnas hay](#qué-columnas-hay)).

## Paso 3a: consultar con SQL

1. Instala [DB Browser for SQLite](https://sqlitebrowser.org/dl/) (gratis, Windows y Mac).
2. Ábrelo → *Abrir base de datos* → elige `data/historico.db`.
3. Ve a la pestaña **Ejecutar SQL**.
4. Abre [`consultas.sql`](../consultas.sql), copia **una** consulta, pégala y pulsa
   **Ctrl+Enter** (Cmd+Enter en Mac).

Consultas incluidas:

| # | Consulta | Para qué |
|---|---|---|
| 1 | Las más recientes que coinciden con tus palabras | Ver lo último de "analista", "datos"... en tu ciudad |
| 2 | Las que mejor encajan con tu perfil | Las mejor puntuadas de los últimos 30 días |
| 3 | Ofertas por ciudad | Dónde hay más movimiento |
| 4 | Qué tipo de puestos se buscan | Reparto por familia (Ventas, Datos/BI, TI...) |
| 5 | Empresas que más publican | Quién contrata |
| 6 | Habilidades más pedidas | Qué herramientas exigen (Excel, SQL, Power BI...) |
| 7 | Habilidades por tipo de puesto | Qué piden para Datos/BI, TI, etc. |
| 8 | Ofertas nuevas por semana | Cuánto se mueve el mercado |
| 9 | Ofertas por sitio | Qué portal aporta más |

Para buscar tus propias palabras, usa la consulta 1 como plantilla. Escribe las palabras
en **minúsculas y sin tildes** sobre la columna `titulo_normalizado`: así `'%analisis%'`
encuentra "Análisis", "ANÁLISIS" y "analisis". Sobre `title` no funcionaría igual, porque
SQLite no ignora las mayúsculas en letras con tilde.

Hay dos tablas:

- **`ofertas`**: una fila por oferta.
- **`habilidades`**: qué pide cada oferta (`id`, `habilidad`, `grupo`). Se une con
  `ofertas` por `id`, como en las consultas 6 y 7.

## Paso 3b: abrirlo en Power BI

1. Power BI Desktop → **Obtener datos** → **Texto/CSV** → elige `data/analisis.csv` →
   **Cargar**.
2. Para las habilidades, repite con `data/habilidades.csv`.
3. En la vista **Modelo**, relaciona `analisis[id]` con `habilidades[id]` (uno a varios).
4. Las columnas calculadas (`familia`, `nivel`, `ciudad`, `puntaje`...) sirven directamente
   como segmentadores, sin escribir medidas DAX.

Para las descripciones completas, `data/descripciones.csv` (`id`, `description`) se
relaciona igual, por `id`.

Cuando vuelvas a correr `analizar`, pulsa **Actualizar** en Power BI.

> Power BI también puede leer `historico.db`, pero necesita un driver ODBC de SQLite que
> hay que instalar aparte y no siempre conecta. El CSV no necesita nada.

## Qué columnas hay

Las de cada sitio:

| Columna | Qué es |
|---|---|
| `id` | Identificador de la oferta (une con `habilidades` y `descripciones.csv`) |
| `site` | `linkedin`, `indeed`, `computrabajo`, `multitrabajos` |
| `title`, `company`, `job_url` | Título, empresa y link |
| `location` | Ubicación tal cual la escribe el sitio |
| `ciudad`, `provincia` | Ubicación normalizada: filtra por estas, no por `location` |
| `date_posted` | Fecha de publicación (no siempre viene) |
| `is_remote`, `job_type` | Remoto y tipo de jornada, cuando el sitio lo dice |
| `salary` | Sueldo como texto (solo Computrabajo) |
| `busqueda` | Qué búsqueda la encontró |
| `visto_primera_vez` | Día en que el scraper la vio por primera vez |

Las que calcula `analizar`:

| Columna | Qué es |
|---|---|
| `familia` | Tipo de puesto: Ventas, Datos/BI, Desarrollador/TI... ([cómo se decide](configuracion.md#categorías-y-publicaciones-que-no-son-ofertas--reportepy)) |
| `nivel` | Prácticas, Junior, Senior, Jefatura, si el título lo dice |
| `puntaje`, `terminos` | Compatibilidad con tu perfil y qué palabras la dieron ([perfil.py](configuracion.md#tu-perfil--perfilpy)) |
| `motivo_exclusion` | Por qué tu perfil la descarta (vacío si no la descarta) |
| `empresa`, `empresa_confidencial` | Empresa normalizada; las ~20 formas de "confidencial" juntas |
| `es_oferta_real` | 0 si es una publicación que no describe un puesto ("Trabaja con nosotros") |
| `titulo_normalizado` | Título en minúsculas y sin tildes, para buscar con `LIKE` |

## Qué se puede medir y qué no

Antes de construir un gráfico, mira cuánto se llena cada columna. Medido sobre 392
ofertas reales:

```
site 100% · location 96% · company 93% · date_posted 79% · is_remote 76%
salary (texto, solo Computrabajo) 16% · job_type 9%
min_amount / max_amount 3% · company_industry 3% · job_level 0%
```

- **No se pueden analizar sueldos.** Con un 3% de ofertas con sueldo numérico, ningún
  promedio ni gráfico es fiable. Por eso `min_amount`/`max_amount` no están en la base.
- **Habilidades: solo de las ofertas con descripción.** La traen Multitrabajos (siempre) e
  Indeed (~87%); LinkedIn y Computrabajo no. En un histórico real son unas 340 de 11.600
  ofertas. Los porcentajes de la consulta 6 son sobre esas, no sobre todas. Con
  `--descripcion` en las búsquedas sueltas se piden también las de LinkedIn (más lento).
- **Fechas:** cuando falta `date_posted`, las consultas usan `visto_primera_vez`.
- **Spam:** LinkedIn publica anuncios que no son ofertas ("Trabaja con nosotros",
  clickbait). Filtra con `es_oferta_real = 1`.

Las habilidades que se buscan están en `HABILIDADES` de `habilidades.py`. Si añades una,
la próxima corrida con ofertas nuevas regenera `data/habilidades.csv` entero.
