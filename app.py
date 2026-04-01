from flask import Flask, render_template, request, jsonify
import mysql.connector
from decimal import Decimal, ROUND_UP
from admin import admin_bp
from notifications import controlla_e_notifica
import os

app = Flask(__name__)
app.register_blueprint(admin_bp)

# Configurazione database
DB_CONFIG = {
    'host': os.environ.get('MYSQLHOST', 'localhost'),
    'user': os.environ.get('MYSQLUSER', 'root'),
    'password': os.environ.get('MYSQLPASSWORD', '12345678'),
    'database': os.environ.get('MYSQLDATABASE', 'CDD_YM'),
    'port': int(os.environ.get('MYSQLPORT', 3306))
}

MOTIVAZIONI_VALIDE = ('DNR', 'Correlato al Reso', 'Articolo Errato', 'Articolo Mancante', 'Altro')

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def ensure_configurazione():
    """Crea la tabella Configurazione e il record distribuzione_attiva se non esistono."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Configurazione (
            chiave VARCHAR(64) PRIMARY KEY,
            valore VARCHAR(64) NOT NULL
        )
    """)
    cursor.execute(
        "INSERT IGNORE INTO Configurazione (chiave, valore) VALUES ('distribuzione_attiva', '1')"
    )
    conn.commit()
    cursor.close()
    conn.close()

def is_distribuzione_attiva():
    """Restituisce True se la distribuzione codici è attiva."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valore FROM Configurazione WHERE chiave = 'distribuzione_attiva'")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row is not None and row[0] == '1'

def is_campagna_attiva(tipo, edizione):
    """Restituisce True se la campagna tipo+edizione non è disabilitata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT valore FROM Configurazione WHERE chiave = %s",
        (f'disabilitato_{tipo}_{edizione}',)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row is None or row[0] != '1'

def check_codici_disponibili(tipo, edizione):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Recupera i tagli disabilitati per questa campagna
    prefix = f'disabilitato_{tipo}_{edizione}_'
    cursor.execute(
        "SELECT chiave FROM Configurazione WHERE chiave LIKE %s AND valore = '1'",
        (prefix + '%',)
    )
    tagli_disabilitati = set()
    for (chiave,) in cursor.fetchall():
        tagli_disabilitati.add(chiave[len(prefix):])

    query = """
        SELECT CodiceID, Tipo, Importo, Edizione
        FROM Codici
        WHERE Tipo = %s
          AND Edizione = %s
          AND StatoCodice = 'Disponibile'
        ORDER BY Importo DESC, CodiceID ASC
    """
    cursor.execute(query, (tipo, edizione))
    righe = cursor.fetchall()
    cursor.close()
    conn.close()

    if tagli_disabilitati:
        righe = [r for r in righe if f'{float(r[2]):.2f}' not in tagli_disabilitati]

    return righe

def calcola_codici_necessari(tipo, edizione, importo_richiesto):
    # Regola di arrotondamento:
    # - cent == 0        → invariato    (es. 23.00 → 23.00)
    # - 0 < cent < 0.50 → arrotonda a .50 (es. 23.45 → 23.50)
    # - cent >= 0.50     → intero superiore (es. 23.50 → 24, 23.80 → 24)
    d = Decimal(str(importo_richiesto))
    interi = int(d)
    centesimi = d - Decimal(str(interi))
    if centesimi == 0:
        importo_target = d
    elif centesimi < Decimal('0.50'):
        importo_target = Decimal(str(interi)) + Decimal('0.50')
    else:
        importo_target = Decimal(str(interi + 1))

    righe = check_codici_disponibili(tipo, edizione)
    codici = []
    somma = Decimal('0')
    residuo = importo_target
    rimanenti = []

    for el in righe:
        importo_codice = Decimal(str(el[2]))

        if importo_codice <= residuo:
            codici.append(el)
            somma += importo_codice
            residuo = importo_target - somma

            if somma >= importo_target:
                break
        else:
            rimanenti.append(el)

    if somma < importo_target and rimanenti:
        residuo = importo_target - somma
        candidati = [c for c in rimanenti if Decimal(str(c[2])) >= residuo]
        if candidati:
            codici.append(candidati[-1])

    return codici

def crea_ordine(conn, cursor, ordine, contatto, motivazione, motivazione_dettaglio):
    """Inserisce un nuovo ordine in Ordini e restituisce l'ID generato."""
    cursor.execute(
        """INSERT INTO Ordini (Ordine, Contatto, Motivazione, MotivazioneDettaglio, DataUtilizzo)
           VALUES (%s, %s, %s, %s, CURDATE())""",
        (ordine, contatto, motivazione, motivazione_dettaglio or None)
    )
    return cursor.lastrowid

def marca_codici_usati(conn, cursor, codici_selezionati, identificativo_ordine):
    """Marca i codici come Usato e li collega all'ordine."""
    dati = [(identificativo_ordine, el[0]) for el in codici_selezionati]
    cursor.executemany(
        "UPDATE Codici SET StatoCodice = 'Usato', IdentificativoOrdine = %s WHERE CodiceID = %s",
        dati
    )

@app.route('/campagne-attive')
def campagne_attive():
    """
    Restituisce i tipi e le edizioni che hanno almeno un codice Disponibile, raggruppati per tipo.
    Usato dal frontend per popolare dinamicamente i selettori di tipo ed edizione.
    Output: { "campagne": [{"tipo": "CDD", "edizioni": ["2024", "2025"]}, ...] }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT Tipo, Edizione FROM Codici WHERE StatoCodice = 'Disponibile' ORDER BY Tipo, Edizione"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        campagne = {}
        for tipo_r, edizione_r in rows:
            if tipo_r not in campagne:
                campagne[tipo_r] = []
            campagne[tipo_r].append(edizione_r)
        return jsonify({'campagne': [{'tipo': t, 'edizioni': e} for t, e in campagne.items()]})
    except Exception as e:
        print(f'Errore campagne-attive: {e}')
        return jsonify({'error': 'Errore interno del server'}), 500


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/guida')
def guida():
    return render_template('guida.html')

@app.route('/assegna', methods=['POST'])
def assegna_codici():
    """
    Riceve JSON: { tipo, edizione, importo, ordine, contatto, motivazione, motivazione_dettaglio }
    Restituisce JSON: { codici, totale, importo_richiesto, identificativo_ordine }
    """
    if not is_distribuzione_attiva():
        return jsonify({'error': 'Sistema di distribuzione temporaneamente disattivato'}), 503

    try:
        data = request.get_json()

        tipo       = data.get('tipo', '').strip()
        edizione   = data.get('edizione', '').strip()
        importo    = float(data.get('importo', 0))
        ordine     = data.get('ordine', '').strip()
        contatto   = data.get('contatto', '').strip()
        motivazione = data.get('motivazione', '').strip()
        motivazione_dettaglio = data.get('motivazione_dettaglio', '').strip()

        # Validazione
        if not tipo:
            return jsonify({'error': 'Tipo voucher non specificato'}), 400
        if not edizione:
            return jsonify({'error': 'Edizione non specificata'}), 400
        if importo <= 0:
            return jsonify({'error': 'Importo deve essere maggiore di zero'}), 400
        if not ordine:
            return jsonify({'error': 'Il numero ordine è obbligatorio'}), 400
        if not contatto:
            return jsonify({'error': 'Il contatto è obbligatorio'}), 400
        if motivazione not in MOTIVAZIONI_VALIDE:
            return jsonify({'error': 'Motivazione non valida'}), 400
        if motivazione == 'Altro' and not motivazione_dettaglio:
            return jsonify({'error': 'Specificare la motivazione per "Altro"'}), 400

        if not is_campagna_attiva(tipo, edizione):
            return jsonify({'error': f'Campagna {tipo} {edizione} temporaneamente disabilitata'}), 503

        codici_selezionati = calcola_codici_necessari(tipo, edizione, importo)
        if not codici_selezionati:
            return jsonify({'error': 'Nessun codice disponibile per questa richiesta'}), 404

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            id_ordine = crea_ordine(conn, cursor, ordine, contatto, motivazione,
                                    motivazione_dettaglio if motivazione == 'Altro' else None)
            marca_codici_usati(conn, cursor, codici_selezionati, id_ordine)
            conn.commit()
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"Errore DB: {e}")
            return jsonify({'error': 'Errore durante il salvataggio nel database'}), 500

        cursor.close()
        conn.close()

        # Controlla i livelli residui e invia email se sotto soglia
        controlla_e_notifica()

        codici_response = []
        totale = Decimal('0')
        for codice in codici_selezionati:
            importo_codice = float(codice[2])
            codici_response.append({
                'codice_id': codice[0],
                'tipo': codice[1],
                'importo': importo_codice,
                'edizione': codice[3]
            })
            totale += Decimal(str(importo_codice))

        return jsonify({
            'codici': codici_response,
            'totale': float(totale),
            'importo_richiesto': importo,
            'identificativo_ordine': id_ordine
        })

    except Exception as e:
        print(f"Errore nel server: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500


@app.route('/annulla', methods=['POST'])
def annulla_codici():
    """
    Riceve JSON: { "codici": ["ID1", "ID2", ...] }
    Restituisce JSON: { ripristinati, codici_ripristinati, non_trovati }
    """
    try:
        data = request.get_json()
        codici_ids = [c.strip() for c in data.get('codici', []) if c.strip()]

        if not codici_ids:
            return jsonify({'error': 'Nessun codice fornito'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        placeholders = ', '.join(['%s'] * len(codici_ids))
        cursor.execute(
            f"SELECT CodiceID, IdentificativoOrdine FROM Codici WHERE CodiceID IN ({placeholders}) AND StatoCodice = 'Usato'",
            codici_ids
        )
        rows = cursor.fetchall()
        trovati = [row[0] for row in rows]
        ordini_ids = list({row[1] for row in rows if row[1] is not None})
        non_trovati = [c for c in codici_ids if c not in trovati]

        if trovati:
            # Ripristina TUTTI i codici legati agli ordini coinvolti
            if ordini_ids:
                ord_placeholders = ', '.join(['%s'] * len(ordini_ids))
                cursor.execute(
                    f"UPDATE Codici SET StatoCodice = 'Disponibile', IdentificativoOrdine = NULL WHERE IdentificativoOrdine IN ({ord_placeholders})",
                    ordini_ids
                )
                cursor.execute(
                    f"DELETE FROM Ordini WHERE IdentificativoOrdine IN ({ord_placeholders})",
                    ordini_ids
                )
            else:
                # Codici senza ordine associato (caso raro)
                cursor.executemany(
                    "UPDATE Codici SET StatoCodice = 'Disponibile', IdentificativoOrdine = NULL WHERE CodiceID = %s",
                    [(c,) for c in trovati]
                )
            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            'ripristinati': len(trovati),
            'codici_ripristinati': trovati,
            'non_trovati': non_trovati
        })

    except Exception as e:
        print(f"Errore nel server: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500


@app.route('/cerca', methods=['POST'])
def cerca_ordine():
    """
    Riceve JSON: { "query": "..." }
    Cerca per numero ordine, codice o contatto.
    Restituisce JSON: { "ordini": [...] }
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()

        if not query:
            return jsonify({'error': 'Inserire un termine di ricerca'}), 400

        like = f'%{query}%'

        conn = get_db_connection()
        cursor = conn.cursor()

        # Trova gli IdentificativoOrdine che corrispondono a ordine, contatto o codice
        cursor.execute("""
            SELECT DISTINCT o.IdentificativoOrdine FROM Ordini o
            WHERE o.Ordine LIKE %s OR o.Contatto LIKE %s
            UNION
            SELECT DISTINCT o.IdentificativoOrdine FROM Ordini o
            JOIN Codici c ON c.IdentificativoOrdine = o.IdentificativoOrdine
            WHERE c.CodiceID LIKE %s
        """, (like, like, like))

        order_ids = [row[0] for row in cursor.fetchall()]

        if not order_ids:
            cursor.close()
            conn.close()
            return jsonify({'ordini': []})

        placeholders = ', '.join(['%s'] * len(order_ids))
        cursor.execute(f"""
            SELECT o.IdentificativoOrdine, o.Ordine, o.Contatto, o.Motivazione, o.MotivazioneDettaglio, o.DataUtilizzo,
                   c.CodiceID, c.Tipo, c.Importo, c.Edizione, c.StatoCodice
            FROM Ordini o
            LEFT JOIN Codici c ON c.IdentificativoOrdine = o.IdentificativoOrdine
            WHERE o.IdentificativoOrdine IN ({placeholders})
            ORDER BY o.IdentificativoOrdine DESC, c.CodiceID
        """, order_ids)

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        orders = {}
        for row in rows:
            oid, ordine, contatto, motivazione, mot_det, data_uso, codice_id, tipo, importo, edizione, stato = row
            if oid not in orders:
                orders[oid] = {
                    'id': oid,
                    'ordine': ordine,
                    'contatto': contatto,
                    'motivazione': motivazione,
                    'motivazione_dettaglio': mot_det,
                    'data': str(data_uso) if data_uso else None,
                    'codici': []
                }
            if codice_id:
                orders[oid]['codici'].append({
                    'codice_id': codice_id,
                    'tipo': tipo,
                    'importo': float(importo),
                    'edizione': edizione,
                    'stato': stato
                })

        return jsonify({'ordini': list(orders.values())})

    except Exception as e:
        print(f"Errore nel server: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500


if __name__ == '__main__':
    try:
        conn = get_db_connection()
        conn.close()
        print("[OK] Connessione al database MySQL riuscita")
        ensure_configurazione()
    except Exception as e:
        print(f"[ERR] Errore connessione database: {e}")
        print("Verifica che MySQL sia attivo e che le credenziali siano corrette")

    app.run(debug=True, host='0.0.0.0', port=8080)
