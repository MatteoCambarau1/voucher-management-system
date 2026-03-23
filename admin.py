from flask import Blueprint, render_template, request, jsonify
import mysql.connector
from decimal import Decimal, InvalidOperation
import csv
import io
from notifications import get_conteggio_codici, controlla_e_notifica, SOGLIA

admin_bp = Blueprint('admin', __name__)

# Configurazione database (deve corrispondere a quella in app.py)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345678',
    'database': 'CDD_YM'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


@admin_bp.route('/admin')
def admin():
    return render_template('admin.html')


@admin_bp.route('/carica', methods=['POST'])
def carica_codici():
    """
    Input: multipart/form-data con chiave 'file' (CSV)
    Colonne attese: CodiceID, Tipo, Importo, Edizione
    Output: { "inseriti": int, "duplicati": int, "errori": [str, ...] }
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nessun file fornito'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'File non selezionato'}), 400
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Solo file CSV (.csv) sono accettati'}), 400

        contenuto = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(contenuto))

        righe_valide = []
        errori = []

        for i, riga in enumerate(reader, start=2):
            codice   = riga.get('CodiceID', '').strip()
            tipo     = riga.get('Tipo', '').strip().upper()
            importo  = riga.get('Importo', '').strip()
            edizione = riga.get('Edizione', '').strip()

            if not codice:
                errori.append(f'Riga {i}: CodiceID mancante')
                continue
            if len(codice) > 64:
                errori.append(f'Riga {i}: CodiceID troppo lungo ({len(codice)} caratteri)')
                continue
            if tipo not in ('CDD', 'YM'):
                errori.append(f'Riga {i}: Tipo "{tipo}" non valido (usa CDD o YM)')
                continue
            if edizione not in ('2024', '2025'):
                errori.append(f'Riga {i}: Edizione "{edizione}" non valida')
                continue
            try:
                importo_dec = Decimal(importo)
                if importo_dec <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                errori.append(f'Riga {i}: Importo "{importo}" non valido')
                continue

            righe_valide.append((codice, tipo, importo_dec, edizione))

        if not righe_valide:
            return jsonify({'inseriti': 0, 'duplicati': 0, 'errori': errori})

        inseriti = 0
        duplicati = 0

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            sql = "INSERT IGNORE INTO Codici (CodiceID, Tipo, Importo, Edizione, StatoCodice) VALUES (%s, %s, %s, %s, 'Disponibile')"
            for riga in righe_valide:
                cursor.execute(sql, riga)
                if cursor.rowcount == 1:
                    inseriti += 1
                else:
                    duplicati += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f'Errore DB upload: {e}')
            return jsonify({'error': 'Errore durante il salvataggio nel database'}), 500

        cursor.close()
        conn.close()

        return jsonify({'inseriti': inseriti, 'duplicati': duplicati, 'errori': errori})

    except Exception as e:
        print(f'Errore upload: {e}')
        return jsonify({'error': 'Errore interno del server'}), 500


@admin_bp.route('/admin/stato-codici')
def stato_codici():
    """
    Restituisce i conteggi dei codici disponibili per Tipo e Edizione.
    Output: { "codici": [{ tipo, edizione, disponibili }], "soglia": int }
    """
    try:
        conteggi = get_conteggio_codici()
        return jsonify({'codici': conteggi, 'soglia': SOGLIA})
    except Exception as e:
        print(f'Errore monitoraggio: {e}')
        return jsonify({'error': 'Errore nel recupero dei dati'}), 500


@admin_bp.route('/admin/invia-notifica', methods=['POST'])
def invia_notifica():
    """
    Controlla i livelli e invia l'email di notifica se qualcuno è sotto soglia.
    Output: { "sotto_soglia": [...], "email_inviata": bool }
    """
    try:
        conteggi, sotto_soglia = controlla_e_notifica()
        return jsonify({
            'sotto_soglia': sotto_soglia,
            'email_inviata': len(sotto_soglia) > 0
        })
    except Exception as e:
        print(f'Errore invio notifica: {e}')
        return jsonify({'error': 'Errore interno del server'}), 500
