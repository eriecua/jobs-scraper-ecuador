# TODO

Pendientes del scraper, con lo que ya se investigó de cada uno para no repetir trabajo.

---

## 1. Añadir Multitrabajos como cuarto sitio

**Por qué:** hay ofertas buenas ahí que no aparecen en LinkedIn, Indeed ni Computrabajo.

### Lo que ya se investigó (15/08/2026)

El sitio funciona perfecto en el navegador — 6 ofertas para "ingeniero industrial", con
título, empresa, ciudad, fecha y modalidad. **El problema es solo conseguir la página.**

Cualquier cliente HTTP recibe **siempre los mismos 64.533 bytes**, un cascarón sin datos.
El navegador tiene 142.789 bytes en el DOM. Probado y descartado:

| Intento | Resultado |
|---|---|
| `requests` con cabeceras de navegador | 64.533 bytes, cascarón |
| `tls_client` (ya viene con jobspy), 4 perfiles | 64.533 bytes, cascarón |
| `curl_cffi`, 5 perfiles de impersonación | 64.533 bytes, cascarón |
| Buscar una API en las peticiones de red | Solo analítica: Facebook, New Relic, `cdn-cgi/rum` |
| `__NEXT_DATA__` / estado precargado | No existe |

No es huella TLS ni cabeceras: eso ya lo cubrían `tls_client` y `curl_cffi`. El contenido
se pinta en el cliente o lo libera Cloudflare tras un desafío JavaScript (se ve
`__cfBeacon` en `window`).

**Extraer los datos, en cambio, sería fácil.** La página trae un JSON-LD `ItemList` con
título y URL de cada oferta, y las tarjetas del DOM tienen el resto:

```json
{"@type":"ItemList","itemListElement":[
  {"position":1,"name":"Ingeniero Automatización Industrial",
   "url":"https://www.multitrabajos.com/empleos/ingeniero-automatizacion-industrial-1118393380.html"}]}
```

```
Actualizado hace 4 días
Ingeniero Automatización Industrial
Confidencial
Guayaquil, Guayas · Presencial
```

### Cómo hacerlo

Un `multitrabajos.py` hermano de `computrabajo.py`, con la misma firma `scrape()` y las
mismas columnas, para que `buscador.py` solo tenga que añadirlo a `SITIOS_DEFECTO`.

La única decisión real es cómo obtener el HTML:

| Opción | Coste | Riesgo |
|---|---|---|
| **Playwright** (navegador headless) | ~300 MB de dependencia, ~10-15s por búsqueda | Bajo: es un navegador de verdad |
| Cookie `cf_clearance` capturada a mano | Barato | Caduca en horas; no sirve para una tarea agendada |
| `cloudscraper` | Barato de probar | Cloudflare lo detecta desde hace años |

**Estimación: 2-3 horas con Playwright.** Una hora es el parseo (comparable a
Computrabajo); el resto es integrar el navegador y que no rompa la tarea agendada.

**Antes de empezar**, media hora probando `cloudscraper` y una petición con Playwright a
pelo: si Playwright funciona sin más, el resto es mecánico.

### Lo que hay que sopesar

Meter un navegador headless cambia la naturaleza del proyecto: hoy son tres módulos de
HTTP plano que corren en segundos. Playwright añade peso, lentitud y una pieza más que
puede fallar a las 08:00 sin que nadie mire.

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
