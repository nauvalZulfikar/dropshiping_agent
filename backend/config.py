from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    database_url: str = ""

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # FastAPI
    secret_key: str = "change-me"
    api_port: int = 8000
    environment: str = "development"

    # Proxies
    proxy_list: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Next.js (frontend reads these)
    next_public_api_url: str = "http://localhost:8000"
    next_public_supabase_url: str = ""
    next_public_supabase_anon_key: str = ""

    # Bright Data / Oxylabs
    brightdata_username: str = ""
    brightdata_password: str = ""
    brightdata_host: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def asyncpg_url(self) -> str:
        """Plain postgresql:// URL for asyncpg direct connections."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def sqlalchemy_url(self) -> str:
        """postgresql+asyncpg:// URL for SQLAlchemy async engine."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def proxy_list_parsed(self) -> list[dict]:
        """Parse PROXY_LIST env var into list of proxy dicts."""
        if not self.proxy_list:
            return []
        proxies = []
        for entry in self.proxy_list.split(","):
            parts = entry.strip().split(":")
            if len(parts) == 4:
                host, port, user, password = parts
                proxies.append({"host": host, "port": port, "user": user, "password": password})
        return proxies


settings = Settings()
