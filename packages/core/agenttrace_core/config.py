"""Configuration management for AgentTrace."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database configuration
    database_url: str = "postgresql://agenttrace:dev_password@localhost:5432/agenttrace"

    # OTLP endpoints
    otlp_grpc_port: int = 4317
    otlp_http_port: int = 4318

    # Service configuration
    service_name: str = "agenttrace"
    log_level: str = "INFO"

    # Feature flags
    enable_encryption: bool = False
    enable_auto_classification: bool = True

    model_config = SettingsConfigDict(
        env_prefix="AGENTTRACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
