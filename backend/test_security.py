import pytest
from fastapi.testclient import TestClient
import os

# Set environment vars for testing
os.environ["API_KEY"] = "test-secret-key"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

from backend import app, is_safe_url

client = TestClient(app)

def test_is_safe_url():
    # Safe public URLs
    assert is_safe_url("https://x.com/some_user") is True
    assert is_safe_url("http://google.com") is True
    
    # Unsafe private/loopback URLs
    assert is_safe_url("http://localhost:8000") is False
    assert is_safe_url("http://127.0.0.1:8000") is False
    assert is_safe_url("http://192.168.1.1") is False
    assert is_safe_url("http://10.0.0.1") is False
    
    # Unsafe schemes
    assert is_safe_url("ftp://google.com") is False
    assert is_safe_url("javascript:alert(1)") is False

def test_api_key_unauthorized():
    # Call without key
    response = client.post("/api/analyze-url", json={"url": "https://x.com/test"})
    assert response.status_code == 401
    
    # Call with invalid key
    response = client.post(
        "/api/analyze-url", 
        json={"url": "https://x.com/test"},
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401

def test_api_key_authorized_but_invalid_url():
    # Call with valid key but invalid url (SSRF check should trigger a 400)
    response = client.post(
        "/api/analyze-url", 
        json={"url": "http://127.0.0.1/attacker"},
        headers={"X-API-Key": "test-secret-key"}
    )
    assert response.status_code == 400
    assert "unsafe destination" in response.json()["detail"].lower()
