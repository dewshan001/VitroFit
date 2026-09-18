# BackendAPI/GymAgentService/fitness_agent/agents/safety_agent.py
from fitness_agent.schemas.fitness import HealthInformation, SafetyScreeningResult

HIGH_RISK_SYMPTOMS = [
    "chest pain",
    "heart condition",
    "cardiac",
    "dizziness during exercise",
    "uncontrolled asthma",
    "uncontrolled hypertension",
    "recent knee surgery",
    "spinal herniation",
]


class SafetyScreeningAgent:
    """
    Agent 2: Health & Safety Screening Agent.
    Applies deterministic safety rules to declared health information.
    NOT a medical diagnosis tool — enforces conservative eligibility guardrails.
    """

    def screen_user(self, health_info: HealthInformation) -> SafetyScreeningResult:
        declared_conditions = [c.lower() for c in health_info.conditions]
        injuries_text = (health_info.injuries or "").lower()

        risk_flags = []

        for symptom in HIGH_RISK_SYMPTOMS:
            if any(symptom in c for c in declared_conditions) or symptom in injuries_text:
                risk_flags.append(f"Declared risk condition: '{symptom}'")

        if risk_flags:
            return SafetyScreeningResult(
                status="REVIEW_REQUIRED",
                risk_flags=risk_flags,
                reason="Declared conditions or acute symptoms require clinical assessment before starting an automated physical workout routine.",
                recommended_action="CONTACT_PROFESSIONAL"
            )

        return SafetyScreeningResult(
            status="SAFE",
            risk_flags=[],
            reason="User meets conservative non-clinical safety criteria for automated progressive fitness scheduling.",
            recommended_action="CONTINUE"
        )
