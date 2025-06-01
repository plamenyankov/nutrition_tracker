-- Exercise Database Cleanup Queries

-- 1. View exercises with numeric names (these should probably be deleted)
SELECT id, name, muscle_group FROM exercises WHERE name REGEXP '^[0-9]+$';

-- 2. View exercises with missing muscle groups
SELECT id, name, muscle_group FROM exercises WHERE muscle_group IS NULL OR muscle_group = '';

-- 3. Find potential duplicates
SELECT name, COUNT(*) as count
FROM exercises
GROUP BY LOWER(REPLACE(name, ' ', ''))
HAVING count > 1;

-- 4. Delete exercises with numeric names
DELETE FROM exercises WHERE name REGEXP '^[0-9]+$';

-- 5. Fix incorrect muscle groups
UPDATE exercises SET muscle_group = 'Shoulders' WHERE LOWER(name) LIKE '%shoulder%press%';
UPDATE exercises SET muscle_group = 'Triceps' WHERE LOWER(name) LIKE '%french press%';
UPDATE exercises SET muscle_group = 'Shoulders' WHERE LOWER(name) LIKE '%side lateral%';
UPDATE exercises SET muscle_group = 'Back' WHERE LOWER(name) LIKE '%trap%';
UPDATE exercises SET muscle_group = 'Back' WHERE LOWER(name) LIKE '%low back%';
UPDATE exercises SET muscle_group = 'Chest' WHERE LOWER(name) LIKE '%machine push%';

-- 6. Remove duplicate "Squats" (keep the one with proper capitalization)
DELETE FROM exercises WHERE name = 'Squats' AND id = 84;
DELETE FROM exercises WHERE name = 'Squads' AND id = 46;

-- 7. Standardize exercise names
UPDATE exercises SET name = 'Dumbbell Press' WHERE name = 'Dumbels press';
UPDATE exercises SET name = 'Shoulder Dumbbell Press' WHERE name = 'shoulder dumbels press';
UPDATE exercises SET name = 'Bent Over Row' WHERE name = 'Bend over row';
UPDATE exercises SET name = 'Side Laterals' WHERE name = 'side laterals';
UPDATE exercises SET name = 'Incline Barbell Press' WHERE name = 'inc. bench barbel';

-- 8. Add muscle groups to exercises that are missing them
UPDATE exercises SET muscle_group = 'Core' WHERE LOWER(name) LIKE '%low back%';
UPDATE exercises SET muscle_group = 'Shoulders' WHERE LOWER(name) LIKE '%machine side literal%';
UPDATE exercises SET muscle_group = 'Chest' WHERE LOWER(name) LIKE '%machine push up%';
UPDATE exercises SET muscle_group = 'Shoulders' WHERE LOWER(name) LIKE '%trap%';

-- 9. View cleaned up exercises table
SELECT id, name, muscle_group FROM exercises ORDER BY muscle_group, name;
