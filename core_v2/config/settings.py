from typing import List, Union, Optional
from pydantic import Field, field_validator
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
    def parse_api_keys(cls, v: Union[str, List[str], None]) -> List[str]:
        if v is None:
            raise ValueError("GROQ_API_KEYS cannot be None")
        
        parsed_keys = []
        if isinstance(v, list):
            parsed_keys = v
        elif isinstance(v, str):
            v = v.strip()
            if not v:
                # Empty string provided
                raise ValueError("GROQ_API_KEYS cannot be empty")
            try:
                # Try JSON format first
                parsed_keys = json.loads(v)
            except json.JSONDecodeError:
                # Fallback to CSV
                parsed_keys = [k.strip() for k in v.split(",") if k.strip()]
        
        # Final validation
        if not parsed_keys:
             raise ValueError("GROQ_API_KEYS must contain at least one key")
        
        return parsed_keys

settings = Settings()
