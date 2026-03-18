"""
Unit tests for API Gateway.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/gateway/src'))

from main import app


client = TestClient(app)


def test_health_check():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gateway"
    assert "status" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Gateway Event Horizon - API Gateway"
    assert "version" in data


def test_rate_limit_headers():
    """Test rate limiting headers are present."""
    response = client.get("/")
    assert "X-Correlation-ID" in response.headers
    assert "X-Response-Time" in response.headers
