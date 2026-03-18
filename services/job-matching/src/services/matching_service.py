"""
Job matching algorithm service.
"""

from typing import List
from datetime import datetime
import json


class MatchingService:
    """Service for job-candidate matching."""
    
    @staticmethod
    def calculate_match_score(job_skills: List[str], candidate_skills: List[str]) -> float:
        """
        Calculate match score between job requirements and candidate skills.
        
        Returns:
            Score from 0-100
        """
        if not job_skills:
            return 50.0
        
        job_set = set(skill.lower() for skill in job_skills)
        candidate_set = set(skill.lower() for skill in candidate_skills)
        
        if not candidate_set:
            return 0.0
        
        # Calculate overlap
        matched = job_set & candidate_set
        total_unique = job_set | candidate_set
        
        if not total_unique:
            return 0.0
        
        # Score based on:
        # - Percentage of job skills matched (70% weight)
        # - Overall skill overlap (30% weight)
        job_match_ratio = len(matched) / len(job_set) if job_set else 0
        overall_ratio = len(matched) / len(total_unique) if total_unique else 0
        
        score = (job_match_ratio * 0.7 + overall_ratio * 0.3) * 100
        return round(score, 2)
    
    @staticmethod
    def rank_jobs(jobs: List[dict], candidate: dict) -> List[dict]:
        """
        Rank jobs by relevance to candidate.
        
        Args:
            jobs: List of job dictionaries
            candidate: Candidate dictionary
            
        Returns:
            Jobs sorted by match score (descending)
        """
        candidate_skills = candidate.get("skills", [])
        if isinstance(candidate_skills, str):
            candidate_skills = json.loads(candidate_skills)
        
        candidate_location = candidate.get("location", "").lower()
        
        scored_jobs = []
        for job in jobs:
            job_skills = job.get("required_skills", [])
            if isinstance(job_skills, str):
                job_skills = json.loads(job_skills)
            
            # Calculate base score
            base_score = MatchingService.calculate_match_score(job_skills, candidate_skills)
            
            # Location bonus
            location_bonus = 0
            job_location = job.get("location", "").lower()
            if job_location == candidate_location:
                location_bonus = 10
            elif job.get("remote"):
                location_bonus = 5
            
            # Recency bonus (jobs posted in last 7 days get bonus)
            recency_bonus = 0
            created_at = job.get("created_at")
            if created_at:
                try:
                    from datetime import datetime, timedelta
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if datetime.now() - created_at < timedelta(days=7):
                        recency_bonus = 5
                except:
                    pass
            
            final_score = min(100, base_score + location_bonus + recency_bonus)
            
            job_with_score = dict(job)
            job_with_score["calculated_score"] = final_score
            scored_jobs.append(job_with_score)
        
        # Sort by score descending
        scored_jobs.sort(key=lambda x: x["calculated_score"], reverse=True)
        return scored_jobs
