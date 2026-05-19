from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Patient, RiskHistory
from schemas.schemas import PatientCreate, PatientOut
from core.auth import doctor_only, patient_only, hash_password

router = APIRouter(prefix="/patient", tags=["patient"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/all")
def get_patients(db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    return db.query(Patient).filter(Patient.doctor_id == current_doctor.id).all()

@router.post("/add")
def add_patient(patient: PatientCreate, db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    db_patient = Patient(
        p_name=patient.p_name,
        email=patient.email,
        password=hash_password(patient.password),
        age=patient.age,
        gender=patient.gender,
        medical_history=patient.medical_history,
        doctor_id=current_doctor.id
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return {
        "message": "Patient added successfully",
        "patient_code": db_patient.patient_code
    }

@router.delete("/delete/{p_id}")
def delete_patient(p_id: int, db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    patient = db.query(Patient).filter(Patient.id == p_id, Patient.doctor_id == current_doctor.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}

@router.put("/risk/{p_id}")
def update_risk(p_id: int, risk: int, db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    patient = db.query(Patient).filter(Patient.id == p_id, Patient.doctor_id == current_doctor.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.risk = risk
    history = RiskHistory(patient_id=p_id, risk=risk)
    db.add(history)
    db.commit()
    return {"message": "Risk updated successfully"}

@router.get("/risk/history/{p_id}")
def get_risk_history(p_id: int, db: Session = Depends(get_db), current_doctor=Depends(doctor_only)):
    patient = db.query(Patient).filter(Patient.id == p_id, Patient.doctor_id == current_doctor.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = db.query(RiskHistory).filter(RiskHistory.patient_id == p_id).all()
    return history

@router.get("/me", response_model=PatientOut)
def get_my_data(db: Session = Depends(get_db), current_patient=Depends(patient_only)):
    patient = db.query(Patient).filter(Patient.id == current_patient.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient