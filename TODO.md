# TODO

Pendientes del scraper, con lo que ya se investigó de cada uno para no repetir trabajo.

---

## 1. Multitrabajos — integrado (05/10/2026)

En `SITIOS_DEFECTO` y en `FUENTES_PROPIAS` de `buscador.py`; entra en `scrap.cmd` y en el
diario sin más cambios. Diario completo probado en una copia del histórico, correo
simulado: 55 de 152 ofertas nuevas (36%) vinieron de Multitrabajos, y solo 2 de sus 57
estaban ya en otro sitio. Se añadió Cuenca a `CIUDADES` (slug de Computrabajo ya existía).

### Cómo se consigue (05/10/2026) — sin Playwright

El HTML es un cascarón, pero la web llama a una API JSON que responde con HTTP plano:

```
POST https://www.multitrabajos.com/api/avisos/searchV2?pageSize=100&page=0&sort=RECIENTES
x-site-id: BMEC · Content-Type: application/json · Referer: https://www.multitrabajos.com/
User-Agent de navegador COMPLETO (con "Mozilla/5.0" a secas devuelve cuerpo vacío)
{"filtros": [...], "query": "ingeniero industrial"}
-> {number, size, total, content: [{id, titulo, empresa, confidencial, localizacion,
    fechaPublicacion "dd-mm-aaaa", modalidadTrabajo, tipoTrabajo, ...}]}
```

- **Filtros**: `{"id": <tipo>, "value": <idSemantico>}`. El catálogo con conteos sale de
  `GET /api/avisos/filtersV2` (mismos headers). Se usa el `idSemantico`, **no** el `id`
  numérico (con `"77"` da 0). Un valor inválido devuelve 200 con 0 ofertas, sin error.
  - Provincia: `{"id":"provincia","value":"ecuador|pichincha"}`
  - Ciudad: `{"id":"localidad","value":"ecuador|pichincha|quito"}` (slug provincia|ciudad)
  - Fecha: `{"id":"dias_fecha_publicacion","value":"publicacion-hoy"}`; también
    `publicacion-menor-a-{2..6}-dias`, `-7-dias`, `-15-dias`, `-1-mes`. Formatos
    `now-1d/d` o `menor-a-1-dia` dan 0.
- **Orden**: query param `sort=RECIENTES` (por defecto `RELEVANTES`).
- **Paginación**: `page` desde 0. `pageSize=1000` funciona (sin término: 1000 de 5579);
  el módulo usa 100.
- **URL de la oferta**: `/empleos/<slug-titulo>[-<slug-empresa>]-<id>.html` (empresa
  omitida si `confidencial`), igual que `makeFichaAvisoURL` del bundle. El sitio resuelve
  por el id final y redirige a la canónica. Ojo: el HTML responde 200 **para cualquier
  id** (SPA), así que un 200 no prueba nada; se comprobó en el navegador que abre la
  oferta correcta, y `GET /api/candidates/fichaAvisoNormalizada/<id>` da 200 con la
  oferta (id inválido: 500).

### Verificación (05/10/2026, Python 3.12 de uv con `requirements.txt`)

| Llamada | Filas | Web/API |
|---|---|---|
| `scrape('ingeniero industrial')` | 7 | 7 |
| `scrape('analista', resultados=300)` (3 páginas) | 226, ids únicos | 226 |
| `scrape('analista', 'Quito, Ecuador')` | 102, todas Quito | 102 |
| `scrape('', 'Santo Domingo de los Tsachilas, Ecuador')` | 176 | 176 (faceta) |
| `scrape('', 'Guayaquil, Ecuador', dias_max=1)` | 8, fechas 04-05/10 | — |
| `scrape('', dias_max=7, resultados=2000)` | 685, 28/09–05/10 | 684 (faceta) |

Campos llenos: id/title/company/location/date_posted/job_url/is_remote/job_type 100%,
salary 0% (la API no lo trae). `company` = "Confidencial" cuando la oferta lo es.

### Riesgos de la integración — medidos

- **Ventana del diario:** no era riesgo. `dias_max = ceil(24/24) = 1` pide el tramo
  "menor a 2 días" y conserva hoy y ayer.
- **Primera corrida:** con la ventana de 1 día el primer correo fue de tamaño normal
  ("12 de 121 puestos nuevos te encajan").
- **Abiertos:** duplicados entre sitios si el título varía; gráfico "Por sitio" con
  `limite=5` ya tiene exactamente 5 sitios.

### Visto de paso al probar

- LinkedIn respondió **429** a las 12:44 del 05/10 (ver "Vigilar el bloqueo de LinkedIn").
- Computrabajo perdía empresa y fecha — **arreglado el 05/10**. Las empresas sin perfil
  (20%) vienen como texto plano, no como enlace; y pasados unos días la antigüedad sale
  como "25 de septiembre" sin año (10%). Las filas viejas del histórico siguen vacías.

---

## 2. Varios términos y ciudades en un comando — **EN PAUSA**

Pausado el 15/08/2026 por decisión suya.

La idea era imitar a `jobsparser`:

```powershell
.\scrap "analista de datos" "ingeniero industrial" `
    --ubicacion "Quito, Ecuador" --ubicacion "Guayaquil, Ecuador" --horas 168
```

**Estimación: ~40 minutos.** Es un bucle sobre `buscar()`, que ya existe y ya se llama en
bucle dentro de `ejecutar_diario()`. Incluiría `--salida` para elegir carpeta.

Cuidado: 6 combinaciones × 3 sitios = 18 búsquedas. Haría falta una pausa entre ellas o
LinkedIn empezará a bloquear.

### Lo que se descartó al investigarlo

- **Google Jobs**: jobspy devuelve 0 ofertas **en todo el mundo** (probado en Nueva York y
  Londres). Google desmanteló el widget que raspaba. No es un problema de Ecuador.
- **Glassdoor**: jobspy devuelve 0 hasta en EE.UU. (error 400, "location not parsed").
  Además su lista de países no incluye Ecuador, Colombia, Perú, Chile ni Uruguay. Raspar
  directo choca con Cloudflare + CAPTCHA.
- **ZipRecruiter**: 403, es de EE.UU.
- **`--linkedin-experience-level`**: **no funciona, ni siquiera en `jobsparser`.** La URL
  que construye jobspy no lleva el parámetro `f_E` de LinkedIn, y el `**kwargs` de
  `scrape_jobs` se traga cualquier argumento desconocido sin avisar. Comprobado: dos
  llamadas idénticas varían en 17 de 20 resultados, y con el flag varían en 7 — la
  diferencia es ruido, no filtrado.

---

## 3. Pendientes menores

- **Ver el correo en el celular.** Nunca se verificó; en escritorio y modo oscuro se ve
  bien.
- **Decidir `FAMILIAS_EXCLUIDAS`.** El gráfico sigue mostrando ~24 ofertas de Ventas que
  `EXCLUIDOS` no atrapa porque su título no lleva ninguna palabra de la lista
  ("impulsador", "merchandiser", "promotor"). Poner `['Ventas']` las barre todas.
- **No hay pruebas automáticas.** Todo se verificó con scripts desechables. Si algo se
  rompe, no hay nada que avise salvo un correo que no llega. `historico.py`, `perfil.py` y
  `reporte.py` son testeables sin red.
- **Vigilar el bloqueo de LinkedIn.** Con tres corridas diarias se triplican las
  peticiones. Si aparece `[AVISO] linkedin fallo`, bajar a dos corridas o reducir
  `RESULTADOS_DIARIO`.
