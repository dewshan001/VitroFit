# BackendAPI/GymAgentService/fitness_agent/tools/gym_equipment_tool.py
from typing import List
from sqlalchemy.orm import Session
from models import GymDetails


def get_gym_equipment(gym_name: str, session: Session = None) -> List[str]:
    """
    Allow-listed Gym Equipment Tool.
    Queries cached equipment from gym_agent_details table or returns standard default facility gear.
    """
    if not gym_name:
        return ["Dumbbells", "Bodyweight", "Benches", "Mats", "Cable Machines"]

    if session:
        try:
            gym = session.query(GymDetails).filter(GymDetails.name.ilike(f"%{gym_name}%")).first()
            if gym and gym.equipment and isinstance(gym.equipment, list):
                return gym.equipment
        except Exception:
            pass

    return ["Dumbbells", "Bodyweight", "Benches", "Mats", "Cable Machines", "Machines"]
