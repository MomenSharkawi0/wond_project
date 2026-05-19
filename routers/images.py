import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Patient, RiskHistory
from core.auth import doctor_only
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
    patient_id: int = Form(...), # Expecting patient_id from the frontend form data
    db: Session = Depends(get_db),
    current_doctor = Depends(doctor_only) # Ensuring only authenticated doctors can upload
):
    """
    Receives a wound image, saves it locally, analyzes it using the AI model,
    and updates the patient's risk history in the database.
    """
    # 1. Validate Patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 2. Save Image Locally with a unique name to prevent overwriting
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"patient_{patient_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    image_bytes = await file.read()
    
    with open(file_path, "wb") as buffer:
        buffer.write(image_bytes)

    # 3. Analyze the Image using our AI Engine
    try:
        ai_result = analyze_wound_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

    # Extract results from AI
    risk_score = ai_result["risk_score"]
    severity = ai_result["severity"]
    wound_area = ai_result["wound_area_pixels"]

    # 4. Update Database
    # Update the current risk on the patient profile
    patient.risk = risk_score
    
    # Create a new record in the RiskHistory table
    history_record = RiskHistory(
        patient_id=patient.id,
        risk=risk_score,
        image_path=file_path # Saving the path so we can view it later in the UI
    )
    
    db.add(history_record)
    db.commit()

    # 5. Return structured JSON matching the Frontend expectations
    return {
        "message": "Image analyzed successfully",
        "image_url": f"/{file_path}", # The frontend needs this to display the uploaded image
        "segmentation": {
            "severity": severity,
            "risk_score": f"{risk_score}%",
            "area": f"{wound_area} pixels",
            "type": patient.medical_history or "Unspecified Wound",
            "coverage": f"{(risk_score / 100):.2f} ratio"
        }
    }