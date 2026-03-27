import pytest
import json
import urllib.error
from fastapi import HTTPException
from api import fetch_from_api

def test_fetch_from_api_success(mocker):
    # กรณีไม่มีข้อมูลใน Cache (Mock ให้คืน None) จะต้องยิง HTTP Request
    mocker.patch("api.cache_get", return_value=None)
    mocker.patch("api.cache_set") # Mock เพื่อไม่ให้เรียกใช้งานจริง
    
    mock_response_data = '{"totalInProvince": 10, "totalStations": 10, "data": []}'
    
    # Mock urllib.request.urlopen (รองรับ Context Manager 'with ... as ...')
    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = mock_response_data.encode("utf-8")
    
    result = fetch_from_api("ขอนแก่น")
    
    assert result == json.loads(mock_response_data)
    mock_urlopen.assert_called_once()

def test_fetch_from_api_empty_data(mocker):
    # ประเมินว่าเป็นชื่อจังหวัดผิด ถ้าข้อมูล return ออกมาเป็น 0 ทุกค่า
    mocker.patch("api.cache_get", return_value=None)
    
    mock_response_data = '{"totalInProvince": 0, "totalStations": 0}'
    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = mock_response_data.encode("utf-8")
    
    with pytest.raises(HTTPException) as excinfo:
        fetch_from_api("จังหวัดสมมติ")
        
    assert excinfo.value.status_code == 404
    assert "ไม่พบข้อมูลจังหวัด" in excinfo.value.detail

def test_fetch_from_api_http_error_404(mocker):
    mocker.patch("api.cache_get", return_value=None)
    
    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_urlopen.side_effect = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs={}, fp=None)
    
    with pytest.raises(HTTPException) as excinfo:
        fetch_from_api("เชียงใหม่")
        
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "ไม่พบข้อมูลจังหวัดนี้"
