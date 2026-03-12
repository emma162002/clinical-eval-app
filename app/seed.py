from sqlmodel import Session, select

from .auth import hash_password
from .models import Case, ModelOutput, User


SAMPLE_CASES = [
    {
        "title": "CT chest – lung nodule follow-up",
        "clinical_prompt": (
            "Compare current CT chest with prior study from 12 months ago. "
            "Assess for interval change in size or character of the right upper lobe pulmonary nodule. "
            "Comment on any new nodules or lymphadenopathy."
        ),
        "outputs": [
            {
                "model_name": "Model A",
                "text_output": (
                    "There is a 7 mm solid nodule in the right upper lobe, unchanged in size compared "
                    "to prior exam. No new pulmonary nodules are identified. No mediastinal or hilar "
                    "lymphadenopathy. No pleural effusion. Findings are compatible with benign-appearing "
                    "stable nodule."
                ),
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/fc/Chest_X-ray.jpg",
            },
            {
                "model_name": "Model B",
                "text_output": (
                    "Right upper lobe nodule has increased from 7 mm to 11 mm compared with prior exam. "
                    "Multiple new bilateral pulmonary nodules are present. There is bulky mediastinal "
                    "lymphadenopathy. Overall findings are suspicious for metastatic disease."
                ),
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/fc/Chest_X-ray.jpg",
            },
        ],
    },
    {
        "title": "Brain MRI – acute stroke query",
        "clinical_prompt": (
            "Evaluate for acute ischemic stroke in a 72-year-old with left-sided weakness. "
            "Comment on diffusion restriction, hemorrhage, and large vessel occlusion stigmata."
        ),
        "outputs": [
            {
                "model_name": "Model C",
                "text_output": (
                    "There is restricted diffusion in the right MCA territory involving the frontal and "
                    "parietal lobes, consistent with acute ischemic infarct. No evidence of hemorrhagic "
                    "transformation. No significant mass effect or midline shift."
                ),
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/MRI_brain.jpg",
            },
            {
                "model_name": "Model D",
                "text_output": (
                    "Normal MRI of the brain without evidence of acute infarction, hemorrhage, or mass. "
                    "Ventricles and sulci are normal for age."
                ),
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/MRI_brain.jpg",
            },
        ],
    },
]


def seed_if_empty(session: Session) -> None:
    # Seed default users (doctors, technician and admin) if none exist
    if session.exec(select(User)).first() is None:
        # Three doctor accounts
        session.add(
            User(
                username="doctor1",
                password_hash=hash_password("doctor123"),
                role="doctor",
            )
        )
        session.add(
            User(
                username="doctor2",
                password_hash=hash_password("doctor123"),
                role="doctor",
            )
        )
        session.add(
            User(
                username="doctor3",
                password_hash=hash_password("doctor123"),
                role="doctor",
            )
        )
        # One technician account
        session.add(
            User(
                username="technician",
                password_hash=hash_password("technician123"),
                role="technician",
            )
        )
        # One admin account
        session.add(
            User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
        )
        session.flush()

    existing = session.exec(select(Case)).first()
    if existing:
        return

    for case_data in SAMPLE_CASES:
        case = Case(
            title=case_data["title"],
            clinical_prompt=case_data["clinical_prompt"],
            modality="text+image",
        )
        session.add(case)
        session.flush()
        for out in case_data["outputs"]:
            session.add(
                ModelOutput(
                    case_id=case.id,
                    model_name=out["model_name"],
                    text_output=out["text_output"],
                    image_url=out.get("image_url"),
                )
            )
    session.commit()

