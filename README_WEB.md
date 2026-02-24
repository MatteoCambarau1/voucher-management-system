# Sistema Web per Distribuzione Voucher

## 📋 Panoramica

Ho trasformato il tuo sistema Python da linea di comando in un'applicazione web con interfaccia grafica moderna. Ora puoi gestire i voucher tramite browser!

## 🏗️ Struttura del Progetto

```
voucher-system/
├── app.py                      # Server Flask (backend)
├── templates/
│   └── index.html             # Interfaccia web (frontend)
├── requirements.txt           # Dipendenze Python
├── Python_Script.py           # [Vecchio script da terminale]
├── SQL_Architecture.sql       # Schema database
└── README_WEB.md             # Questo file
```

## ⚙️ Installazione

### 1. Installa le dipendenze

```bash
pip install -r requirements.txt
```

Questo installerà:
- **Flask**: Framework web per Python
- **mysql-connector-python**: Connettore MySQL

### 2. Configura il database

Apri `app.py` e modifica le credenziali del database (righe 7-12):

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'TUA_PASSWORD_QUI',  # ⚠️ CAMBIA QUESTA
    'database': 'CDD_YM'
}
```

### 3. Assicurati che il database sia pronto

Il database deve avere la colonna `StatoCodice` nella tabella `Codici`:

```sql
USE CDD_YM;
ALTER TABLE Codici ADD COLUMN StatoCodice VARCHAR(20);

-- Imposta tutti i codici esistenti come disponibili
UPDATE Codici SET StatoCodice = 'Disponibile' WHERE StatoCodice IS NULL;
```

## 🚀 Avvio del Server

```bash
python app.py
```

Vedrai un output simile:

```
✓ Connessione al database MySQL riuscita
 * Running on http://0.0.0.0:5000
```

## 🌐 Utilizzo

1. **Apri il browser** e vai su: `http://localhost:5000`

2. **Seleziona i parametri:**
   - Tipo Voucher: CDD o YM
   - Edizione: 2024 o 2025
   - Importo richiesto in euro

3. **Clicca "Assegna Codici"**

4. **Ricevi i risultati:**
   - Elenco dei codici assegnati
   - Totale coperto
   - Pulsante "Copia" per copiare tutti i codici

## 🔄 Come Funziona

### Frontend (index.html)
- Interfaccia grafica moderna con design dark mode
- Bottoni toggle per tipo e edizione
- Campo input per l'importo
- Visualizzazione risultati con animazioni

### Backend (app.py)

#### Endpoint: `GET /`
Serve la pagina HTML principale

#### Endpoint: `POST /assegna`
Gestisce l'assegnazione dei codici:

**Request:**
```json
{
  "tipo": "CDD",
  "edizione": "2024",
  "importo": 150.00
}
```

**Response (successo):**
```json
{
  "codici": [
    {"codice_id": 123, "tipo": "CDD", "importo": 100.00, "edizione": "2024"},
    {"codice_id": 124, "tipo": "CDD", "importo": 50.00, "edizione": "2024"}
  ],
  "totale": 150.00,
  "importo_richiesto": 150.00
}
```

**Response (errore):**
```json
{
  "error": "Nessun codice disponibile per questa richiesta"
}
```

## 📊 Algoritmo di Selezione

L'algoritmo è lo stesso del tuo script originale:

1. Recupera tutti i codici disponibili per tipo ed edizione
2. Li ordina per importo decrescente
3. Seleziona codici a partire dai più grandi
4. Se resta un residuo, aggiunge il codice più piccolo che lo copre
5. Marca tutti i codici selezionati come "Usato"

## 🔒 Sicurezza

⚠️ **Per uso in produzione, considera:**

1. **Autenticazione:** Aggiungi login per gli operatori
2. **HTTPS:** Usa certificati SSL
3. **Variabili d'ambiente:** Non mettere password nel codice
4. **Validazione input:** Già implementata base
5. **Rate limiting:** Limita richieste per IP

## 🐛 Risoluzione Problemi

### Errore: "Connessione al database fallita"
- Verifica che MySQL sia in esecuzione
- Controlla username e password in `app.py`
- Verifica che il database `CDD_YM` esista

### Errore: "ModuleNotFoundError: No module named 'flask'"
```bash
pip install -r requirements.txt
```

### La pagina non si carica
- Verifica che il server sia avviato
- Controlla che la porta 5000 non sia occupata
- Prova `http://127.0.0.1:5000` invece di localhost

### Codici non vengono marcati come usati
- Controlla che la colonna `StatoCodice` esista
- Verifica i permessi dell'utente MySQL per UPDATE

## 🆚 Confronto: Vecchio vs Nuovo

### Script Python Originale (Python_Script.py)
- ✅ Funziona da terminale
- ❌ Interfaccia testuale
- ❌ Un operatore alla volta
- ❌ Richiede conoscenza Python

### Applicazione Web (app.py + index.html)
- ✅ Interfaccia grafica moderna
- ✅ Accessibile da browser
- ✅ Multi-utente (più operatori possono usarlo)
- ✅ Facile da usare
- ✅ Copia codici con un click
- ✅ Feedback visivo immediato

## 📝 Personalizzazione

### Cambiare porta del server

In `app.py`, ultima riga:

```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Cambia 5000 con 8080
```

### Modificare l'interfaccia

Modifica `templates/index.html`:
- Cambia colori nelle variabili CSS (righe 9-21)
- Modifica testi e titoli
- Aggiungi nuovi campi se necessario

### Aggiungere logging

```python
import logging

logging.basicConfig(
    filename='voucher_system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## 🎯 Prossimi Passi Consigliati

1. **Autenticazione:** Implementa login con Flask-Login
2. **Storico:** Aggiungi tabella per tracciare chi ha assegnato cosa
3. **Dashboard:** Crea pagina con statistiche di utilizzo
4. **API REST:** Espandi per integrazioni esterne
5. **Docker:** Containerizza l'applicazione per deployment facile

## 📞 Supporto

Per problemi o domande, controlla:
- Log del server (output console)
- Browser console (F12 → Console tab)
- File README.md originale per dettagli database

## 📄 Licenza

Stesso autore e progetto del sistema originale.
