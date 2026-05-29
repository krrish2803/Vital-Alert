# VitalAlert 🚑

**AI-Powered Diagnostic Report Analysis & Critical Alert System**

VitalAlert helps diagnostic centres automatically analyze medical reports using AI and instantly alert doctors via WhatsApp when critical values are found.

---

## 📖 Table of Contents

- [What is VitalAlert?](#-what-is-vitalalert)
- [Who is this for?](#-who-is-this-for)
- [How it works](#-how-it-works)
- [Features](#-features)
- [Option 1: Run on Your Computer (Local Setup)](#-option-1-run-on-your-computer-local-setup)
- [Option 2: Deploy Online (Vercel Setup)](#-option-2-deploy-online-vercel-setup)
- [How to Use the Project](#-how-to-use-the-project)
- [Environment Variables Explained](#-environment-variables-explained)
- [Troubleshooting](#-troubleshooting)
- [Tech Stack](#-tech-stack)

---

## 🤔 What is VitalAlert?

When a patient gets a medical test (blood test, X-ray, MRI, etc.), the report needs to be checked by a doctor. If there's a critical finding, the doctor needs to know immediately.

VitalAlert automates this:
1. Upload the report
2. AI reads it and finds any problems
3. If critical, a WhatsApp message is sent to the doctor right away

---

## 🎯 Who is this for?

- **Diagnostic centres** — Automatically alert doctors when patient reports have critical values
- **Patients** — Get your reports analyzed and sent to your doctor
- **Doctors** — Receive alerts on WhatsApp when your patients have critical results

---

## 🔄 How it works

```
Patient uploads report → AI analyzes it → Critical? → WhatsApp alert to doctor
                                              ↓ Not critical?
                                              → Report saved normally
```

---

## ✨ Features

- **AI Report Analysis** — Upload medical reports (X-rays, MRIs, blood tests, etc.) and AI extracts all values
- **Health Summary** — AI explains the report in simple English
- **WhatsApp Alerts** — When critical values are found, doctor gets an instant WhatsApp message
- **Doctor Portal** — Doctors can see all alerts, acknowledge them, call patients
- **Patient Portal** — Patients can upload reports, assign a doctor, and send alerts
- **Staff Panel** — Staff can register patients and upload reports
- **Owner Dashboard** — See statistics, recent activity, and manage everything
- **Auto-Escalation** — If a doctor doesn't respond in 30 minutes, alert gets escalated

---

## 💻 Option 1: Run on Your Computer (Local Setup)

### Step 1: Install Prerequisites

You need these installed on your computer:
- **Python 3.9 or higher** — [Download Python](https://www.python.org/downloads/)
- **MongoDB** — [Download MongoDB Community Edition](https://www.mongodb.com/try/download/community) OR create a free [MongoDB Atlas](https://www.mongodb.com/atlas) account (cloud database)

### Step 2: Download the Project

```bash
git clone https://github.com/krrish2803/Vital-Alert.git
cd Vital-Alert/vitalert
```

### Step 3: Set Up the Backend

Open a terminal and run:

```bash
# Go to backend folder
cd backend

# Create a virtual environment (isolates project dependencies)
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install all required packages
pip install -r requirements.txt
```

### Step 4: Set Up MongoDB

**Option A: Local MongoDB (easiest)**
- Install MongoDB on your computer
- Start MongoDB by running `mongod` in a terminal
- Your connection string will be: `mongodb://localhost:27017`

**Option B: MongoDB Atlas (cloud, free)**
1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) and sign up
2. Create a free cluster (M0 tier)
3. Go to **Security → Database Access** → Add a database user (create a username and password)
4. Go to **Security → Network Access** → Add IP `0.0.0.0/0` (allows access from anywhere)
5. Click **Connect** → **Drivers** → Copy the connection string
6. Replace `<username>` and `<password>` with your credentials

### Step 5: Configure Environment Variables

```bash
# Copy the example .env file
cp .env.example .env

# Now edit the .env file with your details
```

Open the `.env` file and fill in these values:

```env
# MongoDB - use your connection string from Step 4
MONGODB_URI=mongodb://localhost:27017
# OR for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net

MONGODB_DB_NAME=vitalert

# NVIDIA API Key - for AI analysis (get from https://build.nvidia.com)
NVIDIA_API_KEY=nvapi-your-key-here

# Twilio - for WhatsApp alerts (get from https://twilio.com)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

JWT_SECRET=choose-any-secret-key
FRONTEND_URL=http://localhost:3000

# Your WhatsApp number to receive alert copies (optional)
ALERT_CC_WHATSAPP=+919876543210
```

### Step 6: Get Your API Keys

**NVIDIA API Key (for AI analysis):**
1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Sign up for a free account
3. Go to the API section and generate an API key
4. Copy the key starting with `nvapi-...`

**Twilio Account (for WhatsApp alerts):**
1. Go to [twilio.com](https://twilio.com) and sign up
2. Get your Account SID and Auth Token from the dashboard
3. Activate the WhatsApp Sandbox:
   - Go to **Messaging → Try it out → Send a WhatsApp message**
   - The sandbox number is usually `+14155238886`
   - You'll get a code like `join xxxxx` — send this code as a WhatsApp message to the sandbox number
   - This registers your phone to receive test messages
4. **Important:** You need to re-send the code every 72 hours to keep receiving messages in sandbox mode

### Step 7: Start the Backend Server

```bash
# Make sure you're in the backend folder and venv is activated
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Leave this terminal running. You should see:
```
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 8: Start the Frontend

Open a **new terminal** and run:

```bash
cd vitalert/frontend
python -m http.server 3000
```

### Step 9: Open the App

Open your browser and go to:
- **http://localhost:3000** — Login page
- **http://localhost:8000** — Backend API (shows "VitalAlert API is running")
- **http://localhost:8000/docs** — API documentation (nice UI to test endpoints)

---

## 🌐 Option 2: Deploy Online (Vercel Setup)

This makes your project live on the internet so anyone can use it.

### Step 1: Push Code to GitHub

```bash
# Make sure your code is pushed to GitHub
git push origin main
```

### Step 2: Create MongoDB Atlas (Free)

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a free cluster
3. Create a database user (save username & password)
4. Add IP `0.0.0.0/0` in Network Access
5. Get your connection string (looks like `mongodb+srv://...`)

### Step 3: Deploy on Vercel

1. Go to [vercel.com](https://vercel.com) and sign in (use your GitHub account)
2. Click **Add New → Project**
3. Import your GitHub repository (`krrish2803/Vital-Alert`)
4. Vercel will auto-detect the settings from `vercel.json`
5. Click **Deploy** — it will fail the first time, that's expected

6. Now add environment variables:
   - After the failed deploy, go to your project dashboard
   - Click **Settings → Environment Variables**
   - Add these one by one:

| Variable | Value |
|----------|-------|
| `MONGODB_URI` | Your MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | `vitalert` |
| `NVIDIA_API_KEY` | Your NVIDIA API key (`nvapi-...`) |
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` |
| `JWT_SECRET` | Any random string (like `mysecretkey123`) |
| `FRONTEND_URL` | Your Vercel app URL (like `https://vital-alert.vercel.app`) |
| `ALERT_CC_WHATSAPP` | Your WhatsApp number to receive copies (optional) |

7. Go to **Deployments** → Click **Redeploy** (the three dots menu)
8. Wait for it to finish — you'll get a green checkmark ✅
9. Click the generated URL (like `https://vital-alert.vercel.app`) to open your app!

### Important Vercel Note: Background Tasks

The auto-escalation feature (30-minute timeout) won't work on Vercel because it can't run background tasks. To fix this:
1. Go to [cron-job.org](https://cron-job.org) or any free cron service
2. Create a job that hits this URL every 5 minutes:
   `https://your-app.vercel.app/api/v1/alerts/escalate`
3. This will check for alerts that need escalation

---

## 📱 How to Use the Project

### 1. Create an Account

1. Open the app in your browser
2. Click **Register**
3. Enter your name, email, and password
4. After registering, select your role:
   - **Patient** — If you want to upload your reports
   - **Doctor** — If you want to receive alerts
   - **Staff** — If you work at the diagnostic centre

### 2. (For Patients) Upload a Report

1. Log in as a patient
2. Go to the **Analysis Report** tab
3. Select the report type (Blood Test, X-Ray, MRI, etc.)
4. Choose your report file (JPG, PNG, or PDF)
5. Click **Analyze Report**
6. Wait 30-60 seconds while AI analyzes it
7. View your results with AI explanation

### 3. (For Patients) Assign a Doctor

1. Go to the **My Doctor** tab
2. Enter your doctor's name and WhatsApp number
3. Click Save
4. Now when critical reports are found, alerts will be sent

### 4. (For Patients) Send Alert Manually

After analyzing a report, click **🚨 Send Alert to Doctor** button to send a WhatsApp alert immediately.

### 5. (For Doctors) View Alerts

1. Log in as a doctor
2. You'll see all alerts sent to you
3. Click an alert to see full details
4. Click **Mark as Acknowledged** to confirm you've seen it
5. Use **Call Patient** or **Message Patient** to contact them

### 6. (For Owners) Dashboard

Log in as the owner to see:
- Total reports, patients, doctors, alerts
- Reports grouped by type (chart)
- Alerts by day
- Top doctors by report count
- Recent activity feed

---

## 🔧 Environment Variables Explained

| Variable | What it does | Required? |
|----------|-------------|-----------|
| `MONGODB_URI` | Database connection string (MongoDB) | ✅ Yes |
| `MONGODB_DB_NAME` | Database name (default: `vitalert`) | ✅ Yes |
| `NVIDIA_API_KEY` | Key for AI analysis of reports | ✅ Yes |
| `TWILIO_ACCOUNT_SID` | Your Twilio account ID | ✅ Yes (for alerts) |
| `TWILIO_AUTH_TOKEN` | Your Twilio auth token | ✅ Yes (for alerts) |
| `TWILIO_WHATSAPP_FROM` | Twilio's WhatsApp number | ✅ Yes (for alerts) |
| `JWT_SECRET` | Secret key for user login tokens | ✅ Yes |
| `JWT_EXPIRE_HOURS` | How long login lasts (default: 24) | ❌ No |
| `FRONTEND_URL` | Your app URL for alert links | ✅ Yes |
| `MAX_FILE_SIZE_MB` | Max file upload size (default: 10) | ❌ No |
| `ESCALATION_MINUTES` | Time before alert escalates (default: 30) | ❌ No |
| `ALERT_CC_WHATSAPP` | Get a copy of all alerts on your number | ❌ No |

---

## ❓ Troubleshooting

### "Message not coming to my WhatsApp"
- You're using the Twilio **sandbox** — you need to send the join code to `+14155238886` every 72 hours
- Open WhatsApp → send a message to `+14155238886` with the join code shown in your Twilio dashboard

### "Can't connect to MongoDB"
- Make sure MongoDB is running (`mongod` in terminal for local)
- Check your connection string in `.env` is correct
- For Atlas: Make sure your IP is whitelisted (use `0.0.0.0/0`)

### "AI analysis is slow"
- The AI model takes 30-60 seconds to process images
- This is normal — the NVIDIA API needs time to analyze the report

### "Backend won't start"
- Make sure you've installed all packages: `pip install -r requirements.txt`
- Check that your `.env` file has all required values
- Make sure port 8000 is not in use

### "Login says 'Not authenticated'"
- Clear your browser's local storage or log out
- Log in again
- Check that the backend server is running

### "File upload fails"
- Max file size is 10MB by default
- Supported formats: JPG, PNG, WebP, PDF

### Vercel: "Deploy failed"
- Check that you added all environment variables in Vercel dashboard
- Look at the deploy logs for specific errors
- Try redeploying after fixing any issues

---

## 🛠 Tech Stack

- **Backend:** Python, FastAPI
- **Database:** MongoDB with Motor (async driver)
- **AI:** NVIDIA NIM API (Llama vision model for reports, Mistral for summaries)
- **Alerts:** Twilio WhatsApp API
- **Frontend:** HTML, CSS, JavaScript (no frameworks needed)
- **PDF Processing:** PyMuPDF
- **Deployment:** Vercel (serverless)

---

## 📄 License

This project is for educational and demonstration purposes.
