import os
from pathlib import Path
from typing import Annotated
from datetime import datetime

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from starlette.middleware.sessions import SessionMiddleware

from .auth import verify_password
from .database import engine, get_session, init_db
from .models import (
    Case,
    Evaluation,
    EvaluationROI,
    HelpRequest,
    ModelOutput,
    RegisteredModel,
    User,
)
from .seed import seed_if_empty


BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# Direct Wikipedia Commons URLs (public domain) – used when local JPGs are not present
CHEST_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/f/fc/Chest_X-ray.jpg"
BRAIN_MRI_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3c/MRI_brain_-_stroke_-_diffusion_weighted.jpg"

app = FastAPI(title="Clinical Model Evaluation")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


@app.on_event("startup")
def on_startup() -> None:
    import traceback
    try:
        init_db()
        with Session(engine) as session:
            seed_if_empty(session)
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Startup failed: {e}") from e


SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(request: Request, session: SessionDep) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return session.get(User, user_id)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: SessionDep):
    # Always start from a fresh session and show the entry screen,
    # so that pasting the link in the browser brings you to login.
    request.session.clear()
    return templates.TemplateResponse(
        "role_selection.html", {"request": request}
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, role: str = ""):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "role": role or "doctor"},
    )


@app.post("/login")
async def login(
    request: Request,
    session: SessionDep,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    if role not in ("doctor", "technician", "admin"):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "role": "doctor", "error": "Invalid role."},
        )
    user = session.exec(
        select(User).where(User.username == username, User.role == role)
    ).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "role": role, "error": "Invalid username or password."},
        )
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["username"] = user.username
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/home", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


@app.get("/home", response_class=HTMLResponse)
def home(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=302)
    total_cases = session.exec(select(func.count(Case.id))).one()
    user_evals = session.exec(
        select(func.count(Evaluation.id)).where(Evaluation.annotator_id == user.username)
    ).one()
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "current_user": user,
            "total_cases": total_cases,
            "user_evaluations_count": user_evals,
        },
    )


@app.get("/evaluation", response_class=HTMLResponse)
def evaluation_list(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    cases = session.exec(select(Case).order_by(Case.id)).all()
    return templates.TemplateResponse(
        "evaluation_list.html",
        {"request": request, "current_user": user, "cases": cases},
    )


@app.get("/evaluation/cases/{case_id}", response_class=HTMLResponse)
def view_case(case_id: int, request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    case = session.get(Case, case_id)
    if not case:
        return HTMLResponse("Case not found", status_code=404)

    # A case is considered completed only within the current session,
    # so that logging out and logging in again allows a fresh evaluation.
    completed_cases = request.session.get("completed_cases", [])
    completed = case_id in completed_cases

    next_case = (
        session.exec(
            select(Case).where(Case.id > case_id).order_by(Case.id)
        ).first()
    )

    return templates.TemplateResponse(
        "case.html",
        {
            "request": request,
            "case": case,
            "outputs": case.outputs,
            "next_case": next_case,
            "current_user": user,
            "completed": completed,
        },
    )


@app.post("/evaluation/cases/{case_id}/submit")
async def submit_case_evaluations(
    case_id: int,
    request: Request,
    session: SessionDep,
):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    form = await request.form()
    annotator_id = form.get("annotator_id") or user.username or ""

    case = session.get(Case, case_id)
    if not case:
        return HTMLResponse("Case not found", status_code=404)

    preferred_output_id_raw = form.get("preferred_output_id")
    preferred_output_id = int(preferred_output_id_raw) if preferred_output_id_raw else None

    for output in case.outputs:
        prefix = f"output_{output.id}_"
        overall_quality = int(form.get(prefix + "overall_quality", "0"))
        clinical_accuracy = int(form.get(prefix + "clinical_accuracy", "0"))
        completeness = int(form.get(prefix + "completeness", "0"))
        safety = int(form.get(prefix + "safety", "0"))

        evaluation = Evaluation(
            output_id=output.id,
            user_id=user.id,
            annotator_id=annotator_id,
            overall_quality=overall_quality,
            clinical_accuracy=clinical_accuracy,
            completeness=completeness,
            safety=safety,
            preferred_for_case=preferred_output_id == output.id,
            hallucination=prefix + "hallucination" in form,
            missing_important_findings=prefix + "missing_important_findings" in form,
            formatting_issues=prefix + "formatting_issues" in form,
            safety_concerns=prefix + "safety_concerns" in form,
            free_text_feedback=form.get(prefix + "free_text_feedback") or None,
        )
        session.add(evaluation)

    session.commit()

    # Mark this case as completed only for the current session
    completed_cases = request.session.get("completed_cases", [])
    if case_id not in completed_cases:
        completed_cases.append(case_id)
    request.session["completed_cases"] = completed_cases

    next_case = (
        session.exec(
            select(Case).where(Case.id > case_id).order_by(Case.id)
        ).first()
    )
    if next_case:
        return RedirectResponse(
            url=f"/evaluation/cases/{next_case.id}", status_code=303
        )
    return RedirectResponse(url="/thanks", status_code=303)


@app.get("/activity", response_class=HTMLResponse)
def my_activity(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    evals = session.exec(
        select(Evaluation)
        .where(Evaluation.annotator_id == user.username)
        .order_by(Evaluation.created_at.desc())
    ).all()
    # Group evaluations by case so that in the template we can show
    # side-by-side comparison of model outputs per case without complex Jinja logic.
    case_groups = []
    seen = {}
    for e in evals:
        if not e.output or not e.output.case:
            continue
        cid = e.output.case.id
        if cid not in seen:
            seen[cid] = {
                "case": e.output.case,
                "evaluations": [],
                "latest_at": e.created_at,
            }
            case_groups.append(seen[cid])
        group = seen[cid]
        group["evaluations"].append(e)
        if e.created_at and (group["latest_at"] is None or e.created_at > group["latest_at"]):
            group["latest_at"] = e.created_at
    case_groups.sort(key=lambda g: g["latest_at"] or datetime.min, reverse=True)
    return templates.TemplateResponse(
        "activity.html",
        {"request": request, "current_user": user, "case_groups": case_groups},
    )

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "current_user": user},
    )


@app.post("/profile")
async def update_profile(
    request: Request,
    session: SessionDep,
    full_name: str = Form(""),
    email: str = Form(""),
    institution: str = Form(""),
    notes: str = Form(""),
):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    user.full_name = full_name or None
    user.email = email or None
    user.institution = institution or None
    user.notes = notes or None
    session.add(user)
    session.commit()
    # After saving the profile, send the clinician back to case selection
    return RedirectResponse(url="/evaluation", status_code=303)


@app.get("/thanks", response_class=HTMLResponse)
def thanks(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    return templates.TemplateResponse(
        "thanks.html", {"request": request, "current_user": user}
    )


@app.get("/help", response_class=HTMLResponse)
def help_entry(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    if user.role == "technician":
        return RedirectResponse(url="/help/inbox", status_code=302)
    return RedirectResponse(url="/help/my", status_code=302)


@app.get("/help/new", response_class=HTMLResponse)
def help_new(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    return templates.TemplateResponse(
        "help/new.html",
        {"request": request, "current_user": user},
    )


@app.post("/help/new")
async def help_create(
    request: Request,
    session: SessionDep,
    subject: str = Form(...),
    question: str = Form(...),
):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    ticket = HelpRequest(
        from_user_id=user.id,
        to_role="technician",
        subject=subject,
        question=question,
        status="open",
    )
    session.add(ticket)
    session.commit()
    return RedirectResponse(url="/help/my", status_code=303)


@app.get("/help/my", response_class=HTMLResponse)
def help_my(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    tickets = session.exec(
        select(HelpRequest)
        .where(HelpRequest.from_user_id == user.id)
        .order_by(HelpRequest.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        "help/my.html",
        {"request": request, "current_user": user, "tickets": tickets},
    )


@app.get("/help/inbox", response_class=HTMLResponse)
def help_inbox(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=technician", status_code=302)
    if user.role != "technician":
        return RedirectResponse(url="/home", status_code=302)
    tickets = session.exec(
        select(HelpRequest)
        .where(HelpRequest.to_role == "technician")
        .order_by(HelpRequest.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        "help/inbox.html",
        {"request": request, "current_user": user, "tickets": tickets},
    )


@app.get("/technician/models", response_class=HTMLResponse)
def technician_models(request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None or user.role != "technician":
        return RedirectResponse(url="/login?role=technician", status_code=302)
    models = session.exec(
        select(RegisteredModel).order_by(RegisteredModel.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        "technician/models.html",
        {"request": request, "current_user": user, "models": models},
    )


@app.post("/technician/models")
async def technician_add_model(
    request: Request,
    session: SessionDep,
    name: str = Form(...),
    version: str = Form(""),
    description: str = Form(""),
):
    user = get_current_user(request, session)
    if user is None or user.role != "technician":
        return RedirectResponse(url="/login?role=technician", status_code=302)
    model = RegisteredModel(
        name=name,
        version=version or None,
        description=description or None,
        created_by_id=user.id,
    )
    session.add(model)
    session.commit()
    return RedirectResponse(url="/technician/models", status_code=303)


@app.get("/help/{ticket_id}", response_class=HTMLResponse)
def help_detail(ticket_id: int, request: Request, session: SessionDep):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=technician", status_code=302)
    ticket = session.get(HelpRequest, ticket_id)
    if not ticket:
        return HTMLResponse("Ticket not found", status_code=404)
    if user.role != "technician" and ticket.from_user_id != user.id:
        return HTMLResponse("Not allowed", status_code=403)
    return templates.TemplateResponse(
        "help/detail.html",
        {"request": request, "current_user": user, "ticket": ticket},
    )


@app.post("/help/{ticket_id}/answer")
async def help_answer(
    ticket_id: int,
    request: Request,
    session: SessionDep,
    answer: str = Form(...),
):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=technician", status_code=302)
    if user.role != "technician":
        return HTMLResponse("Only technicians can answer tickets", status_code=403)
    ticket = session.get(HelpRequest, ticket_id)
    if not ticket:
        return HTMLResponse("Ticket not found", status_code=404)
    ticket.answer = answer
    ticket.status = "answered"
    ticket.answered_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    return RedirectResponse(url="/help/inbox", status_code=303)

def require_admin(request: Request, session: SessionDep) -> User | None:
    user = get_current_user(request, session)
    if user is None or user.role != "admin":
        return None
    return user


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, session: SessionDep):
    user = require_admin(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=admin", status_code=302)
    total_cases = session.exec(select(func.count(Case.id))).one()
    total_evals = session.exec(select(func.count(Evaluation.id))).one()
    # Count distinct doctor users who have submitted at least one evaluation
    doctor_ids = session.exec(
        select(User.id)
        .join(Evaluation, Evaluation.user_id == User.id)
        .where(User.role == "doctor")
        .distinct()
    ).all()
    annotator_count = len(doctor_ids)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": user,
            "total_cases": total_cases,
            "total_evaluations": total_evals,
            "annotator_count": annotator_count,
        },
    )


@app.get("/admin/progress", response_class=HTMLResponse)
def admin_progress(request: Request, session: SessionDep):
    user = require_admin(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=admin", status_code=302)
    # Per-annotator: how many case evaluations (one case = 2 evals for 2 outputs)
    rows = session.exec(
        select(Evaluation.annotator_id, func.count(Evaluation.id).label("cnt"))
        .group_by(Evaluation.annotator_id)
    ).all()
    progress = [{"annotator_id": r[0], "evaluations_count": r[1]} for r in rows]
    total_cases = session.exec(select(func.count(Case.id))).one()
    return templates.TemplateResponse(
        "admin/progress.html",
        {
            "request": request,
            "current_user": user,
            "progress": progress,
            "total_cases": total_cases,
        },
    )


@app.get("/admin/annotators", response_class=HTMLResponse)
def admin_annotators(request: Request, session: SessionDep):
    user = require_admin(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=admin", status_code=302)
    rows = session.exec(
        select(
            Evaluation.annotator_id,
            func.count(Evaluation.id).label("cnt"),
            func.min(Evaluation.created_at).label("first_at"),
            func.max(Evaluation.created_at).label("last_at"),
        ).group_by(Evaluation.annotator_id)
    ).all()
    annotators = [
        {
            "annotator_id": r[0],
            "evaluations_count": r[1],
            "first_at": r[2],
            "last_at": r[3],
        }
        for r in rows
    ]
    return templates.TemplateResponse(
        "admin/annotators.html",
        {
            "request": request,
            "current_user": user,
            "annotators": annotators,
        },
    )


@app.get("/admin/quality", response_class=HTMLResponse)
def admin_quality(request: Request, session: SessionDep):
    user = require_admin(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=admin", status_code=302)
    evals = session.exec(select(Evaluation).join(ModelOutput)).all()
    # Per-model distributions for all 4 rating dimensions and error flags
    per_model: dict[str, dict] = {}
    for e in evals:
        model_name = e.output.model_name if e.output else "Unknown"
        if model_name not in per_model:
            per_model[model_name] = {
                "overall": {},
                "accuracy": {},
                "completeness": {},
                "safety": {},
                "count": 0,
                "flags": {
                    "hallucination": 0,
                    "missing_findings": 0,
                    "formatting": 0,
                    "safety_concerns": 0,
                },
            }
        m = per_model[model_name]
        m["overall"][e.overall_quality] = m["overall"].get(e.overall_quality, 0) + 1
        m["accuracy"][e.clinical_accuracy] = m["accuracy"].get(e.clinical_accuracy, 0) + 1
        m["completeness"][e.completeness] = m["completeness"].get(e.completeness, 0) + 1
        m["safety"][e.safety] = m["safety"].get(e.safety, 0) + 1
        m["count"] += 1
        if e.hallucination:
            m["flags"]["hallucination"] += 1
        if e.missing_important_findings:
            m["flags"]["missing_findings"] += 1
        if e.formatting_issues:
            m["flags"]["formatting"] += 1
        if e.safety_concerns:
            m["flags"]["safety_concerns"] += 1
    flags = {
        "hallucination": sum(1 for e in evals if e.hallucination),
        "missing_findings": sum(1 for e in evals if e.missing_important_findings),
        "formatting": sum(1 for e in evals if e.formatting_issues),
        "safety_concerns": sum(1 for e in evals if e.safety_concerns),
    }
    return templates.TemplateResponse(
        "admin/quality.html",
        {
            "request": request,
            "current_user": user,
            "per_model": per_model,
            "flags": flags,
            "total": len(evals),
        },
    )


def _compute_agreement(session: Session) -> list[dict]:
    """Per-case and per-output agreement metrics."""
    cases = session.exec(select(Case).order_by(Case.id)).all()
    result = []
    for case in cases:
        for out in case.outputs:
            evals = session.exec(
                select(Evaluation).where(Evaluation.output_id == out.id)
            ).all()
            if len(evals) < 2:
                continue
            qualities = [e.overall_quality for e in evals]
            preferred = sum(1 for e in evals if e.preferred_for_case)
            mean_q = sum(qualities) / len(qualities)
            variance = sum((q - mean_q) ** 2 for q in qualities) / len(qualities) if qualities else 0
            # Simple agreement: % within 1 point of mean
            within_one = sum(1 for q in qualities if abs(q - mean_q) <= 1)
            result.append({
                "case_id": case.id,
                "case_title": case.title,
                "output_id": out.id,
                "model_name": out.model_name,
                "n_annotators": len(evals),
                "mean_quality": round(mean_q, 2),
                "variance": round(variance, 2),
                "pct_within_one": round(100 * within_one / len(qualities), 1),
                "preferred_count": preferred,
            })
    return result


@app.get("/admin/agreement", response_class=HTMLResponse)
def admin_agreement(request: Request, session: SessionDep):
    user = require_admin(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=admin", status_code=302)
    agreement = _compute_agreement(session)
    # Per-case preferred output agreement
    cases = session.exec(select(Case).order_by(Case.id)).all()
    case_preferred = []
    for case in cases:
        outputs = list(case.outputs)
        if len(outputs) != 2:
            continue
        # For each annotator we need their preferred output for this case: from evaluations with preferred_for_case=True
        evals_a = session.exec(select(Evaluation).where(Evaluation.output_id == outputs[0].id)).all()
        evals_b = session.exec(select(Evaluation).where(Evaluation.output_id == outputs[1].id)).all()
        annotators_a = {e.annotator_id for e in evals_a if e.preferred_for_case}
        annotators_b = {e.annotator_id for e in evals_b if e.preferred_for_case}
        # Count how many chose A vs B (each annotator appears in one of the two)
        n_a = len(annotators_a)
        n_b = len(annotators_b)
        total = n_a + n_b
        if total >= 2:
            pct_agree = 100 * max(n_a, n_b) / total
            case_preferred.append({
                "case_id": case.id,
                "case_title": case.title,
                "n_annotators": total,
                "preferred_a": n_a,
                "preferred_b": n_b,
                "pct_agreement": round(pct_agree, 1),
            })
    return templates.TemplateResponse(
        "admin/agreement.html",
        {
            "request": request,
            "current_user": user,
            "agreement": agreement,
            "case_preferred": case_preferred,
        },
    )


@app.post("/evaluation/cases/{case_id}/roi")
async def save_roi(
    case_id: int,
    request: Request,
    session: SessionDep,
    output_id: int = Form(...),
    points_json: str = Form(...),
):
    user = get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login?role=doctor", status_code=302)
    case = session.get(Case, case_id)
    if not case or not any(o.id == output_id for o in case.outputs):
        return HTMLResponse("Invalid case or output", status_code=400)
    roi = EvaluationROI(
        output_id=output_id,
        user_id=user.id,
        annotator_id=user.username,
        points_json=points_json,
    )
    session.add(roi)
    session.commit()
    # If called via AJAX, return JSON so the evaluation form is not reloaded
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"status": "ok"})
    # Fallback: redirect back to the case page
    return RedirectResponse(
        url=f"/evaluation/cases/{case_id}",
        status_code=303,
    )

