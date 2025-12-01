"""
Training Recommendation Service v2.5

Generates AI-powered daily training recommendations based on:
- Today's readiness, sleep, and cardio metrics
- Last 7 days of training history
- 30-day baseline statistics
- Training goals and interval guidelines

Uses OpenAI GPT-4o to analyze the context and recommend appropriate training
with dynamic interval structures.
"""
import json
import logging
from datetime import date
from typing import Optional, Dict, List, Literal, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


# ============== Data Models (CSResponse v1) ==============

@dataclass
class TrainingInterval:
    """
    A single interval/segment within a training session.
    
    CSResponse v1 supports dynamic intervals with power and HR ranges.
    """
    kind: Literal["warmup", "steady", "interval", "recovery", "cooldown", "progressive", "threshold", "vo2max"]
    duration_minutes: int
    target_zone: Literal["Z1", "Z2", "Z3", "Z4", "Z5"]
    notes: Optional[str] = None
    
    # Power targets (based on athlete_profile and interval_guidelines)
    target_power_w_min: Optional[int] = None
    target_power_w_max: Optional[int] = None
    
    # Heart rate targets
    target_hr_bpm_min: Optional[int] = None
    target_hr_bpm_max: Optional[int] = None
    expected_avg_hr_bpm: Optional[int] = None
    
    # For interval blocks (repeats structure)
    repeats: Optional[int] = None
    work_minutes: Optional[int] = None
    rest_minutes: Optional[int] = None
    
    # Block metadata
    block_name: Optional[str] = None  # e.g., "4x4 VO2max", "3x8 Threshold"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TrainingSessionPlan:
    """Complete session plan with intervals - CSResponse v1"""
    duration_minutes: int
    primary_zone: Literal["Z1", "Z2", "Z3", "Z4", "Z5"]
    overall_intensity: Literal["very_easy", "easy", "moderate", "hard", "very_hard"]
    intervals: List[TrainingInterval]
    comments: Optional[str] = None
    
    # Session-level targets
    session_target_power_w_min: Optional[int] = None
    session_target_power_w_max: Optional[int] = None
    session_target_hr_bpm_min: Optional[int] = None
    session_target_hr_bpm_max: Optional[int] = None
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
        if self.session_target_hr_bpm_min is not None:
            result['session_target_hr_bpm_min'] = self.session_target_hr_bpm_min
        if self.session_target_hr_bpm_max is not None:
            result['session_target_hr_bpm_max'] = self.session_target_hr_bpm_max
        if self.expected_avg_hr_bpm is not None:
            result['expected_avg_hr_bpm'] = self.expected_avg_hr_bpm
        if self.expected_avg_power_w is not None:
            result['expected_avg_power_w'] = self.expected_avg_power_w
        return result


@dataclass
class TrainingRecommendation:
    """
    Complete training recommendation for a day - CSResponse v1
    
    Supports expanded day_type options for interval workouts and
    includes analysis_text for coach reasoning.
    """
    date: str  # YYYY-MM-DD
    day_type: Literal[
        # Rest & Recovery
        "rest",
        "recovery_spin_z1",
        # Endurance
        "easy_endurance_z1",
        "steady_endurance_z2",
        "progressive_endurance",
        # Intervals
        "norwegian_4x4",
        "threshold_3x8",
        "vo2max_intervals",
        "cadence_drills",
        # Other
        "hybrid_endurance",
        "other"
    ]
    reason_short: str  # 1-3 sentences brief summary
    analysis_text: Optional[str] = None  # 3-6 sentences with detailed analysis
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
        if self.analysis_text:
            result['analysis_text'] = self.analysis_text
        return result


# ============== OpenAI System Prompt v4 ==============

TRAINING_COACH_SYSTEM_PROMPT_V4 = """You are an elite endurance cycling coach using Norwegian-style polarized training.

You receive training_context (v2.5) containing 30-day time-series, athlete profile,
7-day load, daily physiology, and interval guidelines.

## Your Job

1. **Determine the athlete's state:**
   - Evaluate fatigue state from HRV trend, RHR comparison, sleep quality
   - Assess readiness score and subjective inputs (energy, mood, muscle fatigue)
   - Consider 7-day training load and workout pattern

2. **Interpret historical data:**
   - Analyze power vs HR behavior from 30-day history
   - Compare today's cardio metrics to baseline
   - Identify signs of adaptation, fatigue, or overreaching

3. **Decide the training type:**
   - REST: Complete recovery day (no session)
   - RECOVERY: Light Z1 spinning, 20-30 min
   - Z1: Easy Zone 1 endurance
   - Z2: Steady Zone 2 endurance
   - ENDURANCE: Progressive build from Z1 to Z2
   - PROGRESSIVE ENDURANCE: Negative split with power build
   - 4x4 VO2max: Norwegian-style 4×4min intervals at Z4-Z5
   - 3x8 Threshold: Threshold intervals at Z3-Z4
   - CADENCE DRILLS: High-cadence technique work
   - HYBRID: Mixed session based on athlete state

4. **Only allow hard sessions (VO2max/threshold) when:**
   - Readiness score > 70
   - HRV status >= 0 (not depressed)
   - RHR status >= 0 (not elevated)
   - Sleep >= 7 hours
   - No symptoms
   - No hard session in last 2-3 days
   - 7-day load is manageable

## Input Structure (training_context v2.5)

- **evaluation_date**: The date you are recommending for
- **day**: Readiness, sleep, cardio for evaluation_date
- **history_7d**: 7 days BEFORE evaluation_date with workouts, TSS, cardio
- **baseline_30d**: 30-day averages for comparison
- **athlete_profile**: Max HR, resting HR, zone data (Z1, Z2, norwegian_4x4)
- **training_goals**: Allowed session types, duration limits, focus
- **interval_guidelines**: Power factors for computing interval targets
  - vo2_power_factor: Multiply Z2 power for VO2max intervals (e.g., 1.25)
  - threshold_power_factor: Multiply Z2 power for threshold intervals (e.g., 1.15)
  - warmup_minutes, cooldown_minutes: Standard warm-up/cool-down durations
- **analysis_requirements**: What must be in your analysis_text

## Computing Numeric Targets

Use athlete_profile.zones and interval_guidelines to calculate SPECIFIC targets:

### Z1 (warmup, recovery, cooldown):
- Power: zones.z1.min_power_w to zones.z1.avg_power_w
- HR: zones.z1.avg_hr_bpm ±5 bpm, or 55-65% of max_hr_bpm

### Z2 (steady endurance):
- Power: zones.z2.min_power_w to zones.z2.max_power_w (or avg * z2_power_factor)
- HR: zones.z2.avg_hr_bpm ±5 bpm, or 65-75% of max_hr_bpm

### Z4/Z5 (4x4 VO2max intervals):
- Power: zones.z2.avg_power_w * interval_guidelines.vo2_power_factor
- HR: 88-95% of max_hr_bpm

### Z3/Z4 (3x8 Threshold intervals):
- Power: zones.z2.avg_power_w * interval_guidelines.threshold_power_factor
- HR: 82-90% of max_hr_bpm

If zone data is NULL, estimate from max_hr_bpm and resting_hr_bpm_30d_avg.

## Output Format (CSResponse v1)

Return ONLY valid JSON:

{
  "date": "YYYY-MM-DD",
  "day_type": "rest" | "recovery_spin_z1" | "easy_endurance_z1" | "steady_endurance_z2" | 
              "progressive_endurance" | "norwegian_4x4" | "threshold_3x8" | 
              "vo2max_intervals" | "cadence_drills" | "hybrid_endurance" | "other",
  "reason_short": "1-3 sentence summary of recommendation",
  "analysis_text": "3-6 sentences including: HRV trend, RHR comparison, fatigue state, load reasoning, power/HR behavior",
  "session_plan": null | {
    "duration_minutes": <int>,
    "primary_zone": "Z1" | "Z2" | "Z3" | "Z4" | "Z5",
    "overall_intensity": "very_easy" | "easy" | "moderate" | "hard" | "very_hard",
    "session_target_power_w_min": <int>,
    "session_target_power_w_max": <int>,
    "session_target_hr_bpm_min": <int>,
    "session_target_hr_bpm_max": <int>,
    "expected_avg_hr_bpm": <int>,
    "expected_avg_power_w": <int>,
    "intervals": [
      {
        "kind": "warmup" | "steady" | "interval" | "recovery" | "cooldown" | "progressive" | "threshold" | "vo2max",
        "duration_minutes": <int>,
        "target_zone": "Z1" | "Z2" | "Z3" | "Z4" | "Z5",
        "target_power_w_min": <int>,
        "target_power_w_max": <int>,
        "target_hr_bpm_min": <int>,
        "target_hr_bpm_max": <int>,
        "expected_avg_hr_bpm": <int>,
        "notes": "<optional coaching cue>",
        "block_name": "<e.g., '4x4 VO2max'>",
        "repeats": <int for interval blocks>,
        "work_minutes": <int for interval blocks>,
        "rest_minutes": <int for interval blocks>
      }
    ],
    "comments": "<optional overall session comment>"
  },
  "flags": {
    "ok_to_push": <bool>,
    "consider_rest_day": <bool>,
    "prioritize_sleep": <bool>,
    "monitor_hrv": <bool>,
    "high_fatigue_detected": <bool>
  }
}

## CRITICAL RULES

1. For rest days: session_plan = null
2. For ALL other days: MUST fill target_hr_bpm_min/max for every interval
3. If power data exists: MUST fill target_power_w_min/max
4. analysis_text MUST include: HRV trend, RHR comparison, fatigue state, 7-day load reasoning, power/HR behavior
5. Use interval_guidelines to compute interval power targets
6. Do NOT leave HR fields empty for non-rest sessions
7. No text outside the JSON object
8. Respect training_goals.max_session_length_min and min_session_length_min

## Safety Bias

When in doubt (low readiness, elevated RHR, depressed HRV, high recent load):
- Choose easier day (rest or Z1/Z2)
- Reduce duration
- Lower power/HR targets
- Set consider_rest_day=true and high_fatigue_detected=true in flags"""

# Keep old prompt for backward compatibility
TRAINING_COACH_SYSTEM_PROMPT = TRAINING_COACH_SYSTEM_PROMPT_V4

TRAINING_USER_PROMPT_TEMPLATE = """Here is the training_context for the athlete and the evaluation date.
Using only this data, choose the best training for that date.
Respond only with valid JSON that matches the CSResponse v1 schema.

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
        rest_minutes=interval_data.get('rest_minutes'),
        block_name=interval_data.get('block_name')
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
        session_target_hr_bpm_min=sp.get('session_target_hr_bpm_min'),
        session_target_hr_bpm_max=sp.get('session_target_hr_bpm_max'),
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
        analysis_text=payload.get('analysis_text'),
        session_plan=session_plan,
        flags=payload.get('flags', {})
    )


# ============== Main Service Function ==============

def generate_training_recommendation(
    user_id: str,
    target_date: date,
    force_refresh: bool = False,
    use_v2_5: bool = True,
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
        use_v2_5: If True, use training_context_v2_5 (default True)
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
    
    # Use v2.5 context if enabled
    if use_v2_5:
        context = service.build_training_context_v2_5(target_date)
        logger.info(f"[TRAINING] Using training_context v2.5 for {date_str}")
    else:
        context = service.build_training_context(target_date)
    
    # Build the user prompt with context (just the JSON)
    context_json = json.dumps(context, indent=2, default=str)
    user_prompt = TRAINING_USER_PROMPT_TEMPLATE.format(context_json=context_json)
    
    logger.info(f"[TRAINING] Generating NEW recommendation for user={user_id}, date={date_str}")
    logger.debug(f"[TRAINING] Context: evaluation_date={context.get('evaluation_date')}, "
                 f"readiness_score={context.get('day', {}).get('readiness', {}).get('score')}")
    
    # Call OpenAI with GPT-4o (best available model)
    model_name = DEFAULT_MODEL_NAME
    try:
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": TRAINING_COACH_SYSTEM_PROMPT_V4},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Slightly creative but mostly deterministic
            max_tokens=2000   # Increased for longer analysis_text
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
    
    # Add analysis text if present
    if recommendation.analysis_text:
        summary += f"\n📊 Analysis:\n{recommendation.analysis_text}\n"
    
    if recommendation.session_plan:
        sp = recommendation.session_plan
        summary += f"\n📋 Session Plan ({sp.duration_minutes} min, {sp.primary_zone}, {sp.overall_intensity}):\n"
        
        # Session-level targets
        if sp.expected_avg_hr_bpm:
            summary += f"   Expected Avg HR: {sp.expected_avg_hr_bpm} bpm\n"
        if sp.expected_avg_power_w:
            summary += f"   Expected Avg Power: {sp.expected_avg_power_w}W\n"
        
        # Session target ranges
        if sp.session_target_hr_bpm_min and sp.session_target_hr_bpm_max:
            summary += f"   Target HR Range: {sp.session_target_hr_bpm_min}–{sp.session_target_hr_bpm_max} bpm\n"
        if sp.session_target_power_w_min and sp.session_target_power_w_max:
            summary += f"   Target Power Range: {sp.session_target_power_w_min}–{sp.session_target_power_w_max} W\n"
        
        summary += "\n"
        
        for i, interval in enumerate(sp.intervals, 1):
            # Handle block name if present
            block_prefix = f"[{interval.block_name}] " if interval.block_name else ""
            
            if interval.repeats:
                summary += f"  {i}. {block_prefix}{interval.kind}: {interval.repeats}× {interval.work_minutes or interval.duration_minutes}min {interval.target_zone}"
                if interval.rest_minutes:
                    summary += f" / {interval.rest_minutes}min rest"
            else:
                summary += f"  {i}. {block_prefix}{interval.kind}: {interval.duration_minutes}min {interval.target_zone}"
            
            # Add targets if available
            targets = []
            if interval.target_hr_bpm_min or interval.target_hr_bpm_max:
                hr_range = f"{interval.target_hr_bpm_min or '?'}–{interval.target_hr_bpm_max or '?'} bpm"
                targets.append(hr_range)
            if interval.expected_avg_hr_bpm:
                targets.append(f"avg ~{interval.expected_avg_hr_bpm} bpm")
            if interval.target_power_w_min or interval.target_power_w_max:
                power_range = f"{interval.target_power_w_min or '?'}–{interval.target_power_w_max or '?'}W"
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


# ============== Day Type Helpers ==============

DAY_TYPE_INFO = {
    'rest': {'label': 'Rest Day', 'color': 'rest', 'icon': '🛌'},
    'recovery_spin_z1': {'label': 'Recovery Z1', 'color': 'z1', 'icon': '🚴‍♂️'},
    'easy_endurance_z1': {'label': 'Easy Z1', 'color': 'z1', 'icon': '🚴'},
    'steady_endurance_z2': {'label': 'Endurance Z2', 'color': 'z2', 'icon': '🚴'},
    'progressive_endurance': {'label': 'Progressive', 'color': 'z2', 'icon': '📈'},
    'norwegian_4x4': {'label': '4×4 VO2max', 'color': 'hard', 'icon': '🔥'},
    'threshold_3x8': {'label': '3×8 Threshold', 'color': 'hard', 'icon': '⚡'},
    'vo2max_intervals': {'label': 'VO2max', 'color': 'hard', 'icon': '🔥'},
    'cadence_drills': {'label': 'Cadence', 'color': 'z2', 'icon': '🎯'},
    'hybrid_endurance': {'label': 'Hybrid', 'color': 'z2', 'icon': '🔄'},
    'other': {'label': 'Training', 'color': '', 'icon': '🏋️'},
}


def get_day_type_display(day_type: str) -> Dict[str, str]:
    """Get display info for a day type."""
    return DAY_TYPE_INFO.get(day_type, DAY_TYPE_INFO['other'])
