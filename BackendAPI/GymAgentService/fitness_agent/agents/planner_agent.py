# BackendAPI/GymAgentService/fitness_agent/agents/planner_agent.py
import json
import re
from typing import List, Optional
from openai import AsyncOpenAI

from fitness_agent.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, LLM_TIMEOUT_SECONDS
from fitness_agent.schemas.fitness import FitnessProfileInput
from fitness_agent.schemas.workout import WorkoutPlan, WorkoutDay, WorkoutExercise
from fitness_agent.schemas.progress import ProgressAnalysis
from fitness_agent.tools.exercise_tool import search_exercises
from fitness_agent.tools.gym_equipment_tool import get_gym_equipment


class FitnessPlannerAgent:
    """
    Agent 3: Fitness Planner Agent.
    Synthesizes user profile, goals, available gym equipment, and progression insights
    to generate a structured, conservative workout schedule using allow-listed exercises.
    """

    def __init__(self):
        if OPENROUTER_API_KEY:
            self.client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
                timeout=LLM_TIMEOUT_SECONDS
            )
        else:
            self.client = None

    async def generate_plan(
        self,
        workflow_id: str,
        profile: FitnessProfileInput,
        progress_analysis: Optional[ProgressAnalysis] = None,
        week_number: int = 1,
        revision_feedback: Optional[str] = None
    ) -> WorkoutPlan:
        # Retrieve allow-listed exercises and equipment
        available_equipment = get_gym_equipment(profile.selected_gym)
        allowed_exercises = search_exercises(beginner_allowed=True)
        exercise_options_summary = "\n".join(
            [f"- ID: {e.id}, Name: {e.name}, Muscle: {e.target_muscle}, Equipment: {e.equipment}" for e in allowed_exercises]
        )

        days = profile.available_days if profile.available_days else ["Monday", "Wednesday", "Friday"]

        # If LLM client is available, prompt for structured plan selection
        if self.client:
            try:
                system_prompt = (
                    "You are a certified sports science fitness planner. "
                    "Generate a conservative, structured weekly workout plan using ONLY the provided approved exercise IDs and equipment. "
                    "Do NOT invent exercises or equipment. "
                    "Respond with ONLY a valid JSON object matching the WorkoutPlan schema."
                )

                user_prompt = (
                    f"User Profile:\n"
                    f"- Age: {profile.age}, Weight: {profile.weight_kg}kg, Height: {profile.height_cm}cm\n"
                    f"- Goal: {profile.fitness_goal}\n"
                    f"- Experience: {profile.experience_level}\n"
                    f"- Available Days: {', '.join(days)}\n"
                    f"- Target Session Duration: {profile.session_duration} mins\n"
                    f"- Available Gym Equipment: {', '.join(available_equipment)}\n"
                    f"- Week Number: {week_number}\n"
                )

                if progress_analysis:
                    user_prompt += f"\nPrevious Progress Guidance: {progress_analysis.next_plan_guidance}\n"

                if revision_feedback:
                    user_prompt += f"\nValidation Revision Required: {revision_feedback}\n"

                user_prompt += (
                    f"\nApproved Exercise Catalog:\n{exercise_options_summary}\n\n"
                    "Generate JSON with format:\n"
                    "{\n"
                    '  "title": "...",\n'
                    '  "target_experience": "Beginner",\n'
                    '  "session_duration_minutes": 45,\n'
                    '  "days": [\n'
                    '    {\n'
                    '      "day": "Monday",\n'
                    '      "focus": "Full Body Foundations",\n'
                    '      "duration_minutes": 45,\n'
                    '      "exercises": [\n'
                    '        {\n'
                    '          "id": "ex-sq-01",\n'
                    '          "name": "Goblet Squat",\n'
                    '          "target_muscle": "Quadriceps, Glutes",\n'
                    '          "sets": 3,\n'
                    '          "reps": "10-12",\n'
                    '          "rest": "60s",\n'
                    '          "equipment": "Dumbbell",\n'
                    '          "instructions": "Keep chest up and knees aligned with toes.",\n'
                    '          "safety_notes": "Avoid knees collapsing inwards."\n'
                    '        }\n'
                    '      ]\n'
                    '    }\n'
                    '  ]\n'
                    "}"
                )

                response = await self.client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1500
                )

                raw_content = response.choices[0].message.content or ""
                parsed = self._extract_json(raw_content)
                if parsed and "days" in parsed:
                    return WorkoutPlan(
                        workflow_id=workflow_id,
                        user_id=profile.user_id,
                        week=week_number,
                        title=parsed.get("title", f"Week {week_number} Adaptive Plan"),
                        target_experience=parsed.get("target_experience", "Beginner"),
                        session_duration_minutes=parsed.get("session_duration_minutes", profile.session_duration),
                        days=[
                            WorkoutDay(
                                day=d.get("day", "Monday"),
                                focus=d.get("focus", "Full Body Foundations"),
                                duration_minutes=d.get("duration_minutes", profile.session_duration),
                                exercises=[
                                    WorkoutExercise(
                                        id=ex.get("id", "ex-sq-01"),
                                        name=ex.get("name", "Goblet Squat"),
                                        target_muscle=ex.get("target_muscle", "Quadriceps"),
                                        sets=int(ex.get("sets", 3)),
                                        reps=str(ex.get("reps", "10-12")),
                                        rest=str(ex.get("rest", "60s")),
                                        equipment=ex.get("equipment", "Dumbbell"),
                                        instructions=ex.get("instructions", "Perform with controlled tempo."),
                                        safety_notes=ex.get("safety_notes")
                                    )
                                    for ex in d.get("exercises", [])
                                ]
                            )
                            for d in parsed.get("days", [])
                        ]
                    )
            except Exception as e:
                print(f"LLM planner call failed or fell back: {e}")

        # Deterministic standard template using allow-listed tools
        return self._build_deterministic_plan(workflow_id, profile, week_number, allowed_exercises, days)

    def _extract_json(self, text: str) -> Optional[dict]:
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None

    def _build_deterministic_plan(
        self,
        workflow_id: str,
        profile: FitnessProfileInput,
        week_number: int,
        catalog: List,
        days: List[str]
    ) -> WorkoutPlan:
        # Construct tailored beginner rotation
        vol_sets = 3 if week_number == 1 else 4
        
        workout_days = []
        for i, day in enumerate(days):
            if i % 3 == 0:
                focus = "Full Body Foundations & Core"
                selected = [catalog[0], catalog[2], catalog[4], catalog[8]]  # Squat, Push-up, Row, Plank
            elif i % 3 == 1:
                focus = "Upper Body & Postural Stability"
                selected = [catalog[3], catalog[5], catalog[6], catalog[9]]  # DB Press, DB Row, OH Press, Bird Dog
            else:
                focus = "Lower Body & Posterior Chain"
                selected = [catalog[1], catalog[7], catalog[10], catalog[8]] # Box Squat, RDL, Leg Press, Plank

            exercises = [
                WorkoutExercise(
                    id=e.id,
                    name=e.name,
                    target_muscle=e.target_muscle,
                    sets=vol_sets,
                    reps="10-12" if "Plank" not in e.name else "30-45s",
                    rest="60s",
                    equipment=e.equipment,
                    instructions=e.instructions,
                    safety_notes=e.safety_notes
                )
                for e in selected
            ]

            workout_days.append(
                WorkoutDay(
                    day=day,
                    focus=focus,
                    duration_minutes=profile.session_duration,
                    exercises=exercises
                )
            )

        return WorkoutPlan(
            workflow_id=workflow_id,
            user_id=profile.user_id,
            week=week_number,
            title=f"Week {week_number} - {profile.fitness_goal.value if hasattr(profile.fitness_goal, 'value') else profile.fitness_goal}",
            target_experience=profile.experience_level.value if hasattr(profile.experience_level, 'value') else profile.experience_level,
            session_duration_minutes=profile.session_duration,
            days=workout_days
        )
