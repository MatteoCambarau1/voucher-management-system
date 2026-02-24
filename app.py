from flask import Flask, render_template, request, jsonify
import mysql.connector
from decimal import Decimal

app = Flask(__name__)

# Configurazione database
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345678',  # CAMBIA CON LA TUA PASSWORD
    'database': 'CDD_YM'
}

def get_db_connection():
    """Crea una connessione al database"""
    return mysql.connector.connect(**DB_CONFIG)

def check_codici_disponibili(tipo, edizione):
    """
    Recupera i codici disponibili dal database
    Args:
        tipo: 'CDD' o 'YM'
        edizione: '2024' o '2025'
    Returns:
        Lista di tuple (CodiceID, Tipo, Importo, Edizione)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    return righe

def calcola_codici_necessari(tipo, edizione, importo_richiesto):
    """
    Calcola quali codici assegnare per coprire l'importo richiesto
    Args:
        tipo: 'CDD' o 'YM'
        edizione: '2024' o '2025'
        importo_richiesto: float dell'importo necessario
    Returns:
        Lista di tuple dei codici selezionati
    """
    righe = check_codici_disponibili(tipo, edizione)
    codici = []
    somma = Decimal('0')
    residuo = Decimal(str(importo_richiesto))
    rimanenti = []

    for el in righe:
        importo_codice = Decimal(str(el[2]))
        
        if importo_codice <= residuo:
            codici.append(el)
            somma += importo_codice
            residuo = Decimal(str(importo_richiesto)) - somma

            if somma >= Decimal(str(importo_richiesto)):
                break
        else:
            rimanenti.append(el)

    # Se l'importo non è ancora coperto, aggiungi il codice più piccolo
    # che copre il residuo (anche se lo supera)
    if somma < Decimal(str(importo_richiesto)) and rimanenti:
        residuo = Decimal(str(importo_richiesto)) - somma
        candidati = [c for c in rimanenti if Decimal(str(c[2])) >= residuo]
        if candidati:
            codici.append(candidati[-1])  # il più piccolo tra quelli sufficienti

    return codici

def marca_codici_usati(codici_selezionati):
    """
    Marca i codici selezionati come 'Usato' nel database
    Args:
        codici_selezionati: Lista di tuple dei codici
    Returns:
        True se successo, False altrimenti
    """
    if not codici_selezionati:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Estrai solo gli ID dei codici
    ID = [(el[0],) for el in codici_selezionati]
    
    query_update = "UPDATE Codici SET StatoCodice = 'Usato' WHERE CodiceID = %s"
    
    try:
        cursor.executemany(query_update, ID)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Errore durante l'aggiornamento: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False

@app.route('/')
def index():
    """Pagina principale"""
    return render_template('index.html')

@app.route('/assegna', methods=['POST'])
def assegna_codici():
    """
    Endpoint per assegnare i codici
    Riceve JSON: { tipo, edizione, importo }
    Restituisce JSON: { codici: [...], totale: float, importo_richiesto: float }
    """
    try:
        data = request.get_json()
        
        tipo = data.get('tipo', '').upper().strip()
        edizione = data.get('edizione', '').strip()
        importo = float(data.get('importo', 0))
        
        # Validazione input
        if tipo not in ['CDD', 'YM']:
            return jsonify({'error': 'Tipo voucher non valido'}), 400
        
        if edizione not in ['2024', '2025']:
            return jsonify({'error': 'Edizione non valida'}), 400
        
        if importo <= 0:
            return jsonify({'error': 'Importo deve essere maggiore di zero'}), 400
        
        # Calcola i codici necessari
        codici_selezionati = calcola_codici_necessari(tipo, edizione, importo)
        
        if not codici_selezionati:
            return jsonify({'error': 'Nessun codice disponibile per questa richiesta'}), 404
        
        # Marca i codici come usati
        if not marca_codici_usati(codici_selezionati):
            return jsonify({'error': 'Errore durante l\'aggiornamento del database'}), 500
        
        # Prepara la risposta
        codici_response = []
        totale = Decimal('0')
        
        for codice in codici_selezionati:
            codice_id = codice[0]
            tipo_codice = codice[1]
            importo_codice = float(codice[2])
            edizione_codice = codice[3]
            
            codici_response.append({
                'codice_id': codice_id,
                'tipo': tipo_codice,
                'importo': importo_codice,
                'edizione': edizione_codice
            })
            
            totale += Decimal(str(importo_codice))
        
        return jsonify({
            'codici': codici_response,
            'totale': float(totale),
            'importo_richiesto': importo
        })
    
    except Exception as e:
        print(f"Errore nel server: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

if __name__ == '__main__':
    # Verifica connessione database all'avvio
    try:
        conn = get_db_connection()
        conn.close()
        print("✓ Connessione al database MySQL riuscita")
    except Exception as e:
        print(f"✗ Errore connessione database: {e}")
        print("Verifica che MySQL sia attivo e che le credenziali siano corrette")
    
    # Avvia il server Flask
    app.run(debug=True, host='0.0.0.0', port=8080)
