# Ventana tkinter — retirada el 15/08/2026

Se construyó una ventana para lanzar búsquedas sin escribir el comando. **No funcionó
como se esperaba y se retiró.** Esta nota es para poder retomarla sin empezar de cero.

## Recuperar el código

No hay que reescribirlo: está entero en git.

```powershell
git show f595a90:ventana.py > ventana.py
git show f595a90:scrap_ventana.cmd > scrap_ventana.cmd
```

Eran 188 y 8 líneas. Para verlo antes de restaurar: `git show f595a90:ventana.py`.

## Cómo estaba hecho

**Un lanzador, no un editor.** La ventana no tocaba ningún archivo del proyecto:
recogía los campos, montaba los argumentos y ejecutaba `main.py` como **subproceso**,
exactamente igual que la línea de comandos. Se descartó a propósito que editara las
constantes de `main.py` o `perfil.py`: un programa que reescribe su propio código puede
dejarlo roto.

**Piezas:**

| Parte | Cómo |
|---|---|
| Formulario | `ttk.Entry` / `Combobox` / `Spinbox` / `Checkbutton` para puesto, ubicación, resultados, horas, sitios y descripción |
| Ejecución | `subprocess.Popen` con `sys.executable main.py <args>`, `CREATE_NO_WINDOW` |
| Salida en vivo | Hilo aparte leyendo `stdout` línea a línea → `queue.Queue` → `root.after(100, ...)` la vuelca al `Text`. Tk no es thread-safe, por eso la cola |
| Codificación | `PYTHONIOENCODING=utf-8` y `PYTHONUNBUFFERED=1` en el entorno del hijo |
| Estado final | Traducía el código de salida a *Listo* / *Fallaron todos los sitios* / *No se pudo enviar el correo* |
| Arranque | `scrap_ventana.cmd`, igual que `scrap.cmd` pero llamando a `ventana.py` |

## Lo que ya quedó verificado

No hace falta volver a comprobarlo:

- **tkinter existe** en el Python 3.12 que provisiona `uv` (Tcl/Tk 8.6). No es obvio: los
  builds de python-build-standalone no siempre traen Tcl/Tk.
- **Los argumentos se construyen bien**, incluso con espacios y comillas en el puesto,
  porque van como **lista** a `Popen` y no como cadena al shell.
- **El streaming funciona**: la salida aparece línea a línea mientras busca, sin congelar
  la ventana, y el código de salida llega correcto (probado con `--sitios inexistente` → 1).
- **Las validaciones funcionan**: horas no numéricas y ningún sitio marcado.

## Lo que nunca se verificó

**Nadie vio la ventana abierta.** Se comprobó que se construye sin errores y que la
lógica funciona, pero no hay forma de capturar una ventana nativa de Windows desde la
sesión, así que **el aspecto visual quedó sin revisar**. Es el sospechoso número uno de
por qué no convenció.

## Si se retoma

1. Restaurar los dos archivos con los comandos de arriba (van en la **raíz**, no en
   `legacy/`: importan `buscador` y `main`, y `RAIZ` se calcula desde su propia carpeta).
2. Abrirla y mirar qué falla de verdad antes de tocar nada.
3. `UBICACIONES` se construía importando `CIUDADES` de `main.py`, así que el desplegable
   se mantiene solo al añadir ciudades.

Alternativa que se descartó entonces y quizá encaje mejor: en vez de una ventana propia,
sacar los parámetros a un `config.json` y editarlo a mano o con cualquier editor. Menos
código que mantener.
