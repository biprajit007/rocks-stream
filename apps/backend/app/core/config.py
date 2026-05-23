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
    playback_token_public_key: str = (
        "-----BEGIN PUBLIC KEY-----\n"
        "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA2Y2wXlEYL3p3TtYYMaSh\n"
        "UWZFH3zavhneWjSK773U0d1LMR4r7VPlsRbiQuRHYganRZj1F0wJoQbijADJC6fI\n"
        "LXHrVX3RmjPU9GE3l4sarxqlwmz8eiEyAHCqPmfCjYgCTzXBLEOfZLBFMSoMfNhG\n"
        "exTgSpB5Tg/glSIiTB1Ehw0PfwqkBWONddpqIkk8CWEAckzt7mzAKC5XAWdMlf0V\n"
        "CeGrba5lu5KaSSHMPyq5iYpSVWGsOM5LrqnV0bSot1kDuhd+GafagHUjGVKYW9SH\n"
        "3p+FoQf3LBT2T5fZ0nuzt2K5hRXzI7zHyDSWvDt9HBy0QtOL1OCFelGpCWzPB3AK\n"
        "ivwb1DCHfRzFQ3Q/8NnXqVX8pBUFG8tYy8tl+b5qygjoTSnIVgBh+dDS3GCYV3/3\n"
        "NsDjgXvJtVB3MpwSN8DB8bjGvabbipK/jGXyYGDg68sUa1FAR8icnexV8ColihNQ\n"
        "A7L0zbZ1zBKqJTOtOspBaR28HITV90Vjp2E2nGlAeFo1vcqVrt3ynQ/BUT/3+Vst\n"
        "UUuGQa2M3wPycccl9cXZQ2Qi23toUiUrcIYynqNJXSa8/MDssKpw30a6jRnBtLZf\n"
        "w7XRCyni35FviWujlGpY0qY7ifUZmMwUpztlKQBQAMBotmPunJ8mZ+IAUCCMV1zs\n"
        "8blEPThnHaLg7v5hUg/FnQsCAwEAAQ==\n"
        "-----END PUBLIC KEY-----"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
