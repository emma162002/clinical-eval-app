from sqlmodel import Session, select

from .auth import hash_password
from .models import Case, ModelOutput, User

CHEST_XRAY_URL = "https://upload.wikimedia.org/wikipedia/commons/f/fc/Chest_X-ray.jpg"
BRAIN_MRI_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3b/MRI_brain.jpg"
PNEUMONIA_XRAY_URL = "https://upload.wikimedia.org/wikipedia/commons/5/51/X-ray_of_lobar_pneumonia.jpg"
LIVER_CT_URL = "https://upload.wikimedia.org/wikipedia/commons/1/1f/Hepatomegaly_-_CT_single_angle.jpg"
KNEE_MRI_URL = "https://upload.wikimedia.org/wikipedia/commons/9/9e/MRI_meniscus_tear.jpg"
MAMMO_URL = "https://upload.wikimedia.org/wikipedia/commons/3/35/Mammogram_with_obvious_cancer.jpg"

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
                "image_url": CHEST_XRAY_URL,
            },
            {
                "model_name": "Model B",
                "text_output": (
                    "Right upper lobe nodule has increased from 7 mm to 11 mm compared with prior exam. "
                    "Multiple new bilateral pulmonary nodules are present. There is bulky mediastinal "
                    "lymphadenopathy. Overall findings are suspicious for metastatic disease."
                ),
                "image_url": CHEST_XRAY_URL,
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
                "image_url": BRAIN_MRI_URL,
            },
            {
                "model_name": "Model D",
                "text_output": (
                    "Normal MRI of the brain without evidence of acute infarction, hemorrhage, or mass. "
                    "Ventricles and sulci are normal for age."
                ),
                "image_url": BRAIN_MRI_URL,
            },
        ],
    },
    {
        "title": "Chest X-ray – community-acquired pneumonia",
        "clinical_prompt": (
            "58-year-old male with three-day history of productive cough, fever 38.9°C, and right-sided "
            "pleuritic chest pain. Assess for consolidation, pleural effusion, or other acute findings. "
            "Comment on extent and severity."
        ),
        "outputs": [
            {
                "model_name": "Model A",
                "text_output": (
                    "Dense right lower lobe consolidation with air bronchograms is present, consistent "
                    "with lobar pneumonia. A small right-sided parapneumonic pleural effusion is noted. "
                    "The left lung is clear. No pneumothorax. Heart size is normal. Findings are "
                    "consistent with community-acquired pneumonia; clinical correlation and antibiotic "
                    "therapy are recommended."
                ),
                "image_url": CHEST_XRAY_URL,
            },
            {
                "model_name": "Model B",
                "text_output": (
                    "The lungs appear clear bilaterally. No focal consolidation, pleural effusion, or "
                    "pneumothorax identified. Cardiomediastinal silhouette is within normal limits. "
                    "Bony thorax is intact. No acute cardiopulmonary process."
                ),
                "image_url": PNEUMONIA_XRAY_URL,
            },
        ],
    },
    {
        "title": "Abdominal CT – liver lesion characterisation",
        "clinical_prompt": (
            "65-year-old male with known hepatitis B cirrhosis and rising AFP. Triphasic CT of the "
            "abdomen requested to evaluate a new hepatic lesion identified on surveillance ultrasound. "
            "Characterise the lesion and comment on portal hypertension features."
        ),
        "outputs": [
            {
                "model_name": "Model C",
                "text_output": (
                    "A 3.2 cm arterially enhancing lesion with washout on portal venous phase is "
                    "identified in hepatic segment VI. Enhancement pattern meets LI-RADS 5 criteria "
                    "for hepatocellular carcinoma. Background liver shows coarsened echotexture and "
                    "nodular contour consistent with cirrhosis. Splenomegaly (16 cm) and small volume "
                    "ascites indicate portal hypertension. No vascular invasion or extrahepatic disease. "
                    "Multidisciplinary tumour board review is recommended."
                ),
                "image_url": LIVER_CT_URL,
            },
            {
                "model_name": "Model D",
                "text_output": (
                    "A hypodense lesion is seen in the right lobe of the liver. Enhancement pattern is "
                    "noted. The liver background is abnormal. Spleen is enlarged. Clinical correlation "
                    "is advised. Further imaging may be required."
                ),
                "image_url": LIVER_CT_URL,
            },
        ],
    },
    {
        "title": "Knee MRI – medial meniscus assessment",
        "clinical_prompt": (
            "34-year-old recreational footballer with acute medial knee pain following a twisting "
            "injury three weeks ago. Persistent joint-line tenderness. Evaluate the menisci, "
            "cruciate ligaments, and articular cartilage."
        ),
        "outputs": [
            {
                "model_name": "Model A",
                "text_output": (
                    "There is a complex grade III tear of the posterior horn of the medial meniscus "
                    "extending to the inferior articular surface. The anterior cruciate ligament shows "
                    "increased T2 signal with partial fibre disruption, consistent with a partial ACL "
                    "tear. The lateral meniscus and collateral ligaments are intact. Mild medial "
                    "compartment chondral thinning (ICRS grade II). Small joint effusion. Orthopaedic "
                    "surgical review is recommended."
                ),
                "image_url": KNEE_MRI_URL,
            },
            {
                "model_name": "Model B",
                "text_output": (
                    "There may be some signal change in the posterior horn of the medial meniscus, "
                    "possibly representing degenerative change or a tear. The cruciate ligaments "
                    "appear possibly intact, though evaluation is limited. No large effusion. Clinical "
                    "correlation with physical examination findings is suggested."
                ),
                "image_url": KNEE_MRI_URL,
            },
        ],
    },
    {
        "title": "Mammography – suspicious mass characterisation",
        "clinical_prompt": (
            "52-year-old woman referred with a self-detected lump in the right breast, upper outer "
            "quadrant. No prior mammography on file. Characterise the lesion and provide BI-RADS "
            "assessment with management recommendation."
        ),
        "outputs": [
            {
                "model_name": "Model C",
                "text_output": (
                    "There is an irregular spiculated mass measuring 18 mm in the right breast upper "
                    "outer quadrant at the 10 o'clock position. The mass demonstrates high density and "
                    "associated architectural distortion. No suspicious microcalcifications. No axillary "
                    "lymphadenopathy identified. BI-RADS 4C — high suspicion for malignancy. "
                    "Ultrasound-guided core needle biopsy is recommended."
                ),
                "image_url": MAMMO_URL,
            },
            {
                "model_name": "Model D",
                "text_output": (
                    "An area of increased density is noted in the right breast. The margins are "
                    "difficult to assess on current views. BI-RADS 0 — incomplete assessment. "
                    "Additional imaging views are recommended."
                ),
                "image_url": MAMMO_URL,
            },
        ],
    },
]

# Number of template (seed) cases — used to identify originals when generating new rounds
SEED_CASE_COUNT = len(SAMPLE_CASES)


def seed_if_empty(session: Session) -> None:
    if session.exec(select(User)).first() is None:
        for username in ["doctor1", "doctor2", "doctor3"]:
            session.add(
                User(
                    username=username,
                    password_hash=hash_password("doctor123"),
                    role="doctor",
                )
            )
        session.add(
            User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
        )
        session.flush()

    if session.exec(select(Case)).first() is not None:
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
