# Deployment Checklist - Advanced Progressive Overload

## Pre-Deployment Verification

- [x] Local testing completed
- [x] All migrations tested locally
- [x] Migration script (`run_all_migrations.py`) created
- [x] Dockerfile updated to run migrations on startup
- [x] Remote migration script (`run_remote_migrations.sh`) created

## New Features Being Deployed

### Database Changes
1. **New columns in `workout_sets`**:
   - `target_reps`
   - `progression_ready`
   - `rpe`
   - `form_quality`
   - `notes`

2. **New columns in `user_gym_preferences`**:
   - `progression_priority_1` through `progression_priority_5`
   - `pyramid_preference`

3. **New tables**:
   - `set_progression_history`
   - `exercise_progression_patterns`
   - `set_pattern_ratios`
   - `workout_volume_tracking`

### New Services
- `AdvancedProgressionService` - Handles set-specific progression analysis

### Updated Features
- Workout completion now calculates volume metrics
- Exercise names display correctly with updated column indexes
- Progression dashboard at `/gym/progression/dashboard`
- Enhanced preferences page with progression priorities

## Deployment Steps

1. **Commit all changes** (if any uncommitted):
   ```bash
   git add -A
   git commit -m "Deploy advanced progressive overload features"
   ```

2. **Run the deployment script**:
   ```bash
   ./deploy_to_digitalocean.sh
   ```

3. **Verify deployment**:
   - Check the app is running: http://164.90.169.51
   - Check gym preferences page loads correctly
   - Check progression dashboard works
   - Verify workout editing shows exercise names

4. **If migrations need to be run manually** (shouldn't be needed as they run on startup):
   ```bash
   ./run_remote_migrations.sh
   ```

## Post-Deployment Verification

- [ ] App is accessible at http://164.90.169.51
- [ ] Gym preferences page loads without errors
- [ ] Progression dashboard displays correctly
- [ ] Workout edit page shows exercise names properly
- [ ] Volume metrics are calculated after workout completion

## Rollback Plan

If issues occur:

1. **Check container logs**:
   ```bash
   ssh root@164.90.169.51 "docker logs nutrition-tracker"
   ```

2. **Run migrations manually if needed**:
   ```bash
   ./run_remote_migrations.sh
   ```

3. **If critical issues, redeploy previous version**:
   ```bash
   ssh root@164.90.169.51 "docker pull plamenyankov1/nutrition-tracker:previous-tag"
   ssh root@164.90.169.51 "docker stop nutrition-tracker && docker rm nutrition-tracker"
   ssh root@164.90.169.51 "docker run -d --name nutrition-tracker -p 80:5000 -v /root/nutrition_tracker_data:/app/data plamenyankov1/nutrition-tracker:previous-tag"
   ```

## Notes

- Migrations are idempotent - safe to run multiple times
- Database is persisted in `/root/nutrition_tracker_data` volume
- The deployment script builds locally, pushes to Docker Hub, then deploys
