from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Russian PII Proxy MVP"
    pii_filter_enabled: bool = True
    disabled_policy: str = "block"
    uncertain_policy: str = "mask"
    redact_threshold: float = 0.80
    review_low: float = 0.35
    uncertain_mask_score: float = 0.81
    max_input_bytes: int = 2_000_000
    max_concurrent_inference: int = 2
    queue_timeout_ms: int = 500
    inference_device: str = "auto"
    mask_organization_pii: bool = False

    natasha_enabled: bool = True
    context_classifier_enabled: bool = True
    context_model_dir: str = "models/context-rubert-tiny2"
    context_max_length: int = 192
    context_not_pii_threshold: float = 0.75

    upstream_llm_url: str | None = None
    upstream_timeout_seconds: float = 30.0
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
