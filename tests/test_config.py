import os
from unittest.mock import patch

def test_settings_load_from_env():
    """
    Tests if the Settings object correctly loads values from environment variables.
    """
    mock_env = {
        "HA_URL": "http://fake-ha.com",
        "HA_TOKEN": "fake_token",
        "OLLAMA_URL": "http://fake-ollama.com",
        "MYSQL_HOST": "fake_mysql",
        "MYSQL_USER": "fake_user",
        "MYSQL_PASSWORD": "fake_password",
        "MYSQL_DB": "fake_db",
        "REDIS_HOST": "fake_redis",
        "REDIS_PORT": "1234"
    }
    with patch.dict(os.environ, mock_env):
        from mcp.config import Settings
        settings = Settings()
        assert settings.HA_URL == "http://fake-ha.com"
        assert settings.REDIS_PORT == 1234