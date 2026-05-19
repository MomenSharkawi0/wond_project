from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ===== Patient =====

class PatientCreate(BaseModel):
    p_name: str
    email: EmailStr
    password: str
    age: int
    gender: str
    medical_history: Optional[str] = None

class PatientOut(BaseModel):
    id: int
    patient_code: int
    p_name: str
    email: str
    age: int
    gender: str
    medical_history: Optional[str] = None
    risk: int
    doctor_id: Optional[int] = None

    class Config:
        from_attributes = True

class PatientUpdate(BaseModel):
    p_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None

# ===== Doctor =====

class DoctorCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    specialty: str
    phone: Optional[str] = None
    hospital: Optional[str] = None
    license_number: Optional[str] = None

class DoctorOut(BaseModel):
    id: int
    name: str
    email: str
    specialty: str

    class Config:
        from_attributes = True

# ===== Login =====

class Login(BaseModel):
    email: EmailStr
    password: str

class PatientLogin(BaseModel):
    patient_code: int
    password: str

# ===== RiskHistory =====

class RiskHistoryOut(BaseModel):
    id: int
    patient_id: int
    risk: int
    recorded_at: datetime

    class Config:
        from_attributes = True

# ===== Appointment =====

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: datetime
    notes: Optional[str] = None

class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    date: datetime
    notes: Optional[str] = None
    status: str

    class Config:
        from_attributes = True