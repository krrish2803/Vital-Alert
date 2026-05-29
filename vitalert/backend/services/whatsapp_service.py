import logging
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

logger = logging.getLogger(__name__)


async def send_whatsapp(phone: str, message: str) -> dict:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured. Skipping WhatsApp send.")
        return {"success": False, "sid": None, "error": "Twilio not configured"}

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        to_number = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
        from_number = TWILIO_WHATSAPP_FROM

        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        logger.info(f"WhatsApp sent to {phone}. SID: {msg.sid}")
        return {"success": True, "sid": msg.sid, "error": None}
    except Exception as e:
        logger.error(f"WhatsApp send failed to {phone}: {e}")
        return {"success": False, "sid": None, "error": str(e)}
