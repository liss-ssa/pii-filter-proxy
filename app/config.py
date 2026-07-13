from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Russian PII Proxy MVP"
    pii_filter_enabled: bool = True
    disabled_policy: str = "block"
    uncertain_policy: str = "review"
    redact_threshold: float = 0.80
    review_low: float = 0.35
    max_input_bytes: int = 2_000_000
    max_concurrent_inference: int = 2
    queue_timeout_ms: int = 500
    inference_device: str = "cpu"
    mask_organization_pii: bool = False
    upstream_llm_url: str | None = None
    upstream_timeout_seconds: float = 30.0
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
