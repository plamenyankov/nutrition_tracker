# Nutrition Tracker - Recipe Features Guide

## Overview
The Nutrition Tracker now includes enhanced recipe management features that allow you to:
1. Create recipes from AI Assistant results (especially useful for meal photos)
2. Add recipes as single meal items (not broken down into ingredients)
3. View recipes with proper links in meal tracking

## New Features

### 1. Create Recipes from AI Assistant Results

When you analyze foods using the AI Assistant (particularly useful with meal photos), you can now easily convert the results into a recipe:

1. Go to **AI Assistant** page
2. Analyze your meal using any method:
   - Text input
   - Meal photo (recommended for creating recipes)
   - Nutrition label analysis
3. After getting results, click the **"Create Recipe"** button next to "Save to Database"
4. In the modal, you can:
   - Name your recipe
   - Set the number of servings
   - Select/deselect specific ingredients to include
5. Click "Create Recipe" to save

### 2. Add Recipes as Single Items or Individual Ingredients

When adding a recipe to your meals, you now have the choice:

1. Navigate to **Recipes** and select a recipe
2. Click **"Add to Meal"**
3. In the modal, you'll see a new checkbox: **"Add as single recipe"**
   - **Checked (default)**: The recipe appears as a single item "[Recipe] Recipe Name" in your meal tracking
   - **Unchecked**: The recipe is broken down into its individual ingredients

### 3. Recipe Links in Meal Tracking

Recipes added as single items now appear with:
- A book icon (📘) to indicate it's a recipe
- The name prefixed with "[Recipe]"
- Clickable links that take you directly to the recipe details page

## Technical Implementation

### Database Changes
- New `recipe_consumption` table tracks recipes added as single items
- Stores: recipe_id, consumption_date, meal_type, and servings

### Service Updates
- `RecipeService.add_recipe_to_meal()` now accepts an `as_recipe` parameter
- `MealService` fetches and merges both regular consumption and recipe consumption data

### UI Enhancements
- Recipe items are visually distinguished with book icons
- Both daily and weekly views support recipe display
- Edit functionality is disabled for recipe items (can only delete)

## Benefits

1. **Meal Photo → Recipe Workflow**: Take a photo of your meal, let AI analyze it, and save it as a recipe for future use
2. **Flexible Tracking**: Choose whether to track a recipe as one item or see individual ingredients
3. **Better Organization**: Recipes are clearly marked and linked in your meal history
4. **Simplified Logging**: Add complex meals with a single click instead of adding each ingredient

## Usage Tips

- Use the meal photo feature to quickly create recipes from your regular meals
- Add recipes as single items when you want a cleaner meal log
- Break down recipes into ingredients when you need detailed nutrient tracking
- The "[Recipe]" prefix makes it easy to distinguish recipes from individual foods in your meal history
