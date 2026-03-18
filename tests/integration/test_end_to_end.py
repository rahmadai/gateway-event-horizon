"""
End-to-end integration tests.
Requires all services to be running.
"""

import pytest
import requests

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def base_url():
    return BASE_URL


class TestHealthEndpoints:
    """Test all health endpoints."""
    
    def test_gateway_health(self, base_url):
        """Test gateway health."""
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "gateway"
        assert data["status"] in ["healthy", "degraded"]
    
    def test_job_matching_health(self, base_url):
        """Test job matching health through gateway."""
        response = requests.get(f"{base_url}/job-matching/jobs?limit=1")
        assert response.status_code == 200
    
    def test_payment_health(self):
        """Test payment health directly."""
        response = requests.get("http://localhost:8003/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "payment"


class TestJobMatchingFlow:
    """Test complete job matching flow."""
    
    def test_list_jobs(self, base_url):
        """Test listing jobs."""
        response = requests.get(f"{base_url}/job-matching/jobs?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "count" in data
    
    def test_filter_jobs_by_location(self, base_url):
        """Test filtering jobs by location."""
        response = requests.get(f"{base_url}/job-matching/jobs?location=Jakarta")
        assert response.status_code == 200
        data = response.json()
        for job in data["jobs"]:
            assert job["location"] == "Jakarta"
    
    def test_get_job_stats(self, base_url):
        """Test getting job statistics."""
        response = requests.get(f"{base_url}/job-matching/jobs/1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_applications" in data


class TestPaymentFlow:
    """Test payment processing flow."""
    
    def test_create_payment(self):
        """Test creating a payment."""
        payload = {
            "amount": 10000,
            "currency": "usd",
            "customer_id": "cus_test",
            "payment_method": "pm_card",
            "description": "Test payment"
        }
        response = requests.post("http://localhost:8003/payments", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "succeeded"
        assert "payment_id" in data
    
    def test_list_payments(self):
        """Test listing payments."""
        response = requests.get("http://localhost:8003/payments")
        assert response.status_code == 200
        data = response.json()
        assert "payments" in data


class TestNotificationFlow:
    """Test notification flow."""
    
    def test_send_email(self, base_url):
        """Test sending email notification."""
        payload = {
            "recipient": "test@example.com",
            "channel": "email",
            "template": "welcome",
            "variables": {"name": "Test User", "email": "test@example.com", "service_name": "Gateway"}
        }
        response = requests.post(f"{base_url}/notifications/send", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "notification_id" in data
        assert data["status"] in ["sent", "queued"]
    
    def test_list_templates(self):
        """Test listing email templates."""
        response = requests.get("http://localhost:8002/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
