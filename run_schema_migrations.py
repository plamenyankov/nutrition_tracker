#!/usr/bin/env python3
"""
Run all schema migrations for the cycling & readiness feature.
Migrations are idempotent - they can be run multiple times safely.
"""
import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_all_migrations():
    """Run all schema migrations in order"""
    migrations = []
    
    # Import and add migrations
    try:
        from migrations.add_cycling_readiness_tables import run_migration as migrate_cycling_readiness
        migrations.append(('add_cycling_readiness_tables', migrate_cycling_readiness))
    except ImportError as e:
        logger.warning(f"Could not import add_cycling_readiness_tables: {e}")
    
    try:
        from migrations.update_sleep_schema import run_migration as migrate_sleep_schema
        migrations.append(('update_sleep_schema', migrate_sleep_schema))
    except ImportError as e:
        logger.warning(f"Could not import update_sleep_schema: {e}")
    
    try:
        from migrations.add_cardio_daily_metrics import run_migration as migrate_cardio_metrics
        migrations.append(('add_cardio_daily_metrics', migrate_cardio_metrics))
    except ImportError as e:
        logger.warning(f"Could not import add_cardio_daily_metrics: {e}")
    
    try:
        from migrations.fix_cardio_schema import run_migration as migrate_cardio_fix
        migrations.append(('fix_cardio_schema', migrate_cardio_fix))
    except ImportError as e:
        logger.warning(f"Could not import fix_cardio_schema: {e}")
    
    try:
        from migrations.add_training_recommendations import run_migration as migrate_training_recs
        migrations.append(('add_training_recommendations', migrate_training_recs))
    except ImportError as e:
        logger.warning(f"Could not import add_training_recommendations: {e}")
    
    try:
        from migrations.add_cardio_manual_override import run_migration as migrate_cardio_override
        migrations.append(('add_cardio_manual_override', migrate_cardio_override))
    except ImportError as e:
        logger.warning(f"Could not import add_cardio_manual_override: {e}")
    
    try:
        from migrations.add_body_weights import run_migration as migrate_body_weights
        migrations.append(('add_body_weights', migrate_body_weights))
    except ImportError as e:
        logger.warning(f"Could not import add_body_weights: {e}")
    
    try:
        from migrations.add_ai_workout_analyses import run_migration as migrate_ai_analyses
        migrations.append(('add_ai_workout_analyses', migrate_ai_analyses))
    except ImportError as e:
        logger.warning(f"Could not import add_ai_workout_analyses: {e}")
    
    try:
        from migrations.add_ai_profiles import run_migration as migrate_ai_profiles
        migrations.append(('add_ai_profiles', migrate_ai_profiles))
    except ImportError as e:
        logger.warning(f"Could not import add_ai_profiles: {e}")
    
    try:
        from migrations.seed_ai_profiles import seed_profiles as seed_ai_profiles
        migrations.append(('seed_ai_profiles', seed_ai_profiles))
    except ImportError as e:
        logger.warning(f"Could not import seed_ai_profiles: {e}")
    
    # Run migrations
    logger.info(f"Running {len(migrations)} schema migrations...")
    
    success_count = 0
    for name, migration_func in migrations:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running migration: {name}")
        logger.info('='*50)
        
        try:
            result = migration_func()
            if result:
                logger.info(f"✓ {name} completed successfully")
                success_count += 1
            else:
                logger.error(f"✗ {name} returned False")
        except Exception as e:
            logger.error(f"✗ {name} failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Migration Summary: {success_count}/{len(migrations)} successful")
    logger.info('='*50)
    
    return success_count == len(migrations)


if __name__ == "__main__":
    print("=" * 60)
    print("Running all schema migrations")
    print("=" * 60)
    
    success = run_all_migrations()
    
    if success:
        print("\n✅ All migrations completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some migrations failed!")
        sys.exit(1)

