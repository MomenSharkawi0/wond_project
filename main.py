import sys
import os

# Ensure the app can find the modules
sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import auth, patient, doctor, images, appointments
from db.database import Base, engine

# Locate the frontend dir relative to this file so it works no matter where
# uvicorn is launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOGIN_PAGE = os.path.join(FRONTEND_DIR, "Animated Login - MedAura AI.html")

# Create database tables if they don't exist (does not touch existing rows)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedAura AI Backend")

# Ensure runtime directories exist (uploads/ is gitignored)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount the uploads directory so the frontend can access images directly via URL
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Serve the static HTML frontend at /app/...
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# Configure CORS (Cross-Origin Resource Sharing)
# Using ["*"] for development allows any frontend to connect. 
# (In production, replace "*" with your actual frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API Routers
app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(doctor.router)
app.include_router(images.router)      # This now handles the /wound AI routes
app.include_router(appointments.router)

# Serve the login page directly at the root so users always land on the UI,
# never on a JSON payload (no redirect, no cache games).
@app.get("/", include_in_schema=False)
def read_root():
    return FileResponse(LOGIN_PAGE)

# Health probe for tooling/monitoring.
@app.get("/health")
def health_check():
    return {"status": "MedAura AI Backend is running smoothly!"}