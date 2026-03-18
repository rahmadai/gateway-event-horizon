"""
Job Matching Service - FastAPI
Handles job-candidate matching with optimized database queries.
"""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import aiomysql
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import redis.asyncio as redis

# Database configuration from environment
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "job_matching_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure_password")
DB_NAME = os.getenv("DB_NAME", "job_matching")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global connections
pool: Optional[aiomysql.Pool] = None
cache: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connection pools on startup."""
    global pool, cache
    
    # Initialize MySQL connection pool
    try:
        pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            minsize=5,
            maxsize=20,
            pool_recycle=3600,
            autocommit=True,
        )
        print(f"Connected to MySQL at {DB_HOST}:{DB_PORT}")
    except Exception as e:
        print(f"Warning: MySQL connection failed: {e}")
        pool = None
    
    # Initialize Redis cache
    try:
        cache = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        cache = None
    
    yield
    
    # Cleanup
    if pool:
        pool.close()
        await pool.wait_closed()
    if cache:
        await cache.close()


app = FastAPI(
    title="Job Matching Service",
    description="Optimized job-candidate matching with MySQL",
    version="1.0.0",
    lifespan=lifespan,
)


# Pydantic models
class Job(BaseModel):
    id: int
    title: str
    company_id: int
    location: str
    required_skills: List[str]
    match_score: Optional[float] = None
    status: str = "active"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MatchRequest(BaseModel):
    candidate_id: int
    location: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


async def get_cached(key: str) -> Optional[dict]:
    """Get data from Redis cache."""
    if not cache:
        return None
    try:
        cached = await cache.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


async def set_cached(key: str, data: dict, ttl: int = 300):
    """Set data in Redis cache."""
    if not cache:
        return
    try:
        await cache.setex(key, ttl, json.dumps(data, default=str))
    except Exception:
        pass


@app.get("/health")
async def health_check():
    """Service health check."""
    db_healthy = False
    cache_healthy = False
    
    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
                    db_healthy = True
        except Exception as e:
            print(f"DB health check failed: {e}")
    
    if cache:
        try:
            await cache.ping()
            cache_healthy = True
        except:
            pass
    
    status_code = 200 if db_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_healthy else "unhealthy",
            "service": "job-matching",
            "database": "connected" if db_healthy else "disconnected",
            "cache": "connected" if cache_healthy else "disconnected",
        }
    )


from fastapi.responses import JSONResponse


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "Job Matching Service", "version": "1.0.0", "docs": "/docs"}


@app.get("/job-matching/jobs")
async def list_jobs(
    location: Optional[str] = Query(None, description="Filter by location"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List jobs with filters."""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Check cache
    cache_key = f"jobs:{location}:{skills}:{limit}:{offset}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT 
                    j.id,
                    j.title,
                    j.company_id,
                    j.location,
                    j.required_skills,
                    j.match_score,
                    j.status,
                    j.created_at
                FROM jobs j
                WHERE j.status = 'active'
            """
            params = []
            
            if location:
                query += " AND j.location = %s"
                params.append(location)
            
            if skills:
                skill_list = skills.split(",")
                query += " AND JSON_OVERLAPS(j.required_skills, %s)"
                params.append(json.dumps(skill_list))
            
            query += " ORDER BY j.match_score DESC, j.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            await cur.execute(query, params)
            rows = await cur.fetchall()
            
            # Convert JSON strings to lists
            jobs = []
            for row in rows:
                row_dict = dict(row)
                if row_dict.get('required_skills'):
                    try:
                        row_dict['required_skills'] = json.loads(row_dict['required_skills'])
                    except:
                        row_dict['required_skills'] = []
                jobs.append(row_dict)
    
    result = {"jobs": jobs, "count": len(jobs)}
    await set_cached(cache_key, result)
    return result


@app.post("/job-matching/match")
async def match_candidate_to_jobs(request: MatchRequest):
    """Find matching jobs for a candidate."""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Get candidate
            await cur.execute(
                "SELECT skills, location FROM candidates WHERE id = %s",
                (request.candidate_id,),
            )
            candidate = await cur.fetchone()
            
            if not candidate:
                raise HTTPException(status_code=404, detail=f"Candidate {request.candidate_id} not found")
            
            location_filter = request.location or candidate["location"]
            candidate_skills = json.loads(candidate["skills"]) if candidate["skills"] else []
            
            # Simple matching query
            await cur.execute(
                """
                SELECT 
                    j.id,
                    j.title,
                    j.company_id,
                    j.location,
                    j.required_skills,
                    j.match_score,
                    j.created_at
                FROM jobs j
                WHERE j.status = 'active'
                    AND (j.location = %s OR j.remote = 1)
                ORDER BY j.match_score DESC
                LIMIT %s
                """,
                (location_filter, request.limit),
            )
            
            rows = await cur.fetchall()
            matches = []
            for row in rows:
                row_dict = dict(row)
                if row_dict.get('required_skills'):
                    try:
                        row_dict['required_skills'] = json.loads(row_dict['required_skills'])
                    except:
                        row_dict['required_skills'] = []
                matches.append(row_dict)
    
    return {
        "candidate_id": request.candidate_id,
        "candidate_skills": candidate_skills,
        "matches": matches,
        "total": len(matches),
    }


@app.get("/job-matching/jobs/{job_id}/stats")
async def get_job_stats(job_id: int):
    """Get job statistics."""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    cache_key = f"job_stats:{job_id}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT 
                    j.id,
                    j.title,
                    COUNT(DISTINCT ja.id) as total_applications,
                    COUNT(DISTINCT CASE WHEN ja.status = 'pending' THEN ja.id END) as pending,
                    COUNT(DISTINCT CASE WHEN ja.status = 'reviewed' THEN ja.id END) as reviewed,
                    COUNT(DISTINCT CASE WHEN ja.status = 'hired' THEN ja.id END) as hired
                FROM jobs j
                LEFT JOIN job_applications ja ON j.id = ja.job_id
                WHERE j.id = %s
                GROUP BY j.id, j.title
                """,
                (job_id,),
            )
            stats = await cur.fetchone()
    
    if not stats:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = dict(stats)
    await set_cached(cache_key, result, ttl=300)
    return result


@app.post("/job-matching/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(job: Job):
    """Create new job."""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO jobs (title, company_id, location, required_skills, match_score, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    job.title,
                    job.company_id,
                    job.location,
                    json.dumps(job.required_skills),
                    job.match_score or 0.0,
                    job.status or 'active',
                ),
            )
            job_id = cur.lastrowid
    
    # Invalidate cache
    if cache:
        try:
            await cache.delete(f"jobs:{job.location}:*")
        except:
            pass
    
    return {**job.dict(), "id": job_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
