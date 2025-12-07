"""
AI Workout Analyzer Service v1

Generates AI-powered post-workout analysis based on:
- The actual workout data (power, HR, duration, TSS)
- Day context (readiness, sleep, HRV/RHR trends)
- AI Coach recommendation for that day (if exists)

Uses OpenAI GPT-4o to analyze workout execution quality,
compare planned vs actual, and assess fatigue risk.
"""
import json
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


# ============== Data Models ==============

@dataclass
class AnalysisDimensionScores:
    """Dimension-level scores for workout analysis."""
    intensity: int  # 0-100: How appropriate was the intensity for the athlete's state
    duration: int   # 0-100: How appropriate was the duration
    hr_response: int  # 0-100: How well did HR respond to the effort

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class AnalysisScores:
    """Complete scoring structure for workout analysis."""
    overall_score: int  # 0-100: Overall execution quality
    dimension_scores: AnalysisDimensionScores
    label: str  # "excellent" | "good" | "ok" | "too_easy" | "overreached"
    fatigue_risk: str  # "low" | "medium" | "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_score': self.overall_score,
            'dimension_scores': self.dimension_scores.to_dict(),
            'label': self.label,
            'fatigue_risk': self.fatigue_risk
        }


@dataclass
class AnalysisCoachComparison:
    """Comparison between AI Coach plan and actual workout."""
    has_coach_plan: bool
    plan_type: Optional[str]  # e.g., "endurance_z2", "recovery_z1", "4x4_vo2"
    compliance_score: int  # 0-100: How well did athlete follow the plan
    notes: str  # Comparison notes
    
    # Actual planned values from the stored AI Coach recommendation
    # These come directly from the coach's session_plan, NOT from templates
    planned_duration_min: Optional[int] = None
    planned_power_min: Optional[int] = None
    planned_power_max: Optional[int] = None
    planned_hr_min: Optional[int] = None
    planned_hr_max: Optional[int] = None
    planned_avg_power: Optional[int] = None
    planned_avg_hr: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'has_coach_plan': self.has_coach_plan,
            'plan_type': self.plan_type,
            'compliance_score': self.compliance_score,
            'notes': self.notes
        }
        # Include planned values if coach plan exists
        if self.has_coach_plan:
            result['planned_duration_min'] = self.planned_duration_min
            result['planned_power'] = {
                'min': self.planned_power_min,
                'max': self.planned_power_max,
                'expected_avg': self.planned_avg_power
            } if self.planned_power_min or self.planned_power_max else None
            result['planned_hr'] = {
                'min': self.planned_hr_min,
                'max': self.planned_hr_max,
                'expected_avg': self.planned_avg_hr
            } if self.planned_hr_min or self.planned_hr_max else None
        return result


@dataclass
class AnalysisSummary:
    """Summary text for workout analysis."""
    short_text: str  # 1-2 sentences
    detailed_text: str  # 3-6 sentences with full analysis

    def to_dict(self) -> Dict[str, str]:
        return {
            'short_text': self.short_text,
            'detailed_text': self.detailed_text
        }


@dataclass
class AiAnalysisModelOutput:
    """
    Complete AI analysis output structure.
    
    This internal schema matches what we expect from OpenAI.
    It may be richer than what we store in the DB.
    """
    analysis_date: str  # YYYY-MM-DD
    scores: AnalysisScores
    coach_comparison: AnalysisCoachComparison
    summary: AnalysisSummary
    physiology: Optional[Dict[str, Any]] = None  # Free-form detail, stored in raw_json
    action_items: Optional[List[str]] = None  # Optional, stored in raw_json

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'analysis_date': self.analysis_date,
            'scores': self.scores.to_dict(),
            'coach_comparison': self.coach_comparison.to_dict(),
            'summary': self.summary.to_dict()
        }
        if self.physiology:
            result['physiology'] = self.physiology
        if self.action_items:
            result['action_items'] = self.action_items
        return result


# ============== OpenAI System Prompt ==============

AI_ANALYZER_SYSTEM_PROMPT = """You are an elite cycling coach and sports scientist specializing in post-workout analysis.

You understand HRV/RHR physiology, Norwegian 4×4, Z1/Z2 endurance principles, recovery science, and fatigue management.

## Your Task

You receive:
1. **day_context**: Readiness, sleep, HRV/RHR data, 7-day history, 30-day baseline
2. **coach_recommendation**: The AI Coach's planned workout for that day (if any)
3. **actual_workout**: What the athlete actually did

Your job:
- Evaluate how APPROPRIATE the workout was given the athlete's physiological state
- Compare planned vs actual (if a plan exists)
- Score execution quality across multiple dimensions
- Assess fatigue risk for the coming days
- Provide actionable insights

## Scoring Guidelines

### overall_score (0-100)
- 90-100: Excellent execution - perfect for athlete's state
- 75-89: Good execution - appropriate with minor adjustments possible
- 60-74: OK execution - workout was done but not optimal
- 40-59: Suboptimal - athlete pushed when shouldn't have or undertrained
- 0-39: Concerning - significant mismatch between state and effort

### dimension_scores (each 0-100)
- **intensity**: Was the intensity level appropriate?
  - Consider: Power output vs athlete's capacity, HR response, readiness state
- **duration**: Was the duration appropriate?
  - Consider: Time vs plan, fatigue state, training load context
- **hr_response**: How healthy was the cardiovascular response?
  - Consider: HR vs power ratio, HR drift, recovery between efforts

### label
- "excellent": Perfect execution, optimal for state
- "good": Solid workout, well-matched to capacity
- "ok": Acceptable but room for improvement
- "too_easy": Underperformed relative to capacity and readiness
- "overreached": Pushed too hard given fatigue/readiness state

### fatigue_risk (for next 1-3 days)
- "low": Athlete is well-recovered, can train normally
- "medium": Some fatigue accumulation, consider easier days
- "high": Significant fatigue, recovery day(s) recommended

### compliance_score (0-100) - Only if coach plan exists
- 90-100: Followed plan closely
- 70-89: Mostly followed with acceptable deviations
- 50-69: Significant deviations from plan
- 0-49: Largely ignored the plan

## Output Format

Return ONLY valid JSON matching this schema:

{
  "analysis_date": "YYYY-MM-DD",
  "scores": {
    "overall_score": <int 0-100>,
    "dimension_scores": {
      "intensity": <int 0-100>,
      "duration": <int 0-100>,
      "hr_response": <int 0-100>
    },
    "label": "excellent" | "good" | "ok" | "too_easy" | "overreached",
    "fatigue_risk": "low" | "medium" | "high"
  },
  "coach_comparison": {
    "has_coach_plan": <bool>,
    "plan_type": "<string or null>",
    "compliance_score": <int 0-100>,
    "notes": "<comparison notes>"
  },
  "summary": {
    "short_text": "<1-2 sentence summary>",
    "detailed_text": "<3-6 sentence analysis covering: workout appropriateness, HR behavior, fatigue implications, recommendations>"
  },
  "physiology": {
    "hrv_state": "<interpretation of HRV trend>",
    "rhr_state": "<interpretation of RHR trend>",
    "cardiac_efficiency": "<power/HR assessment>",
    "recovery_status": "<overall recovery assessment>"
  },
  "action_items": [
    "<actionable recommendation 1>",
    "<actionable recommendation 2>"
  ]
}

## Critical Rules

1. No text outside the JSON object
2. All scores must be integers 0-100
3. label must be one of: excellent, good, ok, too_easy, overreached
4. fatigue_risk must be one of: low, medium, high
5. summary.detailed_text MUST mention: workout appropriateness, HR behavior, and fatigue implications
6. If no coach plan exists: has_coach_plan=false, plan_type=null, compliance_score=50, notes explain this
7. Be honest but constructive - even suboptimal workouts have learning value"""


AI_ANALYZER_USER_PROMPT_TEMPLATE = """Analyze the following workout data for the athlete.

Compare the actual workout to:
1. The athlete's physiological state (readiness, HRV, RHR, sleep)
2. The AI Coach recommendation (if any)
3. The recent training load

Score the workout execution quality and assess fatigue risk.
Respond only with valid JSON matching the analysis schema.

## Analysis Context

{context_json}"""


# ============== Context Builder ==============

def build_analysis_context(
    workout: Dict[str, Any],
    day_context: Dict[str, Any],
    coach_recommendation: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build the analysis context dict to send to OpenAI.
    
    Args:
        workout: The workout data from cycling_workouts table
        day_context: The day training context (from build_training_context_v2_5)
        coach_recommendation: The AI Coach recommendation for that day (if any)
    
    Returns:
        Dict ready to be serialized to JSON for OpenAI
    """
    # Extract workout date
    workout_date = workout.get('date')
    if hasattr(workout_date, 'strftime'):
        workout_date = workout_date.strftime('%Y-%m-%d')
    else:
        workout_date = str(workout_date) if workout_date else None
    
    # Build actual_workout section from available fields
    duration_sec = workout.get('duration_sec')
    duration_min = int(duration_sec / 60) if duration_sec else None
    
    actual_workout = {
        'workout_id': workout.get('id'),
        'date': workout_date,
        'duration_min': duration_min,
        'avg_power_w': workout.get('avg_power_w'),
        'max_power_w': workout.get('max_power_w'),
        'normalized_power_w': workout.get('normalized_power_w'),
        'avg_hr_bpm': workout.get('avg_heart_rate'),
        'max_hr_bpm': workout.get('max_heart_rate'),
        'tss': workout.get('tss'),
        'intensity_factor': workout.get('intensity_factor'),
        'avg_cadence': workout.get('avg_cadence'),
        'distance_km': workout.get('distance_km'),
        'kcal_total': workout.get('kcal_total'),
        'source': workout.get('source'),
        'notes': workout.get('notes')
    }
    
    # Build coach_recommendation section
    coach_section = {
        'has_coach_plan': False,
        'plan_type': None,
        'planned_duration_min': None,
        'planned_primary_zone': None,
        'planned_power_w': None,
        'planned_hr_bpm': None,
        'raw': None
    }
    
    if coach_recommendation:
        coach_section['has_coach_plan'] = True
        coach_section['plan_type'] = coach_recommendation.get('day_type')
        
        session_plan = coach_recommendation.get('session_plan')
        if session_plan:
            coach_section['planned_duration_min'] = session_plan.get('duration_minutes')
            coach_section['planned_primary_zone'] = session_plan.get('primary_zone')
            
            # Power targets
            if session_plan.get('session_target_power_w_min') or session_plan.get('session_target_power_w_max'):
                coach_section['planned_power_w'] = {
                    'min': session_plan.get('session_target_power_w_min'),
                    'max': session_plan.get('session_target_power_w_max'),
                    'expected_avg': session_plan.get('expected_avg_power_w')
                }
            
            # HR targets
            if session_plan.get('session_target_hr_bpm_min') or session_plan.get('session_target_hr_bpm_max'):
                coach_section['planned_hr_bpm'] = {
                    'min': session_plan.get('session_target_hr_bpm_min'),
                    'max': session_plan.get('session_target_hr_bpm_max'),
                    'expected_avg': session_plan.get('expected_avg_hr_bpm')
                }
        
        # Include raw recommendation for full context
        coach_section['raw'] = coach_recommendation
    
    return {
        'date': workout_date,
        'day_context': day_context,
        'coach_recommendation': coach_section,
        'actual_workout': actual_workout
    }


# ============== Response Parser ==============

def parse_analysis_response(response_text: str, fallback_date: str) -> AiAnalysisModelOutput:
    """
    Parse the OpenAI response into an AiAnalysisModelOutput object.
    
    Args:
        response_text: Raw text response from OpenAI
        fallback_date: Date to use if not in response
    
    Returns:
        AiAnalysisModelOutput object
    
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
        logger.error(f"[ANALYZER] JSON parse error: {e}")
        logger.error(f"[ANALYZER] Raw response: {response_text[:500]}")
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
    
    try:
        # Parse scores
        scores_data = data.get('scores', {})
        dimension_data = scores_data.get('dimension_scores', {})
        
        dimension_scores = AnalysisDimensionScores(
            intensity=dimension_data.get('intensity', 50),
            duration=dimension_data.get('duration', 50),
            hr_response=dimension_data.get('hr_response', 50)
        )
        
        scores = AnalysisScores(
            overall_score=scores_data.get('overall_score', 50),
            dimension_scores=dimension_scores,
            label=scores_data.get('label', 'ok'),
            fatigue_risk=scores_data.get('fatigue_risk', 'medium')
        )
        
        # Parse coach comparison
        comp_data = data.get('coach_comparison', {})
        coach_comparison = AnalysisCoachComparison(
            has_coach_plan=comp_data.get('has_coach_plan', False),
            plan_type=comp_data.get('plan_type'),
            compliance_score=comp_data.get('compliance_score', 50),
            notes=comp_data.get('notes', '')
        )
        
        # Parse summary
        summary_data = data.get('summary', {})
        summary = AnalysisSummary(
            short_text=summary_data.get('short_text', 'Analysis completed.'),
            detailed_text=summary_data.get('detailed_text', 'No detailed analysis available.')
        )
        
        return AiAnalysisModelOutput(
            analysis_date=data.get('analysis_date', fallback_date),
            scores=scores,
            coach_comparison=coach_comparison,
            summary=summary,
            physiology=data.get('physiology'),
            action_items=data.get('action_items')
        )
        
    except Exception as e:
        logger.error(f"[ANALYZER] Error building analysis object: {e}")
        raise ValueError(f"Failed to build analysis from AI response: {str(e)}")


# ============== Main Service Function ==============

DEFAULT_MODEL_NAME = "gpt-4o"
PROMPT_VERSION = "ai_analyzer_v1"


def generate_ai_workout_analysis(
    user_id: str,
    workout_id: int,
    force_regenerate: bool = False,
    connection_manager=None
) -> Dict[str, Any]:
    """
    Generate or retrieve AI workout analysis.
    
    If force_regenerate is False and an analysis exists, returns the existing one.
    Otherwise, generates a new analysis via OpenAI and stores it.
    
    Args:
        user_id: The user's ID
        workout_id: The workout ID to analyze
        force_regenerate: If True, always call OpenAI even if analysis exists
        connection_manager: Optional database connection manager
    
    Returns:
        Dict with the analysis data (matches the DB model)
    
    Raises:
        ValueError: If workout not found or doesn't belong to user
    """
    from models.services.cycling_readiness_service import CyclingReadinessService
    from models.services.training_recommendation import get_training_recommendation
    from models.services.openai_extraction import get_openai_client
    from datetime import datetime
    
    logger.info(f"[ANALYZER] Starting analysis for workout_id={workout_id}, user={user_id}, force={force_regenerate}")
    
    # Get the cycling readiness service
    service = CyclingReadinessService(user_id=user_id, connection_manager=connection_manager)
    
    # Fetch the workout
    workout = service.get_cycling_workout_by_id(workout_id)
    if not workout:
        raise ValueError(f"Workout {workout_id} not found")
    
    # Verify ownership
    if workout.get('user_id') != user_id:
        raise ValueError(f"Workout {workout_id} does not belong to user")
    
    # Determine workout date
    workout_date = workout.get('date')
    if hasattr(workout_date, 'strftime'):
        workout_date_obj = workout_date
        workout_date_str = workout_date.strftime('%Y-%m-%d')
    else:
        workout_date_str = str(workout_date)
        try:
            workout_date_obj = datetime.strptime(workout_date_str, '%Y-%m-%d').date()
        except:
            workout_date_obj = datetime.now().date()
            workout_date_str = workout_date_obj.strftime('%Y-%m-%d')
    
    # Check for existing analysis
    if not force_regenerate:
        existing = service.get_analysis_for_workout(workout_id)
        if existing:
            logger.info(f"[ANALYZER] Returning existing analysis for workout_id={workout_id}")
            return existing
    
    logger.info(f"[ANALYZER] Generating NEW analysis for workout_id={workout_id}, date={workout_date_str}")
    
    # Build day context
    try:
        day_context = service.build_training_context_v2_5(workout_date_obj)
        logger.debug(f"[ANALYZER] Built day context for {workout_date_str}")
    except Exception as e:
        logger.warning(f"[ANALYZER] Error building day context: {e}, using minimal context")
        day_context = {'evaluation_date': workout_date_str, 'error': str(e)}
    
    # Try to fetch AI Coach recommendation for that date
    coach_rec = None
    coach_rec_dict = None
    try:
        coach_rec = get_training_recommendation(user_id, workout_date_obj, connection_manager)
        if coach_rec:
            coach_rec_dict = coach_rec.to_dict()
            logger.info(f"[ANALYZER] Found coach recommendation: {coach_rec.day_type}")
    except Exception as e:
        logger.warning(f"[ANALYZER] Could not fetch coach recommendation: {e}")
    
    # Build analysis context
    analysis_context = build_analysis_context(
        workout=workout,
        day_context=day_context,
        coach_recommendation=coach_rec_dict
    )
    
    # Build the prompt
    context_json = json.dumps(analysis_context, indent=2, default=str)
    user_prompt = AI_ANALYZER_USER_PROMPT_TEMPLATE.format(context_json=context_json)
    
    # Call OpenAI
    try:
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model=DEFAULT_MODEL_NAME,
            messages=[
                {"role": "system", "content": AI_ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content
        logger.info(f"[ANALYZER] OpenAI response received, length={len(response_text)}")
        
        # Parse the response
        analysis_output = parse_analysis_response(response_text, workout_date_str)
        prompt_version = PROMPT_VERSION
        
        # CRITICAL: Inject actual planned values from stored coach recommendation
        # OpenAI doesn't return these - we must get them from the coach's session_plan
        if coach_rec_dict:
            session_plan = coach_rec_dict.get('session_plan') or {}
            analysis_output.coach_comparison.has_coach_plan = True
            analysis_output.coach_comparison.plan_type = coach_rec_dict.get('day_type')
            analysis_output.coach_comparison.planned_duration_min = session_plan.get('duration_minutes')
            analysis_output.coach_comparison.planned_power_min = session_plan.get('session_target_power_w_min')
            analysis_output.coach_comparison.planned_power_max = session_plan.get('session_target_power_w_max')
            analysis_output.coach_comparison.planned_avg_power = session_plan.get('expected_avg_power_w')
            analysis_output.coach_comparison.planned_hr_min = session_plan.get('session_target_hr_bpm_min')
            analysis_output.coach_comparison.planned_hr_max = session_plan.get('session_target_hr_bpm_max')
            analysis_output.coach_comparison.planned_avg_hr = session_plan.get('expected_avg_hr_bpm')
            logger.info(f"[ANALYZER] Injected coach plan: power={analysis_output.coach_comparison.planned_power_min}-{analysis_output.coach_comparison.planned_power_max}W, "
                       f"HR={analysis_output.coach_comparison.planned_hr_min}-{analysis_output.coach_comparison.planned_hr_max} bpm")
        else:
            analysis_output.coach_comparison.has_coach_plan = False
        
    except Exception as e:
        logger.error(f"[ANALYZER] OpenAI API error: {e}")
        
        # Check if we have an existing analysis to return
        existing = service.get_analysis_for_workout(workout_id)
        if existing:
            logger.info(f"[ANALYZER] Returning existing analysis after API failure")
            return existing
        
        # Fall back to dummy analysis
        logger.warning(f"[ANALYZER] Using fallback analysis for workout_id={workout_id}")
        
        # Build coach comparison with actual planned values if available
        session_plan = (coach_rec_dict.get('session_plan') or {}) if coach_rec_dict else {}
        coach_comparison = AnalysisCoachComparison(
            has_coach_plan=bool(coach_rec_dict),
            plan_type=coach_rec_dict.get('day_type') if coach_rec_dict else None,
            compliance_score=50,
            notes='Analysis failed - using fallback values',
            planned_duration_min=session_plan.get('duration_minutes'),
            planned_power_min=session_plan.get('session_target_power_w_min'),
            planned_power_max=session_plan.get('session_target_power_w_max'),
            planned_avg_power=session_plan.get('expected_avg_power_w'),
            planned_hr_min=session_plan.get('session_target_hr_bpm_min'),
            planned_hr_max=session_plan.get('session_target_hr_bpm_max'),
            planned_avg_hr=session_plan.get('expected_avg_hr_bpm')
        )
        
        analysis_output = AiAnalysisModelOutput(
            analysis_date=workout_date_str,
            scores=AnalysisScores(
                overall_score=50,
                dimension_scores=AnalysisDimensionScores(
                    intensity=50,
                    duration=50,
                    hr_response=50
                ),
                label='ok',
                fatigue_risk='medium'
            ),
            coach_comparison=coach_comparison,
            summary=AnalysisSummary(
                short_text='Analysis could not be completed.',
                detailed_text=f'The AI analysis failed due to an error: {str(e)[:100]}. Please try again.'
            )
        )
        prompt_version = 'fallback'
    
    # Map to database format
    analysis_data = {
        'overall_score': analysis_output.scores.overall_score,
        'compliance_score': analysis_output.coach_comparison.compliance_score,
        'intensity_score': analysis_output.scores.dimension_scores.intensity,
        'duration_score': analysis_output.scores.dimension_scores.duration,
        'hr_response_score': analysis_output.scores.dimension_scores.hr_response,
        'execution_label': analysis_output.scores.label,
        'fatigue_risk': analysis_output.scores.fatigue_risk,
        'notes_short': analysis_output.summary.short_text,
        'notes_detailed': analysis_output.summary.detailed_text,
        'raw_json': analysis_output.to_dict(),
        'prompt_version': prompt_version
    }
    
    # Save to database
    saved_analysis = service.create_or_update_analysis(workout_id, analysis_data)
    
    logger.info(f"[ANALYZER] Analysis saved: overall_score={analysis_data['overall_score']}, "
                f"label={analysis_data['execution_label']}, fatigue_risk={analysis_data['fatigue_risk']}")
    
    return saved_analysis

