import pytest

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_fuel_status_unauthorized(client):
    # ทดสอบการไม่ส่ง API KEY
    response = client.post("/fuel-status", json={"source_type": "api", "province": "กรุงเทพมหานคร"})
    assert response.status_code == 422  # Missing required header "X-API-KEY"

def test_fuel_status_wrong_api_key(client):
    # ทดสอบกรณีส่ง API KEY ผิด
    response = client.post(
        "/fuel-status",
        json={"source_type": "api", "province": "กรุงเทพมหานคร"},
        headers={"X-API-KEY": "wrong-key"}
    )
    assert response.status_code == 403

def test_fuel_status_invalid_source_type(client):
    # ทดสอบกรณีส่ง source_type ผิด
    response = client.post(
        "/fuel-status",
        json={"source_type": "unknown", "province": "กรุงเทพมหานคร"},
        headers={"X-API-KEY": "test-api-key"}
    )
    assert response.status_code == 400
    assert "กรุณาระบุ source_type เป็น 'api' หรือ 'scrap'" in response.json()["detail"]

def test_fuel_status_api_success(client, mocker):
    # จำลองข้อมูลจาก api.py
    mock_data = {
        "totalStations": 150,
        "reportedStations": 120,
        "dieselOutPct": 15.5,
        "severity": "normal",
        "fuelSummary": {"diesel": {"available": 100, "limited": 10, "out": 10, "total": 120}},
        "brands": [{"brandId": "PTT", "total": 50, "dieselOut": 5, "dieselOk": 45, "b95Out": 0}]
    }
    mocker.patch("main.fetch_from_api", return_value=mock_data)

    response = client.post(
        "/fuel-status",
        json={"source_type": "api", "province": "กรุงเทพมหานคร"},
        headers={"X-API-KEY": "test-api-key"}
    )
    
    assert response.status_code == 200
    assert response.json() == mock_data

def test_fuel_status_markdown_response(client, mocker):
    # ทดสอบการตอบกลับแบบ Markdown
    mock_data = {
        "totalStations": 50,
        "reportedStations": 50,
        "dieselOutPct": 5.0,
        "severity": "normal",
        "fuelSummary": {},
        "brands": []
    }
    mocker.patch("main.fetch_from_scrap", return_value=mock_data)

    response = client.post(
        "/fuel-status",
        json={"source_type": "scrap", "province": "นนทบุรี", "markdown": True},
        headers={"X-API-KEY": "test-api-key"}
    )
    
    assert response.status_code == 200
    assert "markdown_content" in response.json()
    assert "นนทบุรี" in response.json()["markdown_content"]
    assert "50 แห่ง" in response.json()["markdown_content"]
