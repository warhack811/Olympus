from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Core v2 Application Settings.
    Environment variables are loaded here.
    """
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
