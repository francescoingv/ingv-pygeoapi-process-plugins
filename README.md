# ingv_plugin_pygeoapi

Plugin INGV per pygeoapi.

Questo pacchetto permette di estendere pygeoapi con funzionalità specifiche INGV.

---

## Logica

Ciascun plugin gestisce le richieste per uno specifico codice con la seguente logica:

- definisce i metadati per l’utilizzo del servizio
- verifica che i parametri delle richieste di elaborazione siano consistenti con i metadati
- **[sottomette la richiesta a un servizio di elaborazione](#sottomettere-la-richiesta-a-un-servizio)**
- elabora la risposta in funzione dei metadati e delle richieste di elaborazione
- restituisce i risultati

---

## Sottomettere la richiesta a un servizio

È stata fatta la scelta di **non eseguire l’elaborazione del codice sullo stesso server**
su cui è in esecuzione pygeoapi, per permettere la completa indipendenza tra
l’ambiente di esecuzione di plugin differenti, in particolare per quanto riguarda
le librerie utilizzate da ciascun codice.

Ciascun plugin richiede un servizio di elaborazione su un URL specifico;
si ipotizza quindi un server dedicato per ciascun codice.

---

## Gestione delle directory e dei job

A ciascun plugin è associata una directory (riferita nella configurazione del plugin
tramite `private_processor_dir`), al di sotto della quale viene creata una directory
specifica per ciascun job, identificata dal nome univoco del job (UUID - Universal Unique ID).

Il plugin può leggere e scrivere file nella directory specifica del job che sta
elaborando.

Nel caso in cui il servizio di elaborazione richiesto dal plugin debba utilizzare
file di input o restituire file di output, il servizio deve avere accesso alla
directory del plugin associata al servizio (ovvero deve essere una cartella condivisa),
ed in particolare alla sottodirectory relativa al job specifico.

La modalità di scambio di informazioni tra plugin e servizio specifico è gestita
in maniera dedicata all’interno del plugin.

---

## Interfaccia del servizio di elaborazione

Il servizio specifico deve rispondere alla seguente richiesta:

```text
POST /execute
```

Il `Content-Type` della richiesta può essere:

- `text/plain`
- `application/json`

Il body della richiesta deve contenere un oggetto JSON con i seguenti campi:

```json
{
  "code_input_params": {
    "chiave_parametro": "valore_parametro"
  },
  "application_params": {
    "job_id": "UUID",
    "synch_execution": true
  }
}
```


### Parametri

#### `code_input_params`

Dizionario contenente coppie `<chiave_parametro : valore_parametro>`.

I valori possono essere:
- stringhe
- numeri
- booleani

---

#### `application_params`

Dizionario con le seguenti chiavi:

- `job_id`  
  Identificativo del job (UUID)

- `synch_execution`  
  Opzionale, booleano, default `true`; indica se la richiesta deve essere
  eseguita in modalità sincrona

---

```text
GET /job_info/<string:job_id>
```

Restituisce un oggetto JSON con le seguenti informazioni di esempio:

```json
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_info": {
    "received": "2026-01-20T10:00:00Z",
    "start_processing": "2026-01-20T10:01:00Z",
    "end_processing": "2026-01-20T10:02:00Z",
    "exit_code": 0,
    "std_out": "Output standard del processo",
    "std_err": ""
  },
  "params": {
    "param1": "valore1",
    "param2": 123
  }
```

### Parametri

#### `exit_code`

Codice di uscita dell'esecuzione (0 se è terminata senza errori)

#### `std_out`

Quello che l'esecuzione del codice ha prodotto sullo standard output

#### `std_err`

Quello che l'esecuzione del codice ha prodotto sullo standard error

#### `params`

Dizionario con i parametri che sono stati passati al codice
Ricavati principalmente da code_input_params nella richiesta POST,
possono talvolta essere differenti: parametri aggiunti o modificati dal servizio.

---

## Installazione

### Framework di riferimento: pygeoapi

Per l’utilizzo del plugin deve essere configurato il progetto **pygeoapi**:

https://github.com/geopython/pygeoapi

Il presente progetto rappresenta un **plug-in di pygeoapi**.

L’installazione di pygeoapi include tutte le librerie necessarie al runtime
(con riferimento ai file `requirements*.txt` del framework).

---

### Installazione in modalità sviluppo (editable)

```bash
python3 -m pip install -e .
```

---

## Uso con Docker

Il plugin si presta ad essere installato come container Docker.

In tal caso è necessario creare la seguente struttura:

```text
./
├── Dockerfile
├── my.pygeoapi.config.yml
└── ingv_plugin/
    ├── pyproject.toml
    ├── setup.py
    └── ingv_plugin_pygeoapi/
        ├── __init__.py
        └── process/
            ├── base_remote_execution.py
            ├── conduit.py
            ├── solwcad.py
            └── ...
```

---

## Variabili d’ambiente

### Server pygeoapi

- `$SERVER_NAME_epos$`  
  Nome del server su cui è fornito il framework pygeoapi  
  (es. `localhost:5000`, `epos_geoinquire.pi.ingv.it`)

- `$LOCATION_epos_pygeoapi$`  
  Nome della location a cui è fornito il framework pygeoapi  
  (es. stringa vuota oppure `epos_pygeoapi`)

---

### Job Manager di pygeoapi
- `$PYGEOAPI_OUTPUT_DIR$`
  directory utilizzata per scrivere i file dei risultati delle elaborazioni
  
- `$IP_ADDRESS_POSTGRES_SERVER$`
  host che fornisce PostgreSQL
  (es. 127.0.0.1)
  
- `$PORT_POSTGRES_SERVER$`
  porta utilizzata da PostgreSQL
  (es. 5433 , 5432)
  
Nota: attualmente il file di configurazione non prevede come variabili user e password per l'accesso al DB,
      ma in un progetto non isolato è opportuno aggiungerli.
user: ogc_api_user
password: user

---

### Variabili specifiche dei plugin

Nella configurazione proposta si ipotizza che ciascun plugin abbia una directory
dedicata al di sotto di una directory comune che contiene le directory di tutti
i plugin.

- `$PYGEOAPI_BASE_PRIVATE_DIRECTORY$`  
  Directory padre di tutte le directory private dei plugin  
  (es. `/custom_process_dir`)

- `$<SERVICE_ID>_SERVICE_ID$`  
  Directory specifica del servizio offerto dal plugin  
  (es. `solwcad`)

- `$<SERVICE_ID>_URL_BASE$`  
  URL del servizio specifico  
  (es. `http://127.0.0.1:5001`)

