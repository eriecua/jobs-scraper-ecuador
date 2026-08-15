r"""Ventana para lanzar busquedas sin escribir el comando a mano.

No toca ningun archivo del proyecto: arma los argumentos y ejecuta main.py igual que
haria la linea de comandos. Si la busqueda revienta, revienta el proceso hijo y la
ventana sigue viva mostrando el error.

Se abre con:  .\scrap_ventana.cmd
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from buscador import SITIOS_DEFECTO

try:
    from main import CIUDADES
except Exception:  # si main cambia, la ventana no debe caerse por eso
    CIUDADES = ['Ecuador']

RAIZ = os.path.dirname(os.path.abspath(__file__))
UBICACIONES = ['Ecuador'] + CIUDADES + ['Cuenca, Ecuador', 'Ambato, Ecuador']


class Ventana:
    def __init__(self, root):
        self.root = root
        self.proceso = None
        self.cola = queue.Queue()

        root.title('Buscar empleos')
        root.minsize(680, 520)

        marco = ttk.Frame(root, padding=12)
        marco.pack(fill='both', expand=True)
        marco.columnconfigure(1, weight=1)

        fila = 0
        ttk.Label(marco, text='Puesto').grid(row=fila, column=0, sticky='w', pady=4)
        self.puesto = ttk.Entry(marco)
        self.puesto.grid(row=fila, column=1, columnspan=3, sticky='ew', pady=4)
        ttk.Label(marco, text='vacio = todos los puestos', foreground='#666').grid(
            row=fila, column=4, sticky='w', padx=(8, 0))

        fila += 1
        ttk.Label(marco, text='Ubicacion').grid(row=fila, column=0, sticky='w', pady=4)
        self.ubicacion = ttk.Combobox(marco, values=UBICACIONES)
        self.ubicacion.set('Ecuador')
        self.ubicacion.grid(row=fila, column=1, columnspan=3, sticky='ew', pady=4)
        ttk.Label(marco, text='puedes escribir otra', foreground='#666').grid(
            row=fila, column=4, sticky='w', padx=(8, 0))

        fila += 1
        ttk.Label(marco, text='Resultados').grid(row=fila, column=0, sticky='w', pady=4)
        self.resultados = ttk.Spinbox(marco, from_=10, to=500, increment=10, width=8)
        self.resultados.set(100)
        self.resultados.grid(row=fila, column=1, sticky='w', pady=4)
        ttk.Label(marco, text='por sitio', foreground='#666').grid(
            row=fila, column=2, sticky='w')

        fila += 1
        ttk.Label(marco, text='Ultimas horas').grid(row=fila, column=0, sticky='w', pady=4)
        self.horas = ttk.Entry(marco, width=8)
        self.horas.grid(row=fila, column=1, sticky='w', pady=4)
        ttk.Label(marco, text='vacio = sin limite de fecha', foreground='#666').grid(
            row=fila, column=2, columnspan=3, sticky='w')

        fila += 1
        ttk.Label(marco, text='Sitios').grid(row=fila, column=0, sticky='w', pady=4)
        caja = ttk.Frame(marco)
        caja.grid(row=fila, column=1, columnspan=4, sticky='w', pady=4)
        self.sitios = {}
        for sitio in SITIOS_DEFECTO:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(caja, text=sitio, variable=var).pack(side='left', padx=(0, 12))
            self.sitios[sitio] = var

        fila += 1
        self.descripcion = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco, text='Traer la descripcion completa (mucho mas lento)',
                        variable=self.descripcion).grid(
            row=fila, column=1, columnspan=4, sticky='w', pady=(0, 8))

        fila += 1
        botones = ttk.Frame(marco)
        botones.grid(row=fila, column=0, columnspan=5, sticky='w', pady=(4, 10))
        self.boton_buscar = ttk.Button(botones, text='Buscar', command=self.buscar)
        self.boton_buscar.pack(side='left')
        self.boton_parar = ttk.Button(botones, text='Detener', command=self.detener,
                                      state='disabled')
        self.boton_parar.pack(side='left', padx=6)
        ttk.Button(botones, text='Abrir carpeta data',
                   command=self.abrir_data).pack(side='left', padx=6)

        fila += 1
        marco.rowconfigure(fila, weight=1)
        self.log = tk.Text(marco, height=16, wrap='word', bg='#1e1e1e', fg='#d4d4d4',
                           insertbackground='#d4d4d4', font=('Consolas', 9))
        self.log.grid(row=fila, column=0, columnspan=5, sticky='nsew')
        barra = ttk.Scrollbar(marco, command=self.log.yview)
        barra.grid(row=fila, column=5, sticky='ns')
        self.log['yscrollcommand'] = barra.set

        fila += 1
        self.estado = ttk.Label(marco, text='Listo', foreground='#666')
        self.estado.grid(row=fila, column=0, columnspan=5, sticky='w', pady=(6, 0))

        root.protocol('WM_DELETE_WINDOW', self.cerrar)
        self.root.after(100, self._vaciar_cola)

    # ------------------------------------------------------------------ acciones

    def _argumentos(self):
        """Traduce lo de la ventana a los mismos argumentos que acepta main.py."""
        args = [sys.executable, os.path.join(RAIZ, 'main.py')]

        puesto = self.puesto.get().strip()
        if puesto:
            args.append(puesto)

        args += ['--ubicacion', self.ubicacion.get().strip() or 'Ecuador']
        args += ['--resultados', str(self.resultados.get()).strip() or '100']

        horas = self.horas.get().strip()
        if horas:
            args += ['--horas', horas]

        elegidos = [s for s, v in self.sitios.items() if v.get()]
        args += ['--sitios', ','.join(elegidos)]

        if self.descripcion.get():
            args.append('--descripcion')

        return args, elegidos

    def buscar(self):
        args, elegidos = self._argumentos()

        if not elegidos:
            self.escribir('[ERROR] Elige al menos un sitio\n')
            return

        horas = self.horas.get().strip()
        if horas and not horas.isdigit():
            self.escribir(f'[ERROR] "Ultimas horas" debe ser un numero entero, no "{horas}"\n')
            return

        self.log.delete('1.0', 'end')
        self.escribir(f'> {" ".join(args[1:])}\n\n')
        self.boton_buscar['state'] = 'disabled'
        self.boton_parar['state'] = 'normal'
        self.estado['text'] = 'Buscando...'

        threading.Thread(target=self._correr, args=(args,), daemon=True).start()

    def _correr(self, args):
        """Lanza main.py y va mandando su salida a la cola, linea a linea."""
        entorno = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
        try:
            self.proceso = subprocess.Popen(
                args, cwd=RAIZ, env=entorno,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            for linea in self.proceso.stdout:
                self.cola.put(('log', linea))
            codigo = self.proceso.wait()
        except Exception as e:
            self.cola.put(('log', f'\n[ERROR] No se pudo ejecutar: {e}\n'))
            codigo = -1

        self.proceso = None
        self.cola.put(('fin', codigo))

    def detener(self):
        if self.proceso:
            self.proceso.terminate()
            self.escribir('\n[AVISO] Detenido por el usuario\n')

    def abrir_data(self):
        carpeta = os.path.join(RAIZ, 'data')
        os.makedirs(carpeta, exist_ok=True)
        os.startfile(carpeta)

    # ------------------------------------------------------------------ interfaz

    def escribir(self, texto):
        self.log.insert('end', texto)
        self.log.see('end')

    def _vaciar_cola(self):
        """Tk no es thread-safe: el hilo deja mensajes en la cola y aqui se pintan."""
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == 'log':
                    self.escribir(dato)
                else:
                    self._terminado(dato)
        except queue.Empty:
            pass
        self.root.after(100, self._vaciar_cola)

    def _terminado(self, codigo):
        self.boton_buscar['state'] = 'normal'
        self.boton_parar['state'] = 'disabled'
        mensajes = {
            0: ('Listo', '#0a7'),
            1: ('Fallaron todos los sitios', '#c00'),
            2: ('No se pudo enviar el correo', '#c60'),
        }
        texto, color = mensajes.get(codigo, (f'Termino con codigo {codigo}', '#c00'))
        self.estado['text'] = texto
        self.estado['foreground'] = color

    def cerrar(self):
        if self.proceso:
            self.proceso.terminate()
        self.root.destroy()


def main():
    root = tk.Tk()
    Ventana(root)
    root.mainloop()


if __name__ == '__main__':
    main()
