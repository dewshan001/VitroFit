"""Deterministic application policy, independent of model output.

This is a deliberately limited adult beginner feature, not medical clearance.
Bounds are application limits to be reviewed by the team's qualified trainer.
"""
from .schemas import GenerateRequest, Plan, Prescription, WorkoutDay, Exercise


GYM_EXERCISES_INFO = {
    18: ("Dumbbell incline press", "gym", "chest"),
    19: ("Cable crossover", "gym", "chest"),
    20: ("Plate-loaded machine bench press", "gym", "chest"),
    21: ("Decline barbell press", "gym", "chest"),
    22: ("Lying barbell triceps extension", "gym", "triceps"),
    23: ("Single dumbbell tricep overhead extension", "gym", "triceps"),
    24: ("Reverse grip cable tricep pushdown", "gym", "triceps"),
    25: ("Wrist curls", "gym", "arms"),
    26: ("Incline shoulder press", "gym", "upper body"),
    27: ("Front raises", "gym", "upper body"),
    28: ("Hanging side lateral raises", "gym", "upper body"),
    29: ("Smith machine back body shrugs", "gym", "back"),
    30: ("Face pulls", "gym", "back"),
    31: ("Reverse grip barbell rows", "gym", "back"),
    32: ("Bent-over dumbbell rows", "gym", "back"),
    33: ("Straight arm pulldowns", "gym", "back"),
    34: ("Back extensions", "gym", "back"),
    35: ("Cable crunches", "gym", "core"),
    36: ("Sit-ups", "gym", "core"),
    37: ("Leg raises", "gym", "core"),
    38: ("Smith machine front squats", "gym", "legs"),
    39: ("Single leg extensions", "gym", "legs"),
    40: ("Romanian deadlifts", "gym", "legs"),
    41: ("Calf raises", "gym", "legs"),
    42: ("Close grip bicep curls", "gym", "arms"),
    43: ("Wide grip bicep curls", "gym", "arms"),
    44: ("Single arm dumbbell preacher curls", "gym", "arms"),
    45: ("Reverse curls", "gym", "arms"),
}


def progress_guidance(request: GenerateRequest) -> str:
    all_history = request.history or []
    recent_progress = request.progress or []
    records = recent_progress
    legacy_transition = request.previousPlan and request.previousPlan.week == 4
    post_legacy = request.previousPlan and request.previousPlan.week > 4

    # Current/recent pain dictates immediate adaptation
    if any(p.pain for p in recent_progress):
        areas = sorted({area for item in recent_progress if item.pain for area in item.affectedAreas})
        return f"ADAPT: pain reported in recent session; avoid affected muscle groups {', '.join(areas or ['unspecified area'])}; keep unaffected workouts suitable"

    planned = {d.day for d in request.previousPlan.days} if request.previousPlan else set()
    completed = {p.day for p in records if p.completed}

    if legacy_transition:
        completed_count = sum(1 for p in all_history if p.completed) + sum(1 for p in recent_progress if p.completed)
        avg_rpe = sum(p.rpe for p in all_history + recent_progress) / max(1, len(all_history) + len(recent_progress))
        return f"ANALYSIS (4-WEEK BEGINNER RECORD): Completed {completed_count} sessions across 4 weeks with avg RPE {avg_rpe:.1f}/10. Transitioning to 3-month adaptive schedule. PROGRESS: at most 10 percent total volume increase."

    if post_legacy:
        completed_count = sum(1 for p in all_history if p.completed) + sum(1 for p in recent_progress if p.completed)
        avg_rpe = sum(p.rpe for p in all_history + recent_progress) / max(1, len(all_history) + len(recent_progress))
        if completed == planned and all(p.rpe <= 6 for p in records):
            return f"ANALYSIS (PREVIOUS 3-MONTH SCHEDULE): High performance across {completed_count} historical sessions (avg RPE {avg_rpe:.1f}/10). PROGRESS: at most 10 percent volume increase."
        if any(p.rpe >= 8 for p in records):
            return f"ANALYSIS (PREVIOUS 3-MONTH SCHEDULE): High effort detected in recent sessions (avg RPE {avg_rpe:.1f}/10). MAINTAIN: keep workload suitable; do not increase difficulty."
        return f"ANALYSIS (PREVIOUS 3-MONTH SCHEDULE): Steady progress across {completed_count} historical sessions. MAINTAIN: keep total volume stable."

    # If old history had pain but recent sessions were pain-free
    if any(p.pain for p in all_history):
        areas = sorted({area for item in all_history if item.pain for area in item.affectedAreas})
        if completed == planned and all(p.rpe <= 6 for p in records):
            return f"PROGRESS: at most 10 percent total repetition volume increase while avoiding {', '.join(areas)}"
        return f"ADAPT: history includes pain reports in {', '.join(areas)}; maintain conservative workload for affected areas"

    if completed == planned and all(p.rpe <= 6 for p in records):
        return "PROGRESS: at most 10 percent total repetition volume increase"
    if any(p.rpe >= 8 for p in records):
        return "MAINTAIN: keep workload suitable; do not increase difficulty"
    return "MAINTAIN: keep or reduce total repetition volume"


def volume(plan: Plan) -> int:
    return sum(e.sets * e.repetitions for d in plan.days for e in d.exercises)


GYM_3MONTH_PRESETS = {
    1: {
        "focus": "Chest and triceps",
        "exercises": [
            (18, 3, 10, 60),  # Dumbbell incline press
            (19, 3, 10, 60),  # Cable crossover
            (20, 3, 10, 60),  # Plate-loaded machine bench press
            (21, 3, 10, 60),  # Decline barbell press
            (22, 3, 10, 60),  # Lying barbell triceps extension
            (23, 3, 10, 60),  # Single dumbbell tricep overhead extension
            (24, 3, 10, 60),  # Reverse grip cable tricep pushdown
            (25, 3, 10, 60),  # Wrist curls
        ]
    },
    2: {
        "focus": "Shoulders, back and core",
        "exercises": [
            (26, 3, 10, 60),  # Incline shoulder press
            (27, 3, 10, 60),  # Front raises
            (28, 3, 10, 60),  # Hanging side lateral raises
            (29, 3, 10, 60),  # Smith machine back body shrugs
            (30, 3, 10, 60),  # Face pulls
            (31, 3, 10, 60),  # Reverse grip barbell rows
            (32, 3, 10, 60),  # Bent-over dumbbell rows
            (33, 3, 10, 60),  # Straight arm pulldowns
            (34, 3, 10, 60),  # Back extensions
            (35, 4, 25, 60),  # Cable crunches 25 x4
            (36, 4, 25, 60),  # Sit-ups 25x4
            (37, 4, 25, 60),  # Leg raises 25x4
        ]
    },
    3: {
        "focus": "Legs and biceps",
        "exercises": [
            (38, 3, 10, 60),  # Smith machine front squats
            (39, 3, 10, 60),  # Single leg extensions
            (40, 3, 10, 60),  # Romanian deadlifts
            (41, 3, 10, 60),  # Calf raises
            (42, 3, 10, 60),  # Close grip bicep curls
            (43, 3, 10, 60),  # Wide grip bicep curls
            (44, 3, 10, 60),  # Single arm dumbbell preacher curls
            (45, 3, 10, 60),  # Reverse curls
        ]
    }
}


def _rotate_exercises(preset_exercises: list, day_num: int, block_num: int) -> list:
    """Rotate exercise sequence and primary compound emphasis across progressive blocks."""
    rot = (block_num - 1) % 4
    ex_dict = {ex[0]: ex for ex in preset_exercises}
    if rot == 1:
        # Block 2 rotation: Swap compound priority and accessory focus
        if day_num == 1:
            order = [20, 21, 18, 19, 24, 22, 23, 25]
        elif day_num == 2:
            order = [32, 31, 26, 28, 30, 29, 33, 34, 37, 36, 35]
        else:
            order = [40, 38, 39, 41, 43, 44, 42, 45]
    elif rot == 2:
        # Block 3 rotation: Angle variation, isolation, and posterior focus
        if day_num == 1:
            order = [21, 18, 20, 19, 23, 24, 22, 25]
        elif day_num == 2:
            order = [33, 30, 31, 32, 26, 28, 27, 29, 34, 36, 35, 37]
        else:
            order = [39, 38, 40, 41, 44, 42, 43, 45]
    elif rot == 3:
        # Block 4 rotation: Active recovery and stability emphasis
        if day_num == 1:
            order = [19, 18, 20, 21, 22, 24, 23, 25]
        elif day_num == 2:
            order = [28, 26, 27, 30, 33, 29, 31, 32, 34, 35, 36, 37]
        else:
            order = [41, 40, 38, 39, 45, 43, 42, 44]
    else:
        order = [ex[0] for ex in preset_exercises]

    return [ex_dict[eid] for eid in order if eid in ex_dict]


# Beginner presets for Week 1, 2, 3, 4 (Monday: Chest & Triceps, Wednesday: Arms & Back, Saturday: Legs)
BEGINNER_PRESETS = {
    1: {  # Week 1
        1: [18, 19, 22],  # Dumbbell incline press, Cable crossover, Lying barbell triceps extension
        3: [12, 16, 25],  # Bird dog, Wall angel, Wrist curls
        6: [1, 4, 14],    # Chair squat, Seated knee extension, Glute bridge
    },
    2: {  # Week 2
        1: [20, 21, 24],  # Plate-loaded machine bench press, Decline barbell press, Reverse grip cable tricep pushdown
        3: [32, 30, 17],  # Bent-over dumbbell rows, Face pulls, Arm circles
        6: [38, 40, 3],   # Smith machine front squats, Romanian deadlifts, Standing calf raise
    },
    3: {  # Week 3
        1: [18, 20, 23],  # Dumbbell incline press, Plate-loaded bench press, Single dumbbell tricep overhead extension
        3: [31, 33, 25],  # Reverse grip barbell rows, Straight arm pulldowns, Wrist curls
        6: [39, 40, 14],  # Single leg extensions, Romanian deadlifts, Glute bridge
    },
    4: {  # Week 4
        1: [21, 19, 22],  # Decline barbell press, Cable crossover, Lying barbell triceps extension
        3: [32, 30, 34],  # Bent-over dumbbell rows, Face pulls, Back extensions
        6: [38, 4, 41],   # Smith machine front squats, Seated knee extension, Calf raises
    }
}


def prepare_plan(plan: Plan, request: GenerateRequest) -> Plan:
    """Keep model workload proposals while binding exercises to safe catalog focus groups."""
    expected_week = request.previousPlan.week + 1 if request.previousPlan else 1
    plan = plan.model_copy(update={"week": expected_week})
    legacy_week = expected_week <= 4
    weekday_focus = {1: "Chest and triceps", 3: "Arms and back", 6: "Legs"}
    confirmed = set(request.profile.equipment) | {"bodyweight", "gym"}
    affected = {area.lower() for item in (request.history or request.progress) if item.pain for area in item.affectedAreas}
    catalog_by_id = {e.id: e for e in request.catalog}
    for ex_id, (name, eq, mg) in GYM_EXERCISES_INFO.items():
        if ex_id not in catalog_by_id:
            catalog_by_id[ex_id] = Exercise(id=ex_id, name=name, equipment=eq, muscleGroup=mg, instructions="Gym exercise", beginnerAllowed=True)
    catalog = [e for e in catalog_by_id.values() if e.beginnerAllowed and e.equipment in confirmed]

    guidance = progress_guidance(request) if request.previousPlan else "PROGRESS"
    can_progress = "PROGRESS" in guidance

    if legacy_week:
        # Weeks 1 to 4: progressive repetition overload & rotating exercise sets
        reps_by_week = {1: 8, 2: 9, 3: 10, 4: 10}
        base_reps = reps_by_week.get(expected_week, 10)
        if not can_progress and expected_week > 1:
            base_reps = max(8, base_reps - 1)

        week_preset = BEGINNER_PRESETS.get(expected_week, BEGINNER_PRESETS[1])
        prepared_days = []
        for d in sorted(request.profile.days):
            focus = weekday_focus.get(d, "Arms and back")
            # If focus itself is affected by pain, find a non-painful focus
            safe_focus_candidates = [e for e in catalog if _matches_focus(focus, e.muscleGroup, True) and not _is_affected(e.muscleGroup, affected)]
            if not safe_focus_candidates and affected:
                focus = next((cand for cand in ("Arms and back", "Chest and triceps", "Legs")
                              if any(_matches_focus(cand, e.muscleGroup, True) and not _is_affected(e.muscleGroup, affected) for e in catalog)), focus)

            safe_alternatives = [e for e in catalog if _matches_focus(focus, e.muscleGroup, True) and not _is_affected(e.muscleGroup, affected)]
            # Rotate safe alternatives by week offset so adapted weeks differ
            alt_offset = ((expected_week - 1) * 3) % len(safe_alternatives) if safe_alternatives else 0
            rotated_alts = safe_alternatives[alt_offset:] + safe_alternatives[:alt_offset]

            day_ex_ids = week_preset.get(d, [18, 19, 22])
            prescriptions = []
            used_ids = set()

            for ex_id in day_ex_ids:
                ex = catalog_by_id.get(ex_id)
                if ex and _is_affected(ex.muscleGroup, affected):
                    alt = next((a for a in rotated_alts if a.id not in used_ids), None)
                    if alt:
                        prescriptions.append(Prescription(
                            exerciseId=alt.id,
                            sets=3,
                            repetitions=base_reps,
                            restSeconds=60,
                            adaptedFromExerciseId=ex_id,
                            adaptationReason=f"Replaced to avoid reported pain in {', '.join(sorted(affected))}"
                        ))
                        used_ids.add(alt.id)
                elif ex:
                    prescriptions.append(Prescription(
                        exerciseId=ex_id,
                        sets=3,
                        repetitions=base_reps,
                        restSeconds=60
                    ))
                    used_ids.add(ex_id)

            while len(prescriptions) < 3 and safe_alternatives:
                alt = next((a for a in rotated_alts if a.id not in used_ids), None)
                if not alt:
                    break
                prescriptions.append(Prescription(exerciseId=alt.id, sets=3, repetitions=base_reps, restSeconds=60))
                used_ids.add(alt.id)

            prepared_days.append(WorkoutDay(
                day=d,
                focus=focus,
                warmupMinutes=5,
                cooldownMinutes=5,
                durationMinutes=min(60, max(25, request.profile.sessionMinutes)),
                exercises=prescriptions[:3]
            ))
        return plan.model_copy(update={"days": prepared_days})

    # Post-legacy (Weeks 5-16 / Blocks 1-12)
    days_count = recommended_workout_count(request)
    block_num = ((plan.week - 5) % 12) + 1 if plan.week > 4 else 1

    if request.previousPlan and request.previousPlan.week > 4:
        prev_session_vol = volume(request.previousPlan) / max(1, len(request.previousPlan.days))
        max_allowed_session = prev_session_vol * (1.10 if can_progress else 1.0)
    else:
        prev_session_vol = 300.0
        max_allowed_session = 300.0

    core_exercise_ids = {35, 36, 37}
    compound_ids = {18, 20, 21, 26, 29, 31, 32, 38, 40}

    # Dynamically budget repetitions to strictly guarantee volume <= max_allowed_session
    target_session_vol = (prev_session_vol * 1.06) if can_progress else (prev_session_vol * 0.98)
    target_session_vol = min(target_session_vol, max_allowed_session - 1.0)

    core_sets, core_reps = 3, 20
    total_core_vol = 3 * core_sets * core_reps
    remaining_vol = max(100.0, (target_session_vol * 3) - total_core_vol)
    avg_lift_sets = 3
    avg_lift_reps = max(8, min(14, int(round((remaining_vol / 25) / avg_lift_sets))))
    rest_sec = 60 if can_progress else 70

    prepared_days = []
    for day_num in range(1, days_count + 1):
        preset = GYM_3MONTH_PRESETS.get(day_num, GYM_3MONTH_PRESETS[3])
        focus = preset["focus"]
        prescriptions = []

        rotated_exercises = _rotate_exercises(preset["exercises"], day_num, block_num)
        non_painful_ids = {ex_id for ex_id, *_ in rotated_exercises if not (
            (ex := catalog_by_id.get(ex_id)) and _is_affected(ex.muscleGroup, affected)
        )}
        used_ids = set(non_painful_ids)

        safe_alternatives = [e for e in catalog if _matches_focus(focus, e.muscleGroup, False) and not _is_affected(e.muscleGroup, affected)]
        safe_offset = ((block_num - 1) * 3) % len(safe_alternatives) if safe_alternatives else 0
        rotated_safe = safe_alternatives[safe_offset:] + safe_alternatives[:safe_offset]

        for ex_id, default_sets, default_reps, default_rest in rotated_exercises:
            is_core = ex_id in core_exercise_ids
            if is_core:
                p_sets, p_reps = core_sets, core_reps
            elif ex_id in compound_ids and block_num % 2 == 1 and not can_progress:
                p_sets, p_reps = 4, max(8, avg_lift_reps - 1)
            else:
                p_sets, p_reps = avg_lift_sets, avg_lift_reps

            ex = catalog_by_id.get(ex_id)
            if ex and _is_affected(ex.muscleGroup, affected):
                alt = next((a for a in rotated_safe if a.id not in used_ids), None)
                if alt:
                    prescriptions.append(Prescription(
                        exerciseId=alt.id,
                        sets=p_sets,
                        repetitions=p_reps,
                        restSeconds=rest_sec,
                        adaptedFromExerciseId=ex_id,
                        adaptationReason=f"Replaced to avoid reported pain in {', '.join(sorted(affected))}"
                    ))
                    used_ids.add(alt.id)
            elif ex:
                prescriptions.append(Prescription(
                    exerciseId=ex_id,
                    sets=p_sets,
                    repetitions=p_reps,
                    restSeconds=rest_sec
                ))
                used_ids.add(ex_id)

        prepared_days.append(WorkoutDay(
            day=day_num,
            focus=focus,
            warmupMinutes=5,
            cooldownMinutes=5,
            durationMinutes=min(120, max(100, request.profile.sessionMinutes)),
            exercises=prescriptions
        ))

    candidate_plan = plan.model_copy(update={"days": prepared_days})
    curr_session_vol = volume(candidate_plan) / max(1, len(candidate_plan.days))
    if curr_session_vol > max_allowed_session:
        for d in candidate_plan.days:
            for ex in d.exercises:
                if ex.exerciseId not in core_exercise_ids and ex.repetitions > 8:
                    ex.repetitions -= 1

    return candidate_plan


def recommended_workout_count(request: GenerateRequest) -> int:
    """Choose 3 or 4 sessions from availability, goals, current effort, and pain history."""
    if len(request.profile.days) < 4:
        return 3
    if any(progress.pain for progress in request.progress):
        return 3
    recent = request.progress[-4:]
    good_performance = bool(recent) and all(progress.completed and progress.rpe <= 6 for progress in recent)
    goal_supports_four = request.profile.goal in {"strength", "muscle_building", "endurance"}
    enough_time = request.profile.sessionMinutes >= 100
    return 4 if good_performance and goal_supports_four and enough_time else 3


def validate_plan(plan: Plan, request: GenerateRequest) -> list[str]:
    errors: list[str] = []
    catalog = {e.id: e for e in request.catalog}
    for ex_id, (name, eq, mg) in GYM_EXERCISES_INFO.items():
        if ex_id not in catalog:
            catalog[ex_id] = Exercise(id=ex_id, name=name, equipment=eq, muscleGroup=mg, instructions="Gym exercise", beginnerAllowed=True)
    expected_week = request.previousPlan.week + 1 if request.previousPlan else 1
    if plan.week != expected_week:
        errors.append("Incorrect week number")
    legacy_week = plan.week <= 4
    expected_days = request.profile.days if legacy_week else list(range(1, recommended_workout_count(request) + 1))
    if sorted(d.day for d in plan.days) != sorted(expected_days):
        errors.append("Plan must contain exactly the selected 3 or 4 workout days")
    expected_focus = {1: "Chest and triceps", 3: "Arms and back", 6: "Legs"}
    expected_focus_muscles = {
        1: ["chest", "triceps"],
        3: ["arms", "back"],
        6: ["legs"],
    }
    affected = {area.lower() for item in (request.history or request.progress) if item.pain for area in item.affectedAreas}
    for day in plan.days:
        is_expected_focus_painful = any(_is_affected(mg, affected) for mg in expected_focus_muscles.get(day.day, []))
        if legacy_week and not is_expected_focus_painful and day.day in expected_focus and day.focus != expected_focus[day.day]:
            errors.append("Use the requested Monday chest and triceps, Wednesday arms and back, and Saturday legs split")
        ids = [e.exerciseId for e in day.exercises]
        if len(day.exercises) < 2:
            errors.append(f"Catalog needs at least two confirmed beginner exercises for {day.focus}")
        if not legacy_week and not (6 <= len(day.exercises) <= 14):
            errors.append("Each two-hour workout day must contain between 6 and 14 exercises")
        if len(ids) != len(set(ids)):
            errors.append("Duplicate exercises in a session")
        minutes = day.warmupMinutes + day.cooldownMinutes
        for item in day.exercises:
            exercise = catalog.get(item.exerciseId)
            if not exercise or not exercise.beginnerAllowed:
                errors.append("Unknown or non-beginner exercise")
            elif exercise.equipment != "bodyweight" and exercise.equipment != "gym" and exercise.equipment not in request.profile.equipment:
                errors.append("Unconfirmed equipment")
            elif _is_affected(exercise.muscleGroup, affected):
                errors.append(f"Exercise targets painful muscle group {exercise.muscleGroup}")
            elif not _matches_focus(day.focus, exercise.muscleGroup, legacy_week):
                errors.append("Exercise does not match this day's workout focus")
            # Four seconds per repetition plus rest and setup, rounded conservatively.
            minutes += (item.sets * (item.repetitions * 4 + item.restSeconds) + 60) / 60
        if legacy_week and minutes > request.profile.sessionMinutes:
            errors.append("Estimated session exceeds available time")
        if not legacy_week and (day.durationMinutes is None or not 100 <= day.durationMinutes <= 120):
            errors.append("Each new workout day must be approximately two hours")
        if any(p.pain for p in (request.history or request.progress)):
            affected = {area.lower() for p in (request.history or request.progress) if p.pain for area in p.affectedAreas}
            if any((exercise := catalog.get(item.exerciseId)) and _is_affected(exercise.muscleGroup, affected) for item in day.exercises):
                errors.append("Workout still targets a muscle group reported as painful")
    if request.previousPlan:
        guidance = progress_guidance(request)
        factor = 1.10 if "PROGRESS" in guidance else 1.0
        if request.previousPlan.week > 4 and plan.week > 4:
            prev_session = volume(request.previousPlan) / max(1, len(request.previousPlan.days))
            new_session = volume(plan) / max(1, len(plan.days))
            if new_session > prev_session * factor:
                errors.append("Progression exceeds recorded performance limit")
    return sorted(set(errors))


def _matches_focus(focus: str, muscle_group: str, legacy: bool = True) -> bool:
    if legacy:
        allowed = {
            "Chest and triceps": {"chest", "triceps", "upper body"},
            "Arms and back": {"arms", "back"},
            "Legs": {"legs"},
        }
    else:
        allowed = {
            "Chest and triceps": {"chest", "triceps", "upper body", "core", "arms", "full body", "back"},
            "Arms and back": {"arms", "back", "upper body", "core", "chest", "triceps", "full body"},
            "Shoulders, back and core": {"arms", "back", "upper body", "core", "chest", "triceps", "full body"},
            "Legs": {"legs", "core", "full body", "arms"},
            "Legs and biceps": {"legs", "core", "full body", "arms"},
        }
    return muscle_group in allowed.get(focus, set())


def _is_affected(muscle_group: str, affected: set[str]) -> bool:
    muscle = muscle_group.lower()
    if "full body" in affected:
        return True
    return muscle in affected
