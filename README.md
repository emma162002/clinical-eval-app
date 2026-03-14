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

## Evaluation protocol & design rationale

### Why pairwise comparison, not just ratings

Absolute rating scales (1–5) are notoriously sensitive to inter-annotator scale bias: one radiologist's "4" is another's "2". Pairwise preference ("which output would you sign as the final report?") is more reliable because it is a relative judgement that does not require calibration across annotators. Crucially, it maps directly onto the data format required by **Direct Preference Optimisation (DPO)**: each submitted evaluation produces a `(prompt, chosen, rejected)` triple that can be fed into a DPO training loop without any additional preprocessing.

The four rating dimensions — overall quality, clinical accuracy, completeness, and safety — are collected alongside the preference because they decompose the preference signal into interpretable axes. A model may be preferred overall while still hallucinating findings or omitting safety-relevant observations; the dimensional scores and error flags capture this nuance and enable targeted fine-tuning.

### Error flags as categorical signals

Binary flags (hallucination, missing important findings, formatting issues, safety concern) complement ordinal ratings by identifying *failure modes* rather than just severity. These can be used to filter training data (e.g. exclude hallucinated outputs from the preferred set) or to train a reward model that penalises specific error types independently of overall quality.

### Session-based round system

Each login session is treated as an independent annotation round. When a clinician completes all cases in their current batch, the system automatically generates a new round by copying the template cases with a round counter appended to the title (e.g. "CT chest – lung nodule follow-up (#2)"). This design serves two purposes:

1. **Intra-annotator consistency**: repeated evaluations of the same underlying case across sessions allow measurement of how stable a clinician's preferences are over time, which is a proxy for annotation reliability.
2. **Data accumulation without fatigue**: clinicians always have a manageable, bounded set of cases to evaluate (one batch = 6 cases), and the system scales data collection naturally across many sessions without requiring new content.

### Inter-annotator agreement metrics

The admin dashboard computes two complementary agreement metrics:

- **Variance of quality ratings per output**: a low-overhead indicator of disagreement. High variance on a specific output signals that clinicians interpret it very differently, which is itself a finding (the output may be ambiguous or context-dependent).
- **Pairwise Cohen's Kappa (unweighted)**: computed for each pair of annotators who have rated at least two common outputs. Kappa corrects for chance agreement, making it the standard metric in clinical annotation studies (κ > 0.6 = substantial, κ > 0.4 = moderate). Pairwise rather than multi-rater kappa is used here because the annotator pool is sparse (not all clinicians rate all outputs), which is the typical constraint in real consortium studies.

### ROI spatial agreement

Clinicians can draw freehand region-of-interest (ROI) annotations on case images. The bounding-box Intersection over Union (IoU) between each clinician's ROI and the model's predicted region (a fixed mock polygon per model, representing where the model "attended") is computed and displayed per output. IoU = intersection area / union area of the two bounding boxes, derived from the normalised polygon coordinates stored in the database. In a production system, the model ROI would be derived from attention maps or segmentation outputs; the mock polygon here is a structural placeholder that keeps the geometric computation real.

### Data export

All evaluation data (ratings, flags, preferences, timestamps) can be downloaded as CSV from the admin dashboard. The export is structured to be immediately usable for preference optimisation: one row per model output evaluation, with the `preferred_for_case` column directly encoding the chosen/rejected label for DPO.

## Sample data

Sample data is created **automatically on first run** (no extra files to download). The seed (`app/seed.py`) runs at startup and, if the DB is empty:

- **Users:** 3 doctors (`doctor1`, `doctor2`, `doctor3`) and 1 admin (`admin`), all with password `doctor123` / `admin123`.
- **Cases:** 6 clinical cases across different modalities and pathologies (CT chest nodule, brain MRI stroke, chest X-ray pneumonia, abdominal CT liver lesion, knee MRI meniscus, mammography mass), each with 2 model outputs of contrasting quality to make evaluation meaningful.

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