from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Rocks Stream API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://rocksstream:rocksstream@postgres:5432/rocksstream"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    admin_email: str = "admin@rocks.stream"
    admin_password: str = "ChangeMe123!"
    engine_url: str = "http://streaming-engine:8081"
    public_domain: str = "keystream.rockstreamer.com"
    public_scheme: str = "https"
    hls_root: str = "/var/lib/rocks-stream/hls"
    logos_root: str = "/var/lib/rocks-stream/logos"
    logs_root: str = "/var/log/rocks-stream"
    cors_origins: str = "http://localhost:3000,https://keystream.rockstreamer.com"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
