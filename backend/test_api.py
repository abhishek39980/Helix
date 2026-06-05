import pytest
from fastapi.testclient import TestClient
import os

# Set environment vars for testing
os.environ["API_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_backend.db"  # Use a separate test database

from backend import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "cache_sizes" in data

def test_cases_crud(client):
    headers = {"X-API-Key": "test-secret-key"}
    
    # 1. List cases
    response = client.get("/api/cases", headers=headers)
    assert response.status_code == 200
    initial_count = len(response.json())
    
    # 2. Create a case
    response = client.post(
        "/api/cases",
        json={"name": "Test Case Alpha", "description": "Verify DB operations"},
        headers=headers
    )
    assert response.status_code == 200
    case_data = response.json()
    assert case_data["name"] == "Test Case Alpha"
    assert "id" in case_data
    case_id = case_data["id"]
    
    # 3. Get specific case details
    response = client.get(f"/api/cases/{case_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Case Alpha"
    assert "sessions" in data
    
    # 4. List cases again
    response = client.get("/api/cases", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == initial_count + 1
    
    # 5. Delete case
    response = client.delete(f"/api/cases/{case_id}", headers=headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    
    # 6. Verify deletion
    response = client.get(f"/api/cases/{case_id}", headers=headers)
    assert response.status_code == 404

# Cleanup the test database
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    try:
        if os.path.exists("test_backend.db"):
            os.remove("test_backend.db")
    except Exception:
        pass
