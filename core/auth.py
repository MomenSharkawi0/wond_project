from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.config import settings
from db.database import SessionLocal
from models.models import Doctor, Patient

# ===== 1. Settings & Context Configuration =====
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login/doctor")

# ===== 2. Core Hashing Functions (Must be defined first) =====
def hash_password(password: str) -> str:
    """Hashes a plain text password securely using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against its hashed version."""
    return pwd_context.verify(plain_password, hashed_password)

# ===== 3. Token Generation & Verification =====
def create_access_token(data: dict) -> str:
    """Generates a secure JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Decodes and verifies the incoming JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# ===== 4. Database Session Dependency =====
def get_db():
    """Dependency to inject database session per request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== 5. Role-Based Access Control Dependencies =====
def doctor_only(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Dependency guard ensuring the authenticated client is a Doctor."""
    if token.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - doctors only"
        )
    
    user_id = token.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    doctor = db.query(Doctor).filter(Doctor.id == int(user_id)).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return doctor

def patient_only(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Dependency guard ensuring the authenticated client is a Patient."""
    if token.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - patients only"
        )

    user_id = token.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    patient = db.query(Patient).filter(Patient.id == int(user_id)).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


def current_user(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Returns (role, user_model) for any authenticated user — doctor or patient."""
    role = token.get("role")
    user_id = token.get("sub")
    if not role or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    if role == "doctor":
        user = db.query(Doctor).filter(Doctor.id == int(user_id)).first()
    elif role == "patient":
        user = db.query(Patient).filter(Patient.id == int(user_id)).first()
    else:
        raise HTTPException(status_code=401, detail="Unknown role")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return (role, user)
