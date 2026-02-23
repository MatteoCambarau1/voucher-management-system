# Progetto Codici Promozionali

## Obiettivo

Sviluppare un programma che consenta agli operatori di recuperare automaticamente codici promozionali da un database, tramite comandi semplici e immediati.

L’obiettivo è eliminare le attività manuali di copia-incolla e ridurre errori e tempi di gestione.

---

## Contesto

Attualmente i codici promozionali sono archiviati in SharePoint e gestiti manualmente.  
Ogni operatore deve:

- Calcolare il numero di codici necessari
- Copiare e incollare i codici
- Fornire i codici al cliente

---

## Criticità del processo attuale

- Errori frequenti nella selezione dei codici  
- Elevato sforzo operativo  
- Codici già utilizzati o non aggiornati  
- Tempo di gestione elevato  

---

## Soluzione proposta

Il programma automatizza il recupero dei codici tramite:

- Query SQL su database strutturato
- Logica Python per selezione e gestione codici
- Output immediato per l’operatore

Benefici principali:

- Riduzione errori
- Riduzione tempi operativi
- Codici sempre aggiornati
- Processo standardizzato

---

## Struttura del progetto

Il progetto è composto da due componenti principali:

### 1. Script Python

Uno script Python organizzato in funzioni modulari che gestiscono:

- Connessione al database
- Recupero dei codici promozionali
- Logica di selezione in base alla richiesta
- Validazione e controllo disponibilità codici
- Restituzione output all’operatore

Questa struttura modulare rende il codice scalabile e facilmente manutenibile.

---

### 2. Database SQL

La seconda componente riguarda la progettazione e creazione del database.

Il processo è stato articolato in:

- Definizione DDL (schema, tabelle, relazioni)
- Creazione del database
- Strutturazione delle tabelle in base alle esigenze operative
- Creazione di sezioni e campi necessari alla gestione dei codici
- Query SQL per interrogazione e gestione richieste

Il database è stato progettato per supportare in modo efficiente la gestione e l’assegnazione dei codici promozionali.

---

## Tecnologie

- Python
- SQL
- Database relazionale
- Query DDL e DML

---

## Utilizzo

Clona il repository:

```bash
git clone https://github.com/MatteoCambarau1/CDD_YM.git
			
