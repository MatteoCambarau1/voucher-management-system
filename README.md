# Voucher Code Distribution System

## Description

This project is an automated voucher code distribution system connected to a MySQL database. It allows an operator to assign available discount vouchers (*Carta del Docente* or *Giovani Merito*) to users based on the requested type, edition year, and amount needed. Once assigned, codes are automatically marked as used in the database to prevent double allocation.

## Project Structure

```
├── Python_Script.py       # Main application logic
├── SQL_Architecture.sql   # Database schema alteration
└── README.md
```

## How It Works

The system follows a simple 3-step flow:

**1. User Input** — The operator is prompted to enter:
- Voucher type: `CDD` (Carta del Docente) or `YM` (Giovani Merito)
- Edition year: `2024` or `2025`
- Required amount (float)

**2. Code Selection** — The script queries the `Codici` table in the `CDD_YM` MySQL database, retrieving all available codes matching the requested type and edition, ordered by amount descending. It then selects the optimal combination of codes that covers the requested amount.

**3. Status Update** — Selected codes are marked as `'Usato'` (Used) in the database via an `UPDATE` query, ensuring they cannot be assigned again.

## Database

The system connects to a local MySQL database named `CDD_YM`.

### Table: `Codici`

| Column | Type | Description |
|--------|------|-------------|
| `CodiceID` | INT | Primary key, unique code identifier |
| `Tipo` | VARCHAR | Voucher type (`CDD` or `YM`) |
| `Importo` | DECIMAL | Value of the voucher |
| `Edizione` | VARCHAR | Edition year (`2024` or `2025`) |
| `StatoCodice` | VARCHAR(20) | Status: `Disponibile` or `Usato` |

> The `StatoCodice` column is added via `SQL_Architecture.sql`.

## Requirements

- Python 3.x
- MySQL Server (running locally)
- Python library: `mysql-connector-python`

Install the required library with:

```bash
pip install mysql-connector-python
```

## Configuration

Before running the script, update the database connection credentials in `Python_Script.py`:

```python
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="YOUR_PASSWORD",
    database="CDD_YM"
)
```

## Usage

1. Make sure your MySQL server is running and the `CDD_YM` database is set up.
2. Run the SQL script to add the `StatoCodice` column (only needed once):

```sql
USE CDD_YM;
ALTER TABLE Codici ADD COLUMN StatoCodice VARCHAR(20);
```

3. Run the Python script:

```bash
python Python_Script.py
```

4. Follow the prompts to enter the voucher type, edition, and required amount.

## Notes

- Input is case-insensitive and whitespace-tolerant (automatically normalized).
- If no available codes match the request, an empty list is returned.
- The code selection algorithm is greedy: it picks the largest codes first to minimize the number of vouchers used.

## Author

Project developed to automate the management and distribution of educational voucher codes.
