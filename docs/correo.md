# Correo diario

El scraper recorre tus ciudades varias veces al día, compara con lo que ya viste y te
manda por Gmail **solo las ofertas nuevas**, ordenadas según lo bien que encajan con tu
perfil. Si no hay nada nuevo, no te escribe.

Antes de seguir, haz la [instalación](../README.es.md#instalación) y prueba una búsqueda
normal (uso 1): así sabes que el scraper funciona antes de sumarle el correo.

- [1. Tus datos de Gmail](#1-tus-datos-de-gmail)
- [2. Qué buscas y dónde](#2-qué-buscas-y-dónde)
- [3. Probarlo](#3-probarlo)
- [4. Agendarlo en Windows](#4-agendarlo-en-windows)
- [5. Agendarlo en Mac y Linux](#5-agendarlo-en-mac-y-linux)
- [Qué trae el correo](#qué-trae-el-correo)
- [Si el correo falla](#si-el-correo-falla)
- [Códigos de salida](#códigos-de-salida)

## 1. Tus datos de Gmail

1. **Activa la verificación en dos pasos** en tu cuenta de Google (sin ella no existe el
   paso siguiente).
2. **Crea una contraseña de aplicación:** Cuenta de Google → Seguridad → Verificación en
   dos pasos → *Contraseñas de aplicaciones*. Google te da 16 letras. No es la contraseña
   de tu cuenta, y puedes borrarla cuando quieras.
3. **Copia `.env.example` como `.env`** (en la misma carpeta del proyecto) y rellénalo:

   ```
   GMAIL_USUARIO=tucorreo@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   CORREO_DESTINO=tucorreo@gmail.com
   ```

   `CORREO_DESTINO` es a quién le llega el reporte; si lo dejas vacío, te llega a ti.

> Guarda el `.env` **sin BOM** (en Notepad: Codificación "UTF-8", no "UTF-8 con BOM").
> Con BOM la primera línea se lee mal y verás "Faltan GMAIL_USUARIO" aunque esté puesta.
> El lanzador de Mac/Linux lo tolera; el de Windows no.

El `.env` está en `.gitignore`: tus credenciales no se suben nunca a git.

## 2. Qué buscas y dónde

El proyecto viene con un **perfil de ejemplo** (puestos de Datos/BI y Procesos en Quito,
Santo Domingo, Guayaquil y Cuenca). Cámbialo por el tuyo o el correo te ordenará las
ofertas según los gustos de otra persona.

- **Ciudades:** `CIUDADES` al principio de `main.py`. El diario trae **todos** los puestos
  de esas ciudades, sin filtrar por título; luego los ordena con tu perfil.

  ```python
  CIUDADES = [
      'Quito, Ecuador',
      'Santo Domingo de los Tsachilas, Ecuador',
      'Guayaquil, Ecuador',
      'Cuenca, Ecuador',
  ]
  HORAS_DIARIO = 24        # ventana de tiempo del diario
  RESULTADOS_DIARIO = 100  # por sitio Y por ciudad: 4 ciudades x 4 sitios x 100 = 1.600 máx.
  DISTANCIA_DIARIO = 25    # radio en km de LinkedIn e Indeed
  ENVIAR_SI_VACIO = False  # True = te escribe aunque no haya nada nuevo
  ```

  Una ciudad nueva también necesita su ruta de Computrabajo: ver
  [añadir una ciudad](configuracion.md#añadir-una-ciudad).

- **Tu perfil:** `INTERES`, `DESEABLES` y `EXCLUIDOS` en `perfil.py` deciden qué ofertas
  suben en la lista y cuáles desaparecen. Está explicado en
  [configuracion.md](configuracion.md#tu-perfil--perfilpy).

## 3. Probarlo

Windows:
```powershell
.\scrap_diario.cmd
```
Mac y Linux:
```bash
./scrap_diario.sh
```

La primera vez tarda unos minutos y te llega un correo con **todo** como nuevo, porque el
histórico está vacío. A partir de la segunda, solo lo que salió desde la anterior.

## 4. Agendarlo en Windows

Crea la tarea `ScraperEmpleos`, que corre **tres veces al día (08:00, 14:00 y 20:00)** y
**sin abrir ventana**. Ejecuta esto en PowerShell **desde la carpeta del proyecto**:

```powershell
$dir = (Get-Location).Path
$accion = New-ScheduledTaskAction -Execute "wscript.exe" `
          -Argument "`"$dir\scrap_diario_oculto.vbs`"" -WorkingDirectory $dir
$horas = @((New-ScheduledTaskTrigger -Daily -At 08:00),
           (New-ScheduledTaskTrigger -Daily -At 14:00),
           (New-ScheduledTaskTrigger -Daily -At 20:00))
$ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
           -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "ScraperEmpleos" -Action $accion -Trigger $horas -Settings $ajustes
```

Para **cambiar las horas** de una tarea ya creada, arma `$horas` con las que quieras y usa
`Set-ScheduledTask -TaskName "ScraperEmpleos" -Trigger $horas`. Para ver cómo está:

```powershell
Get-ScheduledTaskInfo -TaskName "ScraperEmpleos"      # ultima ejecucion y resultado
schtasks /run /tn "ScraperEmpleos"                    # probarla sin esperar
```

Corre aunque la terminal esté cerrada, siempre que el PC esté encendido.

**Si no llega correo**, puede ser que no hubiera nada nuevo (normal) o que fallara. Para
distinguirlo, abre el Programador de tareas y mira el *Último resultado* (ver
[códigos de salida](#códigos-de-salida)), o córrelo a mano con `.\scrap_diario.cmd`.

**Por qué un `.vbs` y no el `.cmd` directamente:** un `.cmd` abre siempre su ventana de
consola, aunque lo lance el Programador de tareas. `scrap_diario_oculto.vbs` lo arranca
oculto y **devuelve su código de salida**, para que "Último resultado" siga diciendo si
fue 0, 1, 2 o 3. Sin eso, ocultar la ventana costaría perder el diagnóstico.

Ajustes que lleva la tarea (los pone `$ajustes`):

| Ajuste | Valor | Por qué |
|---|---|---|
| `DisallowStartIfOnBatteries` | `False` | Por defecto Windows no ejecuta tareas con el portátil a batería |
| `StartWhenAvailable` | `True` | Si el PC estaba apagado a esa hora, corre en cuanto arranque |
| `ExecutionTimeLimit` | 1 hora | Si se cuelga, no queda un proceso zombi |
| `MultipleInstances` | `IgnoreNew` | Si una corrida se alarga, la siguiente no se solapa |

## 5. Agendarlo en Mac y Linux

Con `cron`. Abre la tabla con `crontab -e` y añade una línea (aquí el proyecto está en
`~/jobs-scraper`; cambia la ruta por la tuya):

```bash
0 8,14,20 * * * PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" "$HOME/jobs-scraper/scrap_diario.sh" >> "$HOME/jobs-scraper/data/cron.log" 2>&1
```

Corre a las 08:00, 14:00 y 20:00 y deja lo que imprime en `data/cron.log`. Antes de
agendarlo, córrelo a mano una vez (paso 3), para que exista `data/`.

Diferencias con Windows que conviene saber:

- **`PATH` en la línea, no es opcional.** `cron` arranca con un `PATH` mínimo que no incluye
  la carpeta de `uv` (`~/.local/bin` o la de Homebrew). Sin él, la tarea falla con
  `uv: not found` y solo lo verías en el log.
- **En Mac, no lo pongas en Escritorio, Documentos ni Descargas.** macOS no deja a `cron`
  leer esas carpetas y la tarea falla con `Operation not permitted`. Usa una carpeta
  propia, como `~/jobs-scraper`, o dale a `cron` *Acceso total al disco* en Ajustes →
  Privacidad y seguridad.
- **Si el equipo está dormido a esa hora, la corrida se salta.** En Windows la tarea corre
  al despertar (`StartWhenAvailable`); `cron` no. No se pierden ofertas: la siguiente
  corrida trae las de las últimas 24 horas. Si la ventana entre corridas pasa de 24 horas,
  sube `HORAS_DIARIO` en `main.py`.
- **No guardes `data/historico.csv` desde Excel ni Numbers.** En Windows, Excel bloquea el
  archivo y el scraper sale con código `3` sin tocar nada. En Mac no hay bloqueo: si lo
  abres, corre el diario y después guardas, pisas lo que el diario acaba de escribir.
  Nada se pierde, pero esas ofertas volverán a llegar como nuevas. Para mirarlo, ábrelo y
  ciérralo sin guardar, o usa los `data/nuevos_*.csv`.

> **Por qué no en la nube:** los servidores de GitHub Actions y similares usan IPs de
> datacenter que LinkedIn bloquea, y `historico.csv` obligaría a guardar estado en cada
> corrida. Haría falta un proxy residencial de pago. Por eso corre en tu equipo.

## Qué trae el correo

Lo construye `reporte.py`. De arriba abajo: cuatro números grandes (ofertas, cuántas te
encajan, ciudades, empresas), un gráfico de **ofertas por ciudad**, otro de **qué están
buscando** (familias de puesto), uno pequeño por sitio, y debajo la lista de ofertas
agrupada por ciudad, **ordenada por compatibilidad**, con su link. El adjunto es el CSV
con todo.

En el CSV del diario hay además `ciudad_busqueda`, y **no es lo mismo que `ciudad`**: la
primera dice qué se buscó, la segunda qué dice la oferta. Una búsqueda en Quito devuelve
legítimamente ofertas de Samborondón.

Al pie, el correo dice qué ocultó y por qué:

```
Se ocultaron 104 publicaciones:
   97 por tus exclusiones — comercial 37 · ventas 25 · sales 11 · vendedor 7 · ...
    7 que no describen un puesto ("Trabaja con nosotros")
```

Así ves qué palabra de `EXCLUIDOS` está recortando y cuánto. Todas siguen en el CSV
adjunto. Los gráficos cuentan lo que se muestra, no el total bruto, para que los números
de arriba cuadren con la lista de abajo.

Los gráficos son barras hechas con tablas y colores de fondo, no imágenes. Un correo no
ejecuta JavaScript ni dibuja SVG, y un PNG tendría tamaño fijo: se leería mal en el
celular y arrastraría su fondo blanco al modo oscuro. Las barras en HTML se reajustan al
ancho y admiten links al lado. Por eso en `reporte.py` no hay flexbox, grid, `<style>`,
SVG ni imágenes: nada de eso sobrevive en Gmail y Outlook.

Lo que se ajusta del correo (familias de puesto, publicaciones que no son ofertas) está en
[configuracion.md](configuracion.md#categorías-y-publicaciones-que-no-son-ofertas--reportepy).

## Si el correo falla

Si Gmail falla después de haber buscado (sin red, credenciales caducadas), las ofertas de
esa corrida quedan en `data/correo_pendiente.csv` y **salen en el correo siguiente**,
junto con las nuevas. Ese archivo se borra solo tras un envío correcto: no lo borres a
mano. En el peor caso recibes un correo duplicado, nunca pierdes una oferta.

Si faltan las credenciales, en cambio, ni siquiera busca: así no se marca nada como visto.

## Códigos de salida

Importan si lo agendas: dicen si falló de verdad o si simplemente no había ofertas.

| Código | Significado | Qué hacer |
|---|---|---|
| `0` | Corrida OK (con o sin ofertas nuevas) | Nada |
| `1` | Todos los sitios fallaron | Revisa tu conexión |
| `2` | Buscó bien pero no pudo enviar el correo | Nada: se reintenta en la siguiente corrida |
| `3` | No pudo escribir `data/historico.csv` | Ciérralo si lo tienes abierto en Excel |
