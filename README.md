# clinical-eval-app (DECIPHER-M)

Web app for **clinical evaluation of AI model outputs** (e.g. radiology report drafts). Clinicians rate and compare model responses per case; admins view progress, agreement, and data quality.

## How it works

- **Doctors** log in, open cases, and for each case see a clinical prompt and two (or more) model outputs (text ± image). They rate quality, accuracy, completeness, and safety, flag issues (e.g. hallucination, safety concern), choose a preferred output, and can optionally draw ROIs on images. Submissions appear under “My activity”.
- **Admin** has a dashboard (overview and per-case/model stats), progress by annotator, data quality and agreement metrics, ROI overlap summary, help-desk inbox, and model management. Data is stored in SQLite.

**Default logins (from seed):**  
Doctors: `doctor1` / `doctor2` / `doctor3` with password `doctor123`.  
Admin: `admin` / `admin123`.

## Features

**Doctor**
- Case list with clinical prompts; open a case to see model outputs (text + optional image).
- Rate each output: overall quality, clinical accuracy, completeness, safety (0–5).
- Flag issues: hallucination, missing important findings, formatting/structure issues, safety concern.
- Choose preferred output per case; optional free-text feedback.
- Optional ROI drawing on images (one ROI per output, saved for agreement/overlap analysis).
- My activity: view past submissions and ratings by case.
- Profile, help desk (submit and view tickets).

**Admin**
- Dashboard: total cases, evaluations, annotators; per-case and per-model summary (counts, average scores, preferred counts).
- Progress: completion and evaluation counts per annotator and per model.
- Data quality: score distributions and error-flag counts per model.
- Agreement: per-output agreement (mean, variance, preferred count); per-case preferred-output agreement.
- ROI overlap: summary of saved ROIs (e.g. Dice-style placeholder) per case/model/doctor.
- Help desk: inbox and model management.

## Running the app

**With Docker (recommended):**
```bash
# Replace with the folder where you cloned or extracted the repo (e.g. cd ~/Downloads/clinical-eval-app)
cd /path/to/clinical-eval-app
docker-compose up --build
```
Then open in your browser: **http://localhost:8000**

**Without Docker:**
```bash
# Same: use the folder where the project is (e.g. cd ~/clinical-eval-app)
cd /path/to/clinical-eval-app
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Then open: **http://127.0.0.1:8000**

## If the app does not open in the browser

1. **Check that the server is running**  
   There should be no errors in the terminal; you should see something like:  
   `Uvicorn running on http://0.0.0.0:8000` (Docker) or `http://127.0.0.1:8000` (uvicorn).

2. **Use the correct URL**  
   - With Docker: **http://localhost:8000**  
   - With uvicorn locally: **http://127.0.0.1:8000**

3. **If you updated the code and it used to work**  
   The database may be outdated. Try:
   - Delete the DB file: `rm -f data/app.db` (in the project folder).
   - Restart the app (Docker: `docker-compose up --build` or run `uvicorn ...` again).  
   A new database with sample data will be created on startup.

4. **If using Docker**  
   Rebuild and restart:  
   `docker-compose down && docker-compose up -d --build`  
   Then check that the container is running:  
   `docker-compose ps`

## Screenshot

You can add a screenshot (e.g. of the case evaluation or dashboard) by placing an image in the repo (e.g. `docs/screenshot.png`) and adding:

```markdown
![App screenshot](docs/screenshot.png)
```
