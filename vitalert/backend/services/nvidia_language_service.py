import json
import logging
import asyncio
from openai import OpenAI
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_LANGUAGE_MODEL

logger = logging.getLogger(__name__)


async def generate_health_summary(extracted_data: dict, patient_info: dict, report_type: str) -> str:
    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY, timeout=90)

    is_radiology = report_type.lower() in ("x-ray", "mri", "ct scan", "ultrasound", "echo")
    has_values = bool(extracted_data.get("extracted_values"))
    impression = extracted_data.get("impression", "")

    if is_radiology and not has_values:
        findings = "\n".join(extracted_data.get("critical_findings", []))
        prompt = (
            f"Write a simple 4-5 sentence health summary for a doctor based on this {report_type} report:\n"
            f"Findings: {findings}\n"
            f"Impression: {impression}\n\n"
            f"Patient: {patient_info.get('name')}, {patient_info.get('age')}, {patient_info.get('gender')}\n\n"
            f"Explain what the findings mean, what is normal, what is concerning, "
            f"and what action the doctor should take."
        )
    else:
        prompt = (
            f"Write a simple 4-5 sentence health summary for a doctor based on these extracted report values:\n"
            f"{json.dumps(extracted_data)}\n\n"
            f"Patient: {patient_info.get('name')}, {patient_info.get('age')}, {patient_info.get('gender')}\n"
            f"Report Type: {report_type}\n\n"
            f"Explain what the findings mean, what is normal, what is concerning, "
            f"and what action the doctor should take."
        )

    for attempt in range(3):
        try:
            logger.info(f"Sending to NVIDIA Language API (attempt {attempt + 1})")
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=NVIDIA_LANGUAGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical AI assistant explaining diagnostic reports "
                            "to doctors in India. Write clear, simple English summaries. "
                            "Never use complex medical jargon. Always mention what is normal "
                            "and what is concerning. Always end with a clear suggested action."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
            )
            summary = response.choices[0].message.content.strip()
            logger.info("Language API success")
            return summary
        except Exception as e:
            logger.error(f"Language API attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                return "AI health summary unavailable. Please review the extracted values manually."
