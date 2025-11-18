"""
Database Schemas for the app

Each Pydantic model represents a MongoDB collection.
Collection name is the lowercase class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class TeamMember(BaseModel):
    username: str = Field(..., description="Unique username for team member")
    password: str = Field(..., description="Plain password for demo (do not use in production)")
    full_name: Optional[str] = Field(None, description="Member full name")
    role: Literal["team"] = "team"
    is_active: bool = True

class Complaint(BaseModel):
    title: str = Field(..., description="Short summary of the complaint")
    description: str = Field(..., description="Detailed description of the internet complaint")
    customer_name: Optional[str] = Field(None)
    customer_contact: Optional[str] = Field(None)
    assigned_to: Optional[str] = Field(None, description="Username of assigned team member")
    status: Literal["pending", "progress", "complete", "critical", "hold", "cancelled"] = "pending"
    notes: List[dict] = []
