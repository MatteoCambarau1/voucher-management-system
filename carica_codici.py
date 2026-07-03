"""
carica_codici.py — Carica codici voucher da un file CSV nel database VoucherManagementSystem.

Utilizzo:
    python3 carica_codici.py <file.csv>

Formato CSV atteso (con intestazione):
    CodiceID,Tipo,Importo,Edizione
    AB12-CD34-EF56,Voucher1,25.00,2025
    GH78-IJ90-KL12,Voucher2,50.00,2025

Colonne:
    CodiceID  — codice voucher (stringa, max 64 caratteri)
    Tipo      — qualsiasi stringa non vuota (es. Voucher1, Voucher2, Voucher3...)
    Importo   — valore in euro (es. 25.00)
    Edizione  — identificativo edizione (es. 2024, 2025)

Note:
    - I duplicati vengono ignorati (INSERT IGNORE).
    - StatoCodice viene impostato automaticamente a 'Disponibile'.
    - Le righe non valide vengono saltate e riportate a fine esecuzione.
    - Il campo Tipo viene convertito in maiuscolo automaticamente.
"""

import csv
import sys
import os
from decimal import Decimal, InvalidOperation
import mysql.connector

# --- Configurazione database ---
DB_CONFIG = {
    'host': os.environ.get('MYSQLHOST', 'localhost'),
    'user': os.environ.get('MYSQLUSER', 'root'),
    'password': os.environ.get('MYSQLPASSWORD', ''),
    'database': os.environ.get('MYSQLDATABASE', 'VoucherManagementSystem'),
    'port': int(os.environ.get('MYSQLPORT', 3306))
}

def valida_riga(riga, numero):
    """Valida una riga del CSV. Restituisce (dati, errore)."""
    codice   = riga.get('CodiceID', '').strip()
    tipo     = riga.get('Tipo', '').strip().upper()
    importo  = riga.get('Importo', '').strip()
    edizione = riga.get('Edizione', '').strip()

    if not codice:
        return None, f"riga {numero}: CodiceID mancante"
    if len(codice) > 64:
        return None, f"riga {numero}: CodiceID troppo lungo ({len(codice)} caratteri)"
    if not tipo:
        return None, f"riga {numero}: Tipo mancante"
    if not edizione:
        return None, f"riga {numero}: Edizione mancante"
    try:
        importo_dec = Decimal(importo)
        if importo_dec <= 0:
            return None, f"riga {numero}: Importo deve essere > 0"
    except InvalidOperation:
        return None, f"riga {numero}: Importo '{importo}' non è un numero valido"

    return {'CodiceID': codice, 'Tipo': tipo, 'Importo': importo_dec, 'Edizione': edizione}, None


def carica(percorso_csv):
    # Leggi il CSV
    righe_valide = []
    errori = []

    with open(percorso_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, riga in enumerate(reader, start=2):   # start=2 perché la riga 1 è l'intestazione
            dati, errore = valida_riga(riga, i)
            if errore:
                errori.append(errore)
            else:
                righe_valide.append(dati)

    if not righe_valide:
        print("Nessuna riga valida trovata. Operazione annullata.")
        _stampa_errori(errori)
        return

    # Inserisci nel database
    inseriti = 0
    duplicati = 0

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        sql = """
            INSERT IGNORE INTO Codici (CodiceID, Tipo, Importo, Edizione, StatoCodice)
            VALUES (%s, %s, %s, %s, 'Disponibile')
        """
        for d in righe_valide:
            cursor.execute(sql, (d['CodiceID'], d['Tipo'], d['Importo'], d['Edizione']))
            if cursor.rowcount == 1:
                inseriti += 1
            else:
                duplicati += 1

        conn.commit()
    finally:
        cursor.close()
        conn.close()

    # Riepilogo
    print(f"\n=== Riepilogo caricamento ===")
    print(f"  Inseriti:   {inseriti}")
    print(f"  Duplicati ignorati: {duplicati}")
    print(f"  Righe non valide:   {len(errori)}")
    _stampa_errori(errori)


def _stampa_errori(errori):
    if errori:
        print("\nProblemi riscontrati:")
        for e in errori:
            print(f"  - {e}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Utilizzo: python3 carica_codici.py <file.csv>")
        sys.exit(1)

    carica(sys.argv[1])
