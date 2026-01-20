# ingv_plugin_pygeoapi

Plugin INGV per pygeoapi.

Questo pacchetto permette di estendere pygeoapi con funzionalità specifiche INGV.

## Logica
Ciascun plugin gestisce le richieste per uno specifico codice:
-) definisce i metadati per l'utilizzo del servizio,
-) verifica che i parametri delle richieste di elaborazione siano consistenti con i metadati
-) *** sottomette la richiesta ad un servizio ***
-) elabora la risposta in funzione dei metadati e delle richieste di elaborazione
-) restituisce i risultati

### Sottomettere la richiesta ad un servizio
E' stata fatta la scelta di non eseguire l'elaborazione del codice sullo stesso server
per permettere la completa indipendenza tra l'ambiente di esecuzione di plugin differenti,
in particolare le librerie utilizzate da ciascun codice.

Ciascun plugin richiede il servizio di elaborazione su un URL specifico,
per cui si ipotizza un server dedicato per ciascun codice.

A ciascun plugin è associata una directory (ref. nella configurazione del plugin <private_processor_dir>)
al di sotto della quale viene creata una directory specifica per ciascun job (con il nome univoco del job, un UUID)
sottomesso al plugin.
Il plugin può leggere/scrivere file nella directory specifica del job che sta elaborando.

Nel caso in cui il servizio di elaborazione richiesto dal plugin debba utilizzare file di input
o restituire file di output, il servizio deve avere accesso alla directory del plugin associata al servizio
(ovvero deve essere una cartella condivisa), ed in particolare alla sottodirectory relativa al job specifico.

La modalità di scambio di informazioni tra plugin e servizio specifico è gestita in maniera specifica
all'interno del plugin.
Il servizio specifico deve rispondere alle seguenti richieste:
/execute : il cui content-type sia <text/plain> o <application/json> ; 
il body della richiesta deve contenere un oggetto in formato JSON
con i seguenti campi:
-) code_input_params : contiene un dizionario con <chiave_parametro : valore_parametro>
I <valore_parametro> possono essere stringhe, numeri o booleani.
-) application_params : contiene un dizionario con <chiave_parametro : valore_parametro>
Le possibili <chiace_parametro> sono:
--) job_id : identificativo del job (UUID)
--) synch_execution : opzionale, booleano, default True, indica se la richiesta deve essere sincrona.


## Installazione

### Progetto framework : PyGeoApi
Per l'utilizzo deve essere configurato il progetto PyGeoAPI (https://github.com/geopython/pygeoapi)
di cui il presente progetto rappresenta un plug-in.
L'installazione di PyGeoApi include anche tutte le librerie necessarie
(ref. requirements*.txt).

### Job Manager - PostgreSQL
I plugin utilizzano come Job Manager PostgreSQL:
i parametri per l'utilizzo devono essere forniti come parte della configurazione di  PyGeoAPI
(https://docs.pygeoapi.io/en/latest/publishing/ogcapi-processes.html#postgresql).

Il database deve essere presente, comen indicato in:
https://github.com/geopython/pygeoapi/blob/master/pygeoapi/process/manager/postgresql.py
e con la struttura del database presente:
https://github.com/geopython/pygeoapi/blob/master/tests/data/postgres_manager_full_structure.backup.sql


### Per installare in modalità sviluppo (editable):

```bash
python3 -m pip install -e .
```

## Uso con docker
Il plugin si presta ad essere installato come docker.
In tal caso è necessario creare la seguente stuttura:
./
./Dockerfile
./my.pygeoapi.config.yml
./ingv_plugin/
./ingv_plugin/pyproject.toml
./ingv_plugin/setup.py
./ingv_plugin/ingv_plugin_pygeoapi/__init__.py
./ingv_plugin/ingv_plugin_pygeoapi/process/base_remote_execution.py
./ingv_plugin/ingv_plugin_pygeoapi/process/conduit.py
./ingv_plugin/ingv_plugin_pygeoapi/process/solwcad.py
./ingv_plugin/ingv_plugin_pygeoapi/process/...

Devono essere fornite come environment le seguenti variabili:
*** per il server ***
$SERVER_NAME_epos$ : nome del server su cui è fornito il framework pygeoapi (e.g.: localhost:5000 ; epos_geoinquire.pi.ingv.it)
$LOCATION_epos_pygeoapi$ : nome della location a cui è fornito il framework pygeoapi (e.g.: <empty> ; epos_pygeoapi)
*** per il Job Manager ***
$PYGEOAPI_OUTPUT_DIR$ : directory utilizzata per scrivere file dei risultati delle elaborazioni
$IP_ADDRESS_POSTGRES_SERVER$ : host che fornisce PostgreSQL (e.g. 127.0.0.1)
$PORT_POSTGRES_SERVER$ : porta utilizzata da PostgreSQL (e.g.: 5433 ; 5432)
Nota: attualmente il file di configurazione non prevede come variabili user e password per l'accesso al DB,
      ma in un progetto non isolato è opportuno aggiungerli.
user: ogc_api_user
password: user
*** per ciascun plugin ***
Nella configurazione proposta si ipotizza che ciascun plugin abbia una directory dedicata
al di sotto di una directory che contiene le directory di tutti i lugin:
            private_processor_dir: 
$PYGEOAPI_BASE_PRIVATE_DIRECTORY$ : directory padre di tutte le directory private dei plugin (e.g. /custom_process_dir)
$xxx_SERVICE_ID$ : directory specifica del servizio offerto dal plugin (e.g. solwcad)
$xxx_URL_BASE$ : URL del servizio specifico (e.g. http://127.0.0.1:5001)





