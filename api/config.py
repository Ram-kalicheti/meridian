from pydantic_settings import BaseSettings, SettingsConfigDict


TENANT_TPM_LIMITS: dict[str, int] = {
    "acme": 100_000,
    "contoso": 50_000,
    "fabrikam": 75_000,
}

INDEX_NAME = "meridian-docs"
EMBEDDING_DIMS = 1536
SEMANTIC_CACHE_THRESHOLD = 0.95


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_endpoint: str
    openai_key: str
    ai_search_endpoint: str
    ai_search_key: str
    redis_url: str = "redis://localhost:6379"
    embedding_deployment: str = "text-embedding-3-small"
    chat_deployment: str = "gpt-4o-mini"


settings = Settings()