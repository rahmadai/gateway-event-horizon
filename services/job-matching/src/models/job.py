"""
Job models.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class JobBase(BaseModel):
    """Base job model."""
    title: str
    company_id: int
    location: str
    required_skills: List[str] = []
    match_score: Optional[float] = None


class JobCreate(JobBase):
    """Job creation model."""
    status: str = "active"


class Job(JobBase):
    """Full job model."""
    id: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobStats(BaseModel):
    """Job statistics."""
    id: int
    title: str
    total_applications: int
    pending: int
    reviewed: int
    hired: int


class Candidate(BaseModel):
    """Candidate model."""
    id: int
    name: str
    email: str
    skills: List[str]
    location: str
    experience_years: int = 0

    class Config:
        from_attributes = True


class MatchRequest(BaseModel):
    """Job matching request."""
    candidate_id: int
    location: Optional[str] = None
    limit: int = 20


class MatchResult(BaseModel):
    """Job matching result."""
    candidate_id: int
    candidate_skills: List[str]
    matches: List[Job]
    total: int
