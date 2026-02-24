#!/bin/bash

echo "======================================"
echo "Sistema Distribuzione Voucher"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trovato. Installalo prima di procedere."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip non trovato. Installalo prima di procedere."
    exit 1
fi

echo "✓ Python 3 trovato"
echo "✓ pip trovato"
echo ""

# Install requirements
echo "Installazione dipendenze..."
pip3 install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo "❌ Errore durante l'installazione delle dipendenze"
    exit 1
fi

echo "✓ Dipendenze installate"
echo ""

# Check if MySQL is running (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if pgrep -x "mysqld" > /dev/null; then
        echo "✓ MySQL in esecuzione"
    else
        echo "⚠️  MySQL non sembra in esecuzione"
        echo "   Avvialo con: mysql.server start"
    fi
fi

echo ""
echo "======================================"
echo "Avvio server..."
echo "======================================"
echo ""
echo "Una volta avviato, apri il browser e vai su:"
echo "👉 http://localhost:5000"
echo ""
echo "Premi CTRL+C per fermare il server"
echo ""

# Start the Flask app
python3 app.py
