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

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'duration_minutes': self.duration_minutes,
            'primary_zone': self.primary_zone,
            'overall_intensity': self.overall_intensity,
            'intervals': [i.to_dict() for i in self.intervals]
        }
        if self.comments:
            result['comments'] = self.comments
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

TRAINING_COACH_SYSTEM_PROMPT = """You are an experienced endurance cycling coach specializing in Norwegian-style polarized training.

You will receive a JSON object called "training_context" containing:
- evaluation_date: The date for which to provide a recommendation (YYYY-MM-DD)
- day: Current day's readiness, sleep, and cardio metrics (NO workout data - you're recommending WHAT to do)
- history_7d: Daily summaries for the 7 days BEFORE evaluation_date, including workouts done, readiness, and recovery
- baseline_30d: Rolling 30-day averages for RHR, HRV, sleep, readiness, and training load

Your task: Recommend the safest and most effective training for the evaluation_date.

## Decision Framework

### When to recommend REST or RECOVERY SPIN (Z1, 20-45 min):
- Readiness score < 50
- HRV status = -1 (significantly below baseline)
- RHR status = 1 (elevated above baseline)
- Poor sleep (< 6 hours or low deep sleep)
- Symptoms flag = true
- 2+ hard sessions (Z3+, TSS > 50) in last 3 days
- 3+ consecutive training days without rest

### When to recommend Z2 ENDURANCE (30-75 min):
- Readiness score 50-70
- Normal HRV/RHR (status = 0)
- Adequate sleep (6-8 hours)
- 1+ rest day in last 3 days
- Weekly TSS not already high

### When to recommend NORWEGIAN 4x4 (40-50 min total):
- Readiness score > 70
- HRV status >= 0 (normal or above baseline)
- RHR status <= 0 (normal or below baseline)
- Good sleep (7+ hours)
- No symptoms
- No hard session in last 2 days
- At least 1 rest day in last 4 days

### General Rules:
1. ALWAYS prefer conservative over aggressive when in doubt
2. Recovery is when adaptation happens - don't skip it
3. Never recommend hard training on consecutive days
4. Weekly structure should be roughly: 2 easy : 1 hard (or 3:1)
5. If last 7 days show high average TSS or many workouts, lean toward rest/recovery

## Output Format

Return ONLY a valid JSON object matching this exact schema:

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
        "notes": "<optional string>",
        "repeats": <optional int for intervals>,
        "work_minutes": <optional int>,
        "rest_minutes": <optional int>
      }
    ],
    "comments": "<optional string>"
  },
  "flags": {
    "ok_to_push": <bool>,
    "consider_rest_day": <bool>,
    "prioritize_sleep": <bool>,
    "monitor_hrv": <bool>
  }
}

For rest days, set session_plan to null.
Do NOT include any text outside the JSON object."""


TRAINING_USER_PROMPT_TEMPLATE = """Analyze the following training context and provide a training recommendation for {date}.

training_context:
{context_json}

Remember: Return ONLY the JSON recommendation, no other text."""


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
        sp = payload['session_plan']
        intervals = []
        for interval_data in sp.get('intervals', []):
            intervals.append(TrainingInterval(
                kind=interval_data.get('kind', 'steady'),
                duration_minutes=interval_data.get('duration_minutes', 0),
                target_zone=interval_data.get('target_zone', 'Z1'),
                notes=interval_data.get('notes'),
                repeats=interval_data.get('repeats'),
                work_minutes=interval_data.get('work_minutes'),
                rest_minutes=interval_data.get('rest_minutes')
            ))
        
        session_plan = TrainingSessionPlan(
            duration_minutes=sp.get('duration_minutes', 0),
            primary_zone=sp.get('primary_zone', 'Z1'),
            overall_intensity=sp.get('overall_intensity', 'easy'),
            intervals=intervals,
            comments=sp.get('comments')
        )
    
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
    
    # Build the user prompt with context
    context_json = json.dumps(context, indent=2, default=str)
    user_prompt = TRAINING_USER_PROMPT_TEMPLATE.format(
        date=date_str,
        context_json=context_json
    )
    
    logger.info(f"[TRAINING] Generating NEW recommendation for user={user_id}, date={date_str}")
    
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
    
    # Build the recommendation object
    try:
        # Parse session plan if present
        session_plan = None
        if data.get('session_plan'):
            sp = data['session_plan']
            intervals = []
            for interval_data in sp.get('intervals', []):
                intervals.append(TrainingInterval(
                    kind=interval_data.get('kind', 'steady'),
                    duration_minutes=interval_data.get('duration_minutes', 0),
                    target_zone=interval_data.get('target_zone', 'Z1'),
                    notes=interval_data.get('notes'),
                    repeats=interval_data.get('repeats'),
                    work_minutes=interval_data.get('work_minutes'),
                    rest_minutes=interval_data.get('rest_minutes')
                ))
            
            session_plan = TrainingSessionPlan(
                duration_minutes=sp.get('duration_minutes', 0),
                primary_zone=sp.get('primary_zone', 'Z1'),
                overall_intensity=sp.get('overall_intensity', 'easy'),
                intervals=intervals,
                comments=sp.get('comments')
            )
        
        recommendation = TrainingRecommendation(
            date=data.get('date', fallback_date),
            day_type=data.get('day_type', 'rest'),
            reason_short=data.get('reason_short', 'Unable to determine recommendation.'),
            session_plan=session_plan,
            flags=data.get('flags', {})
        )
        
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
        summary += f"\n📋 Session Plan ({sp.duration_minutes} min, {sp.primary_zone}):\n"
        for i, interval in enumerate(sp.intervals, 1):
            if interval.repeats:
                summary += f"  {i}. {interval.kind}: {interval.repeats}x {interval.work_minutes}min {interval.target_zone}"
                if interval.rest_minutes:
                    summary += f" / {interval.rest_minutes}min rest"
                summary += "\n"
            else:
                summary += f"  {i}. {interval.kind}: {interval.duration_minutes}min {interval.target_zone}\n"
    
    if recommendation.flags:
        flags = [k for k, v in recommendation.flags.items() if v]
        if flags:
            summary += f"\n⚠️ Flags: {', '.join(flags)}\n"
    
    return summary

