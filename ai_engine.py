"""
AI Backend Handler: sends raw citizen text (any dialect/language) plus a
locality name and pincode to Gemini, and gets back structured JSON:
translation, category, urgency score, landmark, and a lat/lon derived from
Gemini's internal geographic knowledge of India — nationwide, not limited
to any single city or state.
"""
import os
import json
from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.5-flash"

CATEGORIES = ["Roads & Traffic", "Water & Sewage", "Electricity & Power", "Public Health"]

# Nationwide India bounding box (approximate) used as a sanity clamp on AI output.
INDIA_LAT_BOUNDS = (6.0, 38.0)
INDIA_LON_BOUNDS = (68.0, 98.0)
INDIA_DEFAULT_LAT = 20.5937
INDIA_DEFAULT_LON = 78.9629

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "translated_text": {
            "type": "string",
            "description": "The grievance translated/normalized into clear English."
        },
        "category": {
            "type": "string",
            "enum": CATEGORIES,
            "description": "Best-fit civic category for this grievance."
        },
        "urgency": {
            "type": "integer",
            "description": "Urgency score from 1 (trivial) to 10 (life-threatening/critical)."
        },
        "landmark": {
            "type": "string",
            "description": "Named place, street, or landmark mentioned in the text, or the given Area if none is mentioned."
        },
        "lat": {
            "type": "number",
            "description": "Precise latitude corresponding to the given Indian Area/Locality Name and Pincode."
        },
        "lon": {
            "type": "number",
            "description": "Precise longitude corresponding to the given Indian Area/Locality Name and Pincode."
        },
        "summary": {
            "type": "string",
            "description": "One-line actionable summary for an administrator."
        }
    },
    "required": ["translated_text", "category", "urgency", "landmark", "lat", "lon", "summary"]
}

SYSTEM_INSTRUCTION = (
    "You are a nationwide civic grievance triage engine operating across all regions of India. "
    "Analyze the complaint text, the Indian Area/Locality Name, and the 6-digit Indian Postal Pincode. "
    "Using your internal geographic knowledge of India, determine the precise coordinates (Latitude and "
    "Longitude floats) corresponding to that specific locality or Pincode zone. "
    "Citizens submit complaints in English, Hindi, Odia, Bengali, Tamil, Telugu, Marathi, or any other "
    "Indian regional language, or a mix (code-switched). Translate the grievance into clear English, "
    "classify it into exactly one of the given categories, assign an urgency score from 1-10 based on "
    "public safety/health impact and scale, and extract any named landmark, locality, or street (fall "
    "back to the given Area if none is mentioned in the text). Always return valid structured JSON only."
)


def parse_grievance(raw_text: str, area: str, pincode: str) -> dict:
    """
    Send raw citizen text plus a locality name and pincode to Gemini and
    return structured grievance data, including an AI-derived lat/lon
    anywhere in India.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)

    composite_prompt = f"Grievance: {raw_text}\nArea: {area}\nPincode: {pincode}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=composite_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.2,
        ),
    )

    result = json.loads(response.text)

    # Safety clamps
    try:
        result["urgency"] = max(1, min(10, int(result.get("urgency", 5))))
    except (TypeError, ValueError):
        result["urgency"] = 5
    if result.get("category") not in CATEGORIES:
        result["category"] = CATEGORIES[0]

    # Nationwide India bounds check — fallback to country centroid if implausible
    try:
        lat = float(result.get("lat"))
        lon = float(result.get("lon"))
        if not (INDIA_LAT_BOUNDS[0] <= lat <= INDIA_LAT_BOUNDS[1] and
                INDIA_LON_BOUNDS[0] <= lon <= INDIA_LON_BOUNDS[1]):
            raise ValueError("out of expected India bounds")
        result["lat"] = lat
        result["lon"] = lon
    except (TypeError, ValueError):
        result["lat"] = INDIA_DEFAULT_LAT
        result["lon"] = INDIA_DEFAULT_LON

    return result
