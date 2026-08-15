r"""Envio del reporte por Gmail SMTP."""
import os
import smtplib
from email.message import EmailMessage

VARIABLES = ('GMAIL_USUARIO', 'GMAIL_APP_PASSWORD')


def faltan_credenciales():
    """Nombres de las variables de entorno del correo que no estan puestas."""
    return [v for v in VARIABLES if not os.environ.get(v)]


def enviar(asunto, cuerpo_html, adjunto=None):
    """Manda el reporte por Gmail SMTP. Devuelve True si salio.

    Las credenciales van en variables de entorno, nunca en el codigo. GMAIL_APP_PASSWORD
    es una *contrasena de aplicacion* de Google: la normal de la cuenta no sirve para SMTP.
    """
    if faltan_credenciales():
        print('[ERROR] Faltan GMAIL_USUARIO o GMAIL_APP_PASSWORD: no se envio el correo')
        return False

    usuario = os.environ['GMAIL_USUARIO']
    clave = os.environ['GMAIL_APP_PASSWORD']
    destino = os.environ.get('CORREO_DESTINO') or usuario

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = usuario
    msg['To'] = destino
    msg.set_content('Este reporte se ve mejor en un cliente con HTML.')
    msg.add_alternative(cuerpo_html, subtype='html')

    if adjunto and os.path.exists(adjunto):
        with open(adjunto, 'rb') as f:
            msg.add_attachment(f.read(), maintype='text', subtype='csv',
                               filename=os.path.basename(adjunto))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=60) as smtp:
            smtp.login(usuario, clave)
            smtp.send_message(msg)
    except Exception as e:
        print(f'[ERROR] No se pudo enviar el correo: {e}')
        return False

    print(f'[OK] Correo enviado a {destino}')
    return True
