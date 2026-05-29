import json
import logging
import asyncio
import re
from openai import OpenAI
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_VISION_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _try_parse_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        raw = m.group(0)
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    return json.loads(raw)


def _build_fallback(report_type: str, error: str = "AI analysis failed"):
    return {
        "report_type": report_type,
        "extracted_values": [],
        "critical_findings": ["AI analysis failed"],
        "is_critical": False,
        "confidence_score": 0.0,
        "severity": "unknown",
        "suggested_action": f"Manual review required - {error}",
    }


def _build_prompt_content(images: list, report_type: str):
    is_radiology = report_type.lower() in ("x-ray", "mri", "ct scan", "ultrasound", "echo")
    content = []
    for b64_img in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
        })
    if is_radiology:
        text = (
            "Analyze this radiology/imaging report. Extract the key findings and observations.\n\n"
            "Return ONLY valid JSON with this exact structure:\n"
            "{\n"
            '  "report_type": "type of report",\n'
            '  "extracted_values": [\n'
            "    {\"test_name\": \"Finding\", \"value\": \"...\", \"unit\": \"\", \"normal_range\": \"\", \"status\": \"normal\"}\n"
            "  ],\n"
            '  "critical_findings": ["list of all abnormal/key findings mentioned"],\n'
            '  "impression": "overall impression from the report",\n'
            '  "is_critical": true or false,\n'
            '  "confidence_score": 0.0 to 1.0,\n'
            '  "severity": "normal | low | medium | high | critical",\n'
            '  "suggested_action": "recommended follow-up or action"\n'
            "}\n\n"
            "Rules:\n"
            "- Put each key observation as an entry in critical_findings\n"
            "- Put the overall impression in the 'impression' field\n"
            "- is_critical must be true if any finding is serious/abnormal\n"
            "\nReturn ONLY the JSON. No other text."
        )
    else:
        text = (
            "Analyze this diagnostic report image. Extract EVERY test value present in the image.\n"
            "Do not skip any tests. Include ALL of them in the extracted_values array.\n\n"
            "Return ONLY valid JSON with this exact structure:\n"
            "{\n"
            '  "report_type": "type of report",\n'
            '  "extracted_values": [\n'
            "    {\"test_name\": \"...\", \"value\": 0.0, \"unit\": \"...\", \"normal_range\": \"...\", \"status\": \"...\"},\n"
            "    {\"test_name\": \"...\", \"value\": 0.0, \"unit\": \"...\", \"normal_range\": \"...\", \"status\": \"...\"}\n"
            "  ],\n"
            '  "critical_findings": ["..."],\n'
            '  "is_critical": true or false,\n'
            '  "confidence_score": 0.0 to 1.0,\n'
            '  "severity": "normal | low | medium | high | critical",\n'
            '  "suggested_action": "..."\n'
            "}\n\n"
            "Rules:\n"
            "- extracted_values must be an ARRAY with ALL tests found\n"
            "- status must be: normal, low, high, critical_low, or critical_high\n"
            "- is_critical must be true if ANY value is critical_low or critical_high\n"
            "\nReturn ONLY the JSON. No other text."
        )
    content.append({"type": "text", "text": text})
    return content


async def extract_report_data(images: list, report_type: str) -> dict:
    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY, timeout=90)

    content = _build_prompt_content(images, report_type)

    for attempt in range(3):
        try:
            logger.info(f"Sending {len(images)} images to {NVIDIA_VISION_MODEL} (attempt {attempt + 1})")
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=NVIDIA_VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strict JSON-only medical report analyzer. Never output anything except the JSON object.",
                    },
                    {"role": "user", "content": content},
                ],
                max_tokens=4096,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            logger.info(f"Vision raw response ({len(raw)} chars): {raw[:100]}...")
            data = _try_parse_json(raw)
            logger.info(f"Vision API success. Critical: {data.get('is_critical')}, Confidence: {data.get('confidence_score')}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Vision API attempt {attempt + 1} failed to parse JSON: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                return _build_fallback(report_type, f"JSON parse failed: {e}")
        except Exception as e:
            logger.error(f"Vision API attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                return _build_fallback(report_type, str(e))
