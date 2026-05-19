"""Populate the database with demo doctors, patients, appointments, and risk history.

Run from the project root: `python seed.py`
Safe to re-run: existing rows (by email) are skipped, not duplicated.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import Base, engine, SessionLocal
from models.models import Doctor, Patient, RiskHistory, Appointment
from core.auth import hash_password

Base.metadata.create_all(bind=engine)

DOCTORS = [
    {
        "name": "Dr. Ahmed Hassan",
        "email": "ahmed@medaura.com",
        "password": "doctor123",
        "specialty": "Plastic Surgery",
        "phone": "+201001234567",
        "hospital": "Cairo University Hospital",
        "license_number": "MD-EG-10234",
    },
    {
        "name": "Dr. Sara Mahmoud",
        "email": "sara@medaura.com",
        "password": "doctor123",
        "specialty": "Dermatology",
        "phone": "+201007654321",
        "hospital": "Ain Shams Specialized Hospital",
        "license_number": "MD-EG-20871",
    },
]

# Patients are keyed by doctor email so seed is idempotent and predictable.
PATIENTS_BY_DOCTOR = {
    "ahmed@medaura.com": [
        {"p_name": "Ali Mostafa",   "email": "ali@patients.com",   "password": "patient123", "age": 52, "gender": "Male",   "medical_history": "Diabetic foot ulcer", "patient_code": 100001, "risk": 78},
        {"p_name": "Mona Adel",     "email": "mona@patients.com",  "password": "patient123", "age": 34, "gender": "Female", "medical_history": "Post-surgical incision",  "patient_code": 100002, "risk": 35},
        {"p_name": "Khaled Tarek",  "email": "khaled@patients.com","password": "patient123", "age": 67, "gender": "Male",   "medical_history": "Pressure ulcer (stage III)", "patient_code": 100003, "risk": 88},
    ],
    "sara@medaura.com": [
        {"p_name": "Yara Samir",    "email": "yara@patients.com",  "password": "patient123", "age": 29, "gender": "Female", "medical_history": "Burn (second degree)",       "patient_code": 200001, "risk": 55},
        {"p_name": "Hany Nabil",    "email": "hany@patients.com",  "password": "patient123", "age": 45, "gender": "Male",   "medical_history": "Chronic venous ulcer",       "patient_code": 200002, "risk": 42},
    ],
}


def seed():
    db = SessionLocal()
    try:
        # ---- Doctors ----
        doc_by_email = {}
        for d in DOCTORS:
            existing = db.query(Doctor).filter(Doctor.email == d["email"]).first()
            if existing:
                doc_by_email[d["email"]] = existing
                continue
            doc = Doctor(
                name=d["name"], email=d["email"],
                password=hash_password(d["password"]),
                specialty=d["specialty"], phone=d["phone"],
                hospital=d["hospital"], license_number=d["license_number"],
            )
            db.add(doc)
            db.flush()
            doc_by_email[d["email"]] = doc

        # ---- Patients ----
        all_patients = []
        for doctor_email, patients in PATIENTS_BY_DOCTOR.items():
            doctor = doc_by_email[doctor_email]
            for p in patients:
                existing = db.query(Patient).filter(Patient.email == p["email"]).first()
                if existing:
                    all_patients.append(existing)
                    continue
                pat = Patient(
                    patient_code=p["patient_code"],
                    p_name=p["p_name"], email=p["email"],
                    password=hash_password(p["password"]),
                    age=p["age"], gender=p["gender"],
                    medical_history=p["medical_history"],
                    risk=p["risk"], doctor_id=doctor.id,
                )
                db.add(pat)
                db.flush()
                # Seed a small history trail per patient
                for i in range(3):
                    db.add(RiskHistory(
                        patient_id=pat.id,
                        risk=max(0, p["risk"] - (2 - i) * 8),
                        recorded_at=datetime.utcnow() - timedelta(days=(2 - i) * 7),
                    ))
                all_patients.append(pat)

        # ---- Appointments ----
        if not db.query(Appointment).first():
            ahmed = doc_by_email["ahmed@medaura.com"]
            sara = doc_by_email["sara@medaura.com"]
            ahmed_patients = [p for p in all_patients if p.doctor_id == ahmed.id]
            sara_patients = [p for p in all_patients if p.doctor_id == sara.id]
            if ahmed_patients:
                db.add(Appointment(patient_id=ahmed_patients[0].id, doctor_id=ahmed.id,
                                   date=datetime.utcnow() + timedelta(days=1, hours=2),
                                   notes="Dressing change", status="waiting"))
            if len(ahmed_patients) > 1:
                db.add(Appointment(patient_id=ahmed_patients[1].id, doctor_id=ahmed.id,
                                   date=datetime.utcnow() + timedelta(days=2),
                                   notes="Follow-up scan", status="next"))
            if sara_patients:
                db.add(Appointment(patient_id=sara_patients[0].id, doctor_id=sara.id,
                                   date=datetime.utcnow() - timedelta(days=1),
                                   notes="Initial consultation", status="done"))

        db.commit()
        print_summary(db)
    finally:
        db.close()


def print_summary(db):
    print("\n" + "=" * 70)
    print("  SEED COMPLETE — TEST CREDENTIALS")
    print("=" * 70)
    print("\n  DOCTORS (sign in with email + password):")
    for d in db.query(Doctor).order_by(Doctor.id).all():
        print(f"    - {d.name}")
        print(f"        email:    {d.email}")
        print(f"        password: doctor123")
        print(f"        specialty: {d.specialty}\n")

    print("  PATIENTS (sign in with patient code + password):")
    for p in db.query(Patient).order_by(Patient.id).all():
        print(f"    - {p.p_name} (age {p.age}, risk {p.risk})")
        print(f"        patient code: {p.patient_code}")
        print(f"        password:     patient123\n")
    print("=" * 70)


if __name__ == "__main__":
    seed()
