' Lanza scrap_diario.cmd SIN abrir ventana de consola.
'
' Un .cmd siempre muestra su ventana, aunque la tarea programada lo lance sola. Este
' envoltorio lo arranca con la ventana oculta y devuelve su codigo de salida, para que
' el Programador de tareas siga mostrando en "Ultimo resultado" si fue 0, 1 o 2.
'
' No se usa directamente: lo llama la tarea "ScraperEmpleos" a traves de wscript.exe.

Dim shell, carpeta, codigo

Set shell = CreateObject("WScript.Shell")

' La carpeta de este mismo .vbs, para no depender de donde se lance.
carpeta = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' 0 = ventana oculta.  True = esperar a que termine, para poder devolver su codigo.
codigo = shell.Run("""" & carpeta & "scrap_diario.cmd""", 0, True)

WScript.Quit codigo
