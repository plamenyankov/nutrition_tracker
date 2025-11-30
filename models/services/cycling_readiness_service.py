"""
Service layer for Cycling workouts and Morning Readiness tracking.
Handles database operations and business logic.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from models.database.connection_manager import get_db_manager

logger = logging.getLogger(__name__)


class CyclingReadinessService:
    """Service for managing cycling workouts and readiness entries"""

    def __init__(self, user_id: str = None, connection_manager=None):
        self.user_id = user_id
        self.connection_manager = connection_manager or get_db_manager()

    def get_connection(self):
        """Get database connection"""
        return self.connection_manager.get_connection()

    # ============== Morning Readiness Score Calculation ==============

    # Formula explanation for UI tooltip
    SCORE_FORMULA_EXPLANATION = """
    **Readiness Score (0-100)** is calculated from:
    
    **Subjective Inputs (40 pts max):**
    • Energy Level (1-5): up to 20 pts
    • Mood (1-3): up to 10 pts
    • Muscle Fatigue (1-3): up to 10 pts (low fatigue = high score)
    
    **Recovery Indicators (25 pts max):**
    • HRV Status: up to 10 pts (↑ = good)
    • RHR Status: up to 10 pts (↓ = good)
    • Min HR Status: up to 5 pts (lower = better recovery)
    
    **Sleep Quality (25 pts max):**
    • Sleep Duration: up to 10 pts (7-9h optimal)
    • Deep Sleep: up to 10 pts (60-120min optimal)
    • Awake Time: up to 5 pts (less = better)
    
    **Symptoms:** -10 pts if experiencing symptoms
    """

    @staticmethod
    def calculate_morning_score(
        energy: int,
        mood: int,
        muscle_fatigue: int,
        hrv_status: int,
        rhr_status: int,
        min_hr_status: int,
        sleep_minutes: int,
        deep_sleep_minutes: int,
        awake_minutes: int = None,
        symptoms_flag: bool = False
    ) -> int:
        """
        Calculate morning readiness score (0-100) based on inputs.

        Weights:
        - Energy (1-5): 20 points max
        - Mood (1-3): 10 points max
        - Muscle fatigue (1-3): 10 points max (inverted - low fatigue = high score)
        - HRV status (-1/0/1): 10 points max
        - RHR status (-1/0/1): 10 points max
        - Min HR status (-1/0/1): 5 points max
        - Sleep quality: 20 points max (based on duration and deep sleep)
        - Awake time: 5 points max (less awake time = better)
        - Symptoms: -10 points if true
        
        Note: stress_level is no longer used in scoring (removed from form).
        """
        score = 0

        # Energy: 1-5 → 0-20 points
        energy = energy or 3  # Default to neutral
        score += (energy - 1) * 5  # 0, 5, 10, 15, 20

        # Mood: 1-3 → 0-10 points
        mood = mood or 2  # Default to neutral
        score += (mood - 1) * 5  # 0, 5, 10

        # Muscle fatigue: 1-3 → inverted (1=no fatigue=10pts, 3=high fatigue=0pts)
        muscle_fatigue = muscle_fatigue or 2  # Default to moderate
        score += (3 - muscle_fatigue) * 5  # 10, 5, 0

        # HRV status: -1/0/1 → 0/5/10 points
        hrv_status = hrv_status or 0
        score += (hrv_status + 1) * 5  # 0, 5, 10

        # RHR status: -1/0/1 → 0/5/10 points
        rhr_status = rhr_status or 0
        score += (rhr_status + 1) * 5  # 0, 5, 10

        # Min HR status: -1/0/1 → 0/2.5/5 points
        min_hr_status = min_hr_status or 0
        score += (min_hr_status + 1) * 2.5  # 0, 2.5, 5

        # Sleep quality: up to 20 points
        # Ideal sleep: 7-9 hours (420-540 minutes)
        if sleep_minutes:
            if sleep_minutes >= 420 and sleep_minutes <= 540:
                sleep_score = 10
            elif sleep_minutes >= 360:
                sleep_score = 7
            elif sleep_minutes >= 300:
                sleep_score = 5
            else:
                sleep_score = 2
            score += sleep_score

            # Deep sleep bonus: ideal is 60-120 minutes (1-2 hours)
            if deep_sleep_minutes:
                if deep_sleep_minutes >= 60 and deep_sleep_minutes <= 120:
                    score += 10
                elif deep_sleep_minutes >= 45:
                    score += 7
                elif deep_sleep_minutes >= 30:
                    score += 4
                else:
                    score += 2

        # Awake time during sleep: less is better (0-30min = 5pts, 30-60 = 3pts, >60 = 0pts)
        if awake_minutes is not None:
            if awake_minutes <= 30:
                score += 5
            elif awake_minutes <= 60:
                score += 3
            # else: 0 points

        # Symptoms penalty
        if symptoms_flag:
            score -= 10

        # Clamp to 0-100
        return max(0, min(100, int(round(score))))

    # ============== Cycling Workout Methods ==============

    def create_cycling_workout(
        self,
        date: str,
        start_time: str = None,
        source: str = "indoor_cycle",
        notes: str = None,
        duration_sec: int = None,
        distance_km: float = None,
        avg_heart_rate: int = None,
        max_heart_rate: int = None,
        avg_power_w: float = None,
        max_power_w: float = None,
        normalized_power_w: float = None,
        intensity_factor: float = None,
        tss: float = None,
        avg_cadence: int = None,
        kcal_active: int = None,
        kcal_total: int = None
    ) -> int:
        """Create a new cycling workout entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO cycling_workouts (
                    user_id, date, start_time, source, notes,
                    duration_sec, distance_km, avg_heart_rate, max_heart_rate,
                    avg_power_w, max_power_w, normalized_power_w, intensity_factor,
                    tss, avg_cadence, kcal_active, kcal_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.user_id, date, start_time, source, notes,
                duration_sec, distance_km, avg_heart_rate, max_heart_rate,
                avg_power_w, max_power_w, normalized_power_w, intensity_factor,
                tss, avg_cadence, kcal_active, kcal_total
            ))
            conn.commit()
            return cursor.lastrowid

    def get_cycling_workouts(self, limit: int = 30, offset: int = 0) -> List[Dict]:
        """Get cycling workouts for the user"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM cycling_workouts
                    WHERE user_id = %s
                    ORDER BY date DESC, start_time DESC
                    LIMIT %s OFFSET %s
                ''', (self.user_id, limit, offset))
            else:
                cursor.execute('''
                    SELECT * FROM cycling_workouts
                    ORDER BY date DESC, start_time DESC
                    LIMIT %s OFFSET %s
                ''', (limit, offset))
            return cursor.fetchall()

    def get_cycling_workout_by_id(self, workout_id: int) -> Optional[Dict]:
        """Get a specific cycling workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT * FROM cycling_workouts WHERE id = %s
            ''', (workout_id,))
            return cursor.fetchone()

    def update_cycling_workout(self, workout_id: int, **kwargs) -> bool:
        """Update a cycling workout"""
        if not kwargs:
            return False

        # Build dynamic update query
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key not in ['id', 'created_at', 'updated_at']:
                set_clauses.append(f"{key} = %s")
                values.append(value)

        if not set_clauses:
            return False

        values.append(workout_id)
        query = f"UPDATE cycling_workouts SET {', '.join(set_clauses)} WHERE id = %s"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_cycling_workout(self, workout_id: int) -> bool:
        """Delete a cycling workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cycling_workouts WHERE id = %s', (workout_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_cycling_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get cycling statistics for the last N days"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT
                    COUNT(*) as total_workouts,
                    COALESCE(SUM(duration_sec), 0) as total_duration_sec,
                    COALESCE(SUM(distance_km), 0) as total_distance_km,
                    COALESCE(AVG(avg_power_w), 0) as avg_power,
                    COALESCE(AVG(avg_heart_rate), 0) as avg_heart_rate,
                    COALESCE(SUM(tss), 0) as total_tss,
                    COALESCE(SUM(kcal_active), 0) as total_kcal
                FROM cycling_workouts
                WHERE date >= %s
            ''', (start_date,))

            return cursor.fetchone() or {}

    def get_cycling_workout_by_date(self, workout_date: str) -> Optional[Dict]:
        """Get cycling workout for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM cycling_workouts
                    WHERE user_id = %s AND date = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (self.user_id, workout_date))
            else:
                cursor.execute('''
                    SELECT * FROM cycling_workouts
                    WHERE date = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (workout_date,))
            return cursor.fetchone()

    def merge_cycling_workout(
        self,
        workout_date: str,
        payloads: List[Dict]
    ) -> Tuple[int, Dict]:
        """
        Merge multiple cycling payloads into a single workout record.
        If a workout exists for the date, update missing fields.
        If no workout exists, create a new one.

        Returns (workout_id, merged_data)
        """
        # Get existing workout for the date
        existing = self.get_cycling_workout_by_date(workout_date)

        # Merge all payloads into a single data dict
        merged = {}
        fields = [
            'start_time', 'source', 'notes', 'duration_sec', 'distance_km',
            'avg_heart_rate', 'max_heart_rate', 'avg_power_w', 'max_power_w',
            'normalized_power_w', 'intensity_factor', 'tss', 'avg_cadence',
            'kcal_active', 'kcal_total'
        ]
        
        # Fields where 0 should be treated as missing/null
        zero_is_null_fields = ['avg_heart_rate', 'max_heart_rate', 'avg_power_w', 'max_power_w']

        # Helper to check if value is valid (not None and not 0 for HR fields)
        def is_valid_value(field, value):
            if value is None:
                return False
            if field in zero_is_null_fields and value == 0:
                return False
            return True

        # Start with existing data if available
        if existing:
            for field in fields:
                value = existing.get(field)
                if is_valid_value(field, value):
                    merged[field] = value

        # Merge payloads (later values override if current is missing/invalid)
        for payload in payloads:
            for field in fields:
                # Map payload field names to DB field names
                payload_field = field
                if field == 'source':
                    payload_field = 'sport'

                value = payload.get(payload_field)
                # Add value if it's valid AND field is not already set with a valid value
                if is_valid_value(field, value) and field not in merged:
                    merged[field] = value

        if existing:
            # Update existing workout
            self.update_cycling_workout(existing['id'], **merged)
            workout_id = existing['id']
        else:
            # Create new workout
            workout_id = self.create_cycling_workout(
                date=workout_date,
                start_time=merged.get('start_time'),
                source=merged.get('source', 'indoor_cycle'),
                notes=merged.get('notes'),
                duration_sec=merged.get('duration_sec'),
                distance_km=merged.get('distance_km'),
                avg_heart_rate=merged.get('avg_heart_rate'),
                max_heart_rate=merged.get('max_heart_rate'),
                avg_power_w=merged.get('avg_power_w'),
                max_power_w=merged.get('max_power_w'),
                normalized_power_w=merged.get('normalized_power_w'),
                intensity_factor=merged.get('intensity_factor'),
                tss=merged.get('tss'),
                avg_cadence=merged.get('avg_cadence'),
                kcal_active=merged.get('kcal_active'),
                kcal_total=merged.get('kcal_total')
            )

        merged['id'] = workout_id
        merged['date'] = workout_date
        return workout_id, merged

    def update_readiness_from_sleep(
        self,
        readiness_date: str,
        sleep_payload: Dict
    ) -> Optional[Dict]:
        """
        Update or create a readiness entry with sleep data.
        Only updates sleep-related fields, preserving other data if exists.
        """
        # Get existing readiness entry
        existing = self.get_readiness_by_date(readiness_date)

        sleep_minutes = sleep_payload.get('total_sleep_minutes')
        deep_sleep_minutes = sleep_payload.get('deep_sleep_minutes')
        awake_minutes = sleep_payload.get('awake_minutes') or sleep_payload.get('wakeups_count')  # Support both field names
        min_hr = sleep_payload.get('min_heart_rate')

        # Derive min_hr_status from min_heart_rate (simple heuristic)
        # Lower min HR during sleep is generally better
        min_hr_status = 0
        if min_hr is not None:
            if min_hr < 50:
                min_hr_status = 1  # Very low, good recovery
            elif min_hr > 60:
                min_hr_status = -1  # Higher than normal

        if existing:
            # Update existing entry with new sleep data
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE readiness_entries SET
                        sleep_minutes = COALESCE(%s, sleep_minutes),
                        deep_sleep_minutes = COALESCE(%s, deep_sleep_minutes),
                        awake_minutes = COALESCE(%s, awake_minutes),
                        min_hr_status = COALESCE(%s, min_hr_status)
                    WHERE id = %s
                ''', (
                    sleep_minutes, deep_sleep_minutes, awake_minutes,
                    min_hr_status if min_hr is not None else None,
                    existing['id']
                ))
                conn.commit()

            # Always recalculate morning score with defaults for missing values
            updated = self.get_readiness_by_date(readiness_date)
            if updated:
                new_score = self.calculate_morning_score(
                    energy=updated.get('energy') or 3,  # Default neutral energy
                    mood=updated.get('mood') or 2,       # Default neutral mood
                    muscle_fatigue=updated.get('muscle_fatigue') or 2,  # Default moderate
                    hrv_status=updated.get('hrv_status') or 0,
                    rhr_status=updated.get('rhr_status') or 0,
                    min_hr_status=updated.get('min_hr_status') or 0,
                    sleep_minutes=updated.get('sleep_minutes') or 0,
                    deep_sleep_minutes=updated.get('deep_sleep_minutes') or 0,
                    awake_minutes=updated.get('awake_minutes') or 0,
                    symptoms_flag=updated.get('symptoms_flag') or False
                )
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE readiness_entries SET morning_score = %s WHERE id = %s
                    ''', (new_score, existing['id']))
                    conn.commit()

            return self.get_readiness_by_date(readiness_date)
        else:
            # Create new entry with sleep data and calculate initial score
            # Uses default values for user-input fields
            initial_score = self.calculate_morning_score(
                energy=3,  # Default neutral energy
                mood=2,    # Default neutral mood
                muscle_fatigue=2,  # Default moderate fatigue
                hrv_status=0,
                rhr_status=0,
                min_hr_status=min_hr_status if min_hr is not None else 0,
                sleep_minutes=sleep_minutes or 0,
                deep_sleep_minutes=deep_sleep_minutes or 0,
                awake_minutes=awake_minutes or 0,
                symptoms_flag=False
            )
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO readiness_entries (
                        user_id, date, sleep_minutes, deep_sleep_minutes,
                        awake_minutes, min_hr_status, morning_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    self.user_id, readiness_date, sleep_minutes,
                    deep_sleep_minutes, awake_minutes,
                    min_hr_status if min_hr is not None else 0,
                    initial_score
                ))
                conn.commit()

            return self.get_readiness_by_date(readiness_date)

    # ============== Readiness Entry Methods ==============

    def create_or_update_readiness(
        self,
        date: str,
        energy: int,
        mood: int,
        muscle_fatigue: int,
        hrv_status: int = 0,
        rhr_status: int = 0,
        min_hr_status: int = 0,
        sleep_minutes: int = None,
        deep_sleep_minutes: int = None,
        awake_minutes: int = None,
        symptoms_flag: bool = False,
        evening_note: str = None
    ) -> Tuple[int, int]:
        """
        Create or update a readiness entry for the given date.
        Sleep data is preserved from imports if not provided.
        Returns tuple of (entry_id, morning_score)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Check for existing entry to preserve sleep data
            cursor.execute('''
                SELECT * FROM readiness_entries 
                WHERE user_id = %s AND date = %s
            ''', (self.user_id, date))
            existing = cursor.fetchone()
            
            # Use existing sleep data if new values not provided
            if existing:
                if sleep_minutes is None:
                    sleep_minutes = existing.get('sleep_minutes')
                if deep_sleep_minutes is None:
                    deep_sleep_minutes = existing.get('deep_sleep_minutes')
                if awake_minutes is None:
                    awake_minutes = existing.get('awake_minutes')
            
            # Calculate morning score
            morning_score = self.calculate_morning_score(
                energy=energy,
                mood=mood,
                muscle_fatigue=muscle_fatigue,
                hrv_status=hrv_status,
                rhr_status=rhr_status,
                min_hr_status=min_hr_status,
                sleep_minutes=sleep_minutes or 0,
                deep_sleep_minutes=deep_sleep_minutes or 0,
                awake_minutes=awake_minutes,
                symptoms_flag=symptoms_flag
            )

            cursor = conn.cursor()

            # Try to update existing entry first
            cursor.execute('''
                UPDATE readiness_entries SET
                    energy = %s, mood = %s, muscle_fatigue = %s,
                    hrv_status = %s, rhr_status = %s, min_hr_status = %s,
                    sleep_minutes = COALESCE(%s, sleep_minutes),
                    deep_sleep_minutes = COALESCE(%s, deep_sleep_minutes),
                    awake_minutes = COALESCE(%s, awake_minutes),
                    symptoms_flag = %s, morning_score = %s,
                    evening_note = COALESCE(%s, evening_note)
                WHERE user_id = %s AND date = %s
            ''', (
                energy, mood, muscle_fatigue,
                hrv_status, rhr_status, min_hr_status,
                sleep_minutes, deep_sleep_minutes, awake_minutes,
                symptoms_flag, morning_score,
                evening_note, self.user_id, date
            ))

            if cursor.rowcount > 0:
                conn.commit()
                # Get the existing entry id
                cursor.execute('''
                    SELECT id FROM readiness_entries
                    WHERE user_id = %s AND date = %s
                ''', (self.user_id, date))
                result = cursor.fetchone()
                return result[0], morning_score

            # Create new entry
            cursor.execute('''
                INSERT INTO readiness_entries (
                    user_id, date, energy, mood, muscle_fatigue,
                    hrv_status, rhr_status, min_hr_status,
                    sleep_minutes, deep_sleep_minutes, awake_minutes,
                    symptoms_flag, morning_score, evening_note
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.user_id, date, energy, mood, muscle_fatigue,
                hrv_status, rhr_status, min_hr_status,
                sleep_minutes, deep_sleep_minutes, awake_minutes,
                symptoms_flag, morning_score, evening_note
            ))
            conn.commit()
            return cursor.lastrowid, morning_score

    def get_readiness_entries(self, limit: int = 14) -> List[Dict]:
        """Get recent readiness entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM readiness_entries
                    WHERE user_id = %s
                    ORDER BY date DESC
                    LIMIT %s
                ''', (self.user_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM readiness_entries
                    ORDER BY date DESC
                    LIMIT %s
                ''', (limit,))
            return cursor.fetchall()

    def get_readiness_by_date(self, date: str) -> Optional[Dict]:
        """Get readiness entry for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT * FROM readiness_entries
                WHERE user_id = %s AND date = %s
            ''', (self.user_id, date))
            return cursor.fetchone()

    def delete_readiness_entry(self, entry_id: int) -> bool:
        """Delete a readiness entry by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.user_id:
                cursor.execute('''
                    DELETE FROM readiness_entries 
                    WHERE id = %s AND user_id = %s
                ''', (entry_id, self.user_id))
            else:
                cursor.execute('DELETE FROM readiness_entries WHERE id = %s', (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_sleep_summary(self, summary_id: int) -> bool:
        """Delete a sleep summary by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.user_id:
                cursor.execute('''
                    DELETE FROM sleep_summaries 
                    WHERE id = %s AND user_id = %s
                ''', (summary_id, self.user_id))
            else:
                cursor.execute('DELETE FROM sleep_summaries WHERE id = %s', (summary_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_readiness_with_workouts(self, days: int = 14) -> List[Dict]:
        """Get readiness entries combined with cycling workout data for the same dates"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT
                    r.*,
                    c.tss as workout_tss,
                    c.avg_power_w as workout_avg_power,
                    c.duration_sec as workout_duration
                FROM readiness_entries r
                LEFT JOIN cycling_workouts c ON r.date = c.date AND r.user_id = c.user_id
                WHERE r.date >= %s
                ORDER BY r.date DESC
            ''', (start_date,))

            return cursor.fetchall()

    # ============== Sleep Summary Methods ==============

    def save_sleep_summary(
        self,
        date: str,
        sleep_start_time: str = None,
        sleep_end_time: str = None,
        total_sleep_minutes: int = None,
        deep_sleep_minutes: int = None,
        awake_minutes: int = None,
        min_heart_rate: int = None,
        avg_heart_rate: int = None,
        max_heart_rate: int = None,
        notes: str = None
    ) -> int:
        """
        Save or update a sleep summary entry.
        Uses UPSERT to avoid duplicate records for same date/user.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if record exists for this date/user
            cursor.execute('''
                SELECT id FROM sleep_summaries 
                WHERE user_id = %s AND date = %s
            ''', (self.user_id, date))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record, merging with new data
                cursor.execute('''
                    UPDATE sleep_summaries SET
                        sleep_start_time = COALESCE(%s, sleep_start_time),
                        sleep_end_time = COALESCE(%s, sleep_end_time),
                        total_sleep_minutes = COALESCE(%s, total_sleep_minutes),
                        deep_sleep_minutes = COALESCE(%s, deep_sleep_minutes),
                        awake_minutes = COALESCE(%s, awake_minutes),
                        min_heart_rate = COALESCE(%s, min_heart_rate),
                        avg_heart_rate = COALESCE(%s, avg_heart_rate),
                        max_heart_rate = COALESCE(%s, max_heart_rate),
                        notes = COALESCE(%s, notes),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (
                    sleep_start_time, sleep_end_time,
                    total_sleep_minutes, deep_sleep_minutes, awake_minutes,
                    min_heart_rate, avg_heart_rate, max_heart_rate, notes,
                    existing[0]
                ))
                conn.commit()
                return existing[0]
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO sleep_summaries (
                        user_id, date, sleep_start_time, sleep_end_time,
                        total_sleep_minutes, deep_sleep_minutes, awake_minutes,
                        min_heart_rate, avg_heart_rate, max_heart_rate, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    self.user_id, date, sleep_start_time, sleep_end_time,
                    total_sleep_minutes, deep_sleep_minutes, awake_minutes,
                    min_heart_rate, avg_heart_rate, max_heart_rate, notes
                ))
                conn.commit()
                return cursor.lastrowid

    def get_sleep_summaries(self, limit: int = 14) -> List[Dict]:
        """Get recent sleep summaries"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM sleep_summaries
                    WHERE user_id = %s
                    ORDER BY date DESC
                    LIMIT %s
                ''', (self.user_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM sleep_summaries
                    ORDER BY date DESC
                    LIMIT %s
                ''', (limit,))
            return cursor.fetchall()

    def get_sleep_summary_by_date(self, sleep_date: str) -> Optional[Dict]:
        """Get sleep summary for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM sleep_summaries
                    WHERE user_id = %s AND date = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (self.user_id, sleep_date))
            else:
                cursor.execute('''
                    SELECT * FROM sleep_summaries
                    WHERE date = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (sleep_date,))
            return cursor.fetchone()

    # ============== Cardio Daily Metrics Methods ==============

    def get_cardio_metrics_for_date(self, date: str) -> Optional[Dict]:
        """Get cardio metrics for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM cardio_daily_metrics
                    WHERE user_id = %s AND date = %s
                    LIMIT 1
                ''', (self.user_id, date))
            else:
                cursor.execute('''
                    SELECT * FROM cardio_daily_metrics
                    WHERE date = %s
                    LIMIT 1
                ''', (date,))
            return cursor.fetchone()

    def recalculate_readiness_score(self, date: str) -> Optional[int]:
        """
        Recalculate and update morning score for a readiness entry.
        Called when new data (sleep, cardio) affects the score.
        
        Args:
            date: Date to recalculate (YYYY-MM-DD)
        
        Returns:
            New score or None if no readiness entry exists
        """
        existing = self.get_readiness_by_date(date)
        if not existing:
            return None
        
        # Get calculated HRV/RHR status from cardio data
        cardio_status = self.calculate_hrv_rhr_status(date)
        hrv_status = cardio_status.get('hrv_status') if cardio_status.get('hrv_status') is not None else existing.get('hrv_status') or 0
        rhr_status = cardio_status.get('rhr_status') if cardio_status.get('rhr_status') is not None else existing.get('rhr_status') or 0
        
        # Recalculate morning score
        new_score = self.calculate_morning_score(
            energy=existing.get('energy') or 3,
            mood=existing.get('mood') or 2,
            muscle_fatigue=existing.get('muscle_fatigue') or 2,
            hrv_status=hrv_status,
            rhr_status=rhr_status,
            min_hr_status=existing.get('min_hr_status') or 0,
            sleep_minutes=existing.get('sleep_minutes') or 0,
            deep_sleep_minutes=existing.get('deep_sleep_minutes') or 0,
            awake_minutes=existing.get('awake_minutes') or 0,
            symptoms_flag=existing.get('symptoms_flag') or False
        )
        
        # Update entry with new status values and score
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE readiness_entries SET 
                    hrv_status = %s, rhr_status = %s, morning_score = %s
                WHERE id = %s
            ''', (hrv_status, rhr_status, new_score, existing['id']))
            conn.commit()
        
        logger.info(f"[RECALCULATE] Updated readiness for {date}: HRV={hrv_status}, RHR={rhr_status}, score={new_score}")
        return new_score

    def upsert_cardio_metrics(self, date: str, **kwargs) -> int:
        """
        Upsert cardio metrics for a date.
        Only updates provided fields, doesn't overwrite others with NULL.
        
        Args:
            date: Date string (YYYY-MM-DD)
            **kwargs: rhr_bpm (single value), hrv_low_ms, hrv_high_ms
        
        Returns:
            ID of the record (created or updated)
        """
        if not kwargs:
            return None
        
        allowed_fields = ['rhr_bpm', 'hrv_low_ms', 'hrv_high_ms']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Check if record exists
            if self.user_id:
                cursor.execute('''
                    SELECT * FROM cardio_daily_metrics
                    WHERE user_id = %s AND date = %s
                ''', (self.user_id, date))
            else:
                cursor.execute('''
                    SELECT * FROM cardio_daily_metrics
                    WHERE date = %s
                ''', (date,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record using COALESCE to preserve existing values
                set_clauses = []
                values = []
                for field, value in updates.items():
                    set_clauses.append(f"{field} = COALESCE(%s, {field})")
                    values.append(value)
                
                # Add WHERE clause parameters in correct order
                if self.user_id:
                    values.append(self.user_id)  # user_id first
                    values.append(date)          # date second
                    where_clause = "WHERE user_id = %s AND date = %s"
                else:
                    values.append(date)
                    where_clause = "WHERE date = %s"
                
                cursor.execute(f'''
                    UPDATE cardio_daily_metrics
                    SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                    {where_clause}
                ''', values)
                conn.commit()
                return existing['id']
            else:
                # Insert new record
                fields = ['user_id', 'date'] + list(updates.keys())
                placeholders = ['%s'] * len(fields)
                values = [self.user_id, date] + list(updates.values())
                
                cursor.execute(f'''
                    INSERT INTO cardio_daily_metrics ({', '.join(fields)})
                    VALUES ({', '.join(placeholders)})
                ''', values)
                conn.commit()
                return cursor.lastrowid

    def get_cardio_baseline(self, date: str, lookback_days: int = 14) -> Dict[str, Optional[float]]:
        """
        Get baseline averages for RHR and HRV from the previous N days.
        
        Args:
            date: Reference date (YYYY-MM-DD)
            lookback_days: Number of days to look back (default 14)
        
        Returns:
            Dict with baseline_rhr and baseline_hrv (or None if no data)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get metrics from the past N days (excluding the given date)
            if self.user_id:
                cursor.execute('''
                    SELECT rhr_bpm, hrv_low_ms, hrv_high_ms
                    FROM cardio_daily_metrics
                    WHERE user_id = %s 
                      AND date < %s 
                      AND date >= DATE_SUB(%s, INTERVAL %s DAY)
                ''', (self.user_id, date, date, lookback_days))
            else:
                cursor.execute('''
                    SELECT rhr_bpm, hrv_low_ms, hrv_high_ms
                    FROM cardio_daily_metrics
                    WHERE date < %s 
                      AND date >= DATE_SUB(%s, INTERVAL %s DAY)
                ''', (date, date, lookback_days))
            
            rows = cursor.fetchall()
            
            if not rows:
                return {'baseline_rhr': None, 'baseline_hrv': None}
            
            # Calculate average RHR
            rhr_values = [r['rhr_bpm'] for r in rows if r['rhr_bpm'] is not None]
            baseline_rhr = sum(rhr_values) / len(rhr_values) if rhr_values else None
            
            # Calculate average HRV (using midpoint of low/high)
            hrv_values = []
            for r in rows:
                if r['hrv_low_ms'] is not None and r['hrv_high_ms'] is not None:
                    hrv_values.append((r['hrv_low_ms'] + r['hrv_high_ms']) / 2)
            baseline_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else None
            
            return {
                'baseline_rhr': baseline_rhr,
                'baseline_hrv': baseline_hrv
            }

    def calculate_hrv_rhr_status(self, date: str) -> Dict[str, Optional[int]]:
        """
        Calculate HRV and RHR status based on today's values vs 14-day baseline.
        
        Status values:
            -1 = worse than baseline (red)
             0 = neutral/similar to baseline (yellow)
            +1 = better than baseline (green)
        
        Args:
            date: Date to calculate status for (YYYY-MM-DD)
        
        Returns:
            Dict with hrv_status and rhr_status (or None if no data)
        """
        # Get today's cardio metrics
        today_metrics = self.get_cardio_metrics_for_date(date)
        
        if not today_metrics:
            return {'hrv_status': None, 'rhr_status': None, 'has_cardio': False}
        
        # Get baseline from previous 14 days
        baseline = self.get_cardio_baseline(date, lookback_days=14)
        
        result = {
            'hrv_status': None,
            'rhr_status': None,
            'has_cardio': True,
            'rhr_bpm': today_metrics.get('rhr_bpm'),
            'hrv_low_ms': today_metrics.get('hrv_low_ms'),
            'hrv_high_ms': today_metrics.get('hrv_high_ms'),
            'baseline_rhr': baseline['baseline_rhr'],
            'baseline_hrv': baseline['baseline_hrv']
        }
        
        # Calculate RHR status (higher RHR is worse)
        today_rhr = today_metrics.get('rhr_bpm')
        baseline_rhr = baseline['baseline_rhr']
        
        if today_rhr is not None and baseline_rhr is not None and baseline_rhr > 0:
            delta = (today_rhr - baseline_rhr) / baseline_rhr
            if delta > 0.07:
                result['rhr_status'] = -1  # Significantly higher = worse
            elif delta >= 0.03:
                result['rhr_status'] = 0   # Slightly higher = neutral
            else:
                result['rhr_status'] = 1   # Lower or same = good
        elif today_rhr is not None:
            result['rhr_status'] = 0  # No baseline, neutral
        
        # Calculate HRV status (lower HRV is worse)
        hrv_low = today_metrics.get('hrv_low_ms')
        hrv_high = today_metrics.get('hrv_high_ms')
        baseline_hrv = baseline['baseline_hrv']
        
        if hrv_low is not None and hrv_high is not None:
            today_hrv = (hrv_low + hrv_high) / 2
            
            if baseline_hrv is not None and baseline_hrv > 0:
                delta = (baseline_hrv - today_hrv) / baseline_hrv
                if delta > 0.10:
                    result['hrv_status'] = -1  # Significantly lower = worse
                elif delta >= 0.05:
                    result['hrv_status'] = 0   # Slightly lower = neutral
                else:
                    result['hrv_status'] = 1   # Higher or same = good
            else:
                result['hrv_status'] = 0  # No baseline, neutral
        
        return result

    # ============== Chart Data Methods ==============

    def get_cycling_chart_data(self, days: int = 30) -> Dict[str, List]:
        """Get data formatted for cycling charts"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT date, avg_power_w, avg_heart_rate, max_heart_rate, tss
                FROM cycling_workouts
                WHERE date >= %s
                ORDER BY date ASC
            ''', (start_date,))

            results = cursor.fetchall()

            return {
                'dates': [r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']) for r in results],
                'avg_power': [r['avg_power_w'] for r in results],
                'avg_heart_rate': [r['avg_heart_rate'] for r in results],
                'max_heart_rate': [r['max_heart_rate'] for r in results],
                'tss': [r['tss'] for r in results]
            }

    def get_readiness_chart_data(self, days: int = 30) -> Dict[str, List]:
        """Get data formatted for readiness charts"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT date, morning_score, energy, sleep_minutes
                FROM readiness_entries
                WHERE date >= %s
                ORDER BY date ASC
            ''', (start_date,))

            results = cursor.fetchall()

            return {
                'dates': [r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']) for r in results],
                'morning_score': [r['morning_score'] for r in results],
                'energy': [r['energy'] for r in results],
                'sleep_hours': [round(r['sleep_minutes'] / 60, 1) if r['sleep_minutes'] else None for r in results]
            }

    # ============== Readiness Update Method ==============

    def update_readiness_entry(self, entry_id: int, **kwargs) -> bool:
        """
        Update a readiness entry with partial data.
        Only updates fields that are provided.
        """
        if not kwargs:
            return False

        # Build dynamic update query
        allowed_fields = [
            'energy', 'mood', 'muscle_fatigue',
            'hrv_status', 'rhr_status', 'min_hr_status',
            'symptoms_flag', 'evening_note', 'morning_score'
        ]
        
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = %s")
                values.append(value)

        if not set_clauses:
            return False

        values.append(entry_id)
        query = f"UPDATE readiness_entries SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def get_readiness_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        """Get a specific readiness entry by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM readiness_entries WHERE id = %s', (entry_id,))
            return cursor.fetchone()

    # ============== Expanded Table Data ==============

    def get_expanded_data(self, days: int = 90, from_date: str = None, to_date: str = None) -> List[Dict]:
        """
        Get all data for expanded table view.
        Returns one row per date with cycling, readiness, and sleep data combined.
        
        Args:
            days: Number of days to look back (default 90)
            from_date: Optional start date (YYYY-MM-DD)
            to_date: Optional end date (YYYY-MM-DD)
        
        Returns:
            List of dicts with combined data per date
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Determine date range
            if from_date and to_date:
                start_date = from_date
                end_date = to_date
            else:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get all unique dates from all four tables
            cursor.execute('''
                SELECT DISTINCT date FROM (
                    SELECT date FROM cycling_workouts WHERE date BETWEEN %s AND %s
                    UNION
                    SELECT date FROM readiness_entries WHERE date BETWEEN %s AND %s
                    UNION
                    SELECT date FROM sleep_summaries WHERE date BETWEEN %s AND %s
                    UNION
                    SELECT date FROM cardio_daily_metrics WHERE date BETWEEN %s AND %s
                ) AS all_dates
                ORDER BY date DESC
            ''', (start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date))
            
            dates = [row['date'] for row in cursor.fetchall()]
            
            result = []
            for d in dates:
                date_str = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
                
                # Get cycling data
                if self.user_id:
                    cursor.execute('''
                        SELECT * FROM cycling_workouts WHERE user_id = %s AND date = %s LIMIT 1
                    ''', (self.user_id, d))
                else:
                    cursor.execute('SELECT * FROM cycling_workouts WHERE date = %s LIMIT 1', (d,))
                cycling = cursor.fetchone()
                
                # Get readiness data
                if self.user_id:
                    cursor.execute('''
                        SELECT * FROM readiness_entries WHERE user_id = %s AND date = %s LIMIT 1
                    ''', (self.user_id, d))
                else:
                    cursor.execute('SELECT * FROM readiness_entries WHERE date = %s LIMIT 1', (d,))
                readiness = cursor.fetchone()
                
                # Get sleep data
                if self.user_id:
                    cursor.execute('''
                        SELECT * FROM sleep_summaries WHERE user_id = %s AND date = %s LIMIT 1
                    ''', (self.user_id, d))
                else:
                    cursor.execute('SELECT * FROM sleep_summaries WHERE date = %s LIMIT 1', (d,))
                sleep = cursor.fetchone()
                
                # Get cardio metrics
                if self.user_id:
                    cursor.execute('''
                        SELECT * FROM cardio_daily_metrics WHERE user_id = %s AND date = %s LIMIT 1
                    ''', (self.user_id, d))
                else:
                    cursor.execute('SELECT * FROM cardio_daily_metrics WHERE date = %s LIMIT 1', (d,))
                cardio = cursor.fetchone()
                
                # Combine into single row with prefixed keys
                row = {
                    'date': date_str,
                    'has_cycling': cycling is not None,
                    'has_readiness': readiness is not None,
                    'has_sleep': sleep is not None,
                    'has_cardio': cardio is not None,
                    # Cycling fields
                    'c_id': cycling.get('id') if cycling else None,
                    'c_duration_sec': cycling.get('duration_sec') if cycling else None,
                    'c_distance_km': cycling.get('distance_km') if cycling else None,
                    'c_avg_power_w': cycling.get('avg_power_w') if cycling else None,
                    'c_max_power_w': cycling.get('max_power_w') if cycling else None,
                    'c_normalized_power_w': cycling.get('normalized_power_w') if cycling else None,
                    'c_intensity_factor': cycling.get('intensity_factor') if cycling else None,
                    'c_tss': cycling.get('tss') if cycling else None,
                    'c_avg_heart_rate': cycling.get('avg_heart_rate') if cycling else None,
                    'c_max_heart_rate': cycling.get('max_heart_rate') if cycling else None,
                    'c_avg_cadence': cycling.get('avg_cadence') if cycling else None,
                    'c_kcal_active': cycling.get('kcal_active') if cycling else None,
                    'c_kcal_total': cycling.get('kcal_total') if cycling else None,
                    'c_source': cycling.get('source') if cycling else None,
                    'c_notes': cycling.get('notes') if cycling else None,
                    # Readiness fields
                    'r_id': readiness.get('id') if readiness else None,
                    'r_energy': readiness.get('energy') if readiness else None,
                    'r_mood': readiness.get('mood') if readiness else None,
                    'r_muscle_fatigue': readiness.get('muscle_fatigue') if readiness else None,
                    'r_hrv_status': readiness.get('hrv_status') if readiness else None,
                    'r_rhr_status': readiness.get('rhr_status') if readiness else None,
                    'r_min_hr_status': readiness.get('min_hr_status') if readiness else None,
                    'r_symptoms_flag': readiness.get('symptoms_flag') if readiness else None,
                    'r_morning_score': readiness.get('morning_score') if readiness else None,
                    'r_sleep_minutes': readiness.get('sleep_minutes') if readiness else None,
                    'r_deep_sleep_minutes': readiness.get('deep_sleep_minutes') if readiness else None,
                    'r_awake_minutes': readiness.get('awake_minutes') if readiness else None,
                    # Sleep fields
                    's_id': sleep.get('id') if sleep else None,
                    's_total_sleep_minutes': sleep.get('total_sleep_minutes') if sleep else None,
                    's_deep_sleep_minutes': sleep.get('deep_sleep_minutes') if sleep else None,
                    's_awake_minutes': sleep.get('awake_minutes') if sleep else None,
                    's_min_heart_rate': sleep.get('min_heart_rate') if sleep else None,
                    's_max_heart_rate': sleep.get('max_heart_rate') if sleep else None,
                    's_avg_heart_rate': sleep.get('avg_heart_rate') if sleep else None,
                    's_sleep_start': str(sleep.get('sleep_start_time')) if sleep and sleep.get('sleep_start_time') else None,
                    's_sleep_end': str(sleep.get('sleep_end_time')) if sleep and sleep.get('sleep_end_time') else None,
                    # Cardio fields
                    'cardio_id': cardio.get('id') if cardio else None,
                    'cardio_rhr_bpm': cardio.get('rhr_bpm') if cardio else None,
                    'cardio_hrv_low': cardio.get('hrv_low_ms') if cardio else None,
                    'cardio_hrv_high': cardio.get('hrv_high_ms') if cardio else None,
                }
                
                # Get training recommendation for this date (if any)
                if self.user_id:
                    cursor.execute('''
                        SELECT day_type, duration_minutes FROM training_recommendations 
                        WHERE user_id = %s AND date = %s LIMIT 1
                    ''', (self.user_id, d))
                else:
                    cursor.execute('SELECT day_type, duration_minutes FROM training_recommendations WHERE date = %s LIMIT 1', (d,))
                rec = cursor.fetchone()
                row['has_training_rec'] = rec is not None
                row['tr_day_type'] = rec.get('day_type') if rec else None
                row['tr_duration'] = rec.get('duration_minutes') if rec else None
                
                # Add missing field flags
                row['missing_cycling'] = self._get_missing_cycling_fields(cycling) if cycling else []
                row['missing_readiness'] = self._get_missing_readiness_fields(readiness) if readiness else []
                row['missing_sleep'] = self._get_missing_sleep_fields(sleep) if sleep else []
                row['missing_cardio'] = self._get_missing_cardio_fields(cardio) if cardio else []
                
                result.append(row)
            
            return result

    def _get_missing_cycling_fields(self, data: Dict) -> List[str]:
        """Check which cycling fields are missing (null or 0)"""
        important_fields = [
            'duration_sec', 'avg_power_w', 'max_power_w', 
            'avg_heart_rate', 'max_heart_rate', 'tss'
        ]
        missing = []
        for f in important_fields:
            val = data.get(f)
            if val is None or val == 0:
                missing.append(f)
        return missing

    def _get_missing_readiness_fields(self, data: Dict) -> List[str]:
        """Check which readiness fields are missing"""
        important_fields = ['energy', 'mood', 'muscle_fatigue', 'morning_score']
        missing = []
        for f in important_fields:
            if data.get(f) is None:
                missing.append(f)
        return missing

    def _get_missing_sleep_fields(self, data: Dict) -> List[str]:
        """Check which sleep fields are missing"""
        important_fields = [
            'total_sleep_minutes', 'deep_sleep_minutes', 
            'min_heart_rate', 'max_heart_rate'
        ]
        missing = []
        for f in important_fields:
            if data.get(f) is None:
                missing.append(f)
        return missing

    def _get_missing_cardio_fields(self, data: Dict) -> List[str]:
        """Check which cardio fields are missing"""
        important_fields = ['rhr_bpm', 'hrv_low_ms', 'hrv_high_ms']
        missing = []
        for f in important_fields:
            if data.get(f) is None:
                missing.append(f)
        return missing

    # ============== Training Context Builder ==============

    def build_training_context(self, target_date: date) -> Dict[str, Any]:
        """
        Build a comprehensive training context object for AI-powered recommendations.
        
        This function aggregates data from all relevant tables to create a context
        object that can be sent to OpenAI for daily training recommendations.
        
        Args:
            target_date: The date to build context for (typically today)
        
        Returns:
            Dict with three main sections:
            - today: Current day's complete data
            - last_7_days: Summary of previous 7 days
            - baseline_30_days: Rolling statistics for last 30 days
        """
        target_date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, date) else str(target_date)
        
        return {
            'today': self._get_today_context(target_date_str),
            'last_7_days': self._get_last_7_days_context(target_date_str),
            'baseline_30_days': self._get_baseline_30_days(target_date_str)
        }

    def _get_today_context(self, target_date: str) -> Dict[str, Any]:
        """
        Get complete context for the target date.
        
        Args:
            target_date: Date string (YYYY-MM-DD)
        
        Returns:
            Dict with readiness, sleep, cardio, and workout data for the day
        """
        # Get data from all tables for this date
        readiness = self.get_readiness_by_date(target_date)
        sleep = self.get_sleep_summary_by_date(target_date)
        cardio = self.get_cardio_metrics_for_date(target_date)
        workout = self.get_cycling_workout_by_date(target_date)
        
        # Map mood value to label
        mood_map = {1: 'low', 2: 'neutral', 3: 'high'}
        # Map muscle fatigue to label
        fatigue_map = {1: 'low', 2: 'med', 3: 'high'}
        
        # Determine workout type from source or notes
        workout_type = self._determine_workout_type(workout) if workout else 'rest'
        
        return {
            'date': target_date,
            'readiness': {
                'score': readiness.get('morning_score') if readiness else None,
                'energy': readiness.get('energy') if readiness else None,
                'mood': mood_map.get(readiness.get('mood')) if readiness and readiness.get('mood') else None,
                'muscle_fatigue': fatigue_map.get(readiness.get('muscle_fatigue')) if readiness and readiness.get('muscle_fatigue') else None,
                'hrv_status': readiness.get('hrv_status') if readiness else None,
                'rhr_status': readiness.get('rhr_status') if readiness else None,
                'symptoms': readiness.get('symptoms_flag') if readiness else None
            },
            'sleep': {
                'total_minutes': sleep.get('total_sleep_minutes') if sleep else None,
                'deep_minutes': sleep.get('deep_sleep_minutes') if sleep else None,
                'awake_minutes': sleep.get('awake_minutes') if sleep else None,
                'min_hr': sleep.get('min_heart_rate') if sleep else None,
                'max_hr': sleep.get('max_heart_rate') if sleep else None
            },
            'cardio': {
                'rhr_bpm': cardio.get('rhr_bpm') if cardio else None,
                'hrv_low_ms': cardio.get('hrv_low_ms') if cardio else None,
                'hrv_high_ms': cardio.get('hrv_high_ms') if cardio else None
            },
            'workout': {
                'has_workout': workout is not None,
                'type': workout_type,
                'duration_minutes': int(workout.get('duration_sec') / 60) if workout and workout.get('duration_sec') else None,
                'avg_power_w': workout.get('avg_power_w') if workout else None,
                'tss': workout.get('tss') if workout else None,
                'intensity_factor': workout.get('intensity_factor') if workout else None
            }
        }

    def _determine_workout_type(self, workout: Dict) -> str:
        """
        Determine workout type from source and intensity.
        
        Args:
            workout: Workout record from database
        
        Returns:
            Workout type string: 'rest', 'z1', 'z2', 'norwegian_4x4', or 'other'
        """
        if not workout:
            return 'rest'
        
        # Check notes for specific workout types
        notes = (workout.get('notes') or '').lower()
        source = (workout.get('source') or '').lower()
        
        if 'norwegian' in notes or '4x4' in notes or '4 x 4' in notes:
            return 'norwegian_4x4'
        
        # Use intensity factor to guess zone
        intensity = workout.get('intensity_factor')
        if intensity is not None:
            if intensity < 0.55:
                return 'z1'  # Recovery / Zone 1
            elif intensity < 0.75:
                return 'z2'  # Endurance / Zone 2
            elif intensity >= 0.85:
                return 'norwegian_4x4'  # High intensity
            else:
                return 'other'  # Tempo / Threshold range
        
        # Default based on duration if no intensity data
        duration_min = (workout.get('duration_sec') or 0) / 60
        if duration_min < 30:
            return 'z1'  # Short workout = likely recovery
        elif duration_min < 90:
            return 'z2'  # Medium duration = likely endurance
        
        return 'other'

    def _get_last_7_days_context(self, target_date: str) -> List[Dict[str, Any]]:
        """
        Get summary data for the 7 days before target_date.
        
        Args:
            target_date: Date string (YYYY-MM-DD)
        
        Returns:
            List of daily summaries, ordered oldest to newest
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Query all tables for the 7 days before target_date
            query = '''
                WITH date_range AS (
                    SELECT DATE_SUB(%s, INTERVAL n DAY) as date
                    FROM (
                        SELECT 1 as n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 
                        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7
                    ) nums
                )
                SELECT 
                    dr.date,
                    re.morning_score as readiness_score,
                    cw.source as workout_source,
                    cw.notes as workout_notes,
                    cw.intensity_factor,
                    ROUND(cw.duration_sec / 60) as workout_duration_minutes,
                    cw.tss,
                    cdm.rhr_bpm,
                    cdm.hrv_low_ms,
                    cdm.hrv_high_ms
                FROM date_range dr
                LEFT JOIN readiness_entries re ON re.date = dr.date AND re.user_id = %s
                LEFT JOIN cycling_workouts cw ON cw.date = dr.date AND cw.user_id = %s
                LEFT JOIN cardio_daily_metrics cdm ON cdm.date = dr.date AND cdm.user_id = %s
                ORDER BY dr.date ASC
            '''
            cursor.execute(query, (target_date, self.user_id, self.user_id, self.user_id))
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                # Calculate HRV average if both low and high are present
                hrv_avg = None
                if row['hrv_low_ms'] is not None and row['hrv_high_ms'] is not None:
                    hrv_avg = (row['hrv_low_ms'] + row['hrv_high_ms']) / 2
                
                # Determine workout type
                workout_type = None
                if row['workout_duration_minutes']:
                    # Build a fake workout dict for type determination
                    fake_workout = {
                        'source': row['workout_source'],
                        'notes': row['workout_notes'],
                        'intensity_factor': row['intensity_factor'],
                        'duration_sec': (row['workout_duration_minutes'] or 0) * 60
                    }
                    workout_type = self._determine_workout_type(fake_workout)
                else:
                    workout_type = 'rest'
                
                result.append({
                    'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    'readiness_score': row['readiness_score'],
                    'workout_type': workout_type,
                    'workout_duration_minutes': int(row['workout_duration_minutes']) if row['workout_duration_minutes'] else None,
                    'tss': float(row['tss']) if row['tss'] else None,
                    'rhr_bpm': row['rhr_bpm'],
                    'hrv_avg_ms': round(hrv_avg, 1) if hrv_avg else None
                })
            
            return result

    def _get_baseline_30_days(self, target_date: str) -> Dict[str, Any]:
        """
        Calculate rolling statistics for the 30 days before target_date.
        
        Args:
            target_date: Date string (YYYY-MM-DD)
        
        Returns:
            Dict with aggregated statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Calculate date range (30 days before target_date, not including target)
            end_date = target_date
            
            # Get cardio averages
            cursor.execute('''
                SELECT 
                    COUNT(*) as days_with_rhr,
                    AVG(rhr_bpm) as avg_rhr,
                    AVG((hrv_low_ms + hrv_high_ms) / 2) as avg_hrv
                FROM cardio_daily_metrics
                WHERE user_id = %s 
                  AND date >= DATE_SUB(%s, INTERVAL 30 DAY)
                  AND date < %s
            ''', (self.user_id, end_date, end_date))
            cardio_stats = cursor.fetchone()
            
            # Get sleep averages
            cursor.execute('''
                SELECT 
                    COUNT(*) as days_with_sleep,
                    AVG(total_sleep_minutes) as avg_sleep,
                    AVG(deep_sleep_minutes) as avg_deep
                FROM sleep_summaries
                WHERE user_id = %s 
                  AND date >= DATE_SUB(%s, INTERVAL 30 DAY)
                  AND date < %s
            ''', (self.user_id, end_date, end_date))
            sleep_stats = cursor.fetchone()
            
            # Get readiness averages
            cursor.execute('''
                SELECT 
                    COUNT(*) as days_with_readiness,
                    AVG(morning_score) as avg_score
                FROM readiness_entries
                WHERE user_id = %s 
                  AND date >= DATE_SUB(%s, INTERVAL 30 DAY)
                  AND date < %s
                  AND morning_score IS NOT NULL
            ''', (self.user_id, end_date, end_date))
            readiness_stats = cursor.fetchone()
            
            # Get workout stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as workout_count,
                    SUM(tss) as total_tss
                FROM cycling_workouts
                WHERE user_id = %s 
                  AND date >= DATE_SUB(%s, INTERVAL 30 DAY)
                  AND date < %s
            ''', (self.user_id, end_date, end_date))
            workout_stats = cursor.fetchone()
            
            # Calculate per-week averages
            days_in_window = 30
            weeks_in_window = days_in_window / 7.0
            
            workout_count = workout_stats['workout_count'] or 0
            total_tss = workout_stats['total_tss'] or 0
            
            avg_workouts_per_week = round(workout_count / weeks_in_window, 2) if workout_count > 0 else 0
            avg_tss_per_week = round(total_tss / weeks_in_window, 1) if total_tss > 0 else None
            
            return {
                'days_count': days_in_window,
                'avg_rhr_bpm': round(cardio_stats['avg_rhr'], 1) if cardio_stats and cardio_stats['avg_rhr'] else None,
                'avg_hrv_ms': round(cardio_stats['avg_hrv'], 1) if cardio_stats and cardio_stats['avg_hrv'] else None,
                'avg_sleep_minutes': round(sleep_stats['avg_sleep'], 0) if sleep_stats and sleep_stats['avg_sleep'] else None,
                'avg_deep_sleep_minutes': round(sleep_stats['avg_deep'], 0) if sleep_stats and sleep_stats['avg_deep'] else None,
                'avg_readiness_score': round(readiness_stats['avg_score'], 1) if readiness_stats and readiness_stats['avg_score'] else None,
                'avg_workouts_per_week': avg_workouts_per_week,
                'avg_tss_per_week': avg_tss_per_week
            }

