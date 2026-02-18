#Chiediamo all'utente di quai codici(CDD-YM), anno e importo di cui ha bisogno

def request():      #chiedo all'utente di quali codici ha bisgono
    while True:
        x=input("Di quali codici sostitutivi hai bisogno? Carta del Docente o Giovani Merito? (CDD - YM)")
        y=input("Di quale edizione hai bisogno?(2024 o 2025:)")
        try:
            z=float(input("Inserisci Importo di cui hai bisogno: "))
        except:
            print("L'importo inserito non è valido, riprova ")
            continue
#gestisco eventuali inserimenti minuscoli o tab non richiesti
        x=x.upper()
        x=x.strip()
        y=y.strip()
        if x != "CDD" and x!= "YM":
            print('Errore: inserisci CDD oppure YM')
            continue

        if y != "2024" and y != "2025":
            print('Errore: deve essere 2024 o 2025')
            continue

        print('Inserimento completato')
        return x,y,z

x,y,z =request()

print(f'Hai scelto di ottenere {x}, relative edizione {y}, hai bisogno di una somma pari a {z}')

#mi connetto al mio database test
import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345678",
    database="CDD_YM"
)

#set up del mio cursore
cursor=conn.cursor()

def check(tipo,edizione):       #ho creato uno query che cerca i codici basandosi sull'input iserito dall'utente
    query = """
        SELECT CodiceID, Tipo, Importo, Edizione
        FROM Codici
        WHERE Tipo = %s
          AND Edizione = %s
          AND StatoCodice ='Disponibile'
        ORDER BY Importo DESC, CodiceID ASC
    """

    cursor.execute(query, (tipo, edizione))
    righe = cursor.fetchall()
    #cursor.close()
    return righe
check(x,y)


# prova 2
def calcola_codici_necessari2(tipo, edizione, importoinput):        #cacolo quali codici fornire
    righe = check(tipo, edizione)
    codici = []
    somma = 0
    residuo=importoinput

    for el in righe:
        if float(el[2]) <= residuo:
            codici.append(el)
            somma+=(el[2])
            residuo=importoinput-somma

            if somma >=importoinput:
                break
    return codici
codici_scleti=calcola_codici_necessari2(x,y,z)
print(calcola_codici_necessari2(x,y,z))

def usati(calcola_codici_necessari2):
    ID=[(el[0],)  #considerato che con la funzione Check() ogni el è una tupla che rappresenta CodiceID, Tipo IMporto,Edizione
    for el in calcola_codici_necessari2]   #con (el[0],) creo una tupla con un solo elemento

    query_update= "UPDATE Codici SET StatoCodice = 'Usato' WHERE 'CodiceID' = %s"
    try:
        cursor.executemany(query_update, ID)
        conn.commit() #aggiorno il db
        print(f"Aggiornamento riuscito: {len(ID)} codici ora risultano 'Usato'.")
    except Exception as e:
        print(f"Errore durante l'aggiornamento: {e}")
        conn.rollback()
usati(codici_scleti)



