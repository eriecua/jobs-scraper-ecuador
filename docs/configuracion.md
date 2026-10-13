# Configuración

Todo se ajusta editando listas al principio de cada archivo `.py`, con cualquier editor de
texto (Notepad, TextEdit, VS Code). No hay ventana de configuración a propósito: un
programa que reescribe su propio código puede dejarlo roto.

| Qué quieres cambiar | Dónde |
|---|---|
| Qué puestos te interesan y cuáles no | [`perfil.py`](#tu-perfil--perfilpy) |
| Ciudades del correo diario | [`CIUDADES` en `main.py`](#añadir-una-ciudad) |
| Que Computrabajo encuentre una ciudad | [`SLUGS_UBICACION` en `computrabajo.py`](#añadir-una-ciudad) |
| Cómo se agrupan ciudades y provincias | [`ubicaciones.py`](#ciudades-y-provincias--ubicacionespy) |
| En qué sitios se busca | [`buscador.py`](#sitios--buscadorpy) |
| Categorías de puesto del correo y del análisis | [`reporte.py`](#categorías-y-publicaciones-que-no-son-ofertas--reportepy) |
| Habilidades que se miden | `HABILIDADES` en `habilidades.py` ([ver análisis](analisis.md#qué-se-puede-medir-y-qué-no)) |
| Correo y horario | [`.env` y el agendado](correo.md) |

## Tu perfil — `perfil.py`

Decide el **puntaje de compatibilidad** de cada oferta: qué sube en la lista del correo y
qué desaparece. **Es lo primero que tienes que cambiar**: viene con un perfil de ejemplo
(Datos/BI y Procesos). Pon los términos de los puestos que tú buscas, y según vayas viendo
los correos irás afinando.

```python
INTERES   = {'analista': 20, 'datos': 35, ...}   # suben la oferta, NO la filtran
DESEABLES = {'python': 15, 'sql': 15, ...}       # herramientas, suman encima
EXCLUIDOS = ['ventas', 'sales', 'chofer', ...]   # vetan la oferta entera
FAMILIAS_EXCLUIDAS = []                          # categorías enteras: 'Ventas', ...
NIVELES_EXCLUIDOS = ['Practicas']                # niveles que no quieres en el correo
```

Dos mecanismos con papeles **distintos**, y no conviene confundirlos:

| | Listas | Qué hacen |
|---|---|---|
| **Ordenan** | `INTERES`, `DESEABLES` | Suben la oferta en la lista. Nunca la eliminan. |
| **Quitan** | `EXCLUIDOS`, `FAMILIAS_EXCLUIDAS`, `NIVELES_EXCLUIDOS` | Vetan la oferta entera. |

| Lista | Qué contiene |
|---|---|
| `INTERES` | De qué va el puesto que buscas (`datos` 35, `business intelligence` 35, `analista` 20…). **No es obligatorio**: una oferta sin ninguno sale igual, solo que más abajo. Con 30 o más, la oferta "te encaja". |
| `DESEABLES` | Herramientas que suman encima (`python` 15, `sql` 15, `power bi` 15…). |
| `EXCLUIDOS` | Temas que no quieres ver (`ventas`, `sales`, `comercial`, `chofer`…). Vetan la oferta. |
| `FAMILIAS_EXCLUIDAS` | Categorías enteras a descartar (`'Ventas'`, `'Seguridad'`…), usando las `FAMILIAS` de `reporte.py`. Vacía por defecto. |
| `NIVELES_EXCLUIDOS` | Niveles que no quieres en el correo (`'Practicas'`, `'Junior'`…), de `NIVELES`. |

### Comprobar el efecto de un cambio

Después de editar, mira cómo puntúan las ofertas que ya tienes:

```powershell
uv run --python 3.12 --with-requirements requirements.txt --no-project python -c "import pandas as pd, perfil; d=pd.read_csv('data/historico.csv',dtype=str); p=d['title'].fillna('').map(lambda t: perfil.puntuar(t)[0]); print('encajan:', (p>=30).sum(), 'de', len(d)); [print(f'{v:4} {t[:60]}') for t,v in sorted(zip(d['title'].fillna(''),p), key=lambda x:-x[1])[:15]]"
```

Te imprime cuántas encajan y las 15 mejores. Si aparecen puestos que no te interesan,
añade la palabra a `EXCLUIDOS`; si falta alguno que sí, añádela a `INTERES`.

### Por qué el interés no filtra

Antes `INTERES` se llamaba `NUCLEO` y era obligatorio. Medido sobre el histórico, eso
mandaba a 0 el **68%** de las ofertas y enterraba cosas que sí servían:

```
JEFE UNIDAD DE ESTADÍSTICA     ← estadística
Database Consultant            ← datos
Oficial de cumplimiento uafe
```

En una búsqueda dirigida (`.\scrap.cmd "Analista de Datos"`) el filtro **ya lo hizo el
propio sitio**, así que exigirlo otra vez no aporta. En el diario solo servía para perder
ofertas sin saber cuáles. Ahora el interés ordena y solo las listas de exclusión quitan.
El pie del correo dice siempre qué se ocultó y por qué palabra
([ver correo](correo.md#qué-trae-el-correo)).

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
- Los puntajes son relativos, no una nota sobre 100. Una oferta muy buena ronda 45-72.

## Añadir una ciudad

Para el correo diario son **dos pasos**, en dos archivos:

1. **`CIUDADES` en `main.py`**: añade `'Ambato, Ecuador'` a la lista.
2. **`SLUGS_UBICACION` en `computrabajo.py`**: Computrabajo no entiende `"Ambato, Ecuador"`;
   su ruta es `tungurahua-en-ambato`. Las ciudades grandes ya están en la tabla: mira
   primero si la tuya aparece, y si no, añádela.

   ```python
   SLUGS_UBICACION = {
       'quito': 'pichincha-en-quito',
       'guayaquil': 'guayas-en-guayaquil',
       'ambato': 'tungurahua-en-ambato',
       ...
   }
   ```

   El formato es `<provincia>-en-<ciudad>`, sin tildes y con guiones. Para comprobarlo,
   abre `https://ec.computrabajo.com/empleos-en-<slug>` en el navegador: si salen ofertas,
   sirve. **Compruébalo siempre**: un slug mal escrito devuelve cero ofertas **sin dar
   error**.

LinkedIn, Indeed y Multitrabajos no necesitan nada: entienden la ciudad tal cual
(Multitrabajos la traduce sola con `ubicaciones.py`).

Para las búsquedas sueltas (uso 1) basta `--ubicacion "Ambato, Ecuador"`; Computrabajo
avisará si le falta el slug.

## Ciudades y provincias — `ubicaciones.py`

Cada sitio escribe la misma ciudad de forma distinta. En un histórico real hay **19
textos** para 6 ciudades:

```
'Quito, Pichincha, Ecuador'   'Quito, Pichincha'   'Quito, P, EC'
'Quito Canton, Pichincha, Ecuador'   'Pichincha, Ecuador'
```

`normalizar()` los convierte a un par **(ciudad, provincia)**, y ese par es lo que se
guarda en las columnas `ciudad` y `provincia` del CSV y lo que agrupa el gráfico del
correo. Una sola tabla para los dos.

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

Para que una ciudad nueva se agrupe bien, basta su entrada en `CANTONES`. Esto es
independiente de `SLUGS_UBICACION`, que es lo que Computrabajo necesita para *buscar*.

## Sitios — `buscador.py`

```python
SITIOS_DEFECTO = ('linkedin', 'indeed', 'computrabajo', 'multitrabajos')
FUENTES_PROPIAS = {...}   # sitios que no cubre jobspy, con su módulo propio
```

Para buscar solo en algunos sin editar nada, usa `--sitios linkedin,computrabajo`. Un sitio
nuevo con módulo propio se registra en `FUENTES_PROPIAS`, con la firma
`scrape(termino, ubicacion, resultados, dias_max, pais)`.

## Categorías y publicaciones que no son ofertas — `reporte.py`

- **`FAMILIAS`** agrupa los títulos en Ventas, Datos/BI, Logística, etc. Es la columna
  `familia` del análisis y el gráfico "qué están buscando" del correo. Gana la primera que
  coincida, así que las específicas van **antes** que las genéricas. Cubre el **85%**; el
  resto cae en *Otros*.
- **`NO_OFERTAS`** son publicaciones que no describen un puesto (`"Trabaja con nosotros"`,
  `"Postula aquí"`). Son anuncios reales de LinkedIn, no un fallo del scraper. Se ocultan
  **solo del correo**: siguen en el CSV y en el histórico (columna `es_oferta_real = 0` en
  el análisis), y el correo dice al pie cuántas ocultó.
