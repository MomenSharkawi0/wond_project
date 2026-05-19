import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Patient, RiskHistory
from core.auth import current_user
from core.ai_service import analyze_wound_image

# Changed prefix to /wound to match your frontend API calls
router = APIRouter(prefix="/wound", tags=["wound_ai"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_and_analyze_wound(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    reference_width_cm: float = Form(15.0),
    db: Session = Depends(get_db),
    user = Depends(current_user),
):
    """
    Receives a wound image, runs AI segmentation, persists a history row.
    - Doctors may upload for any patient they own.
    - Patients may only upload for themselves.
    """
    role, actor = user

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if role == "doctor":
        if patient.doctor_id != actor.id:
            raise HTTPException(status_code=403, detail="Patient is not assigned to you")
    elif role == "patient":
        if patient.id != actor.id:
            raise HTTPException(status_code=403, detail="You can only analyze your own images")

    # 2. Save Image Locally with a unique name to prevent overwriting
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"patient_{patient_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    image_bytes = await file.read()
    
    with open(file_path, "wb") as buffer:
        buffer.write(image_bytes)

    # 3. Run wound segmentation + risk scoring
    try:
        ai_result = analyze_wound_image(
            image_bytes,
            upload_dir=UPLOAD_DIR,
            reference_width_cm=max(1.0, reference_width_cm),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

    risk_score = ai_result["risk_score"]
    severity = ai_result["severity"]
    wound_area = ai_result["wound_area_pixels"]
    coverage = ai_result["coverage"]
    mask_path = ai_result.get("mask_path")
    wound_area_cm2 = ai_result.get("wound_area_cm2", 0.0)
    wound_diameter_cm = ai_result.get("wound_diameter_cm", 0.0)

    # 4. Persist — store the overlay (annotated) image in history so the
    # doctor sees the AI's segmentation, not the raw photo.
    patient.risk = risk_score
    history_record = RiskHistory(
        patient_id=patient.id,
        risk=risk_score,
        image_path=mask_path or file_path.replace("\\", "/"),
    )
    db.add(history_record)
    db.commit()

    return {
        "message": "Image analyzed successfully",
        "image_url": "/" + file_path.replace("\\", "/"),
        "mask_url": ("/" + mask_path) if mask_path else None,
        "segmentation": {
            "severity": severity,
            "risk_score": f"{risk_score}%",
            "area_pixels": f"{int(wound_area)} px",
            "area_cm2": f"{wound_area_cm2:.2f} cm²",
            "diameter_cm": f"{wound_diameter_cm:.2f} cm",
            "coverage": f"{coverage * 100:.2f}%",
            "reference_width_cm": f"{reference_width_cm:.1f} cm",
            "type": patient.medical_history or "Unspecified Wound",
        },
    }