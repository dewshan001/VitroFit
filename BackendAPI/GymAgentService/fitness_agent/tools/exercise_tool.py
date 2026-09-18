# BackendAPI/GymAgentService/fitness_agent/tools/exercise_tool.py
from typing import List, Optional
from fitness_agent.schemas.workout import Exercise

# Curated, approved exercise database guaranteeing safe beginner exercises
APPROVED_EXERCISE_CATALOG: List[Exercise] = [
    Exercise(
        id="ex-sq-01",
        name="Goblet Squat",
        target_muscle="Quadriceps, Glutes",
        difficulty="Beginner",
        equipment="Dumbbell",
        beginner_allowed=True,
        instructions="Hold dumbbell vertically against chest. Descend keeping torso upright until thighs reach parallel.",
        safety_notes="Keep knees tracking over toes; do not round lower back."
    ),
    Exercise(
        id="ex-bx-02",
        name="Bodyweight Box Squat",
        target_muscle="Quadriceps, Glutes",
        difficulty="Beginner",
        equipment="Bodyweight",
        beginner_allowed=True,
        instructions="Stand in front of a bench or box. Sit back with control until lightly touching the box, then press up.",
        safety_notes="Maintains safe hip hinge for absolute beginners."
    ),
    Exercise(
        id="ex-pu-03",
        name="Incline Push-Up",
        target_muscle="Chest, Triceps, Anterior Deltoids",
        difficulty="Beginner",
        equipment="Bench",
        beginner_allowed=True,
        instructions="Hands placed slightly wider than shoulders on elevated bench. Lower chest to bench edge and press away.",
        safety_notes="Brace core and glutes to avoid sagging hips."
    ),
    Exercise(
        id="ex-db-04",
        name="Dumbbell Flat Bench Press",
        target_muscle="Chest, Triceps",
        difficulty="Beginner",
        equipment="Dumbbell",
        beginner_allowed=True,
        instructions="Lie flat on bench holding dumbbells above chest. Lower with elbows at a 45-degree angle, press up.",
        safety_notes="Keep feet planted firmly on the floor."
    ),
    Exercise(
        id="ex-rw-05",
        name="Seated Cable Row",
        target_muscle="Latissimus Dorsi, Rhomboids",
        difficulty="Beginner",
        equipment="Cable",
        beginner_allowed=True,
        instructions="Sit with slight knee bend. Pull cable handle towards lower abdomen, squeezing shoulder blades together.",
        safety_notes="Avoid excessive backward leaning or torso momentum."
    ),
    Exercise(
        id="ex-dr-06",
        name="Dumbbell Single-Arm Row",
        target_muscle="Latissimus Dorsi, Biceps",
        difficulty="Beginner",
        equipment="Dumbbell",
        beginner_allowed=True,
        instructions="One knee and hand on bench for support. Pull dumbbell to hip crease while maintaining flat back.",
        safety_notes="Keep neck neutral; do not twist torso."
    ),
    Exercise(
        id="ex-oh-07",
        name="Dumbbell Seated Overhead Press",
        target_muscle="Deltoids, Upper Chest",
        difficulty="Beginner",
        equipment="Dumbbell",
        beginner_allowed=True,
        instructions="Sit with back support. Press dumbbells upward from shoulder height until arms are fully extended overhead.",
        safety_notes="Do not arch lower back; avoid if severe shoulder pain declared."
    ),
    Exercise(
        id="ex-rd-08",
        name="Romanian Deadlift (Dumbbell)",
        target_muscle="Hamstrings, Glutes, Lower Back",
        difficulty="Beginner",
        equipment="Dumbbell",
        beginner_allowed=True,
        instructions="Hold dumbbells in front of thighs. Push hips backwards with soft knees, lowering weights along shins.",
        safety_notes="Maintain flat spine; stop at mid-shin or hamstring tension limit."
    ),
    Exercise(
        id="ex-pl-09",
        name="Plank Hold",
        target_muscle="Core, Abdominals",
        difficulty="Beginner",
        equipment="Bodyweight",
        beginner_allowed=True,
        instructions="Forearms on ground, elbows below shoulders. Maintain rigid straight line from head to heels.",
        safety_notes="Do not allow lower back to hyperextend."
    ),
    Exercise(
        id="ex-bd-10",
        name="Bird Dog",
        target_muscle="Core, Glutes, Lower Back Stabilizers",
        difficulty="Beginner",
        equipment="Bodyweight",
        beginner_allowed=True,
        instructions="On all fours, simultaneously extend opposite arm and leg straight out. Hold for 2 seconds and alternate.",
        safety_notes="Keep hips level; excellent for spinal safety and recovery."
    ),
    Exercise(
        id="ex-lp-11",
        name="Leg Press",
        target_muscle="Quadriceps, Glutes",
        difficulty="Beginner",
        equipment="Machine",
        beginner_allowed=True,
        instructions="Place feet shoulder-width on platform. Release safety locks, lower sled until 90-degree knee bend, press back up.",
        safety_notes="Never lock out knees completely at top."
    ),
    Exercise(
        id="ex-lc-12",
        name="Lying / Seated Leg Curl",
        target_muscle="Hamstrings",
        difficulty="Beginner",
        equipment="Machine",
        beginner_allowed=True,
        instructions="Align knee joints with machine pivot. Curl heels towards glutes smoothly.",
        safety_notes="Control the eccentric (lowering) phase."
    ),
    Exercise(
        id="ex-ld-13",
        name="Lat Pulldown",
        target_muscle="Latissimus Dorsi, Biceps",
        difficulty="Beginner",
        equipment="Cable",
        beginner_allowed=True,
        instructions="Grip wide bar, sit with thighs secured under pads. Pull bar down towards upper chest, then return smoothly.",
        safety_notes="Never pull behind the neck."
    )
]


def search_exercises(
    target_muscle: Optional[str] = None,
    difficulty: Optional[str] = None,
    equipment: Optional[str] = None,
    beginner_allowed: bool = True
) -> List[Exercise]:
    """
    Allow-listed Exercise Search Tool.
    Retrieves safe, approved exercises matching input parameters from the catalog.
    """
    results = APPROVED_EXERCISE_CATALOG

    if beginner_allowed:
        results = [e for e in results if e.beginner_allowed]

    if difficulty:
        results = [e for e in results if e.difficulty.lower() == difficulty.lower()]

    if target_muscle:
        results = [
            e for e in results
            if target_muscle.lower() in e.target_muscle.lower()
        ]

    if equipment:
        results = [
            e for e in results
            if equipment.lower() in e.equipment.lower() or e.equipment == "Bodyweight"
        ]

    return results
