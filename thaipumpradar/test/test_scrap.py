import pytest
from fastapi import HTTPException
from playwright.async_api import TimeoutError as PlaywrightTimeout
from scrap import fetch_from_scrap

def test_fetch_from_scrap_success(mocker):
    # Mock cache เพื่อไม่ให้เรียกใช้งานจริง
    mocker.patch("scrap.cache_get", return_value=None)
    mocker.patch("scrap.cache_set")
    
    mock_scrape_result = {"totalStations": 120, "reportedStations": 80}
    mocker.patch("scrap._scrape_province", new_callable=mocker.AsyncMock, return_value=mock_scrape_result)
    
    result = fetch_from_scrap("นครราชสีมา")
    
    assert result == mock_scrape_result

def test_fetch_from_scrap_timeout(mocker):
    # Mock cache เพื่อไม่ให้เรียกใช้งานจริง
    mocker.patch("scrap.cache_get", return_value=None)
    mocker.patch("scrap._scrape_province", new_callable=mocker.AsyncMock, side_effect=PlaywrightTimeout("timeout"))
    
    with pytest.raises(HTTPException) as excinfo:
        fetch_from_scrap("นครราชสีมา")
        
    assert excinfo.value.status_code == 504
    assert "timeout" in excinfo.value.detail.lower()

def test_fetch_from_scrap_general_error(mocker):
    # Mock cache เพื่อไม่ให้เรียกใช้งานจริง
    mocker.patch("scrap.cache_get", return_value=None)
    mocker.patch("scrap._scrape_province", new_callable=mocker.AsyncMock, side_effect=Exception("Unknown Error..."))
    
    with pytest.raises(HTTPException) as excinfo:
        fetch_from_scrap("นครราชสีมา")
        
    assert excinfo.value.status_code == 500
    assert "Unknown Error" in excinfo.value.detail
