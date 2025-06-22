# Nutrition Tracker API Reference

**Framework**: Flask
**Authentication**: Flask-Login (session-based)
**Total Endpoints**: 82
**Base URL**: `http://localhost:5000`

## 🔐 Authentication

All API endpoints (except `/login`) require authentication via Flask-Login session cookies.

```bash
# Login first
curl -X POST http://localhost:5000/login \
  -d "username=demo&password=demo" \
  -c cookies.txt

# Use session cookie for subsequent requests
curl -X GET http://localhost:5000/foods \
  -b cookies.txt
```

## 📊 API Endpoints by Category

### 🔑 Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/login` | User login |
| `GET` | `/logout` | User logout |

### 🍎 Food Database Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/foods` | Food database page |
| `GET` | `/foods/api/paginated` | Get paginated food list |
| `POST` | `/foods/add` | Add new food item |
| `GET` | `/foods/get/<food_id>` | Get specific food item |
| `POST` | `/foods/update/<food_id>` | Update food item |
| `POST` | `/foods/delete/<food_id>` | Delete food item |
| `POST` | `/foods/toggle-favorite/<ingredient_id>` | Toggle food favorite status |

### 🍽️ Meal Tracking
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/meals` | Current day meal tracking |
| `GET` | `/meals/<date_str>` | Specific date meal tracking |
| `GET` | `/meals/week` | Current week meal tracking |
| `GET` | `/meals/week/<start_date>` | Specific week meal tracking |
| `POST` | `/meals/add` | Add food to meal |
| `POST` | `/meals/update-consumption/<consumption_id>` | Update meal consumption |
| `POST` | `/meals/delete-consumption/<consumption_id>` | Delete meal consumption |

### 🥘 Recipe Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recipes` | List all recipes |
| `GET/POST` | `/recipes/create` | Create new recipe |
| `GET` | `/recipes/<recipe_id>` | View recipe details |
| `GET/POST` | `/recipes/<recipe_id>/edit` | Edit recipe |
| `POST` | `/recipes/<recipe_id>/delete` | Delete recipe |
| `POST` | `/recipes/<recipe_id>/add-to-meal` | Add recipe to meal |

### 💪 Gym & Workout Tracking
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gym/` | Gym dashboard |
| `GET` | `/gym/exercises` | List exercises |
| `GET/POST` | `/gym/exercises/add` | Add new exercise |
| `GET/POST` | `/gym/exercises/edit/<exercise_id>` | Edit exercise |
| `POST` | `/gym/exercises/delete/<exercise_id>` | Delete exercise |
| `GET` | `/gym/workout/start` | Start new workout |
| `GET` | `/gym/workout/start/<template_id>` | Start workout from template |
| `POST` | `/gym/workout/log` | Log workout set |
| `POST` | `/gym/workout/update-set` | Update workout set |
| `POST` | `/gym/workout/delete-set` | Delete workout set |
| `POST` | `/gym/workout/<workout_id>/complete` | Complete workout |
| `POST` | `/gym/workout/<workout_id>/abandon` | Abandon workout |

### 📈 Progression Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gym/progression/dashboard` | Progression analytics dashboard |
| `GET` | `/gym/progression/suggestions` | Get progression suggestions |
| `GET` | `/gym/exercise/<exercise_id>/progression` | Exercise progression analysis |
| `GET` | `/gym/exercise/<exercise_id>/quick-progression` | Quick progression check |
| `GET` | `/gym/exercise/<exercise_id>/set-specific-progression/<set_number>` | **Set-specific progression** |
| `GET` | `/gym/exercise/<exercise_id>/comprehensive-progression` | Comprehensive progression data |
| `POST` | `/gym/exercise/<exercise_id>/accept-progression` | Accept progression suggestion |

### 🏋️ Workout Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gym/templates` | List workout templates |
| `GET/POST` | `/gym/templates/create` | Create new template |
| `GET` | `/gym/templates/<template_id>` | View template details |
| `GET` | `/gym/templates/<template_id>/edit` | Edit template |
| `POST` | `/gym/templates/<template_id>/update` | Update template |
| `POST` | `/gym/templates/<template_id>/delete` | Delete template |

### ⏱️ Workout Timer API
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/timer/workout/start` | Start workout timer |
| `POST` | `/api/timer/workout/complete` | Complete workout timer |
| `POST` | `/api/timer/set/complete` | Complete set timer |
| `GET` | `/api/timer/workout/summary/<session_id>` | Get workout timing summary |

### 🤖 AI Assistant
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/ai/assistant` | AI nutrition assistant |
| `POST` | `/ai/save-results` | Save AI recommendations |
| `POST` | `/ai/create-recipe` | Create recipe from AI results |
| `POST` | `/ai/clear-results` | Clear AI session results |

### 📊 Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics` | Analytics dashboard |
| `GET` | `/analytics/data` | Get analytics data |

## 🔥 Key API Examples

### Set-Specific Progression (Your Recent Fix!)
```bash
GET /gym/exercise/72/set-specific-progression/1
```

**Response:**
```json
{
  "has_history": true,
  "set_number": 1,
  "current_weight": 22.5,
  "current_avg_reps": 10,
  "suggested_weight": 22.5,
  "suggested_reps": 15,
  "suggestion": "build_strength",
  "ready": false,
  "confidence": 0.7,
  "reps_to_go": 5,
  "target_reps": 15,
  "last_date": "2025-06-21"
}
```

### Food Database Search
```bash
GET /foods/api/paginated?page=1&per_page=20&search=chicken
```

### Add Food to Meal
```bash
POST /meals/add
Content-Type: application/json

{
  "ingredient_id": 123,
  "quantity": 100,
  "meal_type": "lunch",
  "date": "2025-06-21"
}
```

### Start Workout Timer
```bash
POST /api/timer/workout/start
Content-Type: application/json

{
  "session_id": 410,
  "notes": "Upper body workout"
}
```

## 🚀 Adding Swagger UI

To add interactive API documentation:

1. **Install Flasgger:**
   ```bash
   pip install flasgger==0.9.7.1
   ```

2. **Run setup script:**
   ```bash
   python add_swagger_documentation.py
   ```

3. **Apply modifications to app.py** (see `swagger_app_modifications.txt`)

4. **Access Swagger UI:**
   ```
   http://localhost:5000/docs
   ```

## 📱 Frontend Integration

Most endpoints return JSON for API usage, but also support HTML rendering for the web interface. The application uses:

- **AJAX calls** for dynamic updates
- **Form submissions** for data entry
- **Session-based authentication** (not token-based)
- **Bootstrap UI** for responsive design

## 🛠️ Development Tools

**Current API Listing:**
```bash
python -c "
import sys; sys.path.append('.')
from app import app
for rule in app.url_map.iter_rules():
    print(f'{rule.methods} {rule}')"
```

**Test API Endpoints:**
```bash
# Start the app
python app.py

# Test with curl (after login)
curl -X GET http://localhost:5000/foods/api/paginated -b cookies.txt
```

## 📋 Response Formats

All API endpoints return JSON with consistent structure:

**Success Response:**
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed"
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": "Error description",
  "code": 400
}
```

## 🔗 Related Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Database Guide](DATABASE_PERSISTENCE_GUIDE.md)
- [Brand Guidelines](BRAND_BOOK_MVP.md)
- [Recipe Features](RECIPE_FEATURES_GUIDE.md)
