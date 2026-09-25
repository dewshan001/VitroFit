"""Deterministic application policy, independent of model output.

This is a deliberately limited adult beginner feature, not medical clearance.
Bounds are application limits to be reviewed by the team's qualified trainer.
"""
from .schemas import GenerateRequest, Plan


def progress_guidance(request: GenerateRequest) -> str:
    records = request.progress
    if any(p.pain for p in records):
        return "REVIEW_REQUIRED"
    if not request.previousPlan or not records:
        return "MAINTAIN: no sufficient recorded performance for progression"
    planned = {d.day for d in request.previousPlan.days}
    completed = {p.day for p in records if p.completed}
    if completed == planned and all(p.rpe <= 6 for p in records):
        return "PROGRESS: at most 10 percent total repetition volume increase"
    if any(p.rpe >= 8 for p in records):
        return "RECOVER: reduce total repetition volume; do not increase difficulty"
    return "MAINTAIN: keep or reduce total repetition volume"


def volume(plan: Plan) -> int:
    return sum(e.sets * e.repetitions for d in plan.days for e in d.exercises)


def prepare_plan(plan: Plan, request: GenerateRequest) -> Plan:
    """Keep model workload proposals while binding exercises to safe catalog focus groups."""
    weekday_focus = {1: "Chest and triceps", 3: "Arms and back", 6: "Legs"}
    confirmed = set(request.profile.equipment) | {"bodyweight"}
    catalog = [e for e in request.catalog if e.beginnerAllowed and e.equipment in confirmed]
    prepared_days = []

    for day in plan.days:
        focus = weekday_focus.get(day.day, day.focus)
        candidates = [e for e in catalog if _matches_focus(focus, e.muscleGroup)]
        candidate_ids = {e.id for e in candidates}
        prescriptions = []
        used_ids = set()

        for item in day.exercises:
            if item.exerciseId in candidate_ids and item.exerciseId not in used_ids:
                prescriptions.append(item)
                used_ids.add(item.exerciseId)

        desired_count = min(5, max(2, len(day.exercises)))
        for exercise in candidates:
            if len(prescriptions) >= desired_count:
                break
            if exercise.id not in used_ids:
                source = next((item for item in day.exercises if item.exerciseId not in candidate_ids), day.exercises[0])
                prescriptions.append(source.model_copy(update={"exerciseId": exercise.id}))
                used_ids.add(exercise.id)

        prepared_days.append(day.model_copy(update={"focus": focus, "exercises": prescriptions}))

    return plan.model_copy(update={"days": prepared_days})


def validate_plan(plan: Plan, request: GenerateRequest) -> list[str]:
    errors: list[str] = []
    catalog = {e.id: e for e in request.catalog}
    expected_week = request.previousPlan.week + 1 if request.previousPlan else 1
    if plan.week != expected_week:
        errors.append("Incorrect week number")
    if plan.week > 4:
        errors.append("The self-guided beginner program ends after four schedules")
    if sorted(d.day for d in plan.days) != sorted(request.profile.days):
        errors.append("Plan must use each selected weekday exactly once")
    expected_focus = {1: "Chest and triceps", 3: "Arms and back", 6: "Legs"}
    for day in plan.days:
        if day.day in expected_focus and day.focus != expected_focus[day.day]:
            errors.append("Use the requested Monday chest and triceps, Wednesday arms and back, and Saturday legs split")
        ids = [e.exerciseId for e in day.exercises]
        if len(day.exercises) < 2:
            errors.append(f"Catalog needs at least two confirmed beginner exercises for {day.focus}")
        if len(ids) != len(set(ids)):
            errors.append("Duplicate exercises in a session")
        minutes = day.warmupMinutes + day.cooldownMinutes
        for item in day.exercises:
            exercise = catalog.get(item.exerciseId)
            if not exercise or not exercise.beginnerAllowed:
                errors.append("Unknown or non-beginner exercise")
            elif exercise.equipment != "bodyweight" and exercise.equipment not in request.profile.equipment:
                errors.append("Unconfirmed equipment")
            elif not _matches_focus(day.focus, exercise.muscleGroup):
                errors.append("Exercise does not match this day's workout focus")
            # Four seconds per repetition plus rest and setup, rounded conservatively.
            minutes += (item.sets * (item.repetitions * 4 + item.restSeconds) + 60) / 60
        if minutes > request.profile.sessionMinutes:
            errors.append("Estimated session exceeds available time")
    if request.previousPlan:
        guidance = progress_guidance(request)
        factor = 1.10 if guidance.startswith("PROGRESS") else 1.0
        if volume(plan) > volume(request.previousPlan) * factor:
            errors.append("Progression exceeds recorded performance limit")
        if guidance.startswith("RECOVER") and volume(plan) >= volume(request.previousPlan):
            errors.append("High effort requires reduced volume")
    return sorted(set(errors))


def _matches_focus(focus: str, muscle_group: str) -> bool:
    allowed = {
        # The legacy "upper body" tag is used for the seeded wall push-up,
        # which is a valid beginner chest exercise on older local databases.
        "Chest and triceps": {"chest", "triceps", "upper body"},
        "Arms and back": {"arms", "back"},
        "Legs": {"legs"},
    }
    return muscle_group in allowed.get(focus, set())
