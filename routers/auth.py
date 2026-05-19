from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Patient, Doctor
from schemas.schemas import DoctorCreate, Login, PatientLogin
from core.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@router.post("/register/doctor")
def register_doctor(doctor: DoctorCreate, db: Session = Depends(get_db)):
    existing = db.query(Doctor).filter(Doctor.email == doctor.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_doctor = Doctor(
        name=doctor.name,
        email=doctor.email,
        password=hash_password(doctor.password),
        specialty=doctor.specialty,
        phone=doctor.phone,
        hospital=doctor.hospital,
        license_number=doctor.license_number,
    )

    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return {"message": "Doctor registered successfully", "doctor_id": db_doctor.id}
@router.post("/login/doctor")
def login_doctor(credentials: Login, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.email == credentials.email).first()

    if not doctor or not verify_password(credentials.password, doctor.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({"sub": str(doctor.id), "role": "doctor"})
    return {"access_token": token, "token_type": "bearer", "role": "doctor"}

@router.post("/login/patient")
def login_patient(credentials: PatientLogin, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_code == credentials.patient_code).first()

    if not patient or not verify_password(credentials.password, patient.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid patient code or password"
        )

    token = create_access_token({"sub": str(patient.id), "role": "patient"})
    return {"access_token": token, "token_type": "bearer", "role": "patient"}