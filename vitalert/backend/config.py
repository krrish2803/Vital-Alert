import os
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "vitalert")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"
NVIDIA_LANGUAGE_MODEL = "mistralai/mistral-small-4-119b-2603"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", "20"))
ESCALATION_MINUTES = int(os.getenv("ESCALATION_MINUTES", "30"))
ALERT_CC_WHATSAPP = os.getenv("ALERT_CC_WHATSAPP", "")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/vitalert_uploads")
