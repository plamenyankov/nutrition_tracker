-- MySQL dump 10.13  Distrib 9.3.0, for macos14.7 (x86_64)
--
-- Host: 192.168.11.1    Database: nutri_tracker_prod
-- ------------------------------------------------------
-- Server version	8.4.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Consumption`
--

DROP TABLE IF EXISTS `Consumption`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Consumption` (
  `consumption_id` int NOT NULL AUTO_INCREMENT,
  `consumption_date` date NOT NULL,
  `ingredient_quantity_id` int DEFAULT NULL,
  `ingredient_quantity_portions` int DEFAULT '1',
  `meal_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'other',
  PRIMARY KEY (`consumption_id`),
  KEY `ingredient_quantity_id` (`ingredient_quantity_id`),
  KEY `idx_consumption_date` (`consumption_date`),
  KEY `idx_consumption_meal_type` (`meal_type`),
  CONSTRAINT `Consumption_ibfk_1` FOREIGN KEY (`ingredient_quantity_id`) REFERENCES `Ingredient_Quantity` (`ingredient_quantity_id`)
) ENGINE=InnoDB AUTO_INCREMENT=355 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Consumption`
--

LOCK TABLES `Consumption` WRITE;
/*!40000 ALTER TABLE `Consumption` DISABLE KEYS */;
/*!40000 ALTER TABLE `Consumption` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Exercise`
--

DROP TABLE IF EXISTS `Exercise`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Exercise` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `MuscleGroupID` int DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `MuscleGroupID` (`MuscleGroupID`),
  CONSTRAINT `Exercise_ibfk_1` FOREIGN KEY (`MuscleGroupID`) REFERENCES `MuscleGroup` (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Exercise`
--

LOCK TABLES `Exercise` WRITE;
/*!40000 ALTER TABLE `Exercise` DISABLE KEYS */;
/*!40000 ALTER TABLE `Exercise` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Favorites`
--

DROP TABLE IF EXISTS `Favorites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Favorites` (
  `favorite_id` int NOT NULL AUTO_INCREMENT,
  `ingredient_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`favorite_id`),
  KEY `ingredient_id` (`ingredient_id`),
  CONSTRAINT `Favorites_ibfk_1` FOREIGN KEY (`ingredient_id`) REFERENCES `Ingredient` (`ingredient_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Favorites`
--

LOCK TABLES `Favorites` WRITE;
/*!40000 ALTER TABLE `Favorites` DISABLE KEYS */;
/*!40000 ALTER TABLE `Favorites` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Ingredient`
--

DROP TABLE IF EXISTS `Ingredient`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Ingredient` (
  `ingredient_id` int NOT NULL AUTO_INCREMENT,
  `ingredient_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`ingredient_id`)
) ENGINE=InnoDB AUTO_INCREMENT=129 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Ingredient`
--

LOCK TABLES `Ingredient` WRITE;
/*!40000 ALTER TABLE `Ingredient` DISABLE KEYS */;
/*!40000 ALTER TABLE `Ingredient` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Ingredient_Quantity`
--

DROP TABLE IF EXISTS `Ingredient_Quantity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Ingredient_Quantity` (
  `ingredient_quantity_id` int NOT NULL AUTO_INCREMENT,
  `quantity` float NOT NULL,
  `ingredient_id` int DEFAULT NULL,
  `unit_id` int DEFAULT NULL,
  PRIMARY KEY (`ingredient_quantity_id`),
  KEY `unit_id` (`unit_id`),
  KEY `ingredient_id` (`ingredient_id`),
  CONSTRAINT `Ingredient_Quantity_ibfk_1` FOREIGN KEY (`unit_id`) REFERENCES `Unit` (`unit_id`),
  CONSTRAINT `Ingredient_Quantity_ibfk_2` FOREIGN KEY (`ingredient_id`) REFERENCES `Ingredient` (`ingredient_id`)
) ENGINE=InnoDB AUTO_INCREMENT=348 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Ingredient_Quantity`
--

LOCK TABLES `Ingredient_Quantity` WRITE;
/*!40000 ALTER TABLE `Ingredient_Quantity` DISABLE KEYS */;
/*!40000 ALTER TABLE `Ingredient_Quantity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `MuscleGroup`
--

DROP TABLE IF EXISTS `MuscleGroup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `MuscleGroup` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `MuscleGroup`
--

LOCK TABLES `MuscleGroup` WRITE;
/*!40000 ALTER TABLE `MuscleGroup` DISABLE KEYS */;
/*!40000 ALTER TABLE `MuscleGroup` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Nutrition`
--

DROP TABLE IF EXISTS `Nutrition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Nutrition` (
  `ingredient_id` int NOT NULL,
  `unit_id` int NOT NULL,
  `kcal` float NOT NULL,
  `fat` float NOT NULL,
  `carb` float NOT NULL,
  `fiber` float NOT NULL,
  `net_carb` float NOT NULL,
  `protein` float NOT NULL,
  PRIMARY KEY (`ingredient_id`,`unit_id`),
  KEY `unit_id` (`unit_id`),
  CONSTRAINT `Nutrition_ibfk_1` FOREIGN KEY (`unit_id`) REFERENCES `Unit` (`unit_id`),
  CONSTRAINT `Nutrition_ibfk_2` FOREIGN KEY (`ingredient_id`) REFERENCES `Ingredient` (`ingredient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Nutrition`
--

LOCK TABLES `Nutrition` WRITE;
/*!40000 ALTER TABLE `Nutrition` DISABLE KEYS */;
/*!40000 ALTER TABLE `Nutrition` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Recipe`
--

DROP TABLE IF EXISTS `Recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Recipe` (
  `recipe_id` int NOT NULL AUTO_INCREMENT,
  `recipe_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `recipe_date` date NOT NULL,
  `servings` tinyint NOT NULL,
  PRIMARY KEY (`recipe_id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Recipe`
--

LOCK TABLES `Recipe` WRITE;
/*!40000 ALTER TABLE `Recipe` DISABLE KEYS */;
/*!40000 ALTER TABLE `Recipe` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Recipe_Ingredients`
--

DROP TABLE IF EXISTS `Recipe_Ingredients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Recipe_Ingredients` (
  `recipe_id` int NOT NULL,
  `ingredient_quantity_id` int NOT NULL,
  PRIMARY KEY (`recipe_id`,`ingredient_quantity_id`),
  KEY `ingredient_quantity_id` (`ingredient_quantity_id`),
  CONSTRAINT `Recipe_Ingredients_ibfk_1` FOREIGN KEY (`ingredient_quantity_id`) REFERENCES `Ingredient_Quantity` (`ingredient_quantity_id`),
  CONSTRAINT `Recipe_Ingredients_ibfk_2` FOREIGN KEY (`recipe_id`) REFERENCES `Recipe` (`recipe_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Recipe_Ingredients`
--

LOCK TABLES `Recipe_Ingredients` WRITE;
/*!40000 ALTER TABLE `Recipe_Ingredients` DISABLE KEYS */;
/*!40000 ALTER TABLE `Recipe_Ingredients` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Sets`
--

DROP TABLE IF EXISTS `Sets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Sets` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `ExerciseID` int DEFAULT NULL,
  `WorkoutID` int DEFAULT NULL,
  `SetNumber` int NOT NULL,
  `Load` double NOT NULL,
  `Reps` int NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `WorkoutID` (`WorkoutID`),
  KEY `ExerciseID` (`ExerciseID`),
  CONSTRAINT `Sets_ibfk_1` FOREIGN KEY (`WorkoutID`) REFERENCES `Workout` (`ID`),
  CONSTRAINT `Sets_ibfk_2` FOREIGN KEY (`ExerciseID`) REFERENCES `Exercise` (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Sets`
--

LOCK TABLES `Sets` WRITE;
/*!40000 ALTER TABLE `Sets` DISABLE KEYS */;
/*!40000 ALTER TABLE `Sets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Unit`
--

DROP TABLE IF EXISTS `Unit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Unit` (
  `unit_id` int NOT NULL AUTO_INCREMENT,
  `unit_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`unit_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Unit`
--

LOCK TABLES `Unit` WRITE;
/*!40000 ALTER TABLE `Unit` DISABLE KEYS */;
/*!40000 ALTER TABLE `Unit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Workout`
--

DROP TABLE IF EXISTS `Workout`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Workout` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `Date` date NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Workout`
--

LOCK TABLES `Workout` WRITE;
/*!40000 ALTER TABLE `Workout` DISABLE KEYS */;
/*!40000 ALTER TABLE `Workout` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `body_weight_tracking`
--

DROP TABLE IF EXISTS `body_weight_tracking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `body_weight_tracking` (
  `date` date NOT NULL,
  `weight` float DEFAULT NULL,
  PRIMARY KEY (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `body_weight_tracking`
--

LOCK TABLES `body_weight_tracking` WRITE;
/*!40000 ALTER TABLE `body_weight_tracking` DISABLE KEYS */;
/*!40000 ALTER TABLE `body_weight_tracking` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `calorie_tracking`
--

DROP TABLE IF EXISTS `calorie_tracking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `calorie_tracking` (
  `date` date NOT NULL,
  `calories` int DEFAULT NULL,
  `total_calories` int DEFAULT NULL,
  PRIMARY KEY (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `calorie_tracking`
--

LOCK TABLES `calorie_tracking` WRITE;
/*!40000 ALTER TABLE `calorie_tracking` DISABLE KEYS */;
/*!40000 ALTER TABLE `calorie_tracking` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exercise_progression_patterns`
--

DROP TABLE IF EXISTS `exercise_progression_patterns`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exercise_progression_patterns` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `exercise_id` int NOT NULL,
  `pattern_type` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `typical_sets` int DEFAULT '3',
  `detected_pattern` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `confidence_score` double DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_progression_patterns_user` (`user_id`,`exercise_id`),
  CONSTRAINT `exercise_progression_patterns_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`),
  CONSTRAINT `exercise_progression_patterns_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exercise_progression_patterns`
--

LOCK TABLES `exercise_progression_patterns` WRITE;
/*!40000 ALTER TABLE `exercise_progression_patterns` DISABLE KEYS */;
/*!40000 ALTER TABLE `exercise_progression_patterns` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exercise_progression_rules`
--

DROP TABLE IF EXISTS `exercise_progression_rules`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exercise_progression_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `exercise_id` int NOT NULL,
  `custom_min_reps` int DEFAULT NULL,
  `custom_max_reps` int DEFAULT NULL,
  `custom_weight_increment` double DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_exercise_rules_user` (`user_id`),
  CONSTRAINT `exercise_progression_rules_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exercise_progression_rules`
--

LOCK TABLES `exercise_progression_rules` WRITE;
/*!40000 ALTER TABLE `exercise_progression_rules` DISABLE KEYS */;
/*!40000 ALTER TABLE `exercise_progression_rules` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exercises`
--

DROP TABLE IF EXISTS `exercises`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exercises` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `muscle_group` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=121 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exercises`
--

LOCK TABLES `exercises` WRITE;
/*!40000 ALTER TABLE `exercises` DISABLE KEYS */;
/*!40000 ALTER TABLE `exercises` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `progression_history`
--

DROP TABLE IF EXISTS `progression_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `progression_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `exercise_id` int NOT NULL,
  `progression_date` date NOT NULL,
  `old_weight` double DEFAULT NULL,
  `new_weight` double DEFAULT NULL,
  `old_reps_min` int DEFAULT NULL,
  `old_reps_max` int DEFAULT NULL,
  `new_reps_target` int DEFAULT NULL,
  `progression_type` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_progression_history_user_exercise` (`user_id`,`exercise_id`),
  KEY `idx_progression_history_date` (`progression_date`),
  CONSTRAINT `progression_history_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `progression_history`
--

LOCK TABLES `progression_history` WRITE;
/*!40000 ALTER TABLE `progression_history` DISABLE KEYS */;
/*!40000 ALTER TABLE `progression_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_consumption`
--

DROP TABLE IF EXISTS `recipe_consumption`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recipe_consumption` (
  `recipe_consumption_id` int NOT NULL AUTO_INCREMENT,
  `recipe_id` int NOT NULL,
  `consumption_date` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `meal_type` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `servings` double DEFAULT '1',
  PRIMARY KEY (`recipe_consumption_id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_consumption_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `Recipe` (`recipe_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_consumption`
--

LOCK TABLES `recipe_consumption` WRITE;
/*!40000 ALTER TABLE `recipe_consumption` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_consumption` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `set_pattern_ratios`
--

DROP TABLE IF EXISTS `set_pattern_ratios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `set_pattern_ratios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `pattern_id` int NOT NULL,
  `set_number` int NOT NULL,
  `weight_ratio` double DEFAULT '1',
  `typical_reps` int DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `pattern_id` (`pattern_id`),
  CONSTRAINT `set_pattern_ratios_ibfk_1` FOREIGN KEY (`pattern_id`) REFERENCES `exercise_progression_patterns` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `set_pattern_ratios`
--

LOCK TABLES `set_pattern_ratios` WRITE;
/*!40000 ALTER TABLE `set_pattern_ratios` DISABLE KEYS */;
/*!40000 ALTER TABLE `set_pattern_ratios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `set_progression_history`
--

DROP TABLE IF EXISTS `set_progression_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `set_progression_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `exercise_id` int NOT NULL,
  `set_number` int NOT NULL,
  `progression_date` date NOT NULL,
  `old_weight` double DEFAULT NULL,
  `new_weight` double DEFAULT NULL,
  `old_reps` int DEFAULT NULL,
  `new_reps` int DEFAULT NULL,
  `progression_type` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_set_progression_user_exercise` (`user_id`,`exercise_id`,`set_number`),
  CONSTRAINT `set_progression_history_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`),
  CONSTRAINT `set_progression_history_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `set_progression_history`
--

LOCK TABLES `set_progression_history` WRITE;
/*!40000 ALTER TABLE `set_progression_history` DISABLE KEYS */;
/*!40000 ALTER TABLE `set_progression_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_gym_preferences`
--

DROP TABLE IF EXISTS `user_gym_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_gym_preferences` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `progression_strategy` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `min_reps_target` int DEFAULT '10',
  `max_reps_target` int DEFAULT '15',
  `weight_increment_upper` double DEFAULT '2.5',
  `weight_increment_lower` double DEFAULT '5',
  `rest_timer_enabled` tinyint(1) DEFAULT '1',
  `progression_notification_enabled` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `progression_priority_1` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `progression_priority_2` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `progression_priority_3` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `progression_priority_4` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `progression_priority_5` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `pyramid_preference` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_gym_preferences`
--

LOCK TABLES `user_gym_preferences` WRITE;
/*!40000 ALTER TABLE `user_gym_preferences` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_gym_preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_highlights`
--

DROP TABLE IF EXISTS `workout_highlights`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_highlights` (
  `id` int NOT NULL AUTO_INCREMENT,
  `workout_id` int DEFAULT NULL,
  `highlight_text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `date` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `workout_id` (`workout_id`),
  CONSTRAINT `workout_highlights_ibfk_1` FOREIGN KEY (`workout_id`) REFERENCES `Workout` (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_highlights`
--

LOCK TABLES `workout_highlights` WRITE;
/*!40000 ALTER TABLE `workout_highlights` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_highlights` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_sessions`
--

DROP TABLE IF EXISTS `workout_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `date` date NOT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `template_id` int DEFAULT NULL,
  `status` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `completed_at` timestamp NULL DEFAULT NULL,
  `started_at` timestamp NULL DEFAULT NULL,
  `duration_seconds` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_workout_sessions_user_date` (`user_id`,`date`),
  KEY `idx_workout_sessions_template` (`template_id`),
  KEY `idx_started_at` (`started_at`),
  KEY `idx_duration` (`duration_seconds`),
  CONSTRAINT `workout_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `workout_sessions_ibfk_2` FOREIGN KEY (`template_id`) REFERENCES `workout_templates` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=392 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_sessions`
--

LOCK TABLES `workout_sessions` WRITE;
/*!40000 ALTER TABLE `workout_sessions` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_sets`
--

DROP TABLE IF EXISTS `workout_sets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_sets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int DEFAULT NULL,
  `exercise_id` int DEFAULT NULL,
  `set_number` int DEFAULT NULL,
  `weight` double DEFAULT NULL,
  `reps` int DEFAULT NULL,
  `rpe` int DEFAULT NULL,
  `form_quality` int DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `target_reps` int DEFAULT NULL,
  `progression_ready` tinyint(1) DEFAULT '0',
  `last_progression_date` date DEFAULT NULL,
  `started_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `duration_seconds` int DEFAULT NULL,
  `rest_duration_seconds` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_workout_sets_session` (`session_id`),
  KEY `idx_set_started_at` (`started_at`),
  KEY `idx_set_completed_at` (`completed_at`),
  KEY `idx_set_duration` (`duration_seconds`),
  CONSTRAINT `workout_sets_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`),
  CONSTRAINT `workout_sets_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `workout_sessions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6892 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_sets`
--

LOCK TABLES `workout_sets` WRITE;
/*!40000 ALTER TABLE `workout_sets` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_sets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_template_exercises`
--

DROP TABLE IF EXISTS `workout_template_exercises`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_template_exercises` (
  `id` int NOT NULL AUTO_INCREMENT,
  `template_id` int NOT NULL,
  `exercise_id` int NOT NULL,
  `order_index` int NOT NULL,
  `sets` int DEFAULT '3',
  `target_reps` int DEFAULT NULL,
  `target_weight` double DEFAULT NULL,
  `rest_seconds` int DEFAULT '90',
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_workout_template_exercises_template` (`template_id`),
  CONSTRAINT `workout_template_exercises_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`),
  CONSTRAINT `workout_template_exercises_ibfk_2` FOREIGN KEY (`template_id`) REFERENCES `workout_templates` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_template_exercises`
--

LOCK TABLES `workout_template_exercises` WRITE;
/*!40000 ALTER TABLE `workout_template_exercises` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_template_exercises` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_templates`
--

DROP TABLE IF EXISTS `workout_templates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `user_id` int DEFAULT NULL,
  `is_public` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_workout_templates_user` (`user_id`),
  CONSTRAINT `workout_templates_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_templates`
--

LOCK TABLES `workout_templates` WRITE;
/*!40000 ALTER TABLE `workout_templates` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_templates` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_timing_sessions`
--

DROP TABLE IF EXISTS `workout_timing_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_timing_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int NOT NULL,
  `event_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `exercise_id` int DEFAULT NULL,
  `set_id` int DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `duration_seconds` int DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_timestamp` (`timestamp`),
  CONSTRAINT `workout_timing_sessions_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `workout_sessions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_timing_sessions`
--

LOCK TABLES `workout_timing_sessions` WRITE;
/*!40000 ALTER TABLE `workout_timing_sessions` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_timing_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workout_volume_tracking`
--

DROP TABLE IF EXISTS `workout_volume_tracking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_volume_tracking` (
  `id` int NOT NULL AUTO_INCREMENT,
  `workout_id` int NOT NULL,
  `exercise_id` int NOT NULL,
  `total_volume` double DEFAULT NULL,
  `total_reps` int DEFAULT NULL,
  `total_sets` int DEFAULT NULL,
  `avg_intensity` double DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `idx_volume_tracking_workout` (`workout_id`),
  CONSTRAINT `workout_volume_tracking_ibfk_1` FOREIGN KEY (`exercise_id`) REFERENCES `exercises` (`id`),
  CONSTRAINT `workout_volume_tracking_ibfk_2` FOREIGN KEY (`workout_id`) REFERENCES `workout_sessions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workout_volume_tracking`
--

LOCK TABLES `workout_volume_tracking` WRITE;
/*!40000 ALTER TABLE `workout_volume_tracking` DISABLE KEYS */;
/*!40000 ALTER TABLE `workout_volume_tracking` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-06-15  9:03:18
