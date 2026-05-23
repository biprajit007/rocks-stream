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
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCzoUUfaZ7e05TxehQNBxHAo5ZURgRBQ7EeBofJxw8SjlrTuk3LXCC1fzbvkaw+iTQrHcWPbMub5aR/bKNXI2mc2mW/Lvwsq3t8RVAsp/OcTC6viqWwKvz07c575v6thdf8m7FlbF5R+rTM3lsBeHz0mZkiRZKbNyO+zrk14JiwETmnamlAP3wrS5w47ClCaaiaLgtkOHQ3WUZZU3lR47VkIN5RGkSuLC9pJPSzVT9yJjuPOyqwr1wLRYOj0W6tSE9T2z/K1J51OGrDohjPTuD2vIHQEgoeaU+vCmHBDfPpuUDN3KqKTer/qkuzeR65/Og1DBbofJt+LVPaNuxvMSGpG1clPMRg+F3Gd9EtgE45t+Zdl8b79oDM6hiAcbiujkHCjd2E+YofDoSt8fA47Kf0YiLnKu5HLsww6Khl2SpSbDoFSsqgUmgWzueBSAmb47brSmdgYjWf+qI29R4HF18Pm9ISis1wKhebcUiyI0Sxs0nzHeqG/P6gAPWfWDHVMGtp+6g5mTxgEQ5b/d5wlVXegT8OJd/xUvRSJbNFlzKOAo16SEeYDz8TGx/TTTna8jsOgM1drXBRP57qnrlqfxcEcQHSd6Nn4qjMT5Qnox40s4g+rYcV1+uk6qLLLW2NV6eGgZqnjn8IYtZzmxhnVWLUpjF/vjAEiBOmv463vfuggQ== user@moviestreamhq.com"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
