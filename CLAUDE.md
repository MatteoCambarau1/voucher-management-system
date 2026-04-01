# CLAUDE.md — CDD_YM Project Guide

This file provides context and guidance for working on the CDD_YM codebase. Read it before making any changes.

---

## 1. Project Overview

**CDD_YM** is a proof-of-concept web application built to demonstrate a system for distributing Italian government voucher codes to beneficiaries. It was developed to present an idea to a company, which will be responsible for making the application secure and production-ready.

The system manages voucher types and editions **fully dynamically** — any `Tipo` value loaded into the database via CSV is automatically supported without code changes (e.g. `CDD`, `YM`, `CartaCultura`, `18app`, or any future type). The same applies to editions. The application automates code selection, persists every assignment to a MySQL database, and provides restore and search capabilities through a browser-based interface.

**This is not a production system.** Security hardening, scalability, and infrastructure concerns are intentionally out of scope and will be addressed by the receiving company.

---

## 2. Project Structure

```
CDD_YM/
├── README.md                  # End-user installation guide and API reference
├── CLAUDE.md                  # This file
└── CDD_YM/                    # Application root
    ├── app.py                 # Flask application: core routes, business logic, DB access
    ├── admin.py               # Flask Blueprint: admin routes (/admin, /carica, /admin/stato-codici, /admin/toggle-campagna, /admin/toggle-taglio, /admin/export/*, /admin/invia-notifica)
    ├── notifications.py       # Email monitoring: code-level threshold check and SMTP sending
    ├── carica_codici.py       # CLI script: bulk CSV loader (alternative to web UI upload)
    ├── requirements.txt       # Pinned Python dependencies
    ├── .gitignore
    ├── static/
    │   ├── logo.svg           # Full horizontal logo (icon + wordmark + tagline)
    │   └── logo-icon.svg      # Icon-only logo (scalable, for favicon/avatar use)
    └── templates/
        ├── index.html         # Main UI — Assign / Restore / Search tabs (HTML + CSS + JS)
        ├── admin.html         # Admin panel — Carica Codici / Campagne / Export / Monitoraggio / Sistema tabs
        └── guida.html         # Operator guide page with step-by-step instructions
```

### Key file roles

**`app.py`** contains the core business logic: Flask route definitions, the voucher selection algorithm, database helper functions, and startup connection check. It registers `admin_bp` from `admin.py` and calls `controlla_e_notifica()` from `notifications.py` after every successful assignment.

**`admin.py`** is a Flask Blueprint (`admin_bp`) registered in `app.py`. It owns all admin-facing routes. It has its own `DB_CONFIG` copy (see Section 7 — DB_CONFIG duplication). Admin routes are accessible only via direct URL — there is no link from the main UI. It imports `openpyxl` for Excel export generation (`/admin/export/codici`, `/admin/export/ordini`, `/admin/export/riepilogo`).

**`notifications.py`** contains the monitoring and email logic. It defines `SOGLIA` (threshold), `get_conteggio_codici()` (returns counts grouped by Tipo + Edizione + Importo), `controlla_e_notifica()` (checks counts, sends email if any taglio is below threshold), and `_invia_email()` (SMTP sending). Configure `EMAIL_CONFIG` here before going to production.

**`carica_codici.py`** is a standalone CLI script for loading codes from a CSV file. It replicates the same validation and INSERT IGNORE logic as the web upload. Use it when terminal access is available. Run with: `python3 carica_codici.py <file.csv>`

**`templates/index.html`** is a self-contained frontend. All CSS (via `<style>`) and JavaScript (via `<script>`) are inline in this file. There are no external static assets. The JS includes a complete i18n system (`TRANSLATIONS` object) for Italian and English.

**`templates/admin.html`** is the admin panel UI. It has five tabs: **Carica Codici** (CSV file upload), **Campagne** (per-campaign management — view counts, toggle per campagna, toggle per taglio, delete available codes), **Export** (one-click Excel downloads for codes, orders, and campaign summary), **Monitoraggio** (per-taglio availability dashboard with manual notification trigger), and **Sistema** (distribution kill switch — ON/OFF toggle backed by the `Configurazione` table). CSS is inline and duplicated — changes must also be applied to `index.html` and `guida.html`.

**`templates/guida.html`** is a static informational page for operators. It shares the same visual design as `index.html` but its CSS is duplicated inline — there is no shared stylesheet. Changes to the visual design must be applied to both files manually.

---

## 3. How the Main Algorithm Works

The core of the application is the voucher selection algorithm in `calcola_codici_necessari` (`app.py`, line 37). It runs in two phases.

### Phase 1 — Rounding the target amount

Before selecting codes, the requested amount is rounded up to a distributable target:

| Input cents | Behaviour | Example |
|---|---|---|
| Exactly `.00` | No change | 23.00 → 23.00 |
| Between `.01` and `.49` | Round up to `.50` | 23.30 → 23.50 |
| `.50` or above | Round up to next whole euro | 23.50 → 24.00 |

This rounding uses `Decimal` arithmetic throughout to avoid floating-point errors. The input `float` is always converted via `Decimal(str(value))` before any arithmetic.

### Phase 2 — Greedy code selection

Available codes for the requested type and edition are fetched from the database, **sorted by face value descending** (`ORDER BY Importo DESC`). The algorithm iterates through them greedily:

1. If a code's value is less than or equal to the remaining balance, add it to the selection and reduce the balance.
2. If the code's value exceeds the remaining balance, skip it and store it in `rimanenti` (candidates for overshoot).
3. Stop as soon as the accumulated total meets the target.

If after the main pass the total is still short (no exact fit possible), the algorithm picks the **smallest code from `rimanenti` that covers the remaining gap**. This produces the minimum overshoot.

```python
# Phase 2 fallback — pick smallest overshoot candidate
candidati = [c for c in rimanenti if Decimal(str(c[2])) >= residuo]
if candidati:
    codici.append(candidati[-1])  # [-1] because rimanenti is sorted DESC
```

The algorithm does not guarantee a globally optimal combination in all cases, but it performs well given the typical denomination structure of government vouchers (fixed face values like 5, 10, 25, 50 EUR).

---

## 4. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python / Flask | Flask 3.0.0 |
| Database driver | mysql-connector-python | 8.2.0 |
| Excel generation | openpyxl | 3.1.2 |
| Database | MySQL | 8.0+ |
| Frontend | Vanilla HTML/CSS/JavaScript | No framework |
| Fonts | Google Fonts (DM Sans, Playfair Display) | CDN |

There are no build tools, bundlers, or frontend frameworks. The frontend is intentionally simple: plain JS with `fetch`, DOM manipulation, and inline templates built with template literals.

Python dependencies are pinned exactly in `requirements.txt`. Do not add new dependencies without updating that file.

---

## 5. Database Schema

The database is named `CDD_YM` and contains three tables.

### `Codici` — one row per physical voucher code

| Column | Type | Notes |
|---|---|---|
| `CodiceID` | `VARCHAR(64)` PK | The voucher code string (e.g. `AB12-CD34-EF56`) |
| `Tipo` | `VARCHAR(32)` | Voucher programme — any non-empty string (e.g. `CDD`, `YM`, `CartaCultura`, `18app`) |
| `Importo` | `DECIMAL(10,2)` | Face value in euros — always use DECIMAL, never FLOAT |
| `Edizione` | `VARCHAR(4)` | Edition identifier — any non-empty string (e.g. `'2024'`, `'2025'`, `'2026'`) |
| `StatoCodice` | `ENUM('Disponibile', 'Usato')` | Current availability status |
| `IdentificativoOrdine` | `INT NULL` | FK to `Ordini.IdentificativoOrdine`; NULL when available |

### `Ordini` — one row per assignment event

| Column | Type | Notes |
|---|---|---|
| `IdentificativoOrdine` | `INT AUTO_INCREMENT` PK | Internal order identifier |
| `Ordine` | `VARCHAR(128)` | Order ID from the external order management system |
| `Contatto` | `VARCHAR(128)` | Contact ID from the external system |
| `Motivazione` | `VARCHAR(64)` | One of the five valid motivation values |
| `MotivazioneDettaglio` | `VARCHAR(512)` NULL | Free text, only present when `Motivazione = 'Altro'` |
| `DataUtilizzo` | `DATE` | Assignment date, always set via `CURDATE()` |

### `Configurazione` — key/value settings table

| Column | Type | Notes |
|---|---|---|
| `chiave` | `VARCHAR(64)` PK | Setting key |
| `valore` | `VARCHAR(64)` | Setting value |

Holds multiple rows:
- `distribuzione_attiva` — `'1'` (active) or `'0'` (disabled); created automatically by `ensure_configurazione()` on first startup.
- `disabilitato_{Tipo}_{Edizione}` — `'1'` when a campaign is disabled (e.g. `disabilitato_CDD_2025`).
- `disabilitato_{Tipo}_{Edizione}_{importo}` — `'1'` when a single denomination is disabled (e.g. `disabilitato_CDD_2025_25.00`).

Campaign and taglio keys are created on first toggle and removed automatically when a campaign is deleted via `elimina-campagna`. No manual SQL needed.

### Relationship

`Codici.IdentificativoOrdine` is a soft foreign key to `Ordini`. When a restore operation runs, it sets codes back to `'Disponibile'`, clears `IdentificativoOrdine`, and **deletes the corresponding `Ordini` record**. Restore is used exclusively to correct erroneous assignments — the order record is intentionally removed so the assignment leaves no trace.

---

## 6. Code Conventions

### Python (`app.py`, `admin.py`, `notifications.py`)

**Naming**: functions use `snake_case` in Italian (e.g. `calcola_codici_necessari`, `marca_codici_usati`, `crea_ordine`). Variables and database column references also use Italian names matching the schema. Maintain this consistency when adding functions.

**Blueprint pattern**: admin routes live in `admin.py` as a Flask Blueprint (`admin_bp`). New admin-only features should be added there, not in `app.py`. Register new blueprints in `app.py` with `app.register_blueprint(...)`.

**Notification side effect**: `/assegna` calls `controlla_e_notifica()` after every successful commit. This is a read + optional email send, and it runs synchronously in the request. Keep it fast — do not add blocking operations to `notifications.py`.

**Monetary values**: always use `Decimal` for any arithmetic involving euro amounts. Convert floats immediately on input with `Decimal(str(value))`. Never perform arithmetic directly on `float` values fetched from the database — cast them first.

**Route docstrings**: each route function has a short docstring describing the expected JSON input and output shape. Follow this pattern for any new routes.

**Database helpers**: functions that interact with the database receive `conn` and `cursor` as arguments when they are part of a larger transaction (see `crea_ordine`, `marca_codici_usati`). Functions that open their own connection and close it before returning are used for read-only queries (see `check_codici_disponibili`). Maintain this distinction.

**Error responses**: all routes return `jsonify({'error': '...'})` with an appropriate HTTP status code (400 for validation errors, 404 for not-found, 500 for unexpected failures). The frontend expects this shape for error handling. Do not change the key name `error`.

**Valid motivations**: the tuple `MOTIVAZIONI_VALIDE` at module level defines the accepted motivation values. Update it if new motivations are added — the validation in `/assegna` references it directly.

### JavaScript (`index.html`)

**i18n**: every user-visible string must exist in both `TRANSLATIONS.it` and `TRANSLATIONS.en`. Access strings with `t('key')`. Never hardcode Italian or English text directly in the DOM-building functions.

**DOM building**: results are rendered by constructing HTML strings in `buildResultsHTML`, `buildAnnullaResultHTML`, and `buildCercaResultHTML`. New output sections should follow the same pattern: return an HTML string, assign it to `outputDiv.innerHTML`.

**Global state**: `lang`, `tipo`, `edizione`, and `tipiCampagne` are module-level `let` variables tracking current UI state. `tipiCampagne` is a map of `tipo → [edizioni]` populated at page load from `/campagne-attive`. They are updated by `setLang`, `selectTipo`, and `selectEdizione`. Do not read their values from the DOM — always use these variables.

**Async pattern**: all three forms use the same `async/await` pattern with `fetch`. The button is disabled during the request and re-enabled in `finally`. Follow this pattern for any new form submissions.

---

## 7. Areas of Attention

### Monetary arithmetic and Decimal precision

The algorithm is careful to avoid float precision errors, but the pattern `Decimal(str(float_value))` is required at every boundary where a float enters the system (HTTP input, database read). If you add a code path that receives or returns monetary values, ensure the conversion is applied consistently.

The final response converts `Decimal` back to `float` for JSON serialisation. This is intentional — JSON does not have a decimal type, and the values are display-only at that point.

### Race condition window in code assignment

Between `calcola_codici_necessari` (reads available codes) and `marca_codici_usati` (marks them used), there is a time window during which concurrent requests could select the same codes. In practice this is acceptable for a proof-of-concept with low concurrency, but it is a known architectural limitation. The receiving company will address this with database-level locking or a queue mechanism.

Do not introduce additional reads or slow operations between these two calls — it would widen the race window.

### Database connection lifecycle

Each route opens and closes its own connection manually. Connections are closed in a `try/finally` block in `/assegna`. The `/annulla` and `/cerca` routes close connections at the end of the happy path but rely on the outer `except` to handle teardown in error cases. This is a known inconsistency. Do not change the connection pattern without updating all three routes consistently.

The startup block in `__main__` opens a test connection to verify connectivity. It is separate from the request lifecycle and does not affect runtime behaviour.

### Types and editions are dynamic — not hardcoded

Both voucher types (e.g. `CDD`, `YM`, `CartaCultura`, `18app`) and editions (e.g. `'2024'`, `'2025'`, `'2026'`) are **fully dynamic**. The source of truth is the `Codici` table in the database. To add a new type or edition, simply upload a CSV with the new values via the admin panel — no code changes needed.

The endpoint `GET /campagne-attive` (`app.py`) returns all `(Tipo, Edizione)` pairs that currently have `Disponibile` codes, grouped by tipo. `index.html` calls this on page load via `caricaCampagne()`, builds the tipo buttons dynamically, and updates the edizione buttons whenever the selected tipo changes via `aggiornaEdizioni()`. If a tipo or edition has no available codes, its button does not appear.

`MOTIVAZIONI_VALIDE` (line 15 of `app.py`) is still hardcoded. Adding a new motivation requires updating both `app.py` and the `<select>` in `index.html`.

### DB_CONFIG duplication

`DB_CONFIG` and `get_db_connection()` are defined independently in `app.py`, `admin.py`, `notifications.py`, and `carica_codici.py`. This is intentional for PoC simplicity (each module is self-contained). All four modules already read from environment variables (`MYSQLHOST`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`, `MYSQLPORT`) with local fallbacks — so in practice only the environment needs to be updated, not the code. `carica_codici.py` is the only exception; verify it also uses env vars if you modify it. The receiving company should consolidate this into a single `config.py` if they move away from environment variables.

### Email notification side effects in `/assegna`

After every successful code assignment, `/assegna` calls `controlla_e_notifica()`. If the email is configured and a taglio is below `SOGLIA`, an SMTP connection is opened synchronously during the request. If the SMTP server is slow or unreachable, this will delay the response. For production, move the notification call to a background task or queue.

### CSS duplication between templates

`index.html`, `admin.html`, and `guida.html` share the same CSS custom properties and base styles, but the CSS is duplicated in full in each file. When modifying colours, spacing, or typography, all three files must be updated. Consider this before making visual changes.

---

## 8. How to Add New Features

### Adding a new API route

1. Define the route function in `app.py` following the existing pattern:
   - Accept `POST` with `request.get_json()`
   - Validate all input fields, return 400 on validation failure
   - Open a connection, perform the operation, close in `finally`
   - Return `jsonify({...})` on success

2. Add a corresponding section in `index.html`:
   - Add a tab button in `.mode-tabs` and a panel `div` in the card
   - Register the panel in the `panelMap` inside `switchMode`
   - Add a form event listener following the `async/await` pattern
   - Add all strings to both `TRANSLATIONS.it` and `TRANSLATIONS.en`

3. Document the new endpoint in `README.md` under "API Reference".

### Adding a new voucher type

No code changes required. Simply upload a CSV containing codes with the new `Tipo` value (e.g. `CartaCultura`, `18app`, or any custom string up to 32 characters) via `/admin` → tab "Carica Codici". The backend accepts any non-empty tipo. The frontend will display the new tipo button automatically on the next page load.

### Adding a new edition year

No code changes required. Simply upload a CSV containing codes with the new edition string (e.g. `2026`) via `/admin` → tab "Carica Codici". The backend accepts any non-empty edition value. The frontend will display the new edition button automatically on the next page load.

### Removing an edition (campaign)

Go to `/admin` → tab "Campagne". Each campaign (Tipo + Edizione) is shown with its available/used counts. Click "Elimina" and confirm. This deletes all `Disponibile` codes for that campaign and cleans up the related `Configurazione` keys. Codes already assigned (`Usato`) are preserved. The edition button disappears from the main UI automatically once no available codes remain.

### Loading codes from CSV

Two options are available:

**Web UI (recommended for non-technical users):**
Navigate to `/admin` → tab "Carica Codici" → select a `.csv` file → submit. The backend validates each row and runs `INSERT IGNORE`. Results (inserted / duplicates / errors) are shown on screen.

**CLI (for operators with terminal access):**
```bash
python3 carica_codici.py codici_nuovi.csv
```

Both paths use `INSERT IGNORE`, so re-uploading a file is safe. The expected CSV columns are: `CodiceID`, `Tipo`, `Importo`, `Edizione`.

### Adding an admin route

1. Add the route function to `admin.py` using `@admin_bp.route(...)`.
2. Follow the same error-response pattern as existing routes (`jsonify({'error': '...'})`, appropriate status codes).
3. If the route needs database access, use the local `get_db_connection()` defined in `admin.py`.
4. Add a corresponding section in `admin.html` if UI is needed.

### Configuring email notifications

Open `notifications.py` and fill in `EMAIL_CONFIG`:
- `smtp_host` / `smtp_port`: e.g. `smtp.gmail.com` / `587` for Gmail, `smtp.office365.com` / `587` for Outlook
- `username` / `password`: sender credentials (use an App Password for Gmail)
- `destinatario`: the maintainer's email address

The threshold is `SOGLIA = 20` at the top of the file. Change it to adjust the alert level.
Notifications are per taglio (Tipo + Edizione + Importo). Each denomination is checked independently.

### Extending the search

The `/cerca` endpoint executes a UNION query that searches `Ordini.Ordine`, `Ordini.Contatto`, and `Codici.CodiceID`. To search additional columns, add conditions to the existing query. The frontend `buildCercaResultHTML` function controls which fields are displayed — update it to show any new fields returned by the backend.

---

## 9. What NOT to Do

**Do not use `float` for monetary calculations.** Any arithmetic on euro amounts that bypasses `Decimal` will introduce rounding errors. This will cause the algorithm to select incorrect code combinations.

**Do not preserve `Ordini` rows after a restore operation.** The restore endpoint (`/annulla`) is used exclusively to correct erroneous assignments. It sets codes back to `'Disponibile'`, clears `IdentificativoOrdine`, and deletes the `Ordini` record — so the mistaken assignment leaves no trace in the database.

**Do not change the `error` key name in error responses.** The frontend checks `data.error` in every fetch handler. Renaming it to `message`, `detail`, or anything else will break all error display in the UI silently (no errors shown, no feedback to the operator).

**Do not add frontend state to the DOM and read it back.** The variables `lang`, `tipo`, and `edizione` are the single source of truth for UI state. Do not infer state by reading CSS classes or selected DOM elements — always update and read these variables.

**Do not remove the `ORDER BY Importo DESC` from the available-codes query.** The greedy algorithm depends on codes being sorted by descending face value to work correctly. Changing the sort order will change which codes are selected and may increase overshoot or cause failures on edge-case amounts.

**Do not add Flask-Login, sessions, or authentication middleware.** This is a proof-of-concept with no authentication layer. Adding auth is the responsibility of the receiving company and should be designed as part of a broader security architecture, not bolted on top of the existing routes.

**Do not expose `/admin` publicly without authentication.** The admin panel is currently protected only by URL obscurity. Before deploying, the receiving company must add proper access control (at minimum HTTP Basic Auth or a reverse-proxy rule).

**Do not consolidate DB_CONFIG into a single file without updating all four consumers.** `app.py`, `admin.py`, `notifications.py`, and `carica_codici.py` each define their own `DB_CONFIG`. If you create a shared `config.py`, update all four import sites and verify startup still works.

---

*Last updated: April 2026 — Matteo Cambarau*

---

## 10. Migration Notes

### Branch `differenziazioneCampagna` — April 2026

The `Tipo` column was changed from `ENUM('CDD', 'YM')` to `VARCHAR(32)` to support fully dynamic voucher types. Run the following SQL once on any existing database before deploying:

```sql
ALTER TABLE Codici MODIFY Tipo VARCHAR(32) NOT NULL;
```

All hardcoded type validations (`if tipo not in ('CDD', 'YM')`) were removed from `app.py`, `admin.py`, and `carica_codici.py`. The `/campagne-attive` endpoint now returns `{ "campagne": [{"tipo": ..., "edizioni": [...]}] }` instead of `{ "edizioni": [...] }`. The frontend function `caricaEdizioni()` was replaced by `caricaCampagne()` + `aggiornaEdizioni()`.
