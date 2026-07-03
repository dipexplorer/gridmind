"""
Test: Health Check Endpoint

This is the FIRST test in the project — verifies the API is alive.
Every subsequent test file follows this same pattern.
"""


def test_health_check(client):
    """
    Given: The API is running
    When: GET /health is called (no auth required)
    Then: Returns 200 OK with status: "ok"
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root_endpoint(client):
    """
    Given: The API is running
    When: GET / is called
    Then: Returns 200 OK with a message
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "GridMind" in response.json()["message"]
