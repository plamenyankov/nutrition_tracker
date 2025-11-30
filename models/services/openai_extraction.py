"""
OpenAI-powered extraction service for cycling workout and sleep screenshots.
Uses GPT-4o vision capabilities to extract structured data from images.
Supports batch processing of multiple images in a single API call.
"""
import os
import json
import base64
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, BinaryIO, Dict, Any, List, Union, Tuple
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
    max_cadence: Optional[int] = None
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
    rem_minutes: Optional[int] = None
    core_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None
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


@dataclass
class CardioSeriesPayload:
    """Payload for Apple Health cardio series (RHR or HRV daily ranges)"""
    type: str = "cardio_series"
    metric: str = ""  # "resting_heart_rate" or "hrv"
    entries: List[Dict[str, Any]] = field(default_factory=list)  # [{date, low, high}, ...]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageResult:
    """Result from processing a single image"""
    filename: str
    type: str  # cycling_power, watch_workout, sleep_summary, cardio_series, unknown
    fields: Dict[str, Any]
    confidence: float


@dataclass 
class CanonicalWorkout:
    """Merged cycling workout data from all images"""
    date: Optional[str] = None
    duration_minutes: Optional[float] = None
    avg_power: Optional[float] = None
    max_power: Optional[float] = None
    normalized_power: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    cadence_avg: Optional[int] = None
    cadence_max: Optional[int] = None
    distance_km: Optional[float] = None
    calories_active: Optional[int] = None
    calories_total: Optional[int] = None
    tss: Optional[float] = None
    intensity_factor: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalSleep:
    """Merged sleep data from all images"""
    date: Optional[str] = None
    sleep_start: Optional[str] = None
    sleep_end: Optional[str] = None
    total_sleep_minutes: Optional[int] = None
    deep_sleep_minutes: Optional[int] = None
    rem_minutes: Optional[int] = None
    core_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None
    wakeups: Optional[int] = None
    min_hr: Optional[int] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchExtractionResult:
    """Complete result from batch image extraction"""
    image_results: List[ImageResult]
    canonical_workout: CanonicalWorkout
    canonical_sleep: CanonicalSleep
    missing_fields: Dict[str, List[str]]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'imageResults': [
                {
                    'filename': r.filename,
                    'type': r.type,
                    'fields': r.fields,
                    'confidence': r.confidence
                } for r in self.image_results
            ],
            'canonicalWorkout': self.canonical_workout.to_dict(),
            'canonicalSleep': self.canonical_sleep.to_dict(),
            'missingFields': self.missing_fields,
            'errors': self.errors
        }


# Type alias for any payload
ExtractedPayload = Union[CyclingWorkoutPayload, SleepSummaryPayload, CardioSeriesPayload, UnknownPayload]


# ============== Batch Extraction Prompt (1-4 images, single API call) ==============

BATCH_EXTRACTION_PROMPT = """You are analyzing 1–4 fitness screenshots from cycling apps, Apple Watch, or Apple Health.

=== IMAGE CLASSIFICATION RULES ===

For EACH image, classify it as one of:

"cycling_power" if the image shows ANY of:
- Power metrics (watts, W, WATT)
- Tacx, Zwift, Garmin, TrainerRoad, Wahoo, Strava, Peloton app
- TSS, IF, NP (Training Stress Score, Intensity Factor, Normalized Power)
- Cadence (RPM)
- Cycling-specific graphs or power curves

"watch_workout" if the image shows:
- Apple Watch workout summary with "Indoor Cycle", "Outdoor Cycle", or "Cycling"
- Duration, heart rate, calories for a cycling activity
- Apple Fitness+ cycling workout

"sleep_summary" if the image shows:
- Sleep stages: REM, Core, Deep, Awake
- Apple Health sleep analysis
- Total sleep time with sleep/wake times

"cardio_series" if the image shows:
- Apple Health "All Recorded Data" list view
- Multiple rows with date + range format (e.g., "73 – 73 30 Nov 2025", "12 – 36 29 Nov 2025")
- Pattern: number – number [date]
- Header may mention "Resting Heart Rate", "Heart Rate Variability", "BPM", or "ms"
- If header/unit not visible, use range pattern:
  * If all rows have low == high (e.g., 73–73, 72–72) → metric = "resting_heart_rate"
  * If rows commonly have low != high (e.g., 12–36, 8–38) → metric = "hrv"

"unknown" ONLY if:
- The image contains NO cycling metrics AND NO sleep data AND NO cardio series data
- Examples: food photos, random apps, non-fitness screens

CRITICAL: Do NOT classify cycling screenshots as "unknown". If you see ANY power, distance, duration, heart rate, or calories from an exercise, it's likely cycling.

=== EXTRACTION FIELDS ===

For cycling (cycling_power or watch_workout):
- date: YYYY-MM-DD
- duration_minutes: decimal (convert from HH:MM:SS)
- avg_power: watts
- max_power: watts  
- normalized_power: NP in watts
- avg_hr: BPM
- max_hr: BPM
- cadence_avg: RPM
- cadence_max: RPM
- distance_km: kilometers (convert from miles: 1 mi = 1.60934 km)
- calories_active: active calories
- calories_total: total calories
- tss: Training Stress Score
- intensity_factor: IF as decimal

For sleep (sleep_summary):
- date: wake-up date YYYY-MM-DD
- sleep_start: HH:MM 24h format
- sleep_end: HH:MM 24h format
- total_sleep_minutes
- deep_sleep_minutes
- rem_minutes
- core_minutes
- awake_minutes
- wakeups: count
- min_hr, avg_hr, max_hr: BPM

For cardio_series:
- metric: "resting_heart_rate" or "hrv"
- entries: array of {date: "YYYY-MM-DD", low: number, high: number}
- Extract ALL visible rows from the list
- Normalize dates to YYYY-MM-DD format
- Return numbers as numeric values (not strings)
- Classification rules:
  * If header mentions "BPM", "beats per minute", "Resting Heart Rate" → metric = "resting_heart_rate"
  * If header mentions "ms", "milliseconds", "HRV", "Heart Rate Variability" → metric = "hrv"
  * If header not visible:
    - If all rows have low == high → metric = "resting_heart_rate"
    - If rows commonly have low != high → metric = "hrv"

=== MERGING RULES ===

- Use the latest date across all images as canonical date
- For each field: use value with highest confidence, or first non-null value
- Never infer or guess values not shown in screenshots

=== OUTPUT FORMAT (STRICT JSON) ===

{
  "imageResults": [
    {
      "filename": "",
      "type": "cycling_power | watch_workout | sleep_summary | cardio_series | unknown",
      "fields": { },
      "confidence": 0.0
    }
  ],
  "canonicalWorkout": {
    "date": null,
    "duration_minutes": null,
    "avg_power": null,
    "max_power": null,
    "normalized_power": null,
    "avg_hr": null,
    "max_hr": null,
    "cadence_avg": null,
    "cadence_max": null,
    "distance_km": null,
    "calories_active": null,
    "calories_total": null,
    "tss": null,
    "intensity_factor": null
  },
  "canonicalSleep": {
    "date": null,
    "sleep_start": null,
    "sleep_end": null,
    "total_sleep_minutes": null,
    "deep_sleep_minutes": null,
    "rem_minutes": null,
    "core_minutes": null,
    "awake_minutes": null,
    "wakeups": null,
    "min_hr": null,
    "avg_hr": null,
    "max_hr": null
  },
  "missingFields": {
    "workout": [],
    "sleep": []
  },
  "errors": []
}

Rules:
- Return JSON ONLY (no markdown, no comments)
- All fields must be present
- Use null for missing values
- Confidence = 0.0 to 1.0
- Numbers must be numeric, not strings"""


# ============== Unified Single-Image Prompt (robust classification) ==============

UNIFIED_EXTRACTION_PROMPT = """You are a strict data-extraction assistant for a cycling and sleep tracking app.

You receive ONE screenshot. It can be:
1) A cycling workout screen from Tacx, Zwift, Garmin, TrainerRoad, Wahoo, Strava, or similar
2) An Apple Watch Indoor Cycle / Outdoor Cycle / Cycling workout summary
3) An Apple Fitness+ cycling workout
4) An Apple Health sleep summary
5) An Apple Health "All Recorded Data" list showing RHR or HRV ranges
6) Or something unrelated

=== STEP 1: CLASSIFY THE IMAGE ===

Decide the `type` using these rules:

TYPE = "cycling_workout" if ANY of these are true:
- Shows watts / W / WATT / power metrics
- Shows cycling-specific data: cadence (RPM), distance (km/mi), speed (km/h, mph)
- Shows Training Stress Score (TSS) or Intensity Factor (IF) or Normalized Power (NP)
- Displays "Indoor Cycle", "Outdoor Cycle", "Cycling", "Bike", "Ride" as workout type
- Has Tacx, Zwift, Garmin, TrainerRoad, Wahoo, Strava, Peloton branding
- Is an Apple Watch workout summary showing duration, heart rate, calories with cycling context
- Shows a cycling workout graph or power curve

TYPE = "sleep_summary" if:
- Shows sleep stages: REM / Core / Deep / Awake
- Displays total sleep duration with sleep/wake times
- Has Apple Health sleep analysis or similar sleep tracking data

TYPE = "cardio_series" if:
- Shows Apple Health "All Recorded Data" list view
- Multiple rows with date + range format (e.g., "73 – 73 30 Nov 2025", "12 – 36 29 Nov 2025")
- Pattern: number – number [date]
- Header may mention "Resting Heart Rate", "Heart Rate Variability", "BPM", or "ms"
- If header/unit not visible, use range pattern:
  * If all rows have low == high (e.g., 73–73, 72–72) → metric = "resting_heart_rate"
  * If rows commonly have low != high (e.g., 12–36, 8–38) → metric = "hrv"

TYPE = "unknown" ONLY if:
- The image does NOT contain ANY cycling metrics (watts, distance, cadence, cycling workout)
- AND does NOT contain ANY sleep data (sleep stages, sleep duration)
- AND does NOT contain ANY cardio series data (RHR/HRV ranges)
- For example: a photo of food, a random app, a non-fitness screen

CRITICAL: If you see ANY cycling-related metrics (power, distance, cadence, heart rate during workout, calories burned in exercise), classify as "cycling_workout". Do NOT mark cycling screenshots as "unknown".

=== STEP 2: EXTRACT DATA ===

If type = "cycling_workout", extract these fields (use null if NOT visible):

- workout_date: "YYYY-MM-DD" (look for date in header or summary)
- start_time: "HH:MM" in 24h format
- sport: "indoor_cycle" | "outdoor_cycle" | "cycling"
- duration_sec: total duration in SECONDS (convert from HH:MM:SS or MM:SS)
- distance_km: distance in kilometers (convert from miles if shown as mi: 1 mi = 1.60934 km)
- avg_power_w: average power in watts
- max_power_w: maximum power in watts
- normalized_power_w: NP in watts
- intensity_factor: IF as decimal (e.g., 0.85)
- tss: Training Stress Score
- avg_heart_rate: average HR in BPM (look for "Avg" or "Average" near heart icon or "Heart Rate")
- max_heart_rate: maximum HR in BPM (look for "Max" or "Peak")
- avg_cadence: average cadence in RPM
- kcal_active: active calories (smaller number, labeled "Active" or separate from total)
- kcal_total: total calories (larger number, or only number shown)

HEART RATE HINTS:
- Apple Watch: Look for heart icon ♥ with numbers, often shows "Avg" and "Max" separately
- Tacx/Zwift/Garmin: HR is usually in a dedicated section with BPM label
- If only one HR value is shown, it's typically the average

POWER HINTS:
- Look for "W", "watts", "WATT" labels
- "Avg Power" or just "Power" → avg_power_w
- "Max Power" → max_power_w
- "NP" or "Normalized Power" → normalized_power_w

If type = "sleep_summary", extract these fields:

- sleep_start_date: "YYYY-MM-DD" (the night you went to bed)
- sleep_end_date: "YYYY-MM-DD" (the morning you woke up - this is the main date)
- sleep_start_time: "HH:MM" in 24h format
- sleep_end_time: "HH:MM" in 24h format
- total_sleep_minutes: total sleep in minutes (convert from hours if needed)
- deep_sleep_minutes: deep sleep in minutes
- rem_minutes: REM sleep in minutes (if shown)
- core_minutes: core/light sleep in minutes (if shown)
- awake_minutes: awake time in minutes (if shown)
- wakeups_count: number of times woken up
- min_heart_rate: minimum HR during sleep
- avg_heart_rate: average HR during sleep
- max_heart_rate: maximum HR during sleep

If type = "cardio_series", extract these fields:

- metric: "resting_heart_rate" or "hrv"
- entries: array of {date: "YYYY-MM-DD", low: number, high: number}
- Extract ALL visible rows from the list
- Normalize dates to YYYY-MM-DD format
- Return numbers as numeric values (not strings)
- Classification rules:
  * If header mentions "BPM", "beats per minute", "Resting Heart Rate" → metric = "resting_heart_rate"
  * If header mentions "ms", "milliseconds", "HRV", "Heart Rate Variability" → metric = "hrv"
  * If header not visible:
    - If all rows have low == high → metric = "resting_heart_rate"
    - If rows commonly have low != high → metric = "hrv"

=== STEP 3: OUTPUT FORMAT ===

Return ONLY this JSON structure (no markdown, no explanation, no comments):

{
  "type": "cycling_workout",
  "source_hint": "tacx | zwift | garmin | trainerroad | wahoo | strava | apple_watch | apple_fitness | peloton | other",
  "workout_date": null,
  "start_time": null,
  "sport": "indoor_cycle",
  "duration_sec": null,
  "distance_km": null,
  "avg_power_w": null,
  "max_power_w": null,
  "normalized_power_w": null,
  "intensity_factor": null,
  "tss": null,
  "avg_heart_rate": null,
  "max_heart_rate": null,
  "avg_cadence": null,
  "kcal_active": null,
  "kcal_total": null,
  "notes": ""
}

OR for sleep:

{
  "type": "sleep_summary",
  "source_hint": "apple_health | other",
  "sleep_start_date": null,
  "sleep_end_date": null,
  "sleep_start_time": null,
  "sleep_end_time": null,
  "total_sleep_minutes": null,
  "deep_sleep_minutes": null,
  "rem_minutes": null,
  "core_minutes": null,
  "awake_minutes": null,
  "wakeups_count": null,
  "min_heart_rate": null,
  "avg_heart_rate": null,
  "max_heart_rate": null,
  "notes": ""
}

OR for cardio_series (Resting Heart Rate - values are the same):

{
  "type": "cardio_series",
  "source_hint": "apple_health",
  "metric": "resting_heart_rate",
  "entries": [
    {"date": "2025-11-30", "low": 73, "high": 73},
    {"date": "2025-11-29", "low": 72, "high": 72}
  ],
  "notes": ""
}

OR for cardio_series (Heart Rate Variability - values differ):

{
  "type": "cardio_series",
  "source_hint": "apple_health",
  "metric": "hrv",
  "entries": [
    {"date": "2025-11-30", "low": 12, "high": 36},
    {"date": "2025-11-29", "low": 8, "high": 42}
  ],
  "notes": ""
}

OR for unknown:

{
  "type": "unknown",
  "source_hint": "unknown",
  "notes": "Brief description of what the image shows"
}

RULES:
- All numeric values must be numbers, not strings
- Use null for values not visible in the screenshot
- Do NOT guess or infer values not explicitly shown
- Return valid JSON only, no markdown code fences
- If in doubt between cycling_workout and unknown, choose cycling_workout if ANY fitness metrics are visible"""


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
    original_text = text  # Keep for error logging

    # Remove markdown code blocks if present (```json or ``` or ```JSON)
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove first line (```json or ```)
        if lines[0].startswith('```'):
            lines = lines[1:]
        # Remove last line (```) if present
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    
    # Also handle case where ``` is at the end but not on its own line
    if text.endswith('```'):
        text = text[:-3].strip()
    
    # Try to find JSON object in the text if parsing fails
    if not text.startswith('{'):
        # Look for first { and last }
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx + 1]
            logger.warning(f"[PARSE] Extracted JSON from response (had extra text)")

    try:
        parsed = json.loads(text)
        logger.debug(f"[PARSE] Successfully parsed JSON with type: {parsed.get('type', 'unknown')}")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"[PARSE] Failed to parse JSON: {e}")
        logger.error(f"[PARSE] Original response: {original_text[:1000]}")
        logger.error(f"[PARSE] Cleaned text: {text[:1000]}")
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


def call_openai_vision_batch(
    images: List[Tuple[str, str, str]],  # List of (base64_image, mime_type, filename)
    prompt: str = None
) -> str:
    """
    Make OpenAI Vision API call with MULTIPLE images in a single request.
    
    Args:
        images: List of tuples (base64_image, mime_type, filename)
        prompt: Optional custom prompt (uses BATCH_EXTRACTION_PROMPT if None)
    
    Returns:
        Raw response text from OpenAI
    """
    if not images:
        raise ValueError("No images provided for batch extraction")
    
    if len(images) > 4:
        raise ValueError("Maximum 4 images allowed per batch extraction")
    
    client = get_openai_client()
    prompt = prompt or BATCH_EXTRACTION_PROMPT
    
    # Build content array with text prompt + all images
    content = [{"type": "text", "text": prompt}]
    
    for base64_image, mime_type, filename in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}",
                "detail": "high"
            }
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": content
            }],
            temperature=0,
            max_tokens=4000  # Increased for multiple images
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        logger.error(f"OpenAI API batch error: {error_msg}")
        if "insufficient_quota" in error_msg or "429" in error_msg:
            raise ValueError("OpenAI API quota exceeded. Please check your billing and add credits at https://platform.openai.com/account/billing")
        elif "invalid_api_key" in error_msg or "401" in error_msg:
            raise ValueError("Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env file")
        else:
            raise ValueError(f"OpenAI API error: {error_msg}")


def extract_batch(
    images: List[Tuple[BinaryIO, str]]
) -> BatchExtractionResult:
    """
    Extract data from 1-4 images in a SINGLE OpenAI API call.
    
    This is the recommended method for processing multiple images together
    as it reduces API calls and improves merging accuracy.
    
    Args:
        images: List of tuples (image_file, filename)
    
    Returns:
        BatchExtractionResult containing:
        - image_results: Individual extraction results per image
        - canonical_workout: Merged cycling workout data
        - canonical_sleep: Merged sleep data
        - missing_fields: Fields that couldn't be extracted
        - errors: Any extraction errors
    """
    if not images:
        return BatchExtractionResult(
            image_results=[],
            canonical_workout=CanonicalWorkout(),
            canonical_sleep=CanonicalSleep(),
            missing_fields={'workout': [], 'sleep': []},
            errors=['No images provided']
        )
    
    if len(images) > 4:
        logger.warning(f"Received {len(images)} images, limiting to first 4")
        images = images[:4]
    
    # Prepare images for API call
    prepared_images = []
    filenames = []
    for image_file, filename in images:
        try:
            base64_image = encode_image_to_base64(image_file)
            mime_type = get_image_mime_type(filename)
            prepared_images.append((base64_image, mime_type, filename))
            filenames.append(filename)
        except Exception as e:
            logger.error(f"Failed to encode image {filename}: {e}")
    
    if not prepared_images:
        return BatchExtractionResult(
            image_results=[],
            canonical_workout=CanonicalWorkout(),
            canonical_sleep=CanonicalSleep(),
            missing_fields={'workout': [], 'sleep': []},
            errors=['Failed to encode any images']
        )
    
    logger.info(f"Batch extracting data from {len(prepared_images)} images: {filenames}")
    
    try:
        # Single API call for all images
        response_text = call_openai_vision_batch(prepared_images)
        logger.debug(f"OpenAI batch response: {response_text}")
        
        # Parse response
        data = parse_json_response(response_text)
        
        # Build result from parsed data
        return _build_batch_result(data, filenames)
        
    except Exception as e:
        logger.error(f"Batch extraction failed: {e}")
        return BatchExtractionResult(
            image_results=[],
            canonical_workout=CanonicalWorkout(),
            canonical_sleep=CanonicalSleep(),
            missing_fields={'workout': [], 'sleep': []},
            errors=[str(e)]
        )


def _build_batch_result(data: Dict[str, Any], filenames: List[str]) -> BatchExtractionResult:
    """Build BatchExtractionResult from parsed OpenAI response"""
    
    # Parse image results
    image_results = []
    for i, img_data in enumerate(data.get('imageResults', [])):
        filename = img_data.get('filename') or (filenames[i] if i < len(filenames) else f"image_{i}")
        image_results.append(ImageResult(
            filename=filename,
            type=img_data.get('type', 'unknown'),
            fields=img_data.get('fields', {}),
            confidence=float(img_data.get('confidence', 0.0))
        ))
    
    # Parse canonical workout
    cw_data = data.get('canonicalWorkout', {})
    canonical_workout = CanonicalWorkout(
        date=cw_data.get('date'),
        duration_minutes=cw_data.get('duration_minutes'),
        avg_power=cw_data.get('avg_power'),
        max_power=cw_data.get('max_power'),
        normalized_power=cw_data.get('normalized_power'),
        avg_hr=cw_data.get('avg_hr'),
        max_hr=cw_data.get('max_hr'),
        cadence_avg=cw_data.get('cadence_avg'),
        cadence_max=cw_data.get('cadence_max'),
        distance_km=cw_data.get('distance_km'),
        calories_active=cw_data.get('calories_active'),
        calories_total=cw_data.get('calories_total'),
        tss=cw_data.get('tss'),
        intensity_factor=cw_data.get('intensity_factor')
    )
    
    # Parse canonical sleep
    cs_data = data.get('canonicalSleep', {})
    canonical_sleep = CanonicalSleep(
        date=cs_data.get('date'),
        sleep_start=cs_data.get('sleep_start'),
        sleep_end=cs_data.get('sleep_end'),
        total_sleep_minutes=cs_data.get('total_sleep_minutes'),
        deep_sleep_minutes=cs_data.get('deep_sleep_minutes'),
        rem_minutes=cs_data.get('rem_minutes'),
        core_minutes=cs_data.get('core_minutes'),
        awake_minutes=cs_data.get('awake_minutes'),
        wakeups=cs_data.get('wakeups'),
        min_hr=cs_data.get('min_hr'),
        avg_hr=cs_data.get('avg_hr'),
        max_hr=cs_data.get('max_hr')
    )
    
    # Parse missing fields
    missing_fields = data.get('missingFields', {'workout': [], 'sleep': []})
    if not isinstance(missing_fields, dict):
        missing_fields = {'workout': [], 'sleep': []}
    
    # Parse errors
    errors = data.get('errors', [])
    if not isinstance(errors, list):
        errors = []
    
    return BatchExtractionResult(
        image_results=image_results,
        canonical_workout=canonical_workout,
        canonical_sleep=canonical_sleep,
        missing_fields=missing_fields,
        errors=errors
    )


def create_payload_from_data(data: Dict[str, Any]) -> ExtractedPayload:
    """Create the appropriate payload object from parsed JSON data"""
    payload_type = data.get('type', 'unknown')
    source_hint = data.get('source_hint', 'unknown')
    
    # Log classification for debugging
    logger.info(f"[EXTRACTION] Type: {payload_type}, Source: {source_hint}")

    if payload_type == 'cycling_workout':
        # Convert 0 to None for heart rate fields (0 is not a valid HR)
        avg_hr = data.get('avg_heart_rate')
        max_hr = data.get('max_heart_rate')
        if avg_hr == 0:
            avg_hr = None
        if max_hr == 0:
            max_hr = None
        
        # Log key cycling fields for debugging
        logger.info(f"[EXTRACTION] Cycling data: date={data.get('workout_date')}, "
                   f"power={data.get('avg_power_w')}W, HR={avg_hr}/{max_hr}, "
                   f"duration={data.get('duration_sec')}s, TSS={data.get('tss')}")
        
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
        # Log key sleep fields for debugging
        logger.info(f"[EXTRACTION] Sleep data: date={data.get('sleep_end_date')}, "
                   f"total={data.get('total_sleep_minutes')}min, deep={data.get('deep_sleep_minutes')}min")
        
        return SleepSummaryPayload(
            type="sleep_summary",
            sleep_start_date=data.get('sleep_start_date'),
            sleep_end_date=data.get('sleep_end_date'),
            sleep_start_time=data.get('sleep_start_time'),
            sleep_end_time=data.get('sleep_end_time'),
            total_sleep_minutes=data.get('total_sleep_minutes'),
            deep_sleep_minutes=data.get('deep_sleep_minutes'),
            rem_minutes=data.get('rem_minutes'),
            core_minutes=data.get('core_minutes'),
            awake_minutes=data.get('awake_minutes'),
            wakeups_count=data.get('wakeups_count'),
            min_heart_rate=data.get('min_heart_rate'),
            avg_heart_rate=data.get('avg_heart_rate'),
            max_heart_rate=data.get('max_heart_rate'),
            notes=data.get('notes', '')
        )
    elif payload_type == 'cardio_series':
        # Log key cardio series fields for debugging
        entries = data.get('entries', [])
        logger.info(f"[EXTRACTION] Cardio series: metric={data.get('metric')}, entries={len(entries)}")
        
        return CardioSeriesPayload(
            type="cardio_series",
            metric=data.get('metric', ''),
            entries=entries,
            notes=data.get('notes', '')
        )
    else:
        # Log unknown type with notes for debugging
        logger.warning(f"[EXTRACTION] Unknown type! Notes: {data.get('notes', 'No notes')}")
        
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

    logger.info(f"[EXTRACTION] Processing image: {filename} ({mime_type})")

    try:
        # Call OpenAI with unified prompt
        response_text = call_openai_vision(base64_image, mime_type, UNIFIED_EXTRACTION_PROMPT)
        
        # Log raw response for debugging (truncated)
        response_preview = response_text[:500] if len(response_text) > 500 else response_text
        logger.info(f"[EXTRACTION] Raw OpenAI response for {filename}: {response_preview}")

        # Parse and create payload
        data = parse_json_response(response_text)
        
        # Log parsed type
        parsed_type = data.get('type', 'unknown')
        logger.info(f"[EXTRACTION] {filename} -> classified as: {parsed_type}")
        
        payload = create_payload_from_data(data)
        
        # Final summary log
        logger.info(f"[EXTRACTION] {filename} complete: type={payload.type}")
        
        return payload
        
    except Exception as e:
        logger.error(f"[EXTRACTION] Failed to process {filename}: {str(e)}")
        return UnknownPayload(
            type="unknown",
            notes=f"Extraction error: {str(e)}"
        )


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
