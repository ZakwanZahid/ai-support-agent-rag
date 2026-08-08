from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Support Agent RAG", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    frontend_origin: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_ORIGIN",
    )
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ai_support_agent_rag",
        alias="DATABASE_URL",
    )
    # Migrations connect as the table owner; the application does not. Row-level
    # security is bypassed outright by a superuser and by a table's owner, so an
    # application connecting as `postgres` would pass through every policy. Left
    # unset, migrations fall back to DATABASE_URL — convenient, and fine while
    # DATABASE_URL still points at the owner, which is the pre-RLS state.
    migration_database_url: str | None = Field(
        default=None,
        alias="MIGRATION_DATABASE_URL",
    )
    # The non-owning login role the application uses, created by the RLS
    # migration. DATABASE_URL should name this role, not the owner.
    app_db_role: str = Field(default="supportmind_app", alias="APP_DB_ROLE")
    app_db_password: str = Field(
        default="supportmind_app",
        alias="APP_DB_PASSWORD",
    )
    jwt_secret_key: str = Field(default="change-me-in-development", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES", gt=0)
    upload_dir: Path = Field(default=Path("storage/uploads"), alias="UPLOAD_DIR")
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB", gt=0)
    # Off by default: preparation is an explicit action via the prepare
    # endpoint, which owns the whole extract-then-index lifecycle. Starting
    # ingestion automatically on upload leaves the document mid-flight, so a
    # prepare call moments later conflicts with work already in progress and
    # the document stalls after extraction with nothing to index it.
    auto_ingest_on_upload: bool = Field(default=False, alias="AUTO_INGEST_ON_UPLOAD")
    chunk_size: int = Field(default=1200, alias="CHUNK_SIZE", gt=0)
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP", ge=0)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    preparation_queue_name: str = Field(
        default="preparation",
        alias="PREPARATION_QUEUE_NAME",
    )
    # A preparation job holds no locks and is safe to re-run, so the ceiling is
    # about not burning embedding spend on a provider that is genuinely down.
    preparation_max_attempts: int = Field(
        default=3,
        alias="PREPARATION_MAX_ATTEMPTS",
        ge=1,
        le=10,
    )
    # Backoff between attempts, in seconds. Long enough for a brief provider
    # blip to clear without making a stuck document wait many minutes.
    preparation_retry_delays: str = Field(
        default="10,60,180",
        alias="PREPARATION_RETRY_DELAYS",
    )
    # A job still marked processing after this long has lost its worker. The
    # value must exceed the slowest realistic preparation, or the sweep will
    # fail documents that are merely slow.
    preparation_stale_after_seconds: int = Field(
        default=900,
        alias="PREPARATION_STALE_AFTER_SECONDS",
        gt=0,
    )
    # Hard ceiling on a single job. Without it a hung provider call keeps a
    # worker occupied indefinitely.
    preparation_job_timeout_seconds: int = Field(
        default=600,
        alias="PREPARATION_JOB_TIMEOUT_SECONDS",
        gt=0,
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # JSON in every environment that ships its logs somewhere, plain text on a
    # laptop where a human is reading them directly.
    log_json: bool = Field(default=True, alias="LOG_JSON")
    # Unset means error reporting is wired but off. Nothing here requires an
    # account to exist.
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    # Rate limiting. Disabling it is for tests and for local work where a
    # reload loop would otherwise lock you out of your own login form.
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    # Auth is limited per client address: enough headroom for someone
    # mistyping a password, far below what credential stuffing needs.
    rate_limit_auth_max_requests: int = Field(
        default=10,
        alias="RATE_LIMIT_AUTH_MAX_REQUESTS",
        gt=0,
    )
    rate_limit_auth_window_seconds: int = Field(
        default=60,
        alias="RATE_LIMIT_AUTH_WINDOW_SECONDS",
        gt=0,
    )
    # Chat is limited per organization, because the cost of a message is an
    # embedding call plus a completion and the bill is per organization, not
    # per user or per address.
    rate_limit_chat_max_requests: int = Field(
        default=20,
        alias="RATE_LIMIT_CHAT_MAX_REQUESTS",
        gt=0,
    )
    rate_limit_chat_window_seconds: int = Field(
        default=60,
        alias="RATE_LIMIT_CHAT_WINDOW_SECONDS",
        gt=0,
    )
    # The daily half of the spending controls. Rate limiting bounds a burst;
    # this bounds a day, which a per-minute limit does not: twenty messages a
    # minute is nearly thirty thousand a day.
    daily_budget_enabled: bool = Field(default=True, alias="DAILY_BUDGET_ENABLED")
    # Counted in tokens because tokens are what the provider reports. A cap on
    # requests would treat a one-line question and a full-context one alike;
    # a cap on estimated cost would move whenever the price table went stale.
    daily_token_budget: int = Field(
        default=1_000_000,
        alias="DAILY_TOKEN_BUDGET",
        ge=0,
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS", gt=0)
    index_batch_size: int = Field(default=50, alias="INDEX_BATCH_SIZE", gt=0)
    chat_provider: str = Field(default="openai", alias="CHAT_PROVIDER")
    chat_model: str = Field(default="gpt-4o-mini", alias="CHAT_MODEL")
    chat_temperature: float = Field(
        default=0.2,
        alias="CHAT_TEMPERATURE",
        ge=0,
        le=2,
    )
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K", ge=1, le=50)
    rag_max_context_chars: int = Field(
        default=12000,
        alias="RAG_MAX_CONTEXT_CHARS",
        gt=0,
    )

    @property
    def preparation_retry_intervals(self) -> list[int]:
        """Backoff delays parsed from the comma-separated setting.

        Padded or trimmed to one interval per retry, so the policy stays
        coherent if the two settings are configured inconsistently.
        """
        retries = self.preparation_max_attempts - 1
        if retries <= 0:
            return []

        parsed = [
            int(part.strip())
            for part in self.preparation_retry_delays.split(",")
            if part.strip()
        ] or [10]

        if len(parsed) >= retries:
            return parsed[:retries]
        return parsed + [parsed[-1]] * (retries - len(parsed))

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        self.embedding_provider = self.embedding_provider.strip().lower()
        self.chat_provider = self.chat_provider.strip().lower()
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
