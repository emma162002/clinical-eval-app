# clinical-eval-app (DECIPHER-M)

Deploying multimodal foundation models in clinical oncology requires structured human feedback at scale. Radiologists' time is scarce, so collecting high-quality preference data must be frictionless. This application is a data-collection frontend for that pipeline: it lets clinicians evaluate model-drafted radiology reports side by side, express structured preferences, flag errors, and annotate images — while giving study coordinators real-time visibility into annotation coverage, inter-annotator agreement, and data quality. The resulting signals (pairwise preferences, quality ratings, error categories, ROI annotations) are designed to feed directly into preference optimisation pipelines such as DPO or RLHF.

Web app for **clinical evaluation of AI model outputs** (e.g. radiology report drafts). Clinicians rate and compare model responses per case; admins view progress, agreement, and data quality.

## How it works

- **Doctors** log in, open cases, and for each case see a clinical prompt and two (or more) model outputs (text ± image). They rate quality, accuracy, completeness, and safety, flag issues (e.g. hallucination, safety concern), choose a preferred output, and can optionally draw ROIs on images. Submissions appear under “My activity”.
- **Admin** has a dashboard (overview and per-case/model stats), progress by annotator, data quality and agreement metrics, ROI overlap summary, help-desk inbox, and model management. Data is stored in SQLite.

**Default logins (from seed):**  
Doctors: `doctor1` / `doctor2` / `doctor3` with password `doctor123`.  
Admin: `admin` / `admin123`.

## Architecture overview

- **Backend:** FastAPI; session-based auth (Doctor / Admin). Data layer: SQLModel (SQLite), single DB file at `data/app.db`.
- **Main modules:** `app/main.py` (routes, auth, admin logic), `app/models.py` (User, Case, ModelOutput, Evaluation, EvaluationROI, HelpRequest, RegisteredModel), `app/seed.py` (creates default users and sample cases on first run), `app/auth.py` (password hashing), `app/database.py` (engine, `init_db`).
- **Frontend:** Jinja2 templates in `app/templates/` (Tailwind CSS), static files in `app/static/`.
- **Docker:** `Dockerfile` (Python 3.11-slim, uvicorn on port 8000); `docker-compose.yml` builds the app and exposes 8000, mounts `./data` for the DB.

## Sample data

Sample data is created **automatically on first run** (no extra files to download). The seed (`app/seed.py`) runs at startup and, if the DB is empty:

- **Users:** 3 doctors (`doctor1`, `doctor2`, `doctor3`) and 1 admin (`admin`), all with password `doctor123` / `admin123`.
- **Cases:** 2 clinical cases with prompts and 2 model outputs each (e.g. CT chest lung nodule, Brain MRI stroke). Images use public-domain URLs or local placeholders.

So after `docker-compose up --build`, open http://localhost:8000 and log in with the credentials above to use the app with sample data.

## Features

**Doctor**
- Case list with clinical prompts; open a case to see model outputs (text + optional image).
- Rate each output: overall quality, clinical accuracy, completeness, safety (1–5).
- Flag issues: hallucination, missing important findings, formatting/structure issues, safety concern.
- Choose preferred output per case; optional free-text feedback.
- Optional ROI drawing on images (one ROI per output, saved for agreement/overlap analysis).
- My activity: view past submissions and ratings by case.
- Profile, help desk (submit and view tickets).

**Admin**
- Dashboard: total cases, evaluations, annotators; per-case and per-model summary (counts, average scores, preferred counts).
- Progress: completion and evaluation counts per annotator and per model.
- Data quality: score distributions and error-flag counts per model.
- Agreement: per-output mean/variance, pairwise Cohen's Kappa on quality ratings, per-case preferred-output agreement.
- ROI overlap: bounding-box IoU between each doctor's drawn ROI and the model's predicted region.
- Data export: download all evaluations as CSV for downstream analysis.
- Help desk: inbox and model management.

## Running the app

The app is containerized with Docker Compose. Run `docker compose up` (or `docker-compose up --build`) and open **http://localhost:8000** to see a working interface with sample data immediately.

```bash
# Replace with the folder where you cloned or extracted the repo (e.g. cd ~/Downloads/clinical-eval-app)
cd /path/to/clinical-eval-app
docker compose up --build
```
Then open in your browser: **http://localhost:8000**