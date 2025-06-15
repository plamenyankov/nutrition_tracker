#!/usr/bin/env python3
"""
Test script to verify timer functionality works with MySQL database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.services.gym_service import GymService
from models.services.workout_timer_service import WorkoutTimerService

def test_database_connection():
    """Test that we can connect to the database and see workout data"""
    print("="*60)
    print("TESTING DATABASE CONNECTION AND WORKOUT DATA")
    print("="*60)

    try:
        gym_service = GymService()

        # Test connection
        print("Testing database connection...")
        with gym_service.get_connection() as conn:
            cursor = conn.cursor()
            if gym_service.connection_manager.use_mysql:
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                print(f"✓ Connected to MySQL database: {db_name}")
            else:
                print("✓ Connected to SQLite database")

        # Get workout data
        print("\nFetching workout data...")
        workouts = gym_service.get_user_workouts(limit=5)
        print(f"✓ Found {len(workouts)} workout sessions")

        if workouts:
            for i, workout in enumerate(workouts):
                print(f"  Workout {i+1}: ID={workout[0]}, Date={workout[2]}, Exercises={workout[-1]}")

        # Get exercises
        print("\nFetching exercises...")
        exercises = gym_service.get_all_exercises()
        print(f"✓ Found {len(exercises)} exercises")

        return True, workouts

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False, []

def test_timer_service(workouts):
    """Test the timer service functionality"""
    print("\n" + "="*60)
    print("TESTING TIMER SERVICE")
    print("="*60)

    try:
        timer_service = WorkoutTimerService()

        if not workouts:
            print("No existing workouts found. Creating a test workout...")
            gym_service = GymService()
            session_id = gym_service.start_workout_session("Test workout for timer")
            print(f"✓ Created test workout session: {session_id}")
        else:
            session_id = workouts[0][0]  # Use first existing workout
            print(f"Using existing workout session: {session_id}")

        # Test workout timer start
        print("\nTesting workout timer start...")
        result = timer_service.start_workout_timer(session_id, "Test timer start")
        if 'started_at' in result:
            print(f"✓ Workout timer started at: {result['started_at']}")
        else:
            print(f"✗ Failed to start workout timer: {result}")
            return False

        # Test workout timer completion
        print("\nTesting workout timer completion...")
        result = timer_service.complete_workout_timer(session_id)
        if 'completed_at' in result:
            print(f"✓ Workout timer completed at: {result['completed_at']}")
            print(f"  Duration: {result.get('duration_formatted', 'N/A')}")
        else:
            print(f"✗ Failed to complete workout timer: {result}")
            return False

        # Test timing summary
        print("\nTesting timing summary...")
        summary = timer_service.get_workout_timing_summary(session_id)
        if 'session_id' in summary:
            print(f"✓ Retrieved timing summary for session {summary['session_id']}")
            print(f"  Status: {summary.get('status', 'N/A')}")
            print(f"  Total duration: {summary.get('total_duration_formatted', 'N/A')}")
            print(f"  Total sets: {summary.get('total_sets', 0)}")
        else:
            print(f"✗ Failed to get timing summary: {summary}")
            return False

        return True

    except Exception as e:
        print(f"✗ Timer service test failed: {e}")
        return False

def main():
    """Main test function"""
    print("WORKOUT TIMER FUNCTIONALITY TEST")
    print("="*60)

    # Test database connection
    db_success, workouts = test_database_connection()
    if not db_success:
        print("\n✗ Database tests failed. Cannot proceed with timer tests.")
        return False

    # Test timer service
    timer_success = test_timer_service(workouts)

    print("\n" + "="*60)
    if db_success and timer_success:
        print("✅ ALL TESTS PASSED!")
        print("The workout timer functionality is working correctly.")
        print("You can now use the timer in the web interface.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the errors above.")
    print("="*60)

    return db_success and timer_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
