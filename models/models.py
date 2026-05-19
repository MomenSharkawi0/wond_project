from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base
import random

def generate_patient_code():
    """Generates a random 6-digit code for new patients."""
    return random.randint(100000, 999999)

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    patient_code = Column(Integer, unique=True, default=generate_patient_code)
    p_name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    age = Column(Integer)
    gender = Column(String)
    medical_history = Column(Text)
    risk = Column(Integer, default=0)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    # SQLAlchemy Relationships
    doctor = relationship("Doctor", back_populates="patients")
    risk_histories = relationship("RiskHistory", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    specialty = Column(String)
    phone = Column(String, nullable=True)
    hospital = Column(String, nullable=True)
    license_number = Column(String, nullable=True)

    # SQLAlchemy Relationships
    patients = relationship("Patient", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")


class RiskHistory(Base):
    __tablename__ = "risk_history"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    risk = Column(Integer)
    image_path = Column(String, nullable=True) # Added to store the AI wound image path
    recorded_at = Column(DateTime, default=func.now())

    # SQLAlchemy Relationships
    patient = relationship("Patient", back_populates="risk_histories")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    date = Column(DateTime)
    notes = Column(String, nullable=True)
    status = Column(String, default="waiting")

    # SQLAlchemy Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")