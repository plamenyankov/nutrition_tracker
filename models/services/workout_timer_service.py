#!/usr/bin/env python3
"""
Workout Timer Service
Handles timing for workouts and individual sets with persistence to database
"""

import os
import time
from datetime import datetime, timedelta
from models.database.connection_manager import get_db_manager

class WorkoutTimerService:
    """Service for managing workout and set timing"""

    def __init__(self, user_id=2):
        self.user_id = user_id
        self.connection_manager = get_db_manager()

    def get_connection(self):
        """Get database connection"""
        return self.connection_manager.get_connection()

    def start_workout_timer(self, session_id, notes=None):
        """Start timing a workout session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            start_time = datetime.now()

            if self.connection_manager.use_mysql:
                # Update workout session with start time and status
                cursor.execute('''
                    UPDATE workout_sessions
                    SET started_at = %s, status = 'in_progress'
                    WHERE id = %s AND user_id = %s
                ''', (start_time, session_id, self.user_id))

                # Log timing event
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp, notes)
                    VALUES (%s, %s, %s, %s)
                ''', (session_id, 'workout_start', start_time, notes))
            else:
                # Update workout session with start time and status
                cursor.execute('''
                    UPDATE workout_sessions
                    SET started_at = ?, status = 'in_progress'
                    WHERE id = ? AND user_id = ?
                ''', (start_time, session_id, self.user_id))

                # Log timing event
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp, notes)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, 'workout_start', start_time, notes))

            conn.commit()

            return {
                'session_id': session_id,
                'started_at': start_time,
                'status': 'in_progress'
            }

    def pause_workout_timer(self, session_id):
        """Pause the workout timer"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            pause_time = datetime.now()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp)
                    VALUES (%s, %s, %s)
                ''', (session_id, 'workout_pause', pause_time))
            else:
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp)
                    VALUES (?, ?, ?)
                ''', (session_id, 'workout_pause', pause_time))

            conn.commit()

            return {'paused_at': pause_time}

    def resume_workout_timer(self, session_id):
        """Resume the workout timer"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            resume_time = datetime.now()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp)
                    VALUES (%s, %s, %s)
                ''', (session_id, 'workout_resume', resume_time))
            else:
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp)
                    VALUES (?, ?, ?)
                ''', (session_id, 'workout_resume', resume_time))

            conn.commit()

            return {'resumed_at': resume_time}

    def complete_workout_timer(self, session_id):
        """Complete the workout and calculate total duration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            complete_time = datetime.now()

            # Get workout start time
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT started_at FROM workout_sessions
                    WHERE id = %s AND user_id = %s
                ''', (session_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT started_at FROM workout_sessions
                    WHERE id = ? AND user_id = ?
                ''', (session_id, self.user_id))

            result = cursor.fetchone()
            if not result or not result[0]:
                return {'error': 'Workout not found or not started'}

            start_time = datetime.fromisoformat(result[0]) if isinstance(result[0], str) else result[0]

            # Calculate total duration (excluding pause times)
            total_duration = self._calculate_workout_duration(session_id, start_time, complete_time)

            # Update workout session
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET completed_at = %s, duration_seconds = %s, status = 'completed'
                    WHERE id = %s AND user_id = %s
                ''', (complete_time, total_duration, session_id, self.user_id))

                # Log timing event
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp, duration_seconds)
                    VALUES (%s, %s, %s, %s)
                ''', (session_id, 'workout_complete', complete_time, total_duration))
            else:
                cursor.execute('''
                    UPDATE workout_sessions
                    SET completed_at = ?, duration_seconds = ?, status = 'completed'
                    WHERE id = ? AND user_id = ?
                ''', (complete_time, total_duration, session_id, self.user_id))

                # Log timing event
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, timestamp, duration_seconds)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, 'workout_complete', complete_time, total_duration))

            conn.commit()

            return {
                'completed_at': complete_time,
                'duration_seconds': total_duration,
                'duration_formatted': self._format_duration(total_duration)
            }

    def start_set_timer(self, session_id, exercise_id, set_id):
        """Start timing a specific set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            start_time = datetime.now()

            # Update the set with start time
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sets
                    SET started_at = %s
                    WHERE id = %s
                ''', (start_time, set_id))

                # Log timing event
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, exercise_id, set_id, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (session_id, 'set_start', exercise_id, set_id, start_time))
            else:
                cursor.execute('''
                    UPDATE workout_sets
                    SET started_at = ?
                    WHERE id = ?
                ''', (start_time, set_id))

                # Log timing event
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, exercise_id, set_id, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, 'set_start', exercise_id, set_id, start_time))

            conn.commit()

            return {
                'set_id': set_id,
                'started_at': start_time
            }

    def complete_set_timer(self, session_id, exercise_id, set_id):
        """Complete timing for a specific set"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            complete_time = datetime.now()

            # Get set start time
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT started_at FROM workout_sets WHERE id = %s
                ''', (set_id,))
            else:
                cursor.execute('''
                    SELECT started_at FROM workout_sets WHERE id = ?
                ''', (set_id,))

            result = cursor.fetchone()
            if not result or not result[0]:
                return {'error': 'Set not found or not started'}

            start_time = datetime.fromisoformat(result[0]) if isinstance(result[0], str) else result[0]
            duration = int((complete_time - start_time).total_seconds())

            # Update the set with completion time and duration
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sets
                    SET completed_at = %s, duration_seconds = %s
                    WHERE id = %s
                ''', (complete_time, duration, set_id))
            else:
                cursor.execute('''
                    UPDATE workout_sets
                    SET completed_at = ?, duration_seconds = ?
                    WHERE id = ?
                ''', (complete_time, duration, set_id))

            conn.commit()

            return {
                'set_id': set_id,
                'completed_at': complete_time,
                'duration_seconds': duration,
                'duration_formatted': self._format_duration(duration)
            }

    def start_rest_timer(self, session_id, previous_set_id, next_exercise_id=None):
        """Start timing rest period between sets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            rest_start = datetime.now()

            if self.connection_manager.use_mysql:
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, set_id, exercise_id, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (session_id, 'rest_start', previous_set_id, next_exercise_id, rest_start))
            else:
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, set_id, exercise_id, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, 'rest_start', previous_set_id, next_exercise_id, rest_start))

            conn.commit()

            return {
                'rest_started_at': rest_start,
                'previous_set_id': previous_set_id
            }

    def complete_rest_timer(self, session_id, previous_set_id):
        """Complete rest period and update previous set with rest duration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            rest_end = datetime.now()

            # Get rest start time
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT timestamp FROM workout_timing_sessions
                    WHERE session_id = %s AND event_type = 'rest_start' AND set_id = %s
                    ORDER BY timestamp DESC LIMIT 1
                ''', (session_id, previous_set_id))
            else:
                cursor.execute('''
                    SELECT timestamp FROM workout_timing_sessions
                    WHERE session_id = ? AND event_type = 'rest_start' AND set_id = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (session_id, previous_set_id))

            result = cursor.fetchone()
            if not result:
                return {'error': 'Rest period not found'}

            rest_start = datetime.fromisoformat(result[0]) if isinstance(result[0], str) else result[0]
            rest_duration = int((rest_end - rest_start).total_seconds())

            # Update previous set with rest duration
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    UPDATE workout_sets
                    SET rest_duration_seconds = %s
                    WHERE id = %s
                ''', (rest_duration, previous_set_id))

                # Log rest completion
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, set_id, timestamp, duration_seconds)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (session_id, 'rest_complete', previous_set_id, rest_end, rest_duration))
            else:
                cursor.execute('''
                    UPDATE workout_sets
                    SET rest_duration_seconds = ?
                    WHERE id = ?
                ''', (rest_duration, previous_set_id))

                # Log rest completion
                cursor.execute('''
                    INSERT INTO workout_timing_sessions
                    (session_id, event_type, set_id, timestamp, duration_seconds)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, 'rest_complete', previous_set_id, rest_end, rest_duration))

            conn.commit()

            return {
                'rest_completed_at': rest_end,
                'rest_duration_seconds': rest_duration,
                'rest_duration_formatted': self._format_duration(rest_duration)
            }

    def get_workout_timing_summary(self, session_id):
        """Get comprehensive timing summary for a workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get workout session timing
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT started_at, completed_at, duration_seconds, status
                    FROM workout_sessions
                    WHERE id = %s AND user_id = %s
                ''', (session_id, self.user_id))
            else:
                cursor.execute('''
                    SELECT started_at, completed_at, duration_seconds, status
                    FROM workout_sessions
                    WHERE id = ? AND user_id = ?
                ''', (session_id, self.user_id))

            workout_info = cursor.fetchone()
            if not workout_info:
                return {'error': 'Workout not found'}

            # Get set timing details
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT ws.id, ws.exercise_id, e.name, ws.set_number,
                           ws.started_at, ws.completed_at, ws.duration_seconds, ws.rest_duration_seconds
                    FROM workout_sets ws
                    JOIN exercises e ON ws.exercise_id = e.id
                    WHERE ws.session_id = %s
                    ORDER BY ws.id
                ''', (session_id,))
            else:
                cursor.execute('''
                    SELECT ws.id, ws.exercise_id, e.name, ws.set_number,
                           ws.started_at, ws.completed_at, ws.duration_seconds, ws.rest_duration_seconds
                    FROM workout_sets ws
                    JOIN exercises e ON ws.exercise_id = e.id
                    WHERE ws.session_id = ?
                    ORDER BY ws.id
                ''', (session_id,))

            sets_timing = cursor.fetchall()

            # Calculate summary statistics
            total_set_time = sum(s[6] for s in sets_timing if s[6])
            total_rest_time = sum(s[7] for s in sets_timing if s[7])

            return {
                'session_id': session_id,
                'started_at': workout_info[0],
                'completed_at': workout_info[1],
                'total_duration_seconds': workout_info[2],
                'total_duration_formatted': self._format_duration(workout_info[2]) if workout_info[2] else None,
                'status': workout_info[3],
                'total_sets': len(sets_timing),
                'total_set_time_seconds': total_set_time,
                'total_set_time_formatted': self._format_duration(total_set_time),
                'total_rest_time_seconds': total_rest_time,
                'total_rest_time_formatted': self._format_duration(total_rest_time),
                'sets_timing': [
                    {
                        'set_id': s[0],
                        'exercise_id': s[1],
                        'exercise_name': s[2],
                        'set_number': s[3],
                        'started_at': s[4],
                        'completed_at': s[5],
                        'duration_seconds': s[6],
                        'duration_formatted': self._format_duration(s[6]) if s[6] else None,
                        'rest_duration_seconds': s[7],
                        'rest_duration_formatted': self._format_duration(s[7]) if s[7] else None
                    }
                    for s in sets_timing
                ]
            }

    def _calculate_workout_duration(self, session_id, start_time, end_time):
        """Calculate total workout duration excluding pause times"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get all pause/resume events
            if self.connection_manager.use_mysql:
                cursor.execute('''
                    SELECT event_type, timestamp FROM workout_timing_sessions
                    WHERE session_id = %s AND event_type IN ('workout_pause', 'workout_resume')
                    ORDER BY timestamp
                ''', (session_id,))
            else:
                cursor.execute('''
                    SELECT event_type, timestamp FROM workout_timing_sessions
                    WHERE session_id = ? AND event_type IN ('workout_pause', 'workout_resume')
                    ORDER BY timestamp
                ''', (session_id,))

            pause_events = cursor.fetchall()

            # Calculate total pause time
            total_pause_time = 0
            pause_start = None

            for event_type, timestamp in pause_events:
                event_time = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp

                if event_type == 'workout_pause':
                    pause_start = event_time
                elif event_type == 'workout_resume' and pause_start:
                    total_pause_time += (event_time - pause_start).total_seconds()
                    pause_start = None

            # If workout ended while paused, count pause time until end
            if pause_start:
                total_pause_time += (end_time - pause_start).total_seconds()

            # Total duration minus pause time
            total_duration = (end_time - start_time).total_seconds() - total_pause_time
            return int(max(0, total_duration))  # Ensure non-negative

    def _format_duration(self, seconds):
        """Format duration in seconds to human readable format"""
        if not seconds:
            return "0s"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
