from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Patient, RiskHistory
from schemas.schemas import PatientOut, RiskHistoryOut
from core.auth import doctor_only

router = APIRouter(prefix="/doctor", tags=["doctor"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== Get all patients =====
@router.get("/patients", response_model=list[PatientOut])
def get_patients(db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    return db.query(Patient).filter(Patient.doctor_id == current_doctor.id).all()

# ===== Get specific patient =====
@router.get("/patient/{p_id}", response_model=PatientOut)
def get_patient(
    p_id: int,
    db: Session = Depends(get_db),
    current_doctor=Depends(doctor_only)
):
    patient = db.query(Patient).filter(
        Patient.id == p_id,
        Patient.doctor_id == current_doctor.id
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient

# ===== Get AI prediction for specific patient =====
@router.get("/predict/{p_id}")
def get_predict(p_id: int, db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    patient = db.query(Patient).filter(
        Patient.id == p_id,
        Patient.doctor_id == current_doctor.id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"p_id": p_id, "risk": patient.risk}

# ===== Get risk history for specific patient =====
@router.get("/risk/history/{p_id}", response_model=list[RiskHistoryOut])
def get_risk_history(p_id: int, db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    patient = db.query(Patient).filter(
        Patient.id == p_id,
        Patient.doctor_id == current_doctor.id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db.query(RiskHistory).filter(RiskHistory.patient_id == p_id).all()
