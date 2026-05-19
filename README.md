# MedAura AI

A wound-assessment platform for doctors and patients. Detects wound regions in uploaded photos using OpenCV segmentation, computes a risk score plus real-world cm measurements, and tracks each patient's progress over time.

---

## Highlights

- **Doctor portal** — manage patients, schedule appointments, view AI risk analysis with before/after wound images
- **Patient portal** — upload wound photos, see instant AI segmentation, view personal history
- **AI segmentation** — detects the wound region, overlays a translucent red mask + yellow outline, computes risk score and approximate size in cm
- **Role-based JWT auth** — bcrypt-hashed passwords, doctors and patients have separate scopes
- **Single-server deployment** — FastAPI serves the API *and* the static HTML dashboards on one port

---

## Tech stack

| Layer        | Tech                                              |
| ------------ | ------------------------------------------------- |
| Web server   | FastAPI + Uvicorn                                 |
| Database     | SQLAlchemy 2.x → SQLite (default), Postgres-ready |
| Auth         | python-jose JWT (HS256) + passlib bcrypt          |
| AI / vision  | OpenCV (color-space segmentation), NumPy, Pillow  |
| Frontend     | Static HTML + vanilla JS + Chart.js               |

---

## Requirements

- **Python 3.11 or newer**
- **pip**
- Any modern browser

Verified to work on Windows 10/11, macOS, Linux. No GPU required.

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/MomenSharkawi0/wond_project.git
cd wond_project
```

### 2. (Recommended) Create a virtual environment

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> The `bcrypt==4.0.1` pin is intentional — `passlib 1.7` is incompatible with `bcrypt 4.1+` (a known upstream issue).

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your own values:

```bash
cp .env.example .env     # macOS / Linux
copy .env.example .env   # Windows
```

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as your `SECRET_KEY`. Example `.env`:

```env
SECRET_KEY=82d88a8a906199d5a130f48108450301b94fdbeb730e18c4481ba9b59c3bb840
DATABASE_URL=sqlite:///./database.db
```

### 5. Run the server

```bash
uvicorn main:app --reload
```

Visit **http://127.0.0.1:8000** — the root redirects to the login page.

The first request auto-creates the database tables. There are no users yet — see the next section.

---

## First-time use

1. Open http://127.0.0.1:8000
2. Click **"Create Account"** in the right panel of the login screen
3. Fill in name, email, specialty, phone, hospital, license, and password
4. Click **Register as Doctor** — you're redirected back to the sign-in tab
5. Sign in as a **Doctor** with the email + password you just used
6. From the **Patients** page, click **Add Patient** to create one
   - The system assigns a **6-digit patient code** (shown in a popup)
   - Share the code and the password you set with the patient
7. The patient can now sign in on the same login screen, selecting the **Patient** tab and entering their code + password

---

## Daily flows

### Doctor

| What you do                                       | Where                                         |
| ------------------------------------------------- | --------------------------------------------- |
| See real-time stats (total, critical, recovery)   | Dashboard page                                |
| Add / edit / delete patients                      | Patients page → Add / row actions             |
| Inspect a patient's wound history + risk chart    | Patients → View                               |
| Upload a wound photo for AI analysis              | Patients → View → **+ Upload & Analyze**      |
| Schedule, reschedule, complete appointments       | Appointments page                             |
| Logout                                            | Sign-out icon (bottom-left sidebar)           |

### Patient

| What you do                          | Where                                              |
| ------------------------------------ | -------------------------------------------------- |
| View your profile, condition, risk   | Integrated Dashboard (auto-loads on login)         |
| Upload a wound photo for AI analysis | Click **Upload Wound Image** card → Capture/Upload |
| See before/after with AI mask        | Wound Segmentation card                            |
| Logout                               | Sign-out icon (bottom-left sidebar)                |

---

## AI behavior — what's actually happening

The wound analysis runs **OpenCV-based color segmentation**, not a neural network. The bundled `unet_model.h5` (226 MB) is *not* loaded — it was flagged corrupted in the original codebase and the OpenCV approach produces clinically interpretable results without TensorFlow.

Pipeline per image:

1. Decode the upload with Pillow and convert to a NumPy RGB array
2. Convert to **LAB color space** and isolate the `a` channel (red↔green axis) — wounds have a higher `a` value than surrounding skin
3. Adaptive threshold: `max(mean + 1.5σ, 92nd percentile, mean + 8)` so the cutoff scales with each photo's own color distribution
4. Require HSV saturation > 50 to drop pale-skin false positives
5. Morphological **open then close** to remove noise and fill the wound interior
6. Pick the best contour by `area × compactness²` (favors round wound-shaped blobs over long thin skin strips)
7. Render the overlay: original image + translucent red fill on the wound + yellow contour outline + centroid dot
8. Compute risk score from `coverage × 600 + redness_excess × 22`, capped 10–95
9. Convert pixel measurements to cm using a user-supplied **reference width** (subject width in cm)

### About the cm measurements

The system has no automatic depth/scale calibration, so it asks the user to estimate the **width of the photo subject in cm** before each upload (default 15 cm — typical phone shot of a forearm). Then:

```
cm_per_pixel = reference_width_cm / image_width_pixels
wound_area_cm2 = wound_pixels × cm_per_pixel²
diameter_cm = 2 × √(area_cm2 / π)
```

For clinical accuracy, place a coin, sticker, or ruler next to the wound and enter that object's known width as the reference.

---

## API reference

Interactive docs at **http://127.0.0.1:8000/docs**.

### Auth
- `POST /auth/register/doctor` — register a doctor
- `POST /auth/login/doctor` — `{email, password}` → JWT
- `POST /auth/login/patient` — `{patient_code, password}` → JWT

### Doctor (Bearer token, role=doctor)
- `GET  /doctor/me` — current doctor profile
- `GET  /doctor/all` — list all doctors
- `GET  /doctor/patients` — patients assigned to current doctor
- `GET  /doctor/patient/{id}` — a single patient
- `GET  /doctor/risk/history/{id}` — risk history for a patient

### Patient management (doctor only)
- `POST   /patient/add` — create a patient (returns generated patient_code)
- `PUT    /patient/{id}` — update name/age/gender/medical_history
- `DELETE /patient/delete/{id}` — delete
- `PUT    /patient/risk/{id}?risk=N` — manually set risk
- `GET    /patient/risk/history/{id}` — risk history

### Patient (Bearer token, role=patient)
- `GET /patient/me` — current patient profile

### Wound analysis (doctor or patient)
- `POST /wound/upload` — multipart: `file`, `patient_id`, `reference_width_cm`
  - Doctors can upload for any of their own patients
  - Patients can upload only for themselves

### Appointments (doctor only)
- `POST   /appointments/` — create
- `GET    /appointments/` — list all
- `GET    /appointments/doctor/{id}` — list a doctor's
- `PUT    /appointments/status/{id}?status=waiting|next|done` — update status
- `DELETE /appointments/{id}` — delete

---

## Project structure

```
.
├── main.py                  # FastAPI entry; mounts /app + /uploads
├── requirements.txt
├── .env.example             # Copy to .env, fill SECRET_KEY + DATABASE_URL
├── .gitignore               # Excludes .env, __pycache__, uploads/, database.db
├── core/
│   ├── auth.py              # JWT + bcrypt + role guards (doctor_only, patient_only, current_user)
│   ├── ai_service.py        # OpenCV wound segmentation + cm conversion
│   └── config.py            # pydantic-settings reads .env
├── db/
│   └── database.py          # SQLAlchemy engine + SessionLocal
├── models/
│   └── models.py            # Doctor, Patient, RiskHistory, Appointment
├── schemas/
│   └── schemas.py           # Pydantic request/response models
├── routers/
│   ├── auth.py              # /auth/*
│   ├── doctor.py            # /doctor/*
│   ├── patient.py           # /patient/*
│   ├── images.py            # /wound/upload
│   └── appointments.py      # /appointments/*
├── frontend/                # Static HTML served at /app/...
│   ├── Animated Login - MedAura AI.html
│   ├── Doctor_Dashboard1.html
│   └── MedAura AI - Integrated Dashboard.html
└── uploads/                 # Wound photos + AI mask overlays (gitignored, auto-created)
```

---

## Troubleshooting

### I see `{"status":"MedAura AI Backend is running smoothly!"}` instead of the login page

That JSON now lives at `/health`, not `/`. The root path `/` serves the login page as HTML. If you're seeing the JSON at `/`, you're on an outdated clone — run:

```bash
git pull
```

and restart the server. Then visit **http://127.0.0.1:8000** (not `/health`).

### `ModuleNotFoundError: No module named '...'`

You didn't install dependencies in the active environment. Run:

```bash
pip install -r requirements.txt
```

inside your virtualenv (if you're using one).

### `passlib` / `bcrypt` error: "password cannot be longer than 72 bytes"

This is a passlib 1.7 vs bcrypt 4.1+ incompatibility. The requirements file pins `bcrypt==4.0.1` to avoid it — make sure you actually installed from `requirements.txt`, not a higher version.

### Port 8000 is in use

```bash
uvicorn main:app --port 8001
```

…or kill whatever's holding port 8000.

### `database.db` file lock errors on Windows

Stop any running Python/uvicorn process before deleting it. SQLite holds an exclusive lock while the server is up.

---

## Resetting the database

Stop the server, delete `database.db`, then restart:

```bash
# Stop the running server (Ctrl+C), then:
rm database.db          # macOS / Linux
del database.db         # Windows
uvicorn main:app --reload
```

Tables are auto-created on first request. Old uploaded images in `uploads/` are not auto-deleted — clean them manually if you want a fully fresh state.

---

## Going to production — checklist

- Tighten **CORS** in `main.py` — currently `allow_origins=["*"]`
- Move from SQLite to PostgreSQL by changing `DATABASE_URL` (e.g. `postgresql+psycopg://user:pass@host/db`)
- Run behind a reverse proxy (nginx, Caddy) with TLS
- Mount `uploads/` on persistent storage outside the container
- Increase the JWT expiry (currently 30 minutes) and consider refresh tokens
- Add rate limiting on `/auth/login/*` and `/wound/upload`
- Replace the OpenCV simulator with a real wound-segmentation model if you have one — drop it into `core/ai_service.py` as `analyze_wound_image`

---

## License

MIT — see source for details.
