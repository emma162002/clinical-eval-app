# clinical-eval-app (DECIPHER-M)

## Avviare l'app

**Con Docker (consigliato):**
```bash
docker-compose up --build
```
Poi apri nel browser: **http://localhost:8000**

**Senza Docker:**
```bash
cd "/Users/emmabattaglia/Documents/PhD apllication TUM"
python -m venv .venv
source .venv/bin/activate   # su Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Poi apri: **http://127.0.0.1:8000**

## Se l'app non si apre nel browser

1. **Controlla che il server sia partito**  
   In terminale non devono esserci errori; dovresti vedere qualcosa tipo:  
   `Uvicorn running on http://0.0.0.0:8000` (Docker) o `http://127.0.0.1:8000` (uvicorn).

2. **Usa l’URL giusto**  
   - Con Docker: **http://localhost:8000**  
   - Con uvicorn in locale: **http://127.0.0.1:8000**

3. **Se hai aggiornato il codice e prima funzionava**  
   Il database potrebbe essere vecchio (schema senza varianti). Prova:
   - Elimina il file del DB: `rm -f data/app.db` (nella cartella del progetto).
   - Riavvia l’app (Docker: `docker-compose up --build` oppure di nuovo `uvicorn ...`).  
   All’avvio verrà creato un nuovo DB con i dati di esempio.

4. **Se usi Docker**  
   Ricostruisci e riavvia:  
   `docker-compose down && docker-compose up -d --build`  
   Poi verifica che il container sia attivo:  
   `docker-compose ps`
