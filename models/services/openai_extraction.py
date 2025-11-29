"""
OpenAI-powered extraction service for cycling workout and sleep screenshots.
Uses GPT-4o vision capabilities to extract structured data from images.
Supports automatic classification of screenshot type.
"""
import os
import json
import base64
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, BinaryIO, Dict, Any, List, Union
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)


def get_openai_client():
    """Get or create OpenAI client with current API key"""
    load_dotenv(override=True)  # Reload env to pick up any changes
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


# ============== Data Models ==============

@dataclass
class CyclingWorkoutPayload:
    """Structured data extracted from cycling workout screenshots"""
    type: str = "cycling_workout"
    workout_date: Optional[str] = None  # YYYY-MM-DD
    start_time: Optional[str] = None    # HH:MM
    sport: str = "indoor_cycle"
    duration_sec: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    avg_power_w: Optional[float] = None
    max_power_w: Optional[float] = None
    normalized_power_w: Optional[float] = None
    intensity_factor: Optional[float] = None
    tss: Optional[float] = None
    avg_cadence: Optional[int] = None
    distance_km: Optional[float] = None
    kcal_active: Optional[int] = None
    kcal_total: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SleepSummaryPayload:
    """Structured data extracted from sleep screenshots"""
    type: str = "sleep_summary"
    sleep_start_date: Optional[str] = None   # YYYY-MM-DD (when sleep started)
    sleep_end_date: Optional[str] = None     # YYYY-MM-DD (when woke up - main date)
    sleep_start_time: Optional[str] = None   # HH:MM
    sleep_end_time: Optional[str] = None     # HH:MM
    total_sleep_minutes: Optional[int] = None
    deep_sleep_minutes: Optional[int] = None
    wakeups_count: Optional[int] = None
    min_heart_rate: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UnknownPayload:
    """Payload for unrecognized screenshots"""
    type: str = "unknown"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Type alias for any payload
ExtractedPayload = Union[CyclingWorkoutPayload, SleepSummaryPayload, UnknownPayload]


# ============== Unified Prompt Template ==============

UNIFIED_EXTRACTION_PROMPT = """You are analyzing a screenshot from a fitness, cycling, or health app. Your task is to:

1. FIRST, classify what type of screenshot this is:
   - "cycling_workout" = Any cycling/workout app showing exercise metrics (power, HR, duration, calories, TSS, etc.)
   - "sleep_summary" = Any sleep tracking app showing sleep data (duration, deep sleep, wake-ups, night HR)
   - "unknown" = Cannot determine or not a fitness/health screenshot

2. THEN, extract ALL available data fields from the image.

IMPORTANT RULES:
- Return ONLY valid JSON, no additional text or explanation.
- Use null for any value that is not visible in the image.
- Convert all durations to the specified unit (seconds for workouts, minutes for sleep).
- Convert distances to kilometers.
- Use 24-hour format for times (HH:MM).
- Use ISO format for dates (YYYY-MM-DD).
- IMPORTANT: Extract ALL numeric values visible in the screenshot.

For CYCLING_WORKOUT, return:
{
  "type": "cycling_workout",
  "workout_date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "sport": "indoor_cycle",
  "duration_sec": null,
  "avg_heart_rate": null,
  "max_heart_rate": null,
  "avg_power_w": null,
  "max_power_w": null,
  "normalized_power_w": null,
  "intensity_factor": null,
  "tss": null,
  "avg_cadence": null,
  "distance_km": null,
  "kcal_active": null,
  "kcal_total": null,
  "notes": ""
}

HEART RATE EXTRACTION (CRITICAL - carefully look for heart rate data):
- Look for these labels: "Avg Heart Rate", "Average Heart Rate", "Avg HR", "Heart Rate", "HR", "♥", "❤️", "BPM"
- avg_heart_rate = average/mean heart rate during workout (typically 100-180 for cycling)
- max_heart_rate = maximum/peak heart rate during workout (typically 150-200 for cycling)
- Heart rate values are shown as "XXX BPM" or "XXX bpm" or just a number near a heart icon
- In Apple Watch/Fitness: look for heart rate in the workout summary, often shows avg and max
- In cycling apps (Zwift, TrainerRoad, Wahoo, Garmin, Strava): HR is usually displayed prominently
- IMPORTANT: If you see ANY heart rate numbers in the screenshot, extract them!

POWER EXTRACTION - Look for:
- "Avg Power", "Average Power", "Power" → avg_power_w (watts)
- "Max Power", "Peak Power" → max_power_w (watts)
- "NP", "Normalized Power" → normalized_power_w (watts)
- "IF", "Intensity Factor" → intensity_factor (decimal like 0.85)
- "TSS", "Training Stress Score" → tss (number)

For SLEEP_SUMMARY, return:
{
  "type": "sleep_summary",
  "sleep_start_date": "YYYY-MM-DD",
  "sleep_end_date": "YYYY-MM-DD",
  "sleep_start_time": "HH:MM",
  "sleep_end_time": "HH:MM",
  "total_sleep_minutes": null,
  "deep_sleep_minutes": null,
  "wakeups_count": null,
  "min_heart_rate": null,
  "avg_heart_rate": null,
  "max_heart_rate": null,
  "notes": ""
}

For UNKNOWN, return:
{
  "type": "unknown",
  "notes": "Brief description of what the image shows"
}

NOTES:
- sleep_start_date is when you went to bed (e.g., previous night)
- sleep_end_date is when you woke up (this is the main date for tracking)
- For Apple Watch/Health screenshots, look for workout summary or sleep analysis data
- If deep sleep is shown as percentage, calculate minutes from total sleep
- sport can be: indoor_cycle, outdoor_cycle, spinning, cycling, etc.
- ALWAYS try to extract avg_heart_rate and max_heart_rate if any heart rate data is visible"""


# ============== Helper Functions ==============

def encode_image_to_base64(image_file: BinaryIO) -> str:
    """Encode an image file to base64 string"""
    return base64.b64encode(image_file.read()).decode('utf-8')


def get_image_mime_type(filename: str) -> str:
    """Determine MIME type from filename"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'heic': 'image/heic',
    }
    return mime_types.get(ext, 'image/jpeg')


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON from OpenAI response, handling potential markdown code blocks"""
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove first line (```json or ```)
        if lines[0].startswith('```'):
            lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Response text: {text[:500]}")
        raise ValueError(f"Invalid JSON response from OpenAI: {e}")


def call_openai_vision(base64_image: str, mime_type: str, prompt: str) -> str:
    """Make OpenAI Vision API call with error handling"""
    client = get_openai_client()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        logger.error(f"OpenAI API error: {error_msg}")
        if "insufficient_quota" in error_msg or "429" in error_msg:
            raise ValueError("OpenAI API quota exceeded. Please check your billing and add credits at https://platform.openai.com/account/billing")
        elif "invalid_api_key" in error_msg or "401" in error_msg:
            raise ValueError("Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env file")
        else:
            raise ValueError(f"OpenAI API error: {error_msg}")


def create_payload_from_data(data: Dict[str, Any]) -> ExtractedPayload:
    """Create the appropriate payload object from parsed JSON data"""
    payload_type = data.get('type', 'unknown')

    if payload_type == 'cycling_workout':
        # Convert 0 to None for heart rate fields (0 is not a valid HR)
        avg_hr = data.get('avg_heart_rate')
        max_hr = data.get('max_heart_rate')
        if avg_hr == 0:
            avg_hr = None
        if max_hr == 0:
            max_hr = None
        
        return CyclingWorkoutPayload(
            type="cycling_workout",
            workout_date=data.get('workout_date'),
            start_time=data.get('start_time'),
            sport=data.get('sport', 'indoor_cycle'),
            duration_sec=data.get('duration_sec'),
            avg_heart_rate=avg_hr,
            max_heart_rate=max_hr,
            avg_power_w=data.get('avg_power_w'),
            max_power_w=data.get('max_power_w'),
            normalized_power_w=data.get('normalized_power_w'),
            intensity_factor=data.get('intensity_factor'),
            tss=data.get('tss'),
            avg_cadence=data.get('avg_cadence'),
            distance_km=data.get('distance_km'),
            kcal_active=data.get('kcal_active'),
            kcal_total=data.get('kcal_total'),
            notes=data.get('notes', '')
        )
    elif payload_type == 'sleep_summary':
        return SleepSummaryPayload(
            type="sleep_summary",
            sleep_start_date=data.get('sleep_start_date'),
            sleep_end_date=data.get('sleep_end_date'),
            sleep_start_time=data.get('sleep_start_time'),
            sleep_end_time=data.get('sleep_end_time'),
            total_sleep_minutes=data.get('total_sleep_minutes'),
            deep_sleep_minutes=data.get('deep_sleep_minutes'),
            wakeups_count=data.get('wakeups_count'),
            min_heart_rate=data.get('min_heart_rate'),
            avg_heart_rate=data.get('avg_heart_rate'),
            max_heart_rate=data.get('max_heart_rate'),
            notes=data.get('notes', '')
        )
    else:
        return UnknownPayload(
            type="unknown",
            notes=data.get('notes', 'Unrecognized screenshot type')
        )


# ============== Main Extraction Functions ==============

def extract_from_image(
    image_file: BinaryIO,
    filename: str = "image.jpg"
) -> ExtractedPayload:
    """
    Extract data from an image using OpenAI Vision with automatic type classification.

    Args:
        image_file: Binary file object containing the image
        filename: Original filename for MIME type detection

    Returns:
        CyclingWorkoutPayload, SleepSummaryPayload, or UnknownPayload
    """
    # Encode image
    base64_image = encode_image_to_base64(image_file)
    mime_type = get_image_mime_type(filename)

    logger.info(f"Extracting data from image: {filename}")

    # Call OpenAI with unified prompt
    response_text = call_openai_vision(base64_image, mime_type, UNIFIED_EXTRACTION_PROMPT)
    logger.debug(f"OpenAI response: {response_text}")

    # Parse and create payload
    data = parse_json_response(response_text)
    return create_payload_from_data(data)


def extract_from_base64(
    base64_image: str,
    mime_type: str = "image/jpeg"
) -> ExtractedPayload:
    """
    Extract data from a base64-encoded image with automatic type classification.

    Args:
        base64_image: Base64-encoded image string
        mime_type: MIME type of the image

    Returns:
        CyclingWorkoutPayload, SleepSummaryPayload, or UnknownPayload
    """
    logger.info("Extracting data from base64 image")

    response_text = call_openai_vision(base64_image, mime_type, UNIFIED_EXTRACTION_PROMPT)
    logger.debug(f"OpenAI response: {response_text}")

    data = parse_json_response(response_text)
    return create_payload_from_data(data)


def extract_multiple_images(
    images: List[tuple]
) -> List[ExtractedPayload]:
    """
    Extract data from multiple images.

    Args:
        images: List of tuples (image_file, filename)

    Returns:
        List of payload objects
    """
    results = []
    for image_file, filename in images:
        try:
            payload = extract_from_image(image_file, filename)
            results.append(payload)
        except Exception as e:
            logger.error(f"Failed to extract from {filename}: {e}")
            results.append(UnknownPayload(
                type="unknown",
                notes=f"Extraction failed: {str(e)}"
            ))
    return results


# ============== Legacy Functions (for backwards compatibility) ==============

def extract_cycling_workout_from_image(
    image_file: BinaryIO,
    filename: str = "image.jpg"
) -> CyclingWorkoutPayload:
    """Legacy function - extracts cycling workout data from image"""
    payload = extract_from_image(image_file, filename)
    if isinstance(payload, CyclingWorkoutPayload):
        return payload
    # If it's not a cycling workout, return empty payload with any available data
    return CyclingWorkoutPayload()


def extract_sleep_summary_from_image(
    image_file: BinaryIO,
    filename: str = "image.jpg"
) -> SleepSummaryPayload:
    """Legacy function - extracts sleep summary data from image"""
    payload = extract_from_image(image_file, filename)
    if isinstance(payload, SleepSummaryPayload):
        return payload
    # If it's not a sleep summary, return empty payload
    return SleepSummaryPayload()
