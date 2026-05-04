# Deploy Notes — VoucherManagementSystem su Railway

## Variabili d'ambiente da configurare su Railway

Vai su **Railway → progetto → Variables** e aggiungi:

### Database MySQL (Railway MySQL plugin)
Se aggiungi il plugin MySQL di Railway, queste variabili vengono iniettate automaticamente con i nomi giusti. Verifica che siano presenti:

| Variabile | Descrizione |
|---|---|
| `MYSQLHOST` | Host del database MySQL |
| `MYSQLUSER` | Utente del database |
| `MYSQLPASSWORD` | Password del database |
| `MYSQLDATABASE` | Nome del database (`VoucherManagementSystem`) |
| `MYSQLPORT` | Porta MySQL (solitamente `3306`) |

> `PORT` viene iniettata automaticamente da Railway — non va aggiunta manualmente.

### Applicazione
| Variabile | Valore consigliato | Descrizione |
|---|---|---|
| `APP_URL` | `https://<tuo-dominio>.railway.app` | URL pubblico dell'app, usato nelle email di notifica |
| `FLASK_DEBUG` | `false` | Tieni sempre `false` in produzione |

### Email (opzionale — solo se usi le notifiche)
| Variabile | Descrizione |
|---|---|
| `SMTP_HOST` | Server SMTP (es. `smtp.gmail.com`) |
| `SMTP_PORT` | Porta SMTP (es. `587`) |
| `SMTP_USERNAME` | Email mittente |
| `SMTP_PASSWORD` | Password app SMTP |
| `SMTP_DESTINATARIO` | Email del manutentore |

> **Nota:** le credenziali email sono attualmente configurate direttamente in `notifications.py` (variabile `EMAIL_CONFIG`). Se vuoi gestirle tramite env var su Railway, sposta i valori su `os.environ.get(...)` in quel file prima del deploy.

---

## Warning — cose da fare prima o subito dopo il primo avvio

### 1. Inizializzazione della tabella `Configurazione`
`ensure_configurazione()` viene chiamata solo avviando l'app con `python app.py` (blocco `__main__`). Con gunicorn questo blocco **non viene eseguito**.

**Soluzione:** dopo il primo deploy, esegui manualmente questa SQL sul database Railway:

```sql
CREATE TABLE IF NOT EXISTS Configurazione (
    chiave VARCHAR(64) PRIMARY KEY,
    valore VARCHAR(64) NOT NULL
);

INSERT IGNORE INTO Configurazione (chiave, valore) VALUES ('distribuzione_attiva', '1');
```

Puoi farlo da **Railway → MySQL plugin → Query** oppure con un client MySQL connesso alle credenziali Railway.

### 2. Schema del database
Il database MySQL su Railway è vuoto. Devi creare le tabelle prima di usare l'app. Esegui lo schema completo:

```sql
CREATE DATABASE IF NOT EXISTS VoucherManagementSystem;
USE VoucherManagementSystem;

CREATE TABLE IF NOT EXISTS Codici (
    CodiceID VARCHAR(64) PRIMARY KEY,
    Tipo VARCHAR(32) NOT NULL,
    Importo DECIMAL(10,2) NOT NULL,
    Edizione VARCHAR(4) NOT NULL,
    StatoCodice ENUM('Disponibile', 'Usato') NOT NULL DEFAULT 'Disponibile',
    IdentificativoOrdine INT NULL
);

CREATE TABLE IF NOT EXISTS Ordini (
    IdentificativoOrdine INT AUTO_INCREMENT PRIMARY KEY,
    Ordine VARCHAR(128) NOT NULL,
    Contatto VARCHAR(128) NOT NULL,
    Motivazione VARCHAR(64) NOT NULL,
    MotivazioneDettaglio VARCHAR(512) NULL,
    DataUtilizzo DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS Configurazione (
    chiave VARCHAR(64) PRIMARY KEY,
    valore VARCHAR(64) NOT NULL
);

INSERT IGNORE INTO Configurazione (chiave, valore) VALUES ('distribuzione_attiva', '1');
```

### 3. Migrazione da database pre-aprile 2026
Se stai migrando da un database esistente con `Tipo ENUM`, esegui:

```sql
ALTER TABLE Codici MODIFY Tipo VARCHAR(32) NOT NULL;
```

---

## Checklist post-deploy

- [ ] Plugin MySQL aggiunto e collegato al servizio Flask
- [ ] Schema SQL creato (vedi sopra)
- [ ] Variabile `APP_URL` impostata con l'URL pubblico Railway
- [ ] Carica un CSV di test da `/admin` → tab "Carica Codici"
- [ ] Verifica che l'assegnazione funzioni dalla home
- [ ] Verifica che `/admin` sia accessibile (e considera di proteggerlo con Basic Auth)
- [ ] Testa il restore e la ricerca
- [ ] Aggiorna il link live nel `README.md`
