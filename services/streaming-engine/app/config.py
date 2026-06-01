from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://rocksstream:rocksstream@postgres:5432/rocksstream"
    hls_root: str = "/var/lib/rocks-stream/hls"
    logos_root: str = "/var/lib/rocks-stream/logos"
    logs_root: str = "/var/log/rocks-stream"
    public_domain: str = "keystream.rockstreamer.com"
    public_scheme: str = "https"
    redis_url: str = "redis://redis:6379/0"
    pipeline_start_grace_seconds: float = 4.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
