"""
Load Testing with Locust
Simulates production traffic patterns for the microservices.
"""

from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    """Simulates API Gateway traffic."""
    wait_time = between(1, 5)
    
    def on_start(self):
        """Setup before test starts."""
        self.headers = {
            "X-API-Key": "test-api-key",
            "Content-Type": "application/json",
        }
    
    @task(10)
    def health_check(self):
        """Health check endpoint - most frequent."""
        self.client.get("/health", headers=self.headers)
    
    @task(5)
    def list_jobs(self):
        """List jobs with filters."""
        self.client.get(
            "/job-matching/jobs?location=Jakarta&limit=20",
            headers=self.headers
        )
    
    @task(3)
    def get_job_details(self):
        """Get specific job details."""
        self.client.get(
            "/job-matching/jobs/1/stats",
            headers=self.headers
        )
    
    @task(2)
    def match_candidate(self):
        """Candidate matching endpoint - compute intensive."""
        self.client.post(
            "/job-matching/match",
            json={
                "candidate_id": 1,
                "location": "Jakarta",
                "limit": 20
            },
            headers=self.headers
        )


class HighLoadUser(HttpUser):
    """Simulates burst traffic scenarios."""
    wait_time = between(0.1, 0.5)  # Very fast requests
    
    @task(1)
    def burst_health_checks(self):
        """Rapid health checks to test connection pooling."""
        self.client.get("/health")
