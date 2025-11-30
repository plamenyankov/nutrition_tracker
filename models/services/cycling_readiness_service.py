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
        wakeups_count: int,
        stress_level: int,
        symptoms_flag: bool
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
        - Wakeups: 5 points max (fewer = better)
        - Stress level (1-3): 5 points max (inverted)
        - Symptoms: -10 points if true
        """
        score = 0

        # Energy: 1-5 → 0-20 points
        score += (energy - 1) * 5  # 0, 5, 10, 15, 20

        # Mood: 1-3 → 0-10 points
        score += (mood - 1) * 5  # 0, 5, 10

        # Muscle fatigue: 1-3 → inverted (1=no fatigue=10pts, 3=high fatigue=0pts)
        score += (3 - muscle_fatigue) * 5  # 10, 5, 0

        # HRV status: -1/0/1 → 0/5/10 points
        score += (hrv_status + 1) * 5  # 0, 5, 10

        # RHR status: -1/0/1 → 0/5/10 points
        score += (rhr_status + 1) * 5  # 0, 5, 10

        # Min HR status: -1/0/1 → 0/2.5/5 points
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

        # Wakeups: 0-1 = 5pts, 2 = 3pts, 3+ = 0pts
        if wakeups_count is not None:
            if wakeups_count <= 1:
                score += 5
            elif wakeups_count == 2:
                score += 3
            # else: 0 points

        # Stress level: 1-3 → inverted (1=low stress=5pts, 3=high stress=0pts)
        score += (3 - stress_level) * 2.5  # 5, 2.5, 0

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
        wakeups_count = sleep_payload.get('wakeups_count')
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
                        wakeups_count = COALESCE(%s, wakeups_count),
                        min_hr_status = COALESCE(%s, min_hr_status)
                    WHERE id = %s
                ''', (
                    sleep_minutes, deep_sleep_minutes, wakeups_count,
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
                    wakeups_count=updated.get('wakeups_count') or 0,
                    stress_level=updated.get('stress_level') or 2,
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
                wakeups_count=wakeups_count or 0,
                stress_level=2,
                symptoms_flag=False
            )
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO readiness_entries (
                        user_id, date, sleep_minutes, deep_sleep_minutes,
                        wakeups_count, min_hr_status, morning_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    self.user_id, readiness_date, sleep_minutes,
                    deep_sleep_minutes, wakeups_count,
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
        hrv_status: int,
        rhr_status: int,
        min_hr_status: int,
        sleep_minutes: int,
        deep_sleep_minutes: int,
        wakeups_count: int,
        stress_level: int,
        symptoms_flag: bool,
        evening_note: str = None
    ) -> Tuple[int, int]:
        """
        Create or update a readiness entry for the given date.
        Returns tuple of (entry_id, morning_score)
        """
        # Calculate morning score
        morning_score = self.calculate_morning_score(
            energy, mood, muscle_fatigue,
            hrv_status, rhr_status, min_hr_status,
            sleep_minutes, deep_sleep_minutes, wakeups_count,
            stress_level, symptoms_flag
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Try to update existing entry first
            cursor.execute('''
                UPDATE readiness_entries SET
                    energy = %s, mood = %s, muscle_fatigue = %s,
                    hrv_status = %s, rhr_status = %s, min_hr_status = %s,
                    sleep_minutes = %s, deep_sleep_minutes = %s, wakeups_count = %s,
                    stress_level = %s, symptoms_flag = %s, morning_score = %s,
                    evening_note = COALESCE(%s, evening_note)
                WHERE user_id = %s AND date = %s
            ''', (
                energy, mood, muscle_fatigue,
                hrv_status, rhr_status, min_hr_status,
                sleep_minutes, deep_sleep_minutes, wakeups_count,
                stress_level, symptoms_flag, morning_score,
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
                    sleep_minutes, deep_sleep_minutes, wakeups_count,
                    stress_level, symptoms_flag, morning_score, evening_note
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.user_id, date, energy, mood, muscle_fatigue,
                hrv_status, rhr_status, min_hr_status,
                sleep_minutes, deep_sleep_minutes, wakeups_count,
                stress_level, symptoms_flag, morning_score, evening_note
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
        wakeups_count: int = None,
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
                        wakeups_count = COALESCE(%s, wakeups_count),
                        min_heart_rate = COALESCE(%s, min_heart_rate),
                        avg_heart_rate = COALESCE(%s, avg_heart_rate),
                        max_heart_rate = COALESCE(%s, max_heart_rate),
                        notes = COALESCE(%s, notes),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (
                    sleep_start_time, sleep_end_time,
                    total_sleep_minutes, deep_sleep_minutes, wakeups_count,
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
                        total_sleep_minutes, deep_sleep_minutes, wakeups_count,
                        min_heart_rate, avg_heart_rate, max_heart_rate, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    self.user_id, date, sleep_start_time, sleep_end_time,
                    total_sleep_minutes, deep_sleep_minutes, wakeups_count,
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

