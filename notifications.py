"""
notifications.py — Monitoraggio livelli codici e notifiche email.

Configurare EMAIL_CONFIG con i propri dati SMTP prima di andare in produzione.
Supporta qualsiasi provider SMTP (Gmail, Outlook, server aziendale, ecc.).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector
import os

# --- Soglia di attenzione (numero codici disponibili) ---
SOGLIA = 20

# --- Configurazione email ---
# Compilare prima di andare in produzione.
# Gmail: usare una "App Password" (non la password normale dell'account)
# Outlook/Office365: smtp_host = 'smtp.office365.com', smtp_port = 587
EMAIL_CONFIG = {
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'username': '',           # indirizzo email mittente
    'password': '',           # password app SMTP
    'mittente': '',           # visualizzato nel campo "Da:" (se vuoto usa username)
    'destinatario': '',       # indirizzo del manutentore
}

# --- Configurazione database (deve corrispondere a quella in app.py) ---
DB_CONFIG = {
    'host': os.environ.get('MYSQLHOST', 'localhost'),
    'user': os.environ.get('MYSQLUSER', 'root'),
    'password': os.environ.get('MYSQLPASSWORD', '12345678'),
    'database': os.environ.get('MYSQLDATABASE', 'CDD_YM'),
    'port': int(os.environ.get('MYSQLPORT', 3306))
}


def get_conteggio_codici():
    """
    Restituisce i conteggi dei codici disponibili per ogni combinazione Tipo + Edizione + Importo (taglio).
    Output: lista di dict { tipo, edizione, importo, disponibili }
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Tipo, Edizione, Importo, COUNT(*) AS Disponibili
        FROM Codici
        WHERE StatoCodice = 'Disponibile'
        GROUP BY Tipo, Edizione, Importo
        ORDER BY Tipo, Edizione, Importo DESC
    """)
    righe = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{'tipo': r[0], 'edizione': r[1], 'importo': float(r[2]), 'disponibili': r[3]} for r in righe]


def controlla_e_notifica():
    """
    Controlla i livelli dei codici e invia una email se uno o più tipi
    sono sotto soglia. Ritorna (conteggi, sotto_soglia).
    """
    conteggi = get_conteggio_codici()
    sotto_soglia = [c for c in conteggi if c['disponibili'] < SOGLIA]
    if sotto_soglia:
        _invia_email(sotto_soglia)
    return conteggi, sotto_soglia


def _invia_email(sotto_soglia):
    """Invia l'email di notifica al manutentore."""
    cfg = EMAIL_CONFIG
    if not cfg['username'] or not cfg['destinatario']:
        print('[NOTIFICA] Email non configurata — notifica saltata.')
        print('[NOTIFICA] Compilare EMAIL_CONFIG in notifications.py')
        return

    righe = '\n'.join(
        f"  • {c['tipo']} {c['edizione']} — €{c['importo']:.2f}: {c['disponibili']} codici disponibili (soglia: {SOGLIA})"
        for c in sotto_soglia
    )

    corpo = f"""Il sistema CodeMS ha rilevato che i seguenti codici sono sotto soglia:

{righe}

Accedere al pannello admin per caricare nuovi codici:
http://localhost:8080/admin

---
Notifica automatica CodeMS
"""

    msg = MIMEMultipart()
    msg['From'] = cfg['mittente'] or cfg['username']
    msg['To'] = cfg['destinatario']
    msg['Subject'] = f"⚠️ CodeMS — Codici in esaurimento ({len(sotto_soglia)} tipo/edizione sotto soglia)"
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg['username'], cfg['password'])
            server.send_message(msg)
        print(f"[NOTIFICA] Email inviata a {cfg['destinatario']}")
    except Exception as e:
        print(f'[NOTIFICA] Errore invio email: {e}')
