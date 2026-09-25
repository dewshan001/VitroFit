# GymAgentService/models.py
from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from db import Base


class GymDetails(Base):
    """Cached equipment/classes for a gym, keyed by its map-provider place id.

    `source` tracks how trustworthy the equipment/classes fields are:
      - "verified"    : entered by the gym owner/admin - never overwritten by the agent
      - "ai-scraped"   : extracted by the LLM from the gym's own website
      - "ai-generic"   : the LLM's best guess with no website to read (low confidence)
    """

    __tablename__ = "gym_agent_details"

    place_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    website = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    opening_hours = Column(String(255), nullable=True)

    source = Column(String(20), nullable=False, default="ai-generic")
    equipment = Column(JSON, nullable=False, default=list)
    classes = Column(JSON, nullable=False, default=list)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
