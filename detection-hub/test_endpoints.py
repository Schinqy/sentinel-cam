import pytest
from fastapi.testclient import TestClient
import os
import time

# Import the FastAPI app instance from your code
from main import app

# Create a test client
client = TestClient(app)

API_KEY = "sentinel-secret-2026"
HEADERS = {"X-API-Key": API_KEY}

def test_get_diagnostics():
    response = client.get("/diagnostics", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "cpu_load" in data
    assert "active_connections" in data


def test_get_cameras():
    response = client.get("/cameras", headers=HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

import uuid

def test_add_camera():
    random_id = f"testcam_{uuid.uuid4().hex[:6]}"
    payload = {
        "id": random_id,
        "name": "Unit Test Camera",
        "url": "http://testurl/stream",
        "is_active": True
    }
    response = client.post("/cameras", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_set_traffic_light_valid():
    payload = {"status": "RED"}
    response = client.post("/api/traffic-light/status", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["traffic_light"] == "RED"

def test_set_traffic_light_invalid():
    payload = {"status": "PURPLE"} # Invalid color
    response = client.post("/api/traffic-light/status", json=payload, headers=HEADERS)
    assert response.status_code == 400

def test_unauthorized_access():
    payload = {"status": "GREEN"}
    # Missing the X-API-Key header
    response = client.post("/api/traffic-light/status", json=payload) 
    assert response.status_code == 403

def test_generate_challan():
    payload = {
        "cam_id": "testcam1",
        "violation": "ILLEGAL_PARKING",
        "timestamp": "12:00:00",
        "plate_number": "UNIT-TEST",
        "confidence": 0.99
    }
    response = client.post("/api/generate-challan", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "pdf_url" in data
    
    # Verify the physical file was actually generated
    filename = data["pdf_url"].split("/")[-1]
    local_path = os.path.join("captures", filename)
    assert os.path.exists(local_path)

def test_get_violations():
    response = client.get("/violations", headers=HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
