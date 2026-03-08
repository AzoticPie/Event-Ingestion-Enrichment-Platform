"""Application configuration management."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "event-ingestion-platform"
    environment: str = "local"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "event_platform"
    postgres_user: str = "event_platform"
    postgres_password: str = "event_platform"

    redis_host: str = "redis"
    redis_port: int = 6379

    celery_enrichment_queue: str = "enrichment.default"
    enrichment_max_retries: int = 5
    enrichment_backoff_base_seconds: int = 2
    geoip_db_path: str = "/data/GeoLite2-Country.mmdb"

    aggregate_rollup_enabled: bool = False
    aggregate_rollup_refresh_lookback_minutes: int = 180
    aggregate_rollup_refresh_interval_seconds: int = 60
    aggregate_rollup_refresh_tenants_per_tick: int = 100
    aggregate_rollup_refresh_max_inflight_tenant_tasks: int = 20
    aggregate_rollup_backfill_chunk_minutes: int = 1440
    aggregate_rollup_backfill_max_chunks_per_task: int = 24
    aggregate_rollup_lock_retry_max_attempts: int = 8
    aggregate_rollup_lock_retry_base_seconds: int = 5
    aggregate_rollup_max_window_minutes: int = 10080
    celery_rollup_queue: str = "rollup.default"

    enable_readiness_dependency_checks: bool = True
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def postgres_dsn(self) -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Build Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Parse comma-separated CORS origins into a normalized list."""
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

