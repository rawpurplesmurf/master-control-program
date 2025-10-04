import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class Settings(BaseSettings):
    # Home Assistant
    HA_URL: str
    HA_TOKEN: str

    # Ollama
    OLLAMA_URL: str
    OLLAMA_MODEL: str = "mistral"

    # MySQL Database
    MYSQL_HOST: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379

settings = Settings()