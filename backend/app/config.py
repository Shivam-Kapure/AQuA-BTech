from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Agentic Test System"
    API_V1_PREFIX: str = "/api/v1"
    APP_ENV: str = "development"
    AUTH_SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    TARGET_HOST_ALLOWLIST: str = ""
    ALLOW_PRIVATE_TARGETS: bool = False
    HTTP_VERIFY_TLS: bool = True

    # Database
    MONGODB_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "agentic_testing"

    # LLM
    GROQ_API_KEY: str | None = None
    LMSTUDIO_URL: str = "http://localhost:1234"
    LLM_PROVIDER: str = "lmstudio"  # "lmstudio" | "groq"
    LLM_MODEL: str = "meta-llama-3-8b-instruct"
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT_S: float = 180.0
    LLM_MAX_TOKENS: int | None = None

    # Agent / Playwright script generation (can use a separate LM Studio instance/model)
    AGENT_LMSTUDIO_URL: str | None = None
    AGENT_LLM_MODEL: str | None = None

    # Playwright artifacts
    PLAYWRIGHT_SCRIPT_OUTPUT_DIR: str | None = "playwright_scripts"
    PLAYWRIGHT_ARTIFACTS_DIR: str = "playwright_artifacts"
    PLAYWRIGHT_RUN_TIMEOUT_S: float = 180.0

    # Vector DB
    CHROMA_PATH: str = "data/chroma_db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
