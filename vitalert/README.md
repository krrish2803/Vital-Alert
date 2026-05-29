# VitalAlert 🚑

AI-powered diagnostic report analysis and critical alert system for diagnostic centres in India.

## Features

- **AI Report Analysis** — Upload diagnostic reports (images/PDFs), extract test values using NVIDIA Vision AI
- **Health Summary** — Get simple English explanations powered by NVIDIA Mistral Large
- **Critical Alert System** — Auto-alert referring doctors via WhatsApp when critical values are detected
- **Doctor Portal** — Doctors can acknowledge alerts, call patients, and send messages
- **Staff Panel** — Register patients, upload reports, view analysis results
- **Owner Dashboard** — Real-time analytics with auto-refresh every 30 seconds
- **Escalation** — Unacknowledged alerts auto-escalate after 30 minutes

## Tech Stack

- **Backend:** Python, FastAPI, Motor (async MongoDB), NVIDIA NIM API
- **Frontend:** Pure HTML, CSS, JavaScript (no frameworks)
- **Database:** MongoDB Atlas
- **AI:** NVIDIA NIM (llama-3.1-nemotron-nano-vl-8b-v1, mistralai/mistral-large)
- **Alerts:** Twilio WhatsApp API
- **PDF:** PyMuPDF for PDF to image conversion

## Setup

### Prerequisites
- Python 3.11+
- MongoDB Atlas cluster
- NVIDIA NIM API key
- Twilio account with WhatsApp capability

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
Serve the `frontend/` directory with any static server:

```bash
cd frontend
python -m http.server 3000
```

Or use Docker:

```bash
cd backend
docker build -t vitalert .
docker run -p 8000:8000 --env-file .env vitalert
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | Database name (default: vitalert) |
| `NVIDIA_API_KEY` | NVIDIA NIM API key |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp number |
| `JWT_SECRET` | JWT signing secret |
| `FRONTEND_URL` | Frontend URL for alert links |

## API Endpoints

### Auth
- `POST /api/v1/auth/login` — Login
- `POST /api/v1/auth/register` — Register

### Patients
- `POST /api/v1/patients` — Register patient
- `GET /api/v1/patients` — List patients
- `GET /api/v1/patients/search?q=` — Search patients
- `GET /api/v1/patients/{id}` — Patient details

### Reports
- `POST /api/v1/reports/upload` — Upload & analyze reports
- `GET /api/v1/reports` — List reports
- `GET /api/v1/reports/critical` — Critical reports
- `GET /api/v1/reports/{id}` — Report details

### Alerts
- `POST /api/v1/alerts/manual-whatsapp` — Manual alert
- `POST /api/v1/alerts/{id}/acknowledge` — Acknowledge
- `POST /api/v1/alerts/{id}/message-patient` — Message patient

### Dashboard
- `GET /api/v1/dashboard/stats` — Stats cards
- `GET /api/v1/dashboard/reports-by-type` — Chart data
- `GET /api/v1/dashboard/alerts-by-day` — Chart data
- `GET /api/v1/dashboard/top-doctors` — Leaderboard
- `GET /api/v1/dashboard/recent-alerts` — Live feed
- `GET /api/v1/dashboard/recent-patients` — Recent activity
