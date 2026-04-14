# VoucherManagementSystem — Voucher Code Distribution System

A web application for managing and distributing voucher codes to beneficiaries. The system automates code selection, handles order tracking, and provides restore and search capabilities through a clean browser-based interface.

---

## Key Features

- **Automated code selection** — given a requested amount, the system applies a greedy algorithm to pick the optimal combination of available voucher codes, rounding up to the nearest €0.50 increment when an exact match is unavailable
- **Fully dynamic voucher types and editions** — the system supports any combination of voucher type and edition without code changes; loading a CSV with a new `Tipo` (e.g. `Voucher3`, `Voucher4`) automatically makes it selectable in the UI
- **Order tracking** — every assignment is persisted to a MySQL database with the associated order ID, contact ID, motivation, and date
- **Code restore** — previously assigned codes can be reverted to "Available" status, detaching them from their order record
- **Search** — look up past assignments by order number, contact ID, or individual voucher code
- **Bilingual UI** — the interface supports Italian and English, switchable at runtime without a page reload
- **Copy to clipboard** — assigned codes can be copied in a single click, ready to paste into external systems
- **Per-campaign and per-denomination disable** — admin toggles to block assignments for a specific campaign (Tipo + Edizione) or a single denomination (e.g. €25.00 Voucher1 2025) without deleting any codes; re-enabling restores normal operation instantly
- **Distribution kill switch** — global admin toggle that blocks all new assignments system-wide; persisted in the database and survives server restarts
- **Excel export** — one-click download of three reports: full code list with order details, full order list with assigned codes, and an aggregated summary by campaign and denomination

---

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.9 |
| MySQL | 8.0 |
| pip | Any recent version |

The application connects to a local MySQL instance. Ensure the MySQL server is running before starting the app.

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/MatteoCambarau1/VoucherManagementSystem.git
cd VoucherManagementSystem
```

**2. Create and activate a virtual environment (recommended)**

```bash
python3 -m venv venv
source venv/bin/activate # macOS / Linux
venv\Scripts\activate # Windows
```

**3. Install Python dependencies**

```bash
pip install -r requirements.txt
```

The `requirements.txt` pins the following packages:

```
Flask==3.0.0
mysql-connector-python==8.2.0
openpyxl==3.1.2
```

**4. Set up the MySQL database**

Create the database and the two required tables. Connect to your MySQL instance and run:

```sql
CREATE DATABASE VoucherManagementSystem CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE VoucherManagementSystem;

CREATE TABLE Codici (
 CodiceID VARCHAR(64) NOT NULL PRIMARY KEY,
 Tipo VARCHAR(32) NOT NULL,
 Importo DECIMAL(10, 2) NOT NULL,
 Edizione VARCHAR(4) NOT NULL,
 StatoCodice ENUM('Disponibile', 'Usato') NOT NULL DEFAULT 'Disponibile',
 IdentificativoOrdine INT DEFAULT NULL
);

CREATE TABLE Ordini (
 IdentificativoOrdine INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 Ordine VARCHAR(128) NOT NULL,
 Contatto VARCHAR(128) NOT NULL,
 Motivazione VARCHAR(64) NOT NULL,
 MotivazioneDettaglio VARCHAR(512) DEFAULT NULL,
 DataUtilizzo DATE NOT NULL
);
```

> **Note:** Populate the `Codici` table with the voucher codes you want to distribute before using the assignment feature. Each row represents one physical voucher code.

**5. Configure the database connection**

The application reads database credentials from environment variables with sensible fallbacks for local development:

| Variable | Default | Description |
|---|---|---|
| `MYSQLHOST` | `localhost` | Database host |
| `MYSQLUSER` | `root` | Database user |
| `MYSQLPASSWORD` | *(none)* | Database password |
| `MYSQLDATABASE` | `VoucherManagementSystem` | Database name |
| `MYSQLPORT` | `3306` | Database port |

**Local development:** set the variables in your shell or create a `.env` file and export them before running the app.

**Railway / cloud hosting:** set the variables in the platform dashboard. Railway injects them automatically when a MySQL plugin is attached.

---

## Running the Application

```bash
python app.py
```

> **Windows note:** if you get a `UnicodeEncodeError` on startup, run with `python -X utf8 app.py` instead.

On startup the application tests the database connection and reports whether it succeeded:

```
✓ Connessione al database MySQL riuscita
 * Running on http://0.0.0.0:8080
```

Open your browser at [http://localhost:8080](http://localhost:8080).

---

## Usage

The interface is organised into three tabs.

### Assign (Assegna)

Use this tab to distribute voucher codes to a beneficiary.

1. Select the **voucher type** from the available buttons — populated dynamically from the database (e.g. Voucher1, Voucher2, Voucher3, Voucher4).
2. Select the **edition** — updates automatically to show only editions available for the selected type.
3. Enter the **requested amount** in euros (e.g. `47.30`).
4. Enter the **Order ID** and **Contact ID** from your order management system.
5. Choose a **motivation** from the dropdown. If you select "Altro" (Other), an additional text field appears to describe the reason.
6. Click **Assegna Codici**.

The system selects the smallest set of codes whose total meets or exceeds the target amount, marks them as `Usato` in the database, and displays them on screen. A one-click copy button lets you transfer all codes at once.

**Rounding logic:**

| Cents portion | Target amount |
|---|---|
| Exactly `.00` | Unchanged — e.g. €23.00 → €23.00 |
| Between `.01` and `.49` | Rounded up to `.50` — e.g. €23.30 → €23.50 |
| From `.50` onwards | Rounded up to the next whole euro — e.g. €23.50 → €24.00 |

### Restore (Annulla)

Use this tab to reverse a previous assignment — for example, when a customer returns an order.

1. Paste the voucher code IDs to restore, one per line.
2. Click **Ripristina Codici**.

Codes found in the database with status `Usato` are reset to `Disponibile` and their order link is cleared. Codes that are not found or are already available are reported separately.

### Search (Cerca)

Use this tab to look up past assignments.

Enter any of the following in the search field:
- An **Order ID** (partial match supported)
- A **Contact ID** (partial match supported)
- A **Voucher code ID** (partial match supported)

Results show all matching orders with their associated codes, motivation, and assignment date.

---

## Admin Panel

Navigate to [http://localhost:8080/admin](http://localhost:8080/admin) to access the administration panel. It has five tabs.

### Carica Codici

Upload a CSV file to bulk-insert new voucher codes into the database. Expected columns: `CodiceID`, `Tipo`, `Importo`, `Edizione`. Re-uploading the same file is safe — duplicates are silently skipped (`INSERT IGNORE`).

### Campagne

View all campaigns (Tipo + Edizione combinations) loaded in the database with their available and used code counts.

Each campaign has two levels of granular control:

- **Toggle campagna** — disables or re-enables an entire campaign (e.g. all Voucher1 2024 codes). When disabled, `/assegna` rejects requests for that campaign with a `503` error. The codes are not deleted and become available again instantly upon re-enabling.
- **Toggle taglio** — disables or re-enables a single denomination within a campaign (e.g. €25.00 Voucher1 2025 only). Useful to stop distributing a specific face value while keeping others active.
- **Elimina campagna** — permanently deletes all `Disponibile` codes for that campaign. Codes already assigned (`Usato`) are preserved. The campaign button disappears from the main UI once no available codes remain.

### Export

Download database snapshots as formatted Excel files (.xlsx):

| Report | Contents |
|---|---|
| **Codici Completo** | All codes with status, campaign, denomination, and linked order details (number, contact, motivation, date) |
| **Ordini Completo** | All orders with contact, motivation, date, number of vouchers, total amount in euros, and full list of assigned codes |
| **Riepilogo Campagne** | Aggregated counts per Tipo + Edizione + Importo: available, used, and total |

### Monitoraggio

View the current availability of each denomination (Tipo + Edizione + Importo). Rows below the configured threshold (`SOGLIA`, default 20) are highlighted in red. A button to send an immediate email notification appears when one or more denominations are critical.

### Sistema

Global emergency kill switch for the distribution system.

- **Active (green)** — operators can assign voucher codes normally.
- **Disabled (red)** — all calls to `/assegna` are rejected with a `503` error regardless of campaign; no codes can be distributed until re-enabled.

Press the button to toggle between states. The state is persisted in the database (`Configurazione` table) and survives server restarts.

---

## Project Structure

```
VoucherManagementSystem/
├── app.py # Flask application — routes, business logic, DB access
├── admin.py # Flask Blueprint — admin routes (/admin, /carica, /admin/stato-codici, toggle, export, etc.)
├── notifications.py # Email monitoring — threshold check and SMTP sending
├── carica_codici.py # CLI script — bulk CSV loader (alternative to web upload)
├── requirements.txt # Python package dependencies (Flask, mysql-connector-python, openpyxl)
├── .gitignore
└── templates/
 ├── index.html # Main UI (Assign / Restore / Search tabs)
 ├── admin.html # Admin panel (Carica Codici / Campagne / Export / Monitoraggio / Sistema tabs)
 └── guida.html # User guide page with step-by-step instructions
```

---

## API Reference

The Flask backend exposes the following endpoints.

### POST /assegna

Assign voucher codes to an order.

**Request body**

```json
{
 "tipo": "Voucher1",
 "edizione": "2025",
 "importo": 47.30,
 "ordine": "404-XXXXXXXX",
 "contatto": "AX2XXXXXXX",
 "motivazione": "DNR",
 "motivazione_dettaglio": ""
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `tipo` | `string` | Yes | Voucher type — any non-empty string matching a type present in the database (e.g. `Voucher1`, `Voucher2`, `Voucher3`, `Voucher4`) |
| `edizione` | `string` | Yes | Edition — any non-empty string matching an edition present in the database (e.g. `2024`, `2025`, `2026`) |
| `importo` | `number` | Yes | Requested amount in euros (must be > 0) |
| `ordine` | `string` | Yes | Order identifier |
| `contatto` | `string` | Yes | Contact identifier |
| `motivazione` | `string` | Yes | One of: `DNR`, `Correlato al Reso`, `Articolo Errato`, `Articolo Mancante`, `Altro` |
| `motivazione_dettaglio` | `string` | When `motivazione` is `Altro` | Free-text description |

**Error response (503)** — returned when the distribution system is disabled from the admin panel:

```json
{ "error": "Sistema di distribuzione temporaneamente disattivato" }
```

**Success response (200)**

```json
{
 "codici": [
 { "codice_id": "AB12-CD34-EF56", "tipo": "Voucher1", "importo": 30.00, "edizione": "2025" },
 { "codice_id": "GH78-IJ90-KL12", "tipo": "Voucher1", "importo": 17.50, "edizione": "2025" }
 ],
 "totale": 47.50,
 "importo_richiesto": 47.30,
 "identificativo_ordine": 42
}
```

---

### POST /annulla

Restore one or more voucher codes to "Available" status.

**Request body**

```json
{
 "codici": ["AB12-CD34-EF56", "GH78-IJ90-KL12"]
}
```

**Success response (200)**

```json
{
 "ripristinati": 2,
 "codici_ripristinati": ["AB12-CD34-EF56", "GH78-IJ90-KL12"],
 "non_trovati": []
}
```

---

### POST /cerca

Search for past orders by order ID, contact ID, or voucher code.

**Request body**

```json
{
 "query": "404-XXXXXXXX"
}
```

**Success response (200)**

```json
{
 "ordini": [
 {
 "id": 42,
 "ordine": "404-XXXXXXXX",
 "contatto": "AX2XXXXXXX",
 "motivazione": "DNR",
 "motivazione_dettaglio": null,
 "data": "2025-03-07",
 "codici": [
 { "codice_id": "AB12-CD34-EF56", "tipo": "Voucher1", "importo": 30.00, "edizione": "2025", "stato": "Usato" }
 ]
 }
 ]
}
```

---

### POST /admin/toggle-campagna

Enable or disable all assignments for a campaign (Tipo + Edizione).

**Request body**

```json
{ "tipo": "Voucher1", "edizione": "2025" }
```

**Success response (200)**

```json
{ "attivo": false }
```

`attivo: false` means the campaign is now disabled; `true` means it is active again.

---

### POST /admin/toggle-taglio

Enable or disable a single denomination within a campaign.

**Request body**

```json
{ "tipo": "Voucher1", "edizione": "2025", "importo": "25.00" }
```

**Success response (200)**

```json
{ "attivo": false }
```

---

### GET /admin/export/codici

Download an Excel file with all codes and their linked order details.

**Response:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` — file download.

---

### GET /admin/export/ordini

Download an Excel file with all orders, including assigned codes and totals.

**Response:** file download (same MIME type as above).

---

### GET /admin/export/riepilogo

Download an Excel file with aggregated counts per Tipo + Edizione + Importo.

**Response:** file download.

---

### GET /campagne-attive

Returns all voucher types and their available editions, grouped by type. Used by the frontend to build the type and edition selectors dynamically. Only types/editions with at least one `Disponibile` code are returned.

**Success response (200)**

```json
{
 "campagne": [
 { "tipo": "Voucher1", "edizioni": ["2024", "2025", "2026"] },
 { "tipo": "Voucher3", "edizioni": ["2026"] },
 { "tipo": "Voucher2", "edizioni": ["2024", "2025"] }
 ]
}
```

---

## Database Schema

```
Codici
┌──────────────────────┬──────────────────────────────────┬──────────┐
│ Column │ Type │ Notes │
├──────────────────────┼──────────────────────────────────┼──────────┤
│ CodiceID │ VARCHAR(64) PK │ Voucher code string │
│ Tipo │ VARCHAR(32) │ Voucher programme │
│ Importo │ DECIMAL(10,2) │ Face value in euros │
│ Edizione │ VARCHAR(4) │ Year or edition identifier (e.g. 2024, 2025, 2026) │
│ StatoCodice │ ENUM('Disponibile','Usato') │ Current status │
│ IdentificativoOrdine │ INT NULL │ FK → Ordini │
└──────────────────────┴──────────────────────────────────┴──────────┘

Ordini
┌──────────────────────┬──────────────────────────────────┬──────────┐
│ Column │ Type │ Notes │
├──────────────────────┼──────────────────────────────────┼──────────┤
│ IdentificativoOrdine │ INT AUTO_INCREMENT PK │ │
│ Ordine │ VARCHAR(128) │ Order ID from external system │
│ Contatto │ VARCHAR(128) │ Contact ID │
│ Motivazione │ VARCHAR(64) │ Assignment reason │
│ MotivazioneDettaglio │ VARCHAR(512) NULL │ Free text for "Altro" │
│ DataUtilizzo │ DATE │ Assignment date (CURDATE()) │
└──────────────────────┴──────────────────────────────────┴──────────┘

Configurazione
┌────────────────┬───────────────┬────────────────────────────────────────────────┐
│ Column │ Type │ Notes │
├────────────────┼───────────────┼────────────────────────────────────────────────┤
│ chiave │ VARCHAR(64) PK│ Setting key │
│ valore │ VARCHAR(64) │ Setting value │
└────────────────┴───────────────┴────────────────────────────────────────────────┘
```

The `Configurazione` table is created automatically on first startup. It holds:
- `distribuzione_attiva` — `'1'` (active) or `'0'` (disabled); the global kill switch
- `disabilitato_{Tipo}_{Edizione}` — `'1'` when a campaign is disabled (e.g. `disabilitato_Voucher1_2025`)
- `disabilitato_{Tipo}_{Edizione}_{importo}` — `'1'` when a single denomination is disabled (e.g. `disabilitato_Voucher1_2025_25.00`)

Campaign and denomination keys are created on first toggle and removed automatically when a campaign is deleted.

---

## Troubleshooting

**"Errore connessione database" on startup**

Verify that MySQL is running and that the `MYSQL*` environment variables are set correctly (see Installation step 5). On macOS you can start MySQL with:

```bash
brew services start mysql
```

**"Nessun codice disponibile per questa richiesta"**

The `Codici` table has no rows with `StatoCodice = 'Disponibile'` matching the selected type and edition. Import voucher codes into the table before assigning.

**Port already in use**

Another process is using port 8080. Either stop that process or change the port in the last line of `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

> **Warning:** The application runs with `debug=True` by default, which is suitable for local use only. Disable debug mode and use a production WSGI server (such as Gunicorn) before exposing the application on a network.

---

## License

<!-- TODO: specify the license (e.g. MIT, proprietary) -->

---

*Matteo Cambarau*
