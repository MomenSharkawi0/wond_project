import sys
import os

# Ensure the app can find the modules
sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from routers import auth, patient, doctor, images, appointments
from db.database import Base, engine

# Create database tables if they don't exist (does not touch existing rows)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedAura AI Backend")

# Ensure runtime directories exist (uploads/ is gitignored)
os.makedirs("uploads", exist_ok=True)

# Mount the uploads directory so the frontend can access images directly via URL
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve the static HTML frontend at /app/...
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

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

# Redirect root to the login page so users land directly on the app
@app.get("/")
def read_root():
    return RedirectResponse(url="/app/Animated%20Login%20-%20MedAura%20AI.html")

@app.get("/health")
def health_check():
    return {"status": "MedAura AI Backend is running smoothly!"}