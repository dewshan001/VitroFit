# BackendAPI/GymAgentService/fitness_agent/agents/progress_agent.py
from fitness_agent.schemas.progress import ProgressRecord, ProgressAnalysis


class ProgressAnalysisAgent:
    """
    Agent 4: Progress Analysis Agent.
    Evaluates logged workout adherence, RPE difficulty, and weight changes.
    Emits structured progression guidance to avoid blind or aggressive volume spikes.
    """

    def analyze_progress(self, record: ProgressRecord) -> ProgressAnalysis:
        target = max(record.target_sessions, 1)
        adherence = round((record.completed_sessions / target) * 100.0, 1)

        # Conservative adaptation rules based on RPE and adherence
        if adherence >= 80.0:
            if record.rpe_rating <= 6:
                status = "PROGRESSING"
                summary = f"High adherence ({adherence}%) with low perceived effort (RPE {record.rpe_rating}/10)."
                adjustment = "Increase intensity moderately (e.g. +1 set on primary compounds or +2.5kg load)."
                guidance = "Progressive overload recommended: Target +1 repetition per set or slight load increase."
            elif record.rpe_rating <= 8:
                status = "PROGRESSING"
                summary = f"Solid adherence ({adherence}%) with target optimal training stimulus (RPE {record.rpe_rating}/10)."
                adjustment = "Maintain current volume and progress repetition counts smoothly."
                guidance = "Maintain structure: aim to hit upper rep range with strict form."
            else:
                status = "MAINTAINING"
                summary = f"High adherence ({adherence}%) but high exertion reported (RPE {record.rpe_rating}/10)."
                adjustment = "Hold volume constant to facilitate neuromuscular recovery and prevent overtraining."
                guidance = "Consolidate current weights before adding additional volume."
        else:
            status = "FATIGUE_RECOVERY"
            summary = f"Sub-optimal adherence ({adherence}%, {record.completed_sessions}/{target} sessions completed)."
            adjustment = "Reduce session complexity or split into shorter durations to reinforce consistency."
            guidance = "Focus on adherence and consistency: maintain 3 manageable sessions."

        return ProgressAnalysis(
            progress_status=status,
            adherence_percentage=min(adherence, 100.0),
            performance_summary=summary,
            recommended_adjustment=adjustment,
            next_plan_guidance=guidance
        )
