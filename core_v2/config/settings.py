from typing import List, Optional, Union
from pydantic import Field, AnyHttpUrl, validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    """
    Core Configuration for Mami AI v4 (Core v2).
    Follows 12-Factor App principles.
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # --- Application ---
    APP_ENV: str = Field(default="development", description="execution environment")
    APP_NAME: str = "Mami AI v4"
    DEBUG: bool = False

    # --- Redis (Cache & State) ---
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Primary Redis connection string")
    REDIS_SSL_CERT_REQS: str = Field(default="none", description="SSL requirement for Cloud Redis (none/required)")

    # --- Database (Neo4j) ---
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USERNAME: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")

    # --- AI Providers ---
    GROQ_API_KEYS: List[str] = Field(default_factory=list, description="List of API keys for Groq rotation")

    @field_validator("GROQ_API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                # Try JSON format first
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback to CSV
                return [k.strip() for k in v.split(",") if k.strip()]
        return []

settings = Settings()
