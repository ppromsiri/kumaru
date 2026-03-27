import pytest
import os
import sys

# Add root directory to path so tests can import main, api, etc.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variables for testing before importing main
os.environ["API_KEY"] = "test-api-key"
os.environ["PORT"] = "8000"

from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    # Provide a TestClient for testing HTTP endpoints
    return TestClient(app)

@pytest.fixture
def mock_cache_all(mocker):
    # Mock cache functionality globally for modules that use it
    # This prevents the need for a real Redis connection
    mocker.patch("api.cache_get", return_value=None)
    mocker.patch("api.cache_set", return_value=None)
    mocker.patch("scrap.cache_get", return_value=None)
    mocker.patch("scrap.cache_set", return_value=None)
