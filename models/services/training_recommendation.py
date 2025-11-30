"""
Training Recommendation Service

Generates AI-powered daily training recommendations based on:
- Today's readiness, sleep, and cardio metrics
- Last 7 days of training history
- 30-day baseline statistics

Uses OpenAI to analyze the context and recommend appropriate training.
"""
import json
import logging
from datetime import date
from typing import Optional, Dict, List, Literal, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


# ============== Data Models (using dataclasses for compatibility) ==============

@dataclass
class TrainingInterval:
    """A single interval/segment within a training session"""
    kind: Literal["warmup", "steady", "interval", "recovery", "cooldown"]
    duration_minutes: int
    target_zone: Literal["Z1", "Z2", "Z3", "Z4"]
    notes: Optional[str] = None
    
    # Power targets (optional, based on athlete's baseline)
    target_power_w_min: Optional[int] = None
    target_power_w_max: Optional[int] = None
    
    # Heart rate targets (optional)
    target_hr_bpm_min: Optional[int] = None
    target_hr_bpm_max: Optional[int] = None
    expected_avg_hr_bpm: Optional[int] = None
    
    # For interval blocks
    repeats: Optional[int] = None
    work_minutes: Optional[int] = None
    rest_minutes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TrainingSessionPlan:
    """Complete session plan with intervals"""
    duration_minutes: int
    primary_zone: Literal["Z1", "Z2", "Z3", "Z4"]
    overall_intensity: Literal["very_easy", "easy", "moderate", "hard"]
    intervals: List[TrainingInterval]
    comments: Optional[str] = None
    
    # Session-level targets (optional)
    session_target_power_w_min: Optional[int] = None
    session_target_power_w_max: Optional[int] = None
    expected_avg_hr_bpm: Optional[int] = None
    expected_avg_power_w: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'duration_minutes': self.duration_minutes,
            'primary_zone': self.primary_zone,
            'overall_intensity': self.overall_intensity,
            'intervals': [i.to_dict() for i in self.intervals]
        }
        if self.comments:
            result['comments'] = self.comments
        if self.session_target_power_w_min is not None:
            result['session_target_power_w_min'] = self.session_target_power_w_min
        if self.session_target_power_w_max is not None:
            result['session_target_power_w_max'] = self.session_target_power_w_max
        if self.expected_avg_hr_bpm is not None:
            result['expected_avg_hr_bpm'] = self.expected_avg_hr_bpm
        if self.expected_avg_power_w is not None:
            result['expected_avg_power_w'] = self.expected_avg_power_w
        return result


@dataclass
class TrainingRecommendation:
    """Complete training recommendation for a day"""
    date: str  # YYYY-MM-DD
    day_type: Literal[
        "rest",
        "recovery_spin_z1",
        "easy_endurance_z1",
        "steady_endurance_z2",
        "norwegian_4x4",
        "hybrid_endurance",
        "other"
    ]
    reason_short: str  # 1-3 sentences explaining the recommendation
    session_plan: Optional[TrainingSessionPlan] = None
    flags: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'date': self.date,
            'day_type': self.day_type,
            'reason_short': self.reason_short,
            'session_plan': self.session_plan.to_dict() if self.session_plan else None,
            'flags': self.flags
        }
        return result


# ============== OpenAI System Prompt ==============

TRAINING_COACH_SYSTEM_PROMPT = """You are an experienced endurance cycling coach using a Norwegian-style polarized training approach.

## Your Task
You will receive a JSON object called "training_context" for one evaluation_date. You must:
1. Choose the safest and most effective training for that date
2. Output ONLY a JSON object matching the TrainingRecommendation schema
3. Fill in SPECIFIC numeric power & HR targets for every interval using the athlete_profile data

## Input Structure (training_context)

- **evaluation_date**: The date you are recommending for (YYYY-MM-DD)

- **day**: The athlete's state on evaluation_date:
  - readiness: score (0-100), energy (1-5), mood (1-3), muscle_fatigue (1-3), hrv_status (-1/0/1), rhr_status (-1/0/1), symptoms (bool)
  - sleep: total_minutes, deep_minutes, awake_minutes, min_hr, max_hr
  - cardio: rhr_bpm, hrv_low_ms, hrv_high_ms

- **history_7d**: The 7 days BEFORE evaluation_date (D-7 to D-1), each with:
  - readiness_score, workout_type, workout_duration_minutes, tss, rhr_bpm, hrv_avg_ms

- **baseline_30d**: Rolling 30-day averages for comparison

- **athlete_profile**: CRITICAL data for setting numeric targets:
  - max_hr_bpm: Maximum HR observed in any workout (last 30 days)
  - resting_hr_bpm_30d_avg: Average resting HR
  - zones.z1: { avg_power_w, min_power_w, max_power_w, avg_hr_bpm } - typical Z1 workout stats
  - zones.z2: { avg_power_w, min_power_w, max_power_w, avg_hr_bpm } - typical Z2 workout stats
  - zones.norwegian_4x4: { avg_power_w, avg_hr_bpm } - typical 4x4 interval stats

## MANDATORY: Using athlete_profile for Numeric Targets

For EVERY non-rest session, you MUST set specific numeric targets based on athlete_profile:

### For Z1 intervals (warmup, recovery, cooldown, easy spinning):
- target_power_w_min/max: Use zones.z1.min_power_w to zones.z1.avg_power_w (or estimate 40-50% of zones.z2.avg_power_w if z1 data missing)
- target_hr_bpm_min/max: Use zones.z1.avg_hr_bpm ±5 bpm, or 55-65% of max_hr_bpm
- expected_avg_hr_bpm: zones.z1.avg_hr_bpm or 60% of max_hr_bpm

### For Z2 intervals (steady endurance):
- target_power_w_min/max: zones.z2.min_power_w to zones.z2.max_power_w
- target_hr_bpm_min/max: zones.z2.avg_hr_bpm ±5 bpm, or 65-75% of max_hr_bpm
- expected_avg_hr_bpm: zones.z2.avg_hr_bpm or 70% of max_hr_bpm

### For Z4 intervals (Norwegian 4x4 work intervals):
- target_power_w_min/max: zones.norwegian_4x4.avg_power_w ±10% (or 110-120% of zones.z2.avg_power_w if missing)
- target_hr_bpm_min/max: 88-95% of max_hr_bpm
- expected_avg_hr_bpm: zones.norwegian_4x4.avg_hr_bpm or 92% of max_hr_bpm

### If zone data is NULL:
- Use max_hr_bpm and resting_hr_bpm_30d_avg to estimate:
  - Z1 HR = resting + 20-40% of (max - resting)
  - Z2 HR = resting + 50-65% of (max - resting)
  - Z4 HR = 88-95% of max_hr_bpm
- If no power data available, set power fields to null but ALWAYS fill HR targets

## Decision Framework

### When to recommend REST (day_type="rest", session_plan=null):
- Readiness <40, symptoms=true, or signs of overreaching
- 3+ consecutive training days
- Explain clearly in reason_short

### When to recommend RECOVERY SPIN Z1 (20-45 min):
- Readiness 40-55 or recovering from hard effort
- Set HR targets to stay <65% max_hr_bpm

### When to recommend ENDURANCE Z2 (45-90 min):
- Readiness 60-75, good sleep, no recent hard days
- Use zones.z2 data for power/HR targets

### When to recommend NORWEGIAN 4x4:
- Readiness >70
- HRV/RHR status >= 0
- Good sleep (7+ hours)
- No symptoms
- No hard session in last 2-3 days
- Structure MUST be:
  1. Warmup: 10min Z1
  2. Interval block: repeats=4, work_minutes=4, rest_minutes=3, target_zone="Z4"
  3. Cooldown: 10min Z1

## Safety Bias
When in doubt (low readiness, elevated RHR, depressed HRV, high recent load):
- Choose easier day (rest or Z1/Z2)
- Reduce duration
- Lower power/HR targets

## Output Format

Return ONLY valid JSON matching this schema:

{
  "date": "YYYY-MM-DD",
  "day_type": "rest" | "recovery_spin_z1" | "easy_endurance_z1" | "steady_endurance_z2" | "norwegian_4x4" | "hybrid_endurance" | "other",
  "reason_short": "1-3 sentences explaining the recommendation based on the data",
  "session_plan": null | {
    "duration_minutes": <int>,
    "primary_zone": "Z1" | "Z2" | "Z3" | "Z4",
    "overall_intensity": "very_easy" | "easy" | "moderate" | "hard",
    "intervals": [
      {
        "kind": "warmup" | "steady" | "interval" | "recovery" | "cooldown",
        "duration_minutes": <int>,
        "target_zone": "Z1" | "Z2" | "Z3" | "Z4",
        "target_power_w_min": <int - REQUIRED if power data available>,
        "target_power_w_max": <int - REQUIRED if power data available>,
        "target_hr_bpm_min": <int - ALWAYS REQUIRED>,
        "target_hr_bpm_max": <int - ALWAYS REQUIRED>,
        "expected_avg_hr_bpm": <int - ALWAYS REQUIRED for main segments>,
        "notes": "<optional>",
        "repeats": <int - for interval blocks>,
        "work_minutes": <int - for interval blocks>,
        "rest_minutes": <int - for interval blocks>
      }
    ],
    "comments": "<optional>",
    "expected_avg_hr_bpm": <int - session average>,
    "expected_avg_power_w": <int - session average if power data available>
  },
  "flags": {
    "ok_to_push": <bool>,
    "consider_rest_day": <bool>,
    "prioritize_sleep": <bool>,
    "monitor_hrv": <bool>
  }
}

CRITICAL RULES:
- For rest days: session_plan = null
- For ALL other days: MUST fill target_hr_bpm_min/max and expected_avg_hr_bpm for every interval
- If power data exists in athlete_profile: MUST fill target_power_w_min/max
- Use athlete_profile.zones data to set realistic, personalized targets
- Do NOT leave HR fields empty/null for non-rest sessions
- No text outside the JSON object"""


TRAINING_USER_PROMPT_TEMPLATE = """Here is the training_context for the athlete and the evaluation date.
Using only this data, choose the best training for that date.
Respond only with valid JSON that matches the TrainingRecommendation schema.

{context_json}"""


# ============== Database Functions ==============

DEFAULT_MODEL_NAME = "gpt-4o"


def get_training_recommendation(
    user_id: str,
    target_date: date,
    connection_manager=None
) -> Optional[TrainingRecommendation]:
    """
    Fetch an existing training recommendation from the database.
    
    Args:
        user_id: The user's ID
        target_date: The date to fetch recommendation for
        connection_manager: Optional database connection manager
    
    Returns:
        TrainingRecommendation if found, None otherwise
    """
    from models.database.connection_manager import get_db_manager
    
    db = connection_manager or get_db_manager()
    date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, date) else str(target_date)
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT id, payload_json, model_name, created_at
                FROM training_recommendations
                WHERE user_id = %s AND date = %s
                LIMIT 1
            ''', (user_id, date_str))
            
            row = cursor.fetchone()
            
            if not row:
                logger.debug(f"[TRAINING] No stored recommendation for user={user_id}, date={date_str}")
                return None
            
            # Parse the stored JSON payload
            payload = row['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            
            recommendation = _build_recommendation_from_payload(payload, date_str)
            logger.info(f"[TRAINING] Loaded stored recommendation for {date_str}: {recommendation.day_type}")
            return recommendation
            
    except Exception as e:
        logger.error(f"[TRAINING] Error fetching recommendation: {e}")
        return None


def save_training_recommendation(
    user_id: str,
    target_date: date,
    rec: TrainingRecommendation,
    model_name: Optional[str] = None,
    connection_manager=None
) -> TrainingRecommendation:
    """
    Save or update a training recommendation in the database.
    
    Args:
        user_id: The user's ID
        target_date: The date for the recommendation
        rec: The TrainingRecommendation to save
        model_name: Optional name of the AI model used
        connection_manager: Optional database connection manager
    
    Returns:
        The same TrainingRecommendation (for chaining)
    """
    from models.database.connection_manager import get_db_manager
    
    db = connection_manager or get_db_manager()
    date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, date) else str(target_date)
    
    # Serialize the recommendation to JSON
    payload_json = json.dumps(rec.to_dict(), default=str)
    
    # Get duration from session plan if available
    duration_minutes = None
    if rec.session_plan:
        duration_minutes = rec.session_plan.duration_minutes
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Use INSERT ... ON DUPLICATE KEY UPDATE for upsert
            cursor.execute('''
                INSERT INTO training_recommendations 
                    (user_id, date, day_type, duration_minutes, payload_json, model_name, created_at, updated_at)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    day_type = VALUES(day_type),
                    duration_minutes = VALUES(duration_minutes),
                    payload_json = VALUES(payload_json),
                    model_name = VALUES(model_name),
                    updated_at = NOW()
            ''', (
                user_id,
                date_str,
                rec.day_type,
                duration_minutes,
                payload_json,
                model_name or DEFAULT_MODEL_NAME
            ))
            
            conn.commit()
            logger.info(f"[TRAINING] Saved recommendation for user={user_id}, date={date_str}, type={rec.day_type}")
            
    except Exception as e:
        logger.error(f"[TRAINING] Error saving recommendation: {e}")
        raise
    
    return rec


def _parse_interval(interval_data: Dict) -> TrainingInterval:
    """
    Parse a single interval from JSON data.
    
    Args:
        interval_data: Dictionary with interval fields
    
    Returns:
        TrainingInterval object
    """
    return TrainingInterval(
        kind=interval_data.get('kind', 'steady'),
        duration_minutes=interval_data.get('duration_minutes', 0),
        target_zone=interval_data.get('target_zone', 'Z1'),
        notes=interval_data.get('notes'),
        target_power_w_min=interval_data.get('target_power_w_min'),
        target_power_w_max=interval_data.get('target_power_w_max'),
        target_hr_bpm_min=interval_data.get('target_hr_bpm_min'),
        target_hr_bpm_max=interval_data.get('target_hr_bpm_max'),
        expected_avg_hr_bpm=interval_data.get('expected_avg_hr_bpm'),
        repeats=interval_data.get('repeats'),
        work_minutes=interval_data.get('work_minutes'),
        rest_minutes=interval_data.get('rest_minutes')
    )


def _parse_session_plan(sp: Dict) -> TrainingSessionPlan:
    """
    Parse a session plan from JSON data.
    
    Args:
        sp: Dictionary with session plan fields
    
    Returns:
        TrainingSessionPlan object
    """
    intervals = [_parse_interval(i) for i in sp.get('intervals', [])]
    
    return TrainingSessionPlan(
        duration_minutes=sp.get('duration_minutes', 0),
        primary_zone=sp.get('primary_zone', 'Z1'),
        overall_intensity=sp.get('overall_intensity', 'easy'),
        intervals=intervals,
        comments=sp.get('comments'),
        session_target_power_w_min=sp.get('session_target_power_w_min'),
        session_target_power_w_max=sp.get('session_target_power_w_max'),
        expected_avg_hr_bpm=sp.get('expected_avg_hr_bpm'),
        expected_avg_power_w=sp.get('expected_avg_power_w')
    )


def _build_recommendation_from_payload(payload: Dict, fallback_date: str) -> TrainingRecommendation:
    """
    Build a TrainingRecommendation from a stored JSON payload.
    
    Args:
        payload: The parsed JSON payload
        fallback_date: Date to use if not in payload
    
    Returns:
        TrainingRecommendation object
    """
    # Parse session plan if present
    session_plan = None
    if payload.get('session_plan'):
        session_plan = _parse_session_plan(payload['session_plan'])
    
    return TrainingRecommendation(
        date=payload.get('date', fallback_date),
        day_type=payload.get('day_type', 'rest'),
        reason_short=payload.get('reason_short', 'Unable to determine recommendation.'),
        session_plan=session_plan,
        flags=payload.get('flags', {})
    )


# ============== Main Service Function ==============

def generate_training_recommendation(
    user_id: str,
    target_date: date,
    force_refresh: bool = False,
    connection_manager=None
) -> TrainingRecommendation:
    """
    Generate or retrieve a training recommendation for the given date.
    
    If force_refresh is False, attempts to return a stored recommendation.
    Otherwise, generates a new one via OpenAI and stores it.
    
    Args:
        user_id: The user's ID
        target_date: The date to generate recommendation for
        force_refresh: If True, always call OpenAI even if stored rec exists
        connection_manager: Optional database connection manager
    
    Returns:
        TrainingRecommendation object
    
    Raises:
        ValueError: If OpenAI response cannot be parsed
        Exception: If OpenAI API call fails
    """
    from models.services.cycling_readiness_service import CyclingReadinessService
    from models.services.openai_extraction import get_openai_client
    
    date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, date) else str(target_date)
    
    # Check for existing recommendation if not forcing refresh
    if not force_refresh:
        existing = get_training_recommendation(user_id, target_date, connection_manager)
        if existing:
            logger.info(f"[TRAINING] Returning stored recommendation for {date_str}")
            return existing
    
    # Build the training context
    service = CyclingReadinessService(user_id=user_id, connection_manager=connection_manager)
    context = service.build_training_context(target_date)
    
    # Build the user prompt with context (just the JSON)
    context_json = json.dumps(context, indent=2, default=str)
    user_prompt = TRAINING_USER_PROMPT_TEMPLATE.format(context_json=context_json)
    
    logger.info(f"[TRAINING] Generating NEW recommendation for user={user_id}, date={date_str}")
    logger.debug(f"[TRAINING] Context: evaluation_date={context.get('evaluation_date')}, "
                 f"readiness_score={context.get('day', {}).get('readiness', {}).get('score')}")
    
    # Call OpenAI
    model_name = DEFAULT_MODEL_NAME
    try:
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": TRAINING_COACH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Slightly creative but mostly deterministic
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content
        logger.info(f"[TRAINING] OpenAI response received, length={len(response_text)}")
        
    except Exception as e:
        logger.error(f"[TRAINING] OpenAI API error: {e}")
        raise Exception(f"Failed to get training recommendation from AI: {str(e)}")
    
    # Parse the JSON response
    recommendation = parse_recommendation_response(response_text, date_str)
    
    logger.info(f"[TRAINING] Recommendation generated: day_type={recommendation.day_type}")
    
    # Save to database
    save_training_recommendation(
        user_id=user_id,
        target_date=target_date,
        rec=recommendation,
        model_name=model_name,
        connection_manager=connection_manager
    )
    
    return recommendation


def parse_recommendation_response(response_text: str, fallback_date: str) -> TrainingRecommendation:
    """
    Parse the OpenAI response into a TrainingRecommendation object.
    
    Args:
        response_text: Raw text response from OpenAI
        fallback_date: Date to use if not in response
    
    Returns:
        TrainingRecommendation object
    
    Raises:
        ValueError: If response cannot be parsed
    """
    # Clean up the response (remove markdown code blocks if present)
    text = response_text.strip()
    
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    
    if text.endswith('```'):
        text = text[:-3]
    
    text = text.strip()
    
    # Try to find JSON object if there's extra text
    if not text.startswith('{'):
        start = text.find('{')
        if start != -1:
            text = text[start:]
    
    if not text.endswith('}'):
        end = text.rfind('}')
        if end != -1:
            text = text[:end+1]
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"[TRAINING] JSON parse error: {e}")
        logger.error(f"[TRAINING] Raw response: {response_text[:500]}")
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
    
    # Build the recommendation using the reusable helper
    try:
        recommendation = _build_recommendation_from_payload(data, fallback_date)
        return recommendation
        
    except Exception as e:
        logger.error(f"[TRAINING] Error building recommendation object: {e}")
        raise ValueError(f"Failed to build recommendation from AI response: {str(e)}")


# ============== Utility Functions ==============

def get_recommendation_summary(recommendation: TrainingRecommendation) -> str:
    """
    Get a human-readable summary of the recommendation.
    
    Args:
        recommendation: The recommendation object
    
    Returns:
        A formatted string summary
    """
    summary = f"📅 {recommendation.date}\n"
    summary += f"🎯 {recommendation.day_type.replace('_', ' ').title()}\n"
    summary += f"💬 {recommendation.reason_short}\n"
    
    if recommendation.session_plan:
        sp = recommendation.session_plan
        summary += f"\n📋 Session Plan ({sp.duration_minutes} min, {sp.primary_zone}, {sp.overall_intensity}):\n"
        
        # Session-level targets
        if sp.expected_avg_hr_bpm:
            summary += f"   Expected Avg HR: {sp.expected_avg_hr_bpm} bpm\n"
        if sp.expected_avg_power_w:
            summary += f"   Expected Avg Power: {sp.expected_avg_power_w}W\n"
        
        summary += "\n"
        
        for i, interval in enumerate(sp.intervals, 1):
            if interval.repeats:
                summary += f"  {i}. {interval.kind}: {interval.repeats}x {interval.work_minutes}min {interval.target_zone}"
                if interval.rest_minutes:
                    summary += f" / {interval.rest_minutes}min rest"
            else:
                summary += f"  {i}. {interval.kind}: {interval.duration_minutes}min {interval.target_zone}"
            
            # Add targets if available
            targets = []
            if interval.target_hr_bpm_min or interval.target_hr_bpm_max:
                hr_range = f"{interval.target_hr_bpm_min or '?'}-{interval.target_hr_bpm_max or '?'} bpm"
                targets.append(hr_range)
            if interval.expected_avg_hr_bpm:
                targets.append(f"avg ~{interval.expected_avg_hr_bpm} bpm")
            if interval.target_power_w_min or interval.target_power_w_max:
                power_range = f"{interval.target_power_w_min or '?'}-{interval.target_power_w_max or '?'}W"
                targets.append(power_range)
            
            if targets:
                summary += f" ({', '.join(targets)})"
            
            if interval.notes:
                summary += f" [{interval.notes}]"
            
            summary += "\n"
        
        if sp.comments:
            summary += f"\n   💡 {sp.comments}\n"
    
    if recommendation.flags:
        flags = [k for k, v in recommendation.flags.items() if v]
        if flags:
            summary += f"\n⚠️ Flags: {', '.join(flags)}\n"
    
    return summary

