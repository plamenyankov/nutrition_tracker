"""
Cycling Readiness Routes Package.

This package contains route modules for the cycling readiness feature,
split by functional area:

- workouts: Workout CRUD, screenshot import, batch import
- readiness_sleep: Morning readiness entries, sleep summaries
- analytics: KPIs, trends, efficiency metrics
- ai_coach: Training recommendations
- ai_analyzer: Post-workout AI analysis
"""
# Import all route modules to register their routes with the blueprint
from . import workouts  # noqa: F401
from . import readiness_sleep  # noqa: F401
from . import analytics  # noqa: F401
from . import ai_coach  # noqa: F401
from . import ai_analyzer  # noqa: F401
