# CLAUDE.md — CDD_YM Project Guide

This file provides context and guidance for working on the CDD_YM codebase. Read it before making any changes.

---

## 1. Project Overview

**CDD_YM** is a proof-of-concept web application built to demonstrate a system for distributing Italian government voucher codes to beneficiaries. It was developed to present an idea to a company, which will be responsible for making the application secure and production-ready.

The system manages two voucher types:
- **CDD** — Carta del Docente (Teacher's Card)
- **YM** — Giovani Merito (Young Merit)

Each voucher type is issued in annual editions (currently 2024 and 2025). The application automates code selection, persists every assignment to a MySQL database, and provides restore and search capabilities through a browser-based interface.

**This is not a production system.** Security hardening, scalability, and infrastructure concerns are intentionally out of scope and will be addressed by the receiving company.

---

## 2. Project Structure

```
CDD_YM/
├── README.md                  # End-user installation guide and API reference
├── CLAUDE.md                  # This file
└── CDD_YM/                    # Application root
    ├── app.py                 # Flask application: routes, business logic, DB access
    ├── requirements.txt       # Pinned Python dependencies
    ├── .gitignore
    └── templates/
        ├── index.html         # Main UI — Assign / Restore / Search tabs (HTML + CSS + JS)
        └── guida.html         # Operator guide page with step-by-step instructions
```

### Key file roles

**`app.py`** is the single backend file. It contains everything: Flask route definitions, the voucher selection algorithm, database helper functions, and startup connection check. All business logic lives here.

**`templates/index.html`** is a self-contained frontend. All CSS (via `<style>`) and JavaScript (via `<script>`) are inline in this file. There are no external static assets. The JS includes a complete i18n system (`TRANSLATIONS` object) for Italian and English.

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
| Database | MySQL | 8.0+ |
| Frontend | Vanilla HTML/CSS/JavaScript | No framework |
| Fonts | Google Fonts (DM Sans, Playfair Display) | CDN |

There are no build tools, bundlers, or frontend frameworks. The frontend is intentionally simple: plain JS with `fetch`, DOM manipulation, and inline templates built with template literals.

Python dependencies are pinned exactly in `requirements.txt`. Do not add new dependencies without updating that file.

---

## 5. Database Schema

The database is named `CDD_YM` and contains two tables.

### `Codici` — one row per physical voucher code

| Column | Type | Notes |
|---|---|---|
| `CodiceID` | `VARCHAR(64)` PK | The voucher code string (e.g. `AB12-CD34-EF56`) |
| `Tipo` | `ENUM('CDD', 'YM')` | Voucher programme |
| `Importo` | `DECIMAL(10,2)` | Face value in euros — always use DECIMAL, never FLOAT |
| `Edizione` | `VARCHAR(4)` | Year string: `'2024'`, `'2025'` |
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

### Relationship

`Codici.IdentificativoOrdine` is a soft foreign key to `Ordini`. When a restore operation runs, it sets `IdentificativoOrdine = NULL` on the restored codes. The `Ordini` row is intentionally kept for audit purposes — restore operations do not delete order records.

---

## 6. Code Conventions

### Python (`app.py`)

**Naming**: functions use `snake_case` in Italian (e.g. `calcola_codici_necessari`, `marca_codici_usati`, `crea_ordine`). Variables and database column references also use Italian names matching the schema. Maintain this consistency when adding functions.

**Monetary values**: always use `Decimal` for any arithmetic involving euro amounts. Convert floats immediately on input with `Decimal(str(value))`. Never perform arithmetic directly on `float` values fetched from the database — cast them first.

**Route docstrings**: each route function has a short docstring describing the expected JSON input and output shape. Follow this pattern for any new routes.

**Database helpers**: functions that interact with the database receive `conn` and `cursor` as arguments when they are part of a larger transaction (see `crea_ordine`, `marca_codici_usati`). Functions that open their own connection and close it before returning are used for read-only queries (see `check_codici_disponibili`). Maintain this distinction.

**Error responses**: all routes return `jsonify({'error': '...'})` with an appropriate HTTP status code (400 for validation errors, 404 for not-found, 500 for unexpected failures). The frontend expects this shape for error handling. Do not change the key name `error`.

**Valid motivations**: the tuple `MOTIVAZIONI_VALIDE` at module level defines the accepted motivation values. Update it if new motivations are added — the validation in `/assegna` references it directly.

### JavaScript (`index.html`)

**i18n**: every user-visible string must exist in both `TRANSLATIONS.it` and `TRANSLATIONS.en`. Access strings with `t('key')`. Never hardcode Italian or English text directly in the DOM-building functions.

**DOM building**: results are rendered by constructing HTML strings in `buildResultsHTML`, `buildAnnullaResultHTML`, and `buildCercaResultHTML`. New output sections should follow the same pattern: return an HTML string, assign it to `outputDiv.innerHTML`.

**Global state**: `lang`, `tipo`, and `edizione` are module-level `let` variables tracking current UI state. They are updated by `setLang`, `selectTipo`, and `selectEdizione`. Do not read their values from the DOM — always use these variables.

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

### Hardcoded editions and motivation values

`['2024', '2025']` (edition validation, line 124) and `MOTIVAZIONI_VALIDE` (line 15) are the two places where domain values are hardcoded. Adding a new edition year or motivation requires updating both `app.py` (backend validation) and `index.html` (frontend dropdowns and translations). There is no single source of truth for these values.

### CSS duplication between templates

`index.html` and `guida.html` share the same CSS custom properties and base styles, but the CSS is duplicated in full in each file. When modifying colours, spacing, or typography, both files must be updated. Consider this before making visual changes.

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

1. Update the `Tipo` ENUM in MySQL: `ALTER TABLE Codici MODIFY Tipo ENUM('CDD', 'YM', 'NEW_TYPE')`.
2. Add `'NEW_TYPE'` to the validation list in `/assegna` (`if tipo not in ['CDD', 'YM']`).
3. Add a new toggle button in the Tipo field group in `index.html`.
4. Add the label and sublabel strings to both translation objects.

### Adding a new edition year

1. Add the year string to the validation list in `/assegna` (`if edizione not in ['2024', '2025']`).
2. Add a toggle button for the new year in the Edizione field group in `index.html`.
3. Populate the `Codici` table with codes for the new edition.

### Extending the search

The `/cerca` endpoint executes a UNION query that searches `Ordini.Ordine`, `Ordini.Contatto`, and `Codici.CodiceID`. To search additional columns, add conditions to the existing query. The frontend `buildCercaResultHTML` function controls which fields are displayed — update it to show any new fields returned by the backend.

---

## 9. What NOT to Do

**Do not use `float` for monetary calculations.** Any arithmetic on euro amounts that bypasses `Decimal` will introduce rounding errors. This will cause the algorithm to select incorrect code combinations.

**Do not delete `Ordini` rows during a restore operation.** The restore endpoint (`/annulla`) sets codes back to `'Disponibile'` and clears `IdentificativoOrdine`, but intentionally leaves the `Ordini` record intact. Deleting order records breaks the audit trail. If you add a bulk-restore or admin feature, maintain this constraint.

**Do not change the `error` key name in error responses.** The frontend checks `data.error` in every fetch handler. Renaming it to `message`, `detail`, or anything else will break all error display in the UI silently (no errors shown, no feedback to the operator).

**Do not add frontend state to the DOM and read it back.** The variables `lang`, `tipo`, and `edizione` are the single source of truth for UI state. Do not infer state by reading CSS classes or selected DOM elements — always update and read these variables.

**Do not remove the `ORDER BY Importo DESC` from the available-codes query.** The greedy algorithm depends on codes being sorted by descending face value to work correctly. Changing the sort order will change which codes are selected and may increase overshoot or cause failures on edge-case amounts.

**Do not add Flask-Login, sessions, or authentication middleware.** This is a proof-of-concept with no authentication layer. Adding auth is the responsibility of the receiving company and should be designed as part of a broader security architecture, not bolted on top of the existing routes.

---

*Last updated: March 2026 — Matteo Cambarau*
