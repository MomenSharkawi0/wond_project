from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Appointment, Patient, Doctor
from schemas.schemas import AppointmentCreate, AppointmentOut
from core.auth import doctor_only

router = APIRouter(prefix="/appointments", tags=["appointments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== Create appointment =====
@router.post("/", response_model=AppointmentOut)
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db), token=Depends(doctor_only)):
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    db_appointment = Appointment(**appointment.dict())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

# ===== Get all appointments =====
@router.get("/", response_model=list[AppointmentOut])
def get_appointments(db: Session = Depends(get_db), token=Depends(doctor_only)):
    return db.query(Appointment).all()

# ===== Get appointments for specific doctor =====
@router.get("/doctor/{doctor_id}", response_model=list[AppointmentOut])
def get_doctor_appointments(doctor_id: int, db: Session = Depends(get_db), token=Depends(doctor_only)):
    return db.query(Appointment).filter(Appointment.doctor_id == doctor_id).all()

# ===== Update appointment status =====
@router.put("/status/{appointment_id}")
def update_status(appointment_id: int, status: str, db: Session = Depends(get_db), token=Depends(doctor_only)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if status not in ["waiting", "next", "done"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    appointment.status = status
    db.commit()
    return {"message": "Status updated successfully"}

# ===== Delete appointment =====
@router.delete("/{appointment_id}")
def delete_appointment(appointment_id: int, db: Session = Depends(get_db), token=Depends(doctor_only)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    db.delete(appointment)
    db.commit()
    return {"message": "Appointment deleted successfully"}