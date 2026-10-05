# Jobs Scraper (LinkedIn + Indeed + Computrabajo + Multitrabajos)

Busca empleos en LinkedIn, Indeed, Computrabajo y Multitrabajos, los compara contra un histórico y
guarda en CSV **solo lo que no habías visto antes**. Con `--diario` manda además un
correo con las ofertas nuevas agrupadas por ciudad.

Todos los sitios salen en el mismo CSV, con las mismas columnas. Si la misma vacante
aparece en varios sitios, se guarda una sola vez.

## Requisitos

Solo [uv](https://docs.astral.sh/uv/). No hay que instalar nada más ni activar entornos:
`scrap.cmd` provisiona Python 3.12 y las dependencias de `requirements.txt` la primera
vez, y las cachea.

> No corras `pip install -r requirements.txt` con el Python del sistema: fallará
> compilando numpy. `scrap.cmd` es la única vía soportada.

> **Por qué un Python aparte:** `jobspy` exige `numpy==1.26.3` y `pandas 2.x`. El Python
> 3.14 del sistema no tiene wheels para esa versión de numpy e intentaría compilarla.
> El entorno global (pandas 3.0.3) queda intacto.

## Manual de procedimiento

Cómo se usa esto en el día a día. Hay tres formas de lanzarlo, según lo que necesites.

### 1. El diario automático (no haces nada)

Una vez agendado, cada mañana a las 08:00 el PC recorre Quito, Guayaquil y Santo Domingo,
compara con el histórico y te manda un correo **solo si hay ofertas nuevas**.

Al abrirlo verás, en este orden: cuántas ofertas encontró y cuántas te encajan, los tres
gráficos, y debajo la lista ordenada por compatibilidad con el link de cada oferta.
El adjunto es el CSV con todo.

**Si no llega correo**, puede ser que no hubiera nada nuevo (normal) o que fallara. Para
distinguirlo, abre el Programador de tareas y mira el último resultado, o córrelo a mano
con `.\scrap_diario.cmd` y lee el código de salida.

### 2. La línea de comandos (búsquedas puntuales)

Para buscar algo concreto fuera del horario del diario:

```powershell
.\scrap "Data Analyst" --ubicacion "Quito, Ecuador" --resultados 50
```

Las opciones están en la tabla de la sección **Uso**, más abajo.

> Hubo una ventana gráfica para esto. Se retiró el 15/08/2026 porque no funcionaba como
> se esperaba. Cómo estaba hecha y cómo recuperarla: `legacy/NOTA-ventana-tkinter.md`.

### Qué hacer si algo falla

| Síntoma | Qué significa | Qué hacer |
|---|---|---|
| `[AVISO] <sitio> fallo` | Ese sitio no respondió; los demás siguen | Nada, si otros trajeron datos. Si se repite en LinkedIn, puede ser bloqueo por exceso de peticiones: espera unas horas |
| `'X' no esta en el mapa de ubicaciones de Computrabajo` | La ciudad no tiene slug | Añade su slug a `SLUGS_UBICACION` (ver configuración) |
| `computrabajo: recorriendo 12 provincias` | Normal: buscaste sin puesto ni ciudad | Nada. Tarda ~16s en vez de ~2s |
| `Faltan GMAIL_USUARIO...` | No hay credenciales | Revisa el `.env`. No scrapea nada, así que no se pierde ninguna oferta |
| `Posible cambio de estructura en Computrabajo` | Cambió el HTML del sitio | Hay que actualizar los selectores en `computrabajo.py` |
| Código de salida `1` | Fallaron todos los sitios | Revisa tu conexión |
| Código de salida `2` | Scrapeó bien pero no envió el correo | Las ofertas están en `data/diario_*.csv`; **no se repetirán** en el correo siguiente |

## Configurar los parámetros del buscador

Todo se ajusta editando constantes al principio de cada archivo. No hay ventana para
esto a propósito: un programa que reescribe su propio código puede dejarlo roto.

### Lo que buscas cada día — `main.py`

```python
CIUDADES = [
    'Quito, Ecuador',
    'Santo Domingo de los Tsachilas, Ecuador',
    'Guayaquil, Ecuador',
]
HORAS_DIARIO = 24        # ventana de tiempo del diario
RESULTADOS_DIARIO = 100  # por sitio Y por ciudad: 3 ciudades x 3 sitios x 100 = 900 máx.
ENVIAR_SI_VACIO = False  # True = te escribe aunque no haya nada nuevo
```

> **Añadir una ciudad son dos pasos.** Además de ponerla aquí, hay que darle su slug en
> `computrabajo.py` (siguiente apartado) o Computrabajo devolverá cero ofertas **sin dar
> error**.

### Ciudades de Computrabajo — `computrabajo.py`

Computrabajo no entiende `"Quito, Ecuador"`: su ruta es `pichincha-en-quito`.

```python
SLUGS_UBICACION = {
    'quito': 'pichincha-en-quito',
    'guayaquil': 'guayas-en-guayaquil',
    'cuenca': 'azuay-en-cuenca',
    ...
}
```

Para añadir una: abre `https://ec.computrabajo.com/empleos-en-<slug>` en el navegador. Si
salen ofertas, el slug sirve. El formato es `<provincia>-en-<ciudad>`, sin tildes y con
guiones.

### Tus términos de búsqueda — `perfil.py`

Las tres listas que deciden el puntaje de compatibilidad. **Es lo que más vas a tocar**:
según vayas viendo los correos, irás afinando qué te interesa y qué no.

```python
INTERES   = {'analista': 30, 'datos': 30, ...}   # suben la oferta, NO la filtran
DESEABLES = {'python': 15, 'sql': 15, ...}       # herramientas, suman encima
EXCLUIDOS = ['ventas', 'sales', 'chofer', ...]   # vetan la oferta entera
FAMILIAS_EXCLUIDAS = []                          # categorias enteras: 'Ventas', ...
```

Escribe cada término como **palabra completa**: `estadistic` no coincide con
"estadística".

Después de cambiarlas, comprueba el efecto sobre las ofertas que ya tienes:

```powershell
uv run --python 3.12 --with-requirements requirements.txt --no-project python -c "import pandas as pd, perfil; d=pd.read_csv('data/historico.csv',dtype=str); p=d['title'].fillna('').map(lambda t: perfil.puntuar(t)[0]); print('encajan:', (p>=30).sum(), 'de', len(d)); [print(f'{v:4} {t[:60]}') for t,v in sorted(zip(d['title'].fillna(''),p), key=lambda x:-x[1])[:15]]"
```

Te imprime cuántas encajan y las 15 mejores. Si aparecen puestos que no te interesan,
añade la palabra a `EXCLUIDOS`; si falta alguno que sí, añádela a `NUCLEO`.

### Sitios y descripción — `buscador.py`

```python
SITIOS_DEFECTO = ('linkedin', 'indeed', 'computrabajo')
DESCARTAR_DESCRIPCION = True   # False para conservar la descripción en el CSV
```

### Ciudades y provincias — `ubicaciones.py`

Los tres sitios escriben la misma ciudad de forma distinta. En el histórico hay **19
textos** para 6 ciudades reales:

```
'Quito, Pichincha, Ecuador'   'Quito, Pichincha'   'Quito, P, EC'
'Quito Canton, Pichincha, Ecuador'   'Pichincha, Ecuador'
```

`normalizar()` los convierte a un par **(ciudad, provincia)**, y ese par es lo que se
guarda en el CSV y lo que agrupa el gráfico del correo. Una sola tabla para los dos.

```python
CANTONES = {'quito': ('Quito', 'pichincha'), 'duran': ('Duran', 'guayas'), ...}
ALIAS    = {('eloy alfaro', 'guayas'): 'duran', ...}   # parroquias, no cantones
```

Tres cosas que conviene saber antes de editarlo:

- **Ciudad y provincia son cosas distintas.** Durán y Samborondón son cantones propios, no
  Guayaquil. Si el texto solo nombra la provincia, la ciudad queda **vacía** y el gráfico
  dice `Pichincha (prov.)`: no se inventa la capital.
- **Se trabaja por componentes**, no buscando en la cadena entera. Es lo que permite que
  `"Esmeraldas, Esmeraldas"` (cantón y provincia se llaman igual) y `"La Concordia, Santo
  Domingo de los Tsáchilas"` (el nombre de un cantón está dentro del de la provincia) den
  la respuesta correcta.
- **`ALIAS` lleva la provincia en la clave** a propósito: hay un *Eloy Alfaro* en Guayas
  (parroquia de Durán), otro cantón en Esmeraldas y una parroquia en Manta. Sin la
  provincia no se pueden distinguir.

Para añadir una ciudad, basta su entrada en `CANTONES`. Esto es independiente de
`SLUGS_UBICACION`, que es lo que Computrabajo necesita para *buscar*.

### Categorías de los gráficos — `reporte.py`

`FAMILIAS` agrupa los títulos (Ventas, Datos/BI, Logística…). Gana la primera coincidencia,
así que las específicas van **antes** que las genéricas. `NO_OFERTAS` esconde del correo
las publicaciones que no describen un puesto.

### Correo y agenda

El destinatario y las credenciales van en `.env`, no en el código. La hora del envío se
cambia en el Programador de tareas de Windows, no aquí.

## Uso

Desde **PowerShell o cmd** (no Git Bash: la invocación del `.cmd` falla ahí por la
interoperabilidad con rutas de Windows):

```powershell
.\scrap "Data Analyst"                                   # lo mínimo
.\scrap "Data Analyst" --ubicacion "Quito, Ecuador" --resultados 200
.\scrap "Ingeniero Industrial" --horas 168 --tipo fulltime
.\scrap "Data Analyst" --descripcion                     # trae description, ~3x mas lento

# TODOS los puestos de una ciudad (sin filtrar por título)
.\scrap --ubicacion "Quito, Ecuador" --resultados 200
```

Si omites el puesto, trae empleos de todo tipo de la ubicación y el CSV se nombra por la
ciudad.

| Opción | Default | Qué hace |
|---|---|---|
| `termino` | — | Puesto a buscar (posicional y **opcional**: sin él trae todos los puestos) |
| `--ubicacion` | `Ecuador` | Ciudad, provincia o país |
| `--resultados` | `100` | Cuántos empleos **por sitio** |
| `--sitios` | `linkedin,indeed,computrabajo` | Sitios separados por coma |
| `--pais` | `ecuador` | País que usa Indeed |
| `--horas` | — | Solo ofertas de las últimas N horas |
| `--tipo` | — | `fulltime`, `parttime`, `contract`, `internship` |
| `--distancia` | `50` | Radio en km |
| `--descripcion` | off | Incluye la descripción completa de cada oferta |
| `--diario` | off | Reporte agendado por correo (ver abajo) |

`--descripcion` dispara una petición extra **por cada empleo**: 7s → 22s para 20 ofertas.
Déjalo apagado salvo que necesites el texto.

## Los archivos

Cada uno hace un solo trabajo:

| Archivo | Qué hace |
|---|---|
| `main.py` | Configuración del diario, orquestación y línea de comandos |
| `buscador.py` | Busca en todos los sitios y junta los resultados |
| `computrabajo.py` | Raspa Computrabajo (jobspy no lo cubre) |
| `historico.py` | Decide qué es nuevo y guarda los CSV |
| `ubicaciones.py` | Convierte la ubicación cruda de cada sitio en ciudad + provincia |
| `perfil.py` | Puntúa cada oferta contra lo que buscas |
| `reporte.py` | Arma el correo con los gráficos |
| `correo.py` | Lo envía por Gmail |

## Salida e histórico

Cada corrida escribe **solo las ofertas nuevas** en
`data/nuevos_<etiqueta>_<timestamp>.csv`, con las columnas de jobspy. Las principales:

`site`, `title`, `company`, `location`, `ciudad`, `provincia`, `date_posted`, `job_type`,
`job_url`, `is_remote`, `min_amount`, `max_amount`, `currency`, `company_industry`,
`description`, `salary`.

`ciudad` y `provincia` las añade `ubicaciones.py` a partir de `location`, que se conserva
cruda por si hay que depurar un caso raro. Son las columnas por las que se filtra en
Excel: `location` trae 19 formas distintas de escribir 6 ciudades.

En el CSV del diario hay además `ciudad_busqueda`, y **no es lo mismo que `ciudad`**: la
primera dice qué se buscó, la segunda qué dice la oferta. Una búsqueda en Quito devuelve
legítimamente ofertas de Samborondón.

Cada sitio llena las que puede: LinkedIn e Indeed dan el salario en `min_amount`/
`max_amount`; Computrabajo lo da como texto en `salary`. `date_posted` sí queda
unificada como fecha en los tres.

La columna `description` **se descarta**: no se usa para nada (el índice puntúa con el
título) y son miles de caracteres por oferta que engordan el CSV. Indeed la manda dentro
de sus resultados, así que se elimina al final de la búsqueda. Para conservarla, pon
`DESCARTAR_DESCRIPCION = False` en `buscador.py`, o usa `--descripcion` en una corrida
suelta.

Se guarda en `utf-8-sig` para que Excel abra los acentos bien al doble clic.

Todo lo visto se acumula en `data/historico.csv`, que es lo que permite saber qué es
nuevo. Una oferta se considera repetida si coinciden **empresa + título + ciudad** (así
la misma vacante en Quito y en Guayaquil cuenta como dos) y si se vio hace menos de
`DIAS_CADUCIDAD` días (60 por defecto): pasado ese plazo, un repost vuelve a aparecer.
Si borras el histórico, la próxima corrida te devolverá todo como nuevo.

## Computrabajo

jobspy no soporta Computrabajo, así que `computrabajo.py` raspa el HTML directamente y
devuelve las mismas columnas que los demás sitios. Diferencias a tener en cuenta:

- **La ubicación va por un mapa de slugs.** Computrabajo no entiende `"Quito, Ecuador"`:
  la ruta es `pichincha-en-quito`. El mapa `SLUGS_UBICACION` en `computrabajo.py` trae
  las ciudades grandes de Ecuador. Una ciudad que no esté ahí devuelve **200 con cero
  ofertas**, sin error, así que el scraper avisa cuando eso pasa y los demás sitios sí
  trajeron algo. Para añadir una ciudad, agrega su slug al mapa.
- **No existe página de "todo el país".** `/empleos`, `/trabajo` y `/ofertas-de-trabajo`
  redirigen a la portada, y `/empleos-en-ecuador` responde 200 con cero ofertas. Cuando
  buscas sin puesto y sin ciudad (`--ubicacion Ecuador`, que es el default), el scraper
  **recorre las 12 provincias** una por una y se queda con las más recientes. Tarda ~16s
  frente a los ~2s de una ciudad concreta. Con un puesto sí hay URL de país
  (`trabajo-de-<puesto>`), así que ese caso sigue siendo rápido.
- **`--horas` se redondea a días.** Computrabajo solo publica la antigüedad como "Hace 3
  días", no la hora exacta. `--horas 24` se traduce a "último 1 día".
- **El salario viene como texto** (`"790,00 US$ (Mensual)"`) en la columna `salary`, no
  como `min_amount`/`max_amount` numéricos.
- Va con reintentos, backoff y una pausa de ~2s entre páginas para no hacerse bloquear;
  por eso es más lento que los otros dos.
- Si Computrabajo cambia su HTML, los selectores dejarían de coincidir. El scraper avisa
  (`Posible cambio de estructura`) cuando más de la mitad de las ofertas salen sin
  empresa o sin ubicación, en vez de devolver filas vacías en silencio.

### Códigos de salida

Importan si lo agendas: dicen si falló de verdad o si simplemente no había ofertas.

| Código | Significado |
|---|---|
| `0` | Corrida OK (con o sin ofertas nuevas) |
| `1` | Todos los sitios fallaron |
| `2` | El scrapeo funcionó pero el correo no se pudo enviar (el CSV queda en `data/`) |

## Reporte diario por correo

`main.py` tiene arriba un bloque de configuración editable:

```python
CIUDADES = ['Quito, Ecuador', 'Santo Domingo de los Tsachilas, Ecuador', 'Guayaquil, Ecuador']
HORAS_DIARIO = 24
RESULTADOS_DIARIO = 100
ENVIAR_SI_VACIO = False   # si no hay nada nuevo, no manda correo
```

`--diario` recorre esas ciudades sin filtrar por puesto, actualiza el histórico y manda
el correo con el CSV adjunto.

### Qué trae el correo

Lo construye `reporte.py`. De arriba abajo: cuatro números grandes (ofertas, cuántas te
encajan, ciudades, empresas), un gráfico de **ofertas por ciudad**, otro de **qué están
buscando** (familias de puesto), uno pequeño por sitio, y debajo la lista de ofertas
agrupada por ciudad, **ordenada por compatibilidad**, con su link.

Los gráficos son barras hechas con tablas y colores de fondo, no imágenes. Un correo no
ejecuta JavaScript ni dibuja SVG, y un PNG tendría tamaño fijo: se leería mal en el
celular y arrastraría su fondo blanco al modo oscuro. Las barras en HTML se reajustan al
ancho y admiten links al lado. Por eso en `reporte.py` no hay flexbox, grid, `<style>`,
SVG ni imágenes: nada de eso sobrevive en Gmail y Outlook.

Tres cosas que se ajustan a mano en `reporte.py`:

- **Las ubicaciones** ya no se configuran aquí: viven en `ubicaciones.py` (siguiente
  apartado), que es la misma tabla que rellena las columnas del CSV.
- **`FAMILIAS`** — agrupa los títulos en Ventas, Datos/BI, Logística, etc. Gana la primera
  que coincida, así que las específicas van antes que las genéricas. Cubre el **85%**; el
  resto cae en *Otros*, que siempre se muestra al final aunque sea grande.
- **`NO_OFERTAS`** — publicaciones que no describen un puesto (`"Trabaja con nosotros"`,
  `"Postula aquí"`). Son ofertas reales de LinkedIn, no un fallo del scraper. Se ocultan
  **solo del correo**: siguen en el CSV y en el histórico, y el correo dice al pie cuántas
  ocultó.

## Índice de compatibilidad (`perfil.py`)

Dos mecanismos con papeles **distintos**, y no conviene confundirlos:

| | Listas | Qué hacen |
|---|---|---|
| **Ordenan** | `INTERES`, `DESEABLES` | Suben la oferta en la lista. Nunca la eliminan. |
| **Quitan** | `EXCLUIDOS`, `FAMILIAS_EXCLUIDAS` | Vetan la oferta entera. |

| Lista | Qué contiene |
|---|---|
| `INTERES` | De qué va el puesto que buscas (`analista` 30, `datos` 30, `business intelligence` 30…). **No es obligatorio**: una oferta sin ninguno sale igual, solo que más abajo. |
| `DESEABLES` | Herramientas que suman encima (`python` 15, `sql` 15, `power bi` 15…). |
| `EXCLUIDOS` | Temas que no quieres ver (`ventas`, `sales`, `comercial`, `chofer`…). Vetan la oferta. |
| `FAMILIAS_EXCLUIDAS` | Categorías enteras a descartar (`'Ventas'`, `'Seguridad'`…), usando las `FAMILIAS` de `reporte.py`. Vacía por defecto. |

### Por qué el interés no filtra

Antes `INTERES` se llamaba `NUCLEO` y era obligatorio. Medido sobre el histórico, eso
mandaba a 0 el **68%** de las ofertas y enterraba cosas que sí servían:

```
JEFE UNIDAD DE ESTADÍSTICA     ← estadística
Database Consultant            ← datos
Oficial de cumplimiento uafe
```

En una búsqueda dirigida (`.\scrap "Analista de Datos"`) el filtro **ya lo hizo el propio
sitio**, así que exigirlo otra vez no aporta. En el diario solo servía para perder ofertas
sin saber cuáles. Ahora el interés ordena y solo `EXCLUIDOS` quita.

### Qué se está ocultando

El pie del correo lo dice siempre, con el término responsable y su recuento:

```
Se ocultaron 104 publicaciones:
   97 por tus exclusiones — comercial 37 · ventas 25 · sales 11 · vendedor 7 · ...
    7 que no describen un puesto ("Trabaja con nosotros")
```

Así ves qué palabra está recortando y cuánto, y puedes decidir con criterio si sobra.
Todas siguen en el CSV adjunto.

### Detalles que muerden

- **Escribe los términos como quieras**: `Power BI`, `optimización` o `VBA` funcionan
  igual que en minúsculas y sin tildes. El código los normaliza al cargar, y avisa si dos
  entradas resultan ser el mismo término (se queda con el peso más alto).
- **Los términos se comparan como palabra completa.** Una raíz como `estadistic` **no
  coincide nunca** con "estadística": hay que escribir cada forma. Por eso `bi` no salta
  dentro de "combinado" ni `sales` dentro de "Salesforce".
- **Cuidado con repetir una clave** en el mismo diccionario (`'mejora continua'` dos
  veces): Python se queda con la última en silencio y el otro peso se pierde. El aviso de
  duplicados solo detecta las que difieren en mayúsculas o tildes, no las idénticas.
- **El término más fuerte de `INTERES` cuenta entero y los demás a mitad**, para que
  "Analista de Datos" no se dispare solo por decir dos palabras del mismo tema.
- **`NIVELES` es solo etiqueta** (*Junior / Senior / Jefatura / Prácticas*): no suma ni
  resta, porque muchos títulos no mencionan el nivel y castigarlos por callarlo sería
  inventar información.
- **Los gráficos cuentan lo que se muestra**, no el total bruto, para que los números de
  arriba cuadren con la lista de abajo.
- Los puntajes son relativos, no una nota sobre 100. Una oferta muy buena ronda 45-72.

### Credenciales

Crea un `.env` (ya está en `.gitignore`) junto a `main.py`:

```
GMAIL_USUARIO=tucorreo@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
CORREO_DESTINO=tucorreo@gmail.com
```

`GMAIL_APP_PASSWORD` es una **contraseña de aplicación** de Google, no la de tu cuenta:
Cuenta de Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones.
Sin verificación en dos pasos activada la opción no aparece.

> Guarda el `.env` **sin BOM** (Notepad → Codificación "UTF-8", no "UTF-8 con BOM"). Con
> BOM la primera línea se lee mal y verás "Faltan GMAIL_USUARIO" aunque esté puesta.

Si `--diario` sale con código **2** después de haber scrapeado (fallo de red al enviar),
las ofertas de esa corrida ya quedaron marcadas como vistas y **no se repetirán en el
correo siguiente**: están en el `data/diario_<timestamp>.csv` que generó esa corrida.
Si faltan las credenciales, en cambio, ni siquiera scrapea — así no se pierde nada.

### Agendarlo

```powershell
.\scrap_diario.cmd     # probarlo a mano primero
```

Una vez que llegue el correo, registrar la tarea diaria a las 08:00:

La tarea `ScraperEmpleos` corre **tres veces al día (08:00, 14:00 y 20:00)** y **sin abrir
ventana**. Se creó así:

```powershell
$dir = "C:\Users\MSI ERICK\Desktop\Proyectos varios\scrapper_pruebas\test_python\linkendin_jobs_scrapper"
$accion = New-ScheduledTaskAction -Execute "wscript.exe" `
          -Argument "`"$dir\scrap_diario_oculto.vbs`"" -WorkingDirectory $dir
$horas = @((New-ScheduledTaskTrigger -Daily -At 08:00),
           (New-ScheduledTaskTrigger -Daily -At 14:00),
           (New-ScheduledTaskTrigger -Daily -At 20:00))
Set-ScheduledTask -TaskName "ScraperEmpleos" -Action $accion -Trigger $horas
```

Para **cambiar las horas**, repite ese bloque con las que quieras. Para ver cómo está:

```powershell
Get-ScheduledTaskInfo -TaskName "ScraperEmpleos"      # ultima ejecucion y resultado
schtasks /run /tn "ScraperEmpleos"                    # probarla sin esperar
```

**Por qué un `.vbs` y no el `.cmd` directamente:** un `.cmd` abre siempre su ventana de
consola, aunque lo lance el Programador de tareas. `scrap_diario_oculto.vbs` lo arranca
oculto y **devuelve su código de salida**, para que "Último resultado" siga diciendo si
fue 0, 1 o 2. Sin eso, ocultar la ventana costaría perder el diagnóstico.

Ajustes que lleva la tarea:

| Ajuste | Valor | Por qué |
|---|---|---|
| `DisallowStartIfOnBatteries` | `False` | Por defecto Windows no ejecuta tareas con el portátil a batería |
| `StartWhenAvailable` | `True` | Si el PC estaba apagado a esa hora, corre en cuanto arranque |
| `ExecutionTimeLimit` | 1 hora | Si se cuelga, no queda un proceso zombi |
| `MultipleInstances` | `IgnoreNew` | Si una corrida se alarga, la siguiente no se solapa |

Corre aunque la terminal esté cerrada, siempre que el PC esté encendido.

> **Por qué no en la nube:** los runners de GitHub Actions usan IPs de datacenter que
> LinkedIn bloquea con 429, y `historico.csv` obligaría a commitear estado en cada
> corrida. Haría falta un proxy residencial de pago.

## `legacy/`

Versión anterior: reportes Excel y análisis (`generar_excel.py`, `analisis.py`,
`config.py`, `scraper.py`, `buscar_todo_ecuador.py`). Fuera del MVP, se conserva por si
se retoma.

`NOTA-ventana-tkinter.md` documenta la ventana gráfica que se retiró: cómo estaba hecha,
qué quedó verificado y el comando exacto para recuperar su código desde git.

`legacy/scraper_computrabajo.py` fue **promovido** a `computrabajo.py` en la raíz y
adaptado a la forma de salida de jobspy. La copia de `legacy/` queda como estaba y ya no
se usa.
