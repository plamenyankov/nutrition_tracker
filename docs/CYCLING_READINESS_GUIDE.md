# Cycling & Readiness Feature Documentation

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Database Schema](#database-schema)
5. [OpenAI Integration](#openai-integration)
6. [API Endpoints](#api-endpoints)
7. [Frontend Components](#frontend-components)
8. [User Workflows](#user-workflows)
9. [Image Extraction & Merge Logic](#image-extraction--merge-logic)
10. [Technical Details](#technical-details)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The **Cycling & Readiness** feature (`/cycling-readiness/`) is an AI-powered fitness tracking system that allows users to:

- **Track cycling workouts** by uploading screenshots from cycling apps (Zwift, Tacx, Garmin, Apple Watch, etc.)
- **Monitor morning readiness** with daily readiness scores based on sleep, energy, mood, and recovery metrics
- **Automatically extract data** from images using OpenAI's GPT-4o Vision API
- **Visualize performance trends** with interactive charts showing power, heart rate, TSS, and readiness scores

### Key Capabilities

- **Multi-image upload**: Upload multiple screenshots at once (cycling workouts, sleep data, Apple Watch screens)
- **Intelligent merging**: Automatically combines data from multiple screenshots into a single workout record
- **Automatic classification**: AI determines whether an image is a cycling workout, sleep summary, or unknown
- **Smart date handling**: Automatically determines workout dates and assigns them to payloads
- **Readiness scoring**: Calculates morning readiness scores based on multiple health metrics

---

## Features

### 1. Cycling Workout Tracking

**Import Methods:**
- Single image upload (`/api/cycling/import-image`)
- Multi-image bundle upload (`/api/cycle/import-bundle`) - **Recommended**

**Supported Data Fields:**
- Workout date and start time
- Duration (seconds)
- Distance (kilometers)
- Power metrics: Average, Max, Normalized Power (NP)
- Heart rate: Average and Maximum (BPM)
- Training metrics: TSS (Training Stress Score), IF (Intensity Factor)
- Cadence (RPM)
- Calories: Active and Total
- Notes

**Visualization:**
- Recent workouts table with key metrics
- Performance trends chart showing:
  - Average Power (W) - Green line
  - Average Heart Rate (BPM) - Red line
  - TSS - Yellow line (right axis)

### 2. Morning Readiness Tracking

**Manual Entry:**
- Energy level (1-5)
- Mood (1-3)
- Muscle fatigue (1-3)
- HRV status (-1/0/1)
- RHR status (-1/0/1)
- Min HR status (-1/0/1)
- Sleep minutes
- Deep sleep minutes
- Wake-ups count
- Stress level (1-3)
- Symptoms flag (boolean)

**Automatic Updates:**
- Sleep data from imported sleep screenshots automatically updates readiness entries
- Morning score is automatically calculated using a weighted formula

**Visualization:**
- Readiness history table
- Readiness trend chart showing morning scores over time

### 3. Sleep Summary Import

**Import Methods:**
- Single image upload (`/api/sleep/import-image`)
- Multi-image bundle upload (automatically processes sleep images)

**Supported Data Fields:**
- Sleep start/end dates and times
- Total sleep minutes
- Deep sleep minutes
- Awake minutes (time spent awake during sleep)
- Heart rate metrics: Min, Average, Maximum (BPM)

**Automatic Integration:**
- Sleep data automatically updates readiness entries for the corresponding date
- Sleep end date is used as the readiness entry date

### 4. AI Training Recommendations

**Overview:**
AI-powered daily training recommendations based on your readiness, sleep, cardio metrics, and recent training history.

**How It Works:**
1. Aggregates context from multiple data sources:
   - Today's readiness entry (energy, mood, fatigue, HRV/RHR status)
   - Sleep summary (duration, deep sleep, awake time)
   - Cardio metrics (RHR, HRV vs. 14-day baseline)
   - Last 7 days of training (workouts, TSS, types)
   - 30-day baseline statistics (averages)
2. Sends context to OpenAI with a specialized endurance coach prompt
3. Returns structured recommendation with session plan

**Recommendation Types:**
| Day Type | Description | Typical Duration |
|----------|-------------|------------------|
| `rest` | Full rest day | None |
| `recovery_spin_z1` | Very easy recovery spin | 20-45 min |
| `easy_endurance_z1` | Easy aerobic Zone 1 | 30-60 min |
| `steady_endurance_z2` | Steady aerobic Zone 2 | 30-75 min |
| `norwegian_4x4` | High-intensity 4×4 intervals | 40-50 min |
| `hybrid_endurance` | Mixed zone session | 45-75 min |

**Session Plan Structure:**
- Duration (minutes)
- Primary zone (Z1-Z4)
- Overall intensity (very_easy, easy, moderate, hard)
- Intervals (warmup, steady, interval blocks, cooldown)
- Comments and flags

**Caching:**
- Recommendations are stored in the database
- Cached recommendations are reused (no extra API call)
- "Refresh" forces a new generation

---

## Architecture

### Component Structure

```
/cycling-readiness/
├── Frontend (dashboard.html)
│   ├── Tab 1: Workouts
│   │   ├── Import Cycling Workout (multi-file upload)
│   │   ├── Recent Workouts Table
│   │   └── Performance Trends Chart
│   └── Tab 2: Readiness & Sleep
│       ├── Morning Readiness Form
│       ├── Import Sleep Screenshot
│       ├── Readiness History Table
│       └── Readiness Trend Chart
│
├── Backend Routes (routes.py)
│   ├── Page Route: GET /
│   ├── API Routes:
│   │   ├── POST /api/cycle/import-bundle (multi-image)
│   │   ├── POST /api/cycling/import-image (single)
│   │   ├── POST /api/sleep/import-image (single)
│   │   ├── GET /api/cycling (list workouts)
│   │   ├── DELETE /api/cycling/<id> (delete workout)
│   │   ├── POST /api/readiness (create/update)
│   │   ├── GET /api/readiness (list entries)
│   │   ├── GET /api/cycling/chart (chart data)
│   │   └── GET /api/readiness/chart (chart data)
│
├── Services
│   ├── openai_extraction.py
│   │   ├── Image encoding (base64)
│   │   ├── OpenAI API calls
│   │   ├── JSON parsing
│   │   └── Payload creation
│   └── cycling_readiness_service.py
│       ├── Workout CRUD operations
│       ├── Readiness CRUD operations
│       ├── Merge logic
│       ├── Score calculation
│       └── Chart data preparation
│
└── Database Tables
    ├── cycling_workouts
    ├── readiness_entries
    └── sleep_summaries
```

### Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL (DigitalOcean Managed Database)
- **AI**: OpenAI GPT-4o Vision API
- **Frontend**: HTML, CSS (Bootstrap), JavaScript (Chart.js)
- **Authentication**: Flask-Login

---

## Database Schema

### Table: `cycling_workouts`

Stores cycling workout data extracted from screenshots.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, auto-increment |
| `user_id` | VARCHAR(100) | Foreign key to users table |
| `date` | DATE | Workout date (YYYY-MM-DD) |
| `start_time` | TIME | Workout start time (HH:MM:SS) |
| `source` | VARCHAR(50) | Source type (indoor_cycle, outdoor_cycle, etc.) |
| `notes` | TEXT | Optional notes |
| `duration_sec` | INT | Workout duration in seconds |
| `distance_km` | FLOAT | Distance in kilometers |
| `avg_heart_rate` | INT | Average heart rate (BPM) |
| `max_heart_rate` | INT | Maximum heart rate (BPM) |
| `avg_power_w` | FLOAT | Average power in watts |
| `max_power_w` | FLOAT | Maximum power in watts |
| `normalized_power_w` | FLOAT | Normalized power (NP) in watts |
| `intensity_factor` | FLOAT | Intensity factor (IF) |
| `tss` | FLOAT | Training Stress Score |
| `avg_cadence` | INT | Average cadence (RPM) |
| `kcal_active` | INT | Active calories burned |
| `kcal_total` | INT | Total calories burned |
| `created_at` | DATETIME | Record creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

**Indexes:**
- `user_id` (for user filtering)
- `date` (for date-based queries)

### Table: `readiness_entries`

Stores daily morning readiness assessments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, auto-increment |
| `user_id` | VARCHAR(100) | Foreign key to users table |
| `date` | DATE | Entry date (unique per user) |
| `energy` | INT | Energy level (1-5) |
| `mood` | INT | Mood (1-3) |
| `muscle_fatigue` | INT | Muscle fatigue (1-3) |
| `hrv_status` | INT | HRV status (-1/0/1) |
| `rhr_status` | INT | Resting HR status (-1/0/1) |
| `min_hr_status` | INT | Min HR status (-1/0/1) |
| `sleep_minutes` | INT | Total sleep duration (minutes) |
| `deep_sleep_minutes` | INT | Deep sleep duration (minutes) |
| `wakeups_count` | INT | Number of wake-ups |
| `stress_level` | INT | Stress level (1-3) |
| `symptoms_flag` | BOOLEAN | Symptoms present flag |
| `morning_score` | INT | Calculated readiness score (0-100) |
| `evening_note` | TEXT | Optional evening note |
| `created_at` | DATETIME | Record creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

**Indexes:**
- `user_id` + `date` (unique constraint per user per day)

### Table: `sleep_summaries`

Stores sleep data extracted from screenshots.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, auto-increment |
| `user_id` | VARCHAR(100) | Foreign key to users table |
| `date` | DATE | Sleep end date (when woke up) |
| `sleep_start_time` | TIME | Sleep start time |
| `sleep_end_time` | TIME | Sleep end time |
| `total_sleep_minutes` | INT | Total sleep duration |
| `deep_sleep_minutes` | INT | Deep sleep duration |
| `wakeups_count` | INT | Number of wake-ups |
| `min_heart_rate` | INT | Minimum heart rate during sleep |
| `avg_heart_rate` | INT | Average heart rate during sleep |
| `max_heart_rate` | INT | Maximum heart rate during sleep |
| `notes` | TEXT | Optional notes |
| `created_at` | DATETIME | Record creation timestamp |

**Indexes:**
- `user_id` (for user filtering)
- `date` (for date-based queries)

### Table: `cardio_daily_metrics`

Stores daily Apple Health cardio metrics (Resting HR and HRV).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, auto-increment |
| `user_id` | VARCHAR(100) | Foreign key to users table |
| `date` | DATE | Metric date (unique per user) |
| `rhr_bpm` | INT | Resting Heart Rate (single value, BPM) |
| `hrv_low_ms` | INT | HRV range low (milliseconds) |
| `hrv_high_ms` | INT | HRV range high (milliseconds) |
| `created_at` | DATETIME | Record creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

**Notes:**
- RHR is a single value per day (extracted from Apple Health "All Recorded Data" screenshots)
- HRV is a range (low to high) representing variability throughout the day
- Uses UPSERT pattern: updating one metric doesn't overwrite the other

**Indexes:**
- `user_id` + `date` (unique constraint per user per day)

### Table: `training_recommendations`

Stores AI-generated training recommendations per user per day.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, auto-increment |
| `user_id` | VARCHAR(100) | Foreign key to users table |
| `date` | DATE | Recommendation date (unique per user) |
| `day_type` | VARCHAR(50) | Training type (rest, recovery_spin_z1, etc.) |
| `duration_minutes` | INT | Recommended session duration |
| `payload_json` | JSON | Full TrainingRecommendation object |
| `model_name` | VARCHAR(50) | OpenAI model used for generation |
| `created_at` | DATETIME | Record creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

**Day Types:**
- `rest` - Full rest day
- `recovery_spin_z1` - Easy recovery spin in Zone 1
- `easy_endurance_z1` - Easy endurance in Zone 1
- `steady_endurance_z2` - Steady endurance in Zone 2
- `norwegian_4x4` - High-intensity 4×4 VO2max intervals
- `hybrid_endurance` - Mixed zone endurance session
- `other` - Custom/other training

**Indexes:**
- `user_id` + `date` (unique constraint per user per day)

---

## OpenAI Integration

### How It Works

1. **Image Upload**: User uploads one or more screenshots
2. **Image Encoding**: Each image is converted to base64 format
3. **API Call**: Image(s) sent to OpenAI GPT-4o Vision API with a structured prompt
4. **Response Parsing**: JSON response is parsed and validated
5. **Payload Creation**: Typed payload objects are created (CyclingWorkoutPayload, SleepSummaryPayload, or UnknownPayload)

### API Call Details

**Model**: `gpt-4o`  
**Temperature**: `0` (deterministic responses)  
**Max Tokens**: `4000` (for batch processing)  
**Image Detail**: `high` (maximum resolution)

**Current Implementation (Batch Processing)**: 
- **1-4 images = 1 API call** (single request for all images)
- AI handles classification and merging in one pass
- Returns canonical workout and sleep data pre-merged
- Includes confidence scores and missing field tracking

### Prompt Engineering

The system uses a **unified extraction prompt** that:

1. **Classifies** the image type:
   - `cycling_power` / `watch_workout` - Cycling workout screenshots
   - `sleep_summary` - Sleep data screenshots
   - `cardio_series` - Apple Health "All Recorded Data" for RHR or HRV
   - `unknown` - Unrecognized images
2. **Extracts** all visible data fields
3. **Returns** structured JSON matching predefined schemas

**Key Prompt Features**:
- Explicit instructions for heart rate extraction
- Guidance for different app formats (Apple Watch, Zwift, TrainerRoad, etc.)
- Format specifications (dates, times, units)
- Error handling (use `null` for missing values)

### Cardio Series Detection (RHR/HRV)

The system can detect Apple Health "All Recorded Data" screenshots showing daily metrics:

**Resting Heart Rate (RHR)**:
- Single value per day (e.g., "73 – 73 30 Nov 2025" where low == high)
- Detected by: "beats per minute", "BPM", "Resting Heart Rate" in header
- Or if all rows have identical low/high values
- Stored as single `rhr_bpm` value

**Heart Rate Variability (HRV)**:
- Range per day (e.g., "12 – 36 29 Nov 2025" where low != high)
- Detected by: "ms", "milliseconds", "HRV" in header
- Or if rows commonly have different low/high values
- Stored as `hrv_low_ms` and `hrv_high_ms` range

### Data Extraction Accuracy

**Well-Extracted Fields**:
- Power metrics (watts) - Very reliable
- Duration and distance - Very reliable
- TSS and IF - Reliable
- Heart rate - Good (improved with recent prompt enhancements)

**Challenges**:
- Heart rate extraction can vary based on screenshot quality
- Some apps display data in non-standard formats
- Date extraction may require context (screenshots without dates)

### Error Handling

**API Errors**:
- `insufficient_quota` (429) → User-friendly error message
- `invalid_api_key` (401) → Configuration error message
- Other errors → Generic error with details

**Extraction Errors**:
- Failed extractions are logged but don't stop batch processing
- Unknown payloads are stored for debugging
- Individual image failures don't affect other images in a bundle

---

## API Endpoints

### Page Routes

#### `GET /cycling-readiness/`

Main dashboard page. Requires authentication.

**Response**: Renders `dashboard.html` template with:
- Recent cycling workouts (last 10)
- Recent readiness entries (last 14 days)
- Chart data for performance trends
- Chart data for readiness trends

### Bundle Import (Recommended)

#### `POST /api/cycle/import-bundle`

Import multiple screenshots at once. Automatically classifies and merges data.

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `images` (multiple files)

**Response**:
```json
{
  "success": true,
  "canonical_date": "2025-11-28",
  "extraction_results": [
    {
      "filename": "workout1.jpg",
      "type": "cycling_workout",
      "data": { ... }
    },
    {
      "filename": "sleep1.jpg",
      "type": "sleep_summary",
      "data": { ... }
    }
  ],
  "cycling_workout": {
    "id": 5,
    "date": "2025-11-28",
    "avg_power_w": 53.0,
    "avg_heart_rate": 115,
    ...
  },
  "readiness_entries": [ ... ],
  "summary": {
    "cycling_images": 2,
    "sleep_images": 1,
    "unknown_images": 0,
    "errors": 0
  }
}
```

**Process Flow**:
1. Extract data from each image (separate API calls)
2. Classify payloads (cycling, sleep, unknown)
3. Determine canonical date
4. Merge cycling payloads into single workout
5. Update readiness entries from sleep data
6. Return summary

### Single Image Import

#### `POST /api/cycling/import-image`

Import a single cycling workout screenshot.

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `image` (single file)

**Response**:
```json
{
  "success": true,
  "workout_id": 5,
  "extracted": { ... }
}
```

#### `POST /api/sleep/import-image`

Import a single sleep summary screenshot.

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `image` (single file)

**Response**:
```json
{
  "success": true,
  "summary_id": 3,
  "extracted": { ... }
}
```

### Data Retrieval

#### `GET /api/cycling`

Get list of cycling workouts.

**Query Parameters**:
- `limit` (default: 30) - Number of workouts to return
- `offset` (default: 0) - Pagination offset

**Response**:
```json
{
  "workouts": [
    {
      "id": 5,
      "date": "2025-11-28",
      "avg_power_w": 53.0,
      "avg_heart_rate": 115,
      "max_heart_rate": 131,
      "tss": 6.7,
      ...
    }
  ]
}
```

#### `GET /api/readiness`

Get list of readiness entries.

**Query Parameters**:
- `limit` (default: 14) - Number of entries to return

**Response**:
```json
{
  "entries": [
    {
      "id": 1,
      "date": "2025-11-28",
      "morning_score": 75,
      "energy": 4,
      "sleep_minutes": 480,
      ...
    }
  ]
}
```

#### `GET /api/cycling/chart`

Get cycling data formatted for charts.

**Query Parameters**:
- `days` (default: 30) - Number of days to include

**Response**:
```json
{
  "dates": ["2025-11-01", "2025-11-02", ...],
  "avg_power": [53.0, 55.0, ...],
  "avg_heart_rate": [115, 118, ...],
  "max_heart_rate": [131, 135, ...],
  "tss": [6.7, 7.2, ...]
}
```

#### `GET /api/readiness/chart`

Get readiness data formatted for charts.

**Query Parameters**:
- `days` (default: 30) - Number of days to include

**Response**:
```json
{
  "dates": ["2025-11-01", "2025-11-02", ...],
  "morning_score": [75, 80, ...],
  "energy": [4, 5, ...],
  "sleep_hours": [8.0, 7.5, ...]
}
```

### Data Modification

#### `POST /api/readiness`

Create or update a readiness entry.

**Request Body**:
```json
{
  "date": "2025-11-28",
  "energy": 4,
  "mood": 2,
  "muscle_fatigue": 1,
  "hrv_status": 1,
  "rhr_status": 0,
  "min_hr_status": 1,
  "sleep_minutes": 480,
  "deep_sleep_minutes": 120,
  "wakeups_count": 2,
  "stress_level": 2,
  "symptoms_flag": false
}
```

**Response**:
```json
{
  "success": true,
  "entry_id": 1,
  "morning_score": 75
}
```

#### `DELETE /api/cycling/<workout_id>`

Delete a cycling workout.

**Response**:
```json
{
  "success": true
}
```

### Training Recommendations

#### `GET /api/training-context`

Get the aggregated training context for a date (used internally by recommendation engine).

**Query Parameters**:
- `date` (required) - Date in YYYY-MM-DD format

**Response**:
```json
{
  "success": true,
  "context": {
    "today": {
      "date": "2025-11-30",
      "readiness": { "morning_score": 75, "energy": 4, ... },
      "sleep": { "total_sleep_minutes": 450, ... },
      "cardio": { "rhr_bpm": 52, "hrv_low_ms": 25, ... },
      "workout": null
    },
    "last_7_days": [ ... ],
    "baseline_30_days": {
      "avg_rhr": 53.5,
      "avg_hrv": 32.0,
      "avg_sleep_hours": 7.2,
      "avg_readiness_score": 68,
      "workouts_per_week": 4.2,
      "avg_tss_per_week": 280
    }
  }
}
```

#### `GET /api/training-recommendation`

Get AI-powered training recommendation for a date.

**Query Parameters**:
- `date` (required) - Date in YYYY-MM-DD format
- `refresh` (optional) - Set to `true` to force new generation

**Response**:
```json
{
  "success": true,
  "recommendation": {
    "date": "2025-11-30",
    "day_type": "steady_endurance_z2",
    "reason_short": "Good readiness and well-rested. No hard sessions in the last 2 days. Ideal for steady Zone 2 work.",
    "session_plan": {
      "duration_minutes": 60,
      "primary_zone": "Z2",
      "overall_intensity": "easy",
      "intervals": [
        { "kind": "warmup", "duration_minutes": 10, "target_zone": "Z1" },
        { "kind": "steady", "duration_minutes": 40, "target_zone": "Z2" },
        { "kind": "cooldown", "duration_minutes": 10, "target_zone": "Z1" }
      ],
      "comments": "Maintain conversational pace throughout"
    },
    "flags": {
      "ok_to_push": true,
      "consider_rest_day": false
    }
  },
  "cached": true
}
```

**Notes:**
- First call generates recommendation via OpenAI (takes 5-10 seconds)
- Subsequent calls return cached recommendation (instant)
- Use `refresh=true` to force regeneration

---

## Frontend Components

### Layout Structure

The dashboard uses a **tabbed interface** with two main sections:

#### Tab 1: Workouts

**Import Cycling Workout Section**:
- Drag-and-drop file upload area
- Multi-file selection support
- File list display
- Loading states ("Processing screenshots...")
- Success/error notifications

**Recent Workouts Table**:
- Columns: Date, Time, Power, Avg HR, Max HR, TSS
- Delete button for each workout
- Empty state: "No workouts imported yet"
- Responsive design (mobile-friendly)

**Performance Trends Chart**:
- Line chart showing:
  - Average Power (W) - Green
  - Average Heart Rate (BPM) - Red
  - TSS - Yellow (right axis)
- Fixed height (`h-64`)
- Empty state: "No data yet. Upload screenshots to see your performance trend."

#### Tab 2: Readiness & Sleep

**Training Recommendation Card**:
- "Suggest" button to generate AI recommendation
- Day type badge (color-coded by intensity)
- Duration and primary zone
- Reason explanation
- Session plan intervals (expandable)
- Refresh button for new generation
- Cached indicator when showing stored recommendation

**Morning Readiness Form**:
- All readiness input fields
- Submit button
- Auto-calculates morning score

**Import Sleep Screenshot**:
- Single image upload
- Processes sleep data automatically

**Readiness History Table**:
- Shows recent readiness entries
- Displays morning score, energy, sleep metrics

**Readiness Trend Chart**:
- Line chart showing morning scores over time
- Compact design
- Empty state: "No readiness data yet."

### Styling & Design

**Color Scheme** (Zyra Brandbook):
- **Teal** - Primary UI color
- **Green** - Power/performance metrics
- **Blue** - Sleep/recovery metrics
- **Red** - Warnings/low readiness
- **Yellow** - Moderate state/TSS

**Responsive Design**:
- Mobile-first layout
- Max-width container (1200px)
- Vertical stacking on small screens
- 2-column layout on larger screens

**Interactive Elements**:
- Tab navigation with active state styling
- Loading spinners during API calls
- Toast notifications for success/error
- Confirmation modals for delete actions

---

## User Workflows

### Workflow 1: Import Cycling Workout from Multiple Screenshots

**Scenario**: User has 3 screenshots from different apps showing the same workout:
- Screenshot 1: Tacx/Zwift app (shows power, duration, distance)
- Screenshot 2: Apple Watch (shows heart rate, calories)
- Screenshot 3: Garmin/TrainerRoad (shows TSS, IF, NP)

**Steps**:
1. Navigate to `/cycling-readiness/`
2. Click "Workouts" tab
3. Drag all 3 screenshots into the upload area (or click to select)
4. Click "Extract & Merge" button
5. System processes:
   - Makes **1 API call** to OpenAI (all images in single request)
   - AI classifies each image: `cycling_power`, `watch_workout`, etc.
   - AI merges data automatically with confidence scoring
   - Returns canonical workout with all fields merged
   - Creates/updates single workout record
6. Success notification appears with confidence scores
7. Table and chart automatically refresh

**Result**: Single workout record with complete data from all 3 screenshots, processed in one API call.

### Workflow 2: Morning Readiness Entry

**Scenario**: User wants to log their morning readiness assessment.

**Steps**:
1. Navigate to `/cycling-readiness/`
2. Click "Readiness & Sleep" tab
3. Fill out readiness form:
   - Energy: 4
   - Mood: 2
   - Muscle fatigue: 1
   - HRV status: 1 (good)
   - Sleep minutes: 480 (8 hours)
   - etc.
4. Click "Save Readiness"
5. System calculates morning score automatically
6. Entry appears in Readiness History table
7. Chart updates with new data point

**Result**: Readiness entry saved with calculated morning score.

### Workflow 3: Import Sleep Data from Screenshot

**Scenario**: User has an iPhone Health app screenshot showing last night's sleep.

**Steps**:
1. Navigate to `/cycling-readiness/`
2. Click "Readiness & Sleep" tab
3. Upload sleep screenshot
4. System processes:
   - Extracts sleep data (duration, deep sleep, HR, etc.)
   - Determines sleep end date (when user woke up)
   - Saves sleep summary
   - Updates readiness entry for that date (if exists)
   - Recalculates morning score
5. Success notification appears
6. Readiness History and chart update

**Result**: Sleep data imported and readiness entry automatically updated.

### Workflow 4: Combined Workout + Sleep Import

**Scenario**: User uploads both cycling workout and sleep screenshots together.

**Steps**:
1. Upload bundle with both types of images
2. System processes:
   - Classifies images (cycling vs sleep)
   - Processes cycling images → creates/updates workout
   - Processes sleep images → updates readiness entries
3. Both sections update automatically

**Result**: Complete daily data imported in one operation.

---

## Image Extraction & Merge Logic

### Batch Extraction Process (Recommended)

The system uses a **single API call** to process up to 4 images simultaneously.

**Step 1: Image Encoding (All Images)**
```python
# Prepare all images for batch processing
image_tuples = []
for file in files:
    file.stream.seek(0)  # Reset file pointer
    image_tuples.append((file.stream, file.filename))
```

**Step 2: Single OpenAI API Call (All Images)**
```python
# Build content array with prompt + all images
content = [{"type": "text", "text": BATCH_EXTRACTION_PROMPT}]

for base64_image, mime_type, filename in prepared_images:
    content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_image}",
            "detail": "high"
        }
    })

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": content}],
    temperature=0,
    max_tokens=4000  # Increased for multiple images
)
```

**Step 3: Response Parsing**
The AI returns a structured JSON with:
- `imageResults`: Per-image extraction with confidence scores
- `canonicalWorkout`: Pre-merged cycling data
- `canonicalSleep`: Pre-merged sleep data
- `missingFields`: Fields that couldn't be extracted
- `errors`: Any extraction errors

**Step 4: Database Save**
- Canonical workout saved/merged using existing logic
- Canonical sleep saved and readiness updated

### Response Schema

```json
{
  "imageResults": [
    {
      "filename": "workout1.jpg",
      "type": "cycling_power",
      "fields": { "avg_power": 150, "max_power": 200 },
      "confidence": 0.95
    },
    {
      "filename": "watch.jpg", 
      "type": "watch_workout",
      "fields": { "avg_hr": 145, "max_hr": 175 },
      "confidence": 0.90
    }
  ],
  "canonicalWorkout": {
    "date": "2025-11-28",
    "duration_minutes": 45.5,
    "avg_power": 150,
    "max_power": 200,
    "avg_hr": 145,
    "max_hr": 175,
    ...
  },
  "canonicalSleep": { ... },
  "missingFields": {
    "workout": ["cadence_max", "tss"],
    "sleep": []
  },
  "errors": []
}
```

### Merge Logic

The merge logic is **intelligent** and **non-destructive**:

**Principles**:
1. **Start with existing data** - If a workout exists for the date, use it as base
2. **Fill gaps only** - Only add fields that are missing or invalid
3. **Never overwrite** - Once a field has a valid value, it's not replaced
4. **Validate values** - Treats `0` as invalid for heart rate/power fields

**Example Merge Scenario**:

**Existing DB Record**:
```json
{
  "date": "2025-11-28",
  "avg_power_w": 53.0,
  "avg_heart_rate": 0,  // Invalid (treated as missing)
  "tss": 6.7
}
```

**Payload 1** (from Zwift screenshot):
```json
{
  "avg_power_w": null,
  "avg_heart_rate": null,
  "tss": null
}
```

**Payload 2** (from Apple Watch screenshot):
```json
{
  "avg_power_w": null,
  "avg_heart_rate": 115,  // Valid value
  "max_heart_rate": 131   // Valid value
}
```

**Merged Result**:
```json
{
  "date": "2025-11-28",
  "avg_power_w": 53.0,      // From existing (not overwritten)
  "avg_heart_rate": 115,    // From Payload 2 (fills gap)
  "max_heart_rate": 131,    // From Payload 2 (new field)
  "tss": 6.7                // From existing (not overwritten)
}
```

**Merge Algorithm**:

```python
def merge_cycling_workout(workout_date, payloads):
    # 1. Get existing workout (if any)
    existing = get_cycling_workout_by_date(workout_date)
    
    # 2. Start with existing valid data
    merged = {}
    if existing:
        for field in fields:
            if is_valid_value(field, existing[field]):
                merged[field] = existing[field]
    
    # 3. Fill gaps from payloads
    for payload in payloads:
        for field in fields:
            value = payload.get(field)
            # Only add if valid AND not already set
            if is_valid_value(field, value) and field not in merged:
                merged[field] = value
    
    # 4. Save/update
    if existing:
        update_cycling_workout(existing['id'], **merged)
    else:
        create_cycling_workout(**merged)
```

**Validation Function**:
```python
def is_valid_value(field, value):
    if value is None:
        return False
    # Treat 0 as invalid for HR/power fields
    if field in ['avg_heart_rate', 'max_heart_rate', 'avg_power_w', 'max_power_w']:
        if value == 0:
            return False
    return True
```

### Canonical Date Determination

When multiple images are uploaded, the system determines a **canonical date**:

**Priority Order**:
1. Latest workout date (from cycling payloads)
2. Latest sleep end date (from sleep payloads)
3. Today's date (fallback)

**Logic**:
```python
if all_workout_dates:
    canonical_date = max(all_workout_dates)  # Use latest workout date
elif all_sleep_dates:
    canonical_date = max(all_sleep_dates)    # Use latest sleep date
else:
    canonical_date = datetime.now().strftime('%Y-%m-%d')  # Today
```

**Date Assignment**:
- Payloads with `null` dates are assigned the canonical date
- This ensures all data from a bundle is associated with the same date

---

## Technical Details

### Morning Score Calculation

The morning readiness score is calculated using a weighted formula:

**Formula Components**:
- Energy (1-5): Weighted contribution
- Mood (1-3): Weighted contribution
- Muscle fatigue (1-3): Inverted (lower is better)
- HRV status (-1/0/1): Positive contribution
- RHR status (-1/0/1): Positive contribution
- Min HR status (-1/0/1): Positive contribution
- Sleep quality: Based on sleep minutes and deep sleep
- Stress level (1-3): Inverted (lower is better)
- Symptoms flag: Negative impact if true

**Score Range**: 0-100

**Implementation**: See `CyclingReadinessService.calculate_morning_score()`

### File Upload Handling

**Frontend**:
- Uses HTML5 File API
- Supports drag-and-drop
- Multiple file selection
- File validation (image types)

**Backend**:
- Flask `request.files.getlist('images')` for multiple files
- Each file processed sequentially
- File streams reset before processing (`file.stream.seek(0)`)

### Chart Rendering

**Library**: Chart.js

**Cycling Chart**:
- Type: Line chart
- Datasets: Power (green), HR (red), TSS (yellow)
- Dual Y-axes (left: Power/HR, right: TSS)
- Responsive design
- Fixed height (`h-64`)

**Readiness Chart**:
- Type: Line chart
- Dataset: Morning score (blue)
- Single Y-axis
- Compact design

### Error Handling

**API Errors**:
- OpenAI quota exceeded → User-friendly message
- Invalid API key → Configuration error
- Network errors → Generic error with retry suggestion

**Extraction Errors**:
- Failed extractions logged but don't stop batch
- Unknown payloads stored for debugging
- Individual failures don't affect other images

**Database Errors**:
- Connection failures → Logged and reported
- Constraint violations → User-friendly error

### Performance Considerations

**Current Implementation (Batch Processing)**:
- Single API call for up to 4 images
- AI handles merging in one pass
- Significantly reduced latency vs sequential calls
- Lower cost (one request overhead vs multiple)

**Benefits of Batch Processing**:
- 3 images = 1 API call (vs 3 calls previously)
- Better merge accuracy (AI sees all data together)
- Confidence scores for each extraction
- Missing field tracking
- Faster overall processing time

**Optimization Opportunities**:
- Caching chart data
- Pagination for large datasets
- Background processing for very large uploads

### Security

**Authentication**:
- All routes require `@login_required`
- User ID extracted from Flask-Login session

**File Upload Security**:
- File type validation (MIME type checking)
- File size limits (handled by Flask)
- No file storage (images processed in memory)

**API Key Security**:
- OpenAI API key stored in environment variables
- Never exposed to frontend
- Reloaded dynamically on each request

---

## Troubleshooting

### Issue: Heart Rate Not Extracted

**Symptoms**: Heart rate fields show as `--` or `null` in the dashboard

**Possible Causes**:
1. Screenshot doesn't contain heart rate data
2. Heart rate displayed in non-standard format
3. Image quality too low for OCR

**Solutions**:
- Verify screenshot contains heart rate data
- Try different screenshot (from different app/view)
- Check extraction results in browser console
- Review OpenAI response in logs

**Recent Fix**: Enhanced prompt with explicit HR extraction instructions

### Issue: Multiple Workouts Created Instead of Merged

**Symptoms**: Multiple workout records for the same date

**Possible Causes**:
1. Different dates extracted from screenshots
2. Date extraction failed (null dates)

**Solutions**:
- Check canonical date determination logic
- Verify date extraction in screenshots
- Review merge logic logs

### Issue: OpenAI API Errors

**Symptoms**: "OpenAI API quota exceeded" or "Invalid API key"

**Solutions**:
- Check OpenAI billing/credits
- Verify `OPENAI_API_KEY` in `.env` file
- Ensure API key is valid and has credits
- Check API key format (should start with `sk-`)

### Issue: Images Not Processing

**Symptoms**: Upload succeeds but no data extracted

**Possible Causes**:
1. Images not recognized as fitness screenshots
2. JSON parsing errors
3. API response format issues

**Solutions**:
- Check browser console for errors
- Review server logs for extraction errors
- Verify image format (JPEG, PNG supported)
- Try different screenshot

### Issue: Chart Not Displaying

**Symptoms**: Empty chart with "No data yet" message

**Possible Causes**:
1. No workouts imported yet
2. Date range has no data
3. Chart data API error

**Solutions**:
- Import at least one workout
- Check chart data API endpoint
- Verify database has workout records
- Check browser console for JavaScript errors

### Issue: Readiness Score Not Calculating

**Symptoms**: Morning score shows as `0` or `null`

**Possible Causes**:
1. Missing required fields
2. Calculation function error
3. Database constraint violation

**Solutions**:
- Verify all required fields are provided
- Check calculation function logs
- Review database constraints
- Test with minimal required fields

---

## Expanded Table View

### Overview

The **Expanded Table View** (`/cycling-readiness/expanded`) provides a comprehensive date-oriented view of all data across:
- Cycling workouts
- Readiness entries
- Sleep summaries

### Features

1. **Date-Based View**: One row per date showing all available data
2. **Grouped Columns**: Separate column groups for Cycling, Readiness, and Sleep
3. **Missing Data Indicators**: Yellow highlighting for missing/null values
4. **Filtering**:
   - Date range (from/to)
   - Preset periods (30, 60, 90, 180 days, 1 year)
   - "Missing data only" toggle
5. **CSV Export**: Download data as CSV file

### API Endpoint

```
GET /api/cycling-readiness/expanded-data
  ?days=90
  &from=2025-01-01
  &to=2025-03-31
  &missing_only=true
```

Returns JSON array with combined data per date.

### Access

Click "Expanded View" button in the dashboard header to open.

---

## Sleep Schema Updates

### awake_minutes Field

The `wakeups_count` field has been replaced with `awake_minutes` in both:
- `sleep_summaries` table
- `readiness_entries` table

**Reason**: Real sleep data shows "awake time" in minutes, not count of wake-up events.

### Schema Changes

| Old Field | New Field | Description |
|-----------|-----------|-------------|
| `wakeups_count` | `awake_minutes` | Time spent awake during the night (minutes) |

**Note**: `wakeups_count` is retained for backward compatibility but no longer used.

### Heart Rate Fields

The following fields remain in `sleep_summaries`:
- `min_heart_rate`: Minimum HR during sleep
- `max_heart_rate`: Maximum HR during sleep  
- `avg_heart_rate`: Average HR (optional, kept for sources that provide it)

---

## Morning Readiness Form

### Simplified Form

The Morning Readiness form now focuses on **subjective inputs only**:

**Included:**
- Energy Level (1-5)
- Mood (1-3)
- Muscle Fatigue (1-3)
- HRV Status (-1/0/1)
- RHR Status (-1/0/1)
- Symptoms checkbox

**Removed:**
- Sleep hours (imported via screenshots)
- Deep sleep (imported via screenshots)
- Wakeups (imported via screenshots)
- Stress level (redundant with energy/mood/fatigue)

### Sleep Data

Sleep data should be imported from screenshots using the bundle import feature. This data automatically updates the readiness entry for the corresponding date.

### Readiness Score Formula

The score is calculated from:

| Category | Max Points | Components |
|----------|------------|------------|
| Subjective | 40 pts | Energy (20), Mood (10), Fatigue (10) |
| Recovery | 25 pts | HRV (10), RHR (10), Min HR (5) |
| Sleep | 25 pts | Duration (10), Deep Sleep (10), Awake Time (5) |
| Symptoms | -10 pts | If symptoms present |

**Total: 0-100 points**

A tooltip explaining this formula is available in the Readiness History section.

---

## Future Enhancements

### Planned Features

1. ~~**Batch API Calls**: Optimize to use single API call for multiple images~~ ✅ Implemented
2. **Parallel Processing**: Process images concurrently for faster results
3. ~~**Export Functionality**: Export workouts/readiness data to CSV/JSON~~ ✅ Implemented
4. **Advanced Analytics**: More detailed performance analysis
5. **Workout Templates**: Save and reuse workout templates
6. **Integration**: Connect with Strava, Garmin Connect APIs
7. **Mobile App**: Native mobile app for easier screenshot upload

### Performance Improvements

1. **Caching**: Cache chart data and reduce database queries
2. **Lazy Loading**: Load chart data on demand
3. **Pagination**: Implement proper pagination for large datasets
4. **Background Processing**: Process images asynchronously

### UX Improvements

1. **Progress Indicators**: Show extraction progress for multiple images
2. **Preview**: Show extracted data before saving
3. **Edit Functionality**: Allow manual editing of extracted data
4. **Bulk Operations**: Delete/edit multiple workouts at once

---

## Appendix

### Code Locations

**Routes**: `models/blueprints/cycling_readiness/routes.py`  
**Service**: `models/services/cycling_readiness_service.py`  
**Training Recommendations**: `models/services/training_recommendation.py`  
**OpenAI Integration**: `models/services/openai_extraction.py`  
**Frontend - Dashboard**: `templates/cycling_readiness/dashboard.html`  
**Frontend - Expanded Table**: `templates/cycling_readiness/expanded_table.html`  
**Migration - Initial**: `migrations/add_cycling_readiness_tables.py`  
**Migration - Sleep Schema**: `migrations/update_sleep_schema.py`  
**Migration - Cardio Metrics**: `migrations/add_cardio_daily_metrics.py`  
**Migration - Cardio Fix**: `migrations/fix_cardio_schema.py`  
**Migration - Training Recs**: `migrations/add_training_recommendations.py`

### Related Documentation

- [API Reference](./API_REFERENCE.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Database Persistence Guide](./DATABASE_PERSISTENCE_GUIDE.md)
- [Zyra Brandbook](./zyra_brandbook.md)

### Support

For issues or questions:
1. Check this documentation
2. Review server logs
3. Check browser console for frontend errors
4. Verify database connectivity
5. Test with sample screenshots

---

**Last Updated**: November 30, 2025  
**Version**: 3.0  
**Author**: Zyra Development Team

### Changelog v3.0
- **AI Training Recommendations**: OpenAI-powered daily training suggestions
  - Training context aggregation (today + 7-day history + 30-day baseline)
  - Personalized session plans with intervals and zones
  - Caching to reduce API calls
  - Integration with Daily Expanded View
  - Coach column in Expanded Table
- Added `training_recommendations` database table
- Added `/api/training-context` and `/api/training-recommendation` endpoints
- Training recommendation card in Readiness & Sleep tab

### Changelog v2.0
- Added Expanded Table View page with CSV export
- Added Edit functionality for Readiness History
- Added awake_minutes field (replacing wakeups_count)
- Simplified Morning Readiness form (removed manual sleep inputs)
- Added score formula tooltip
- Added readiness entry update API
- Added cardio_daily_metrics table for RHR/HRV tracking
- Auto-fill HRV/RHR status from cardio data with 14-day baseline

