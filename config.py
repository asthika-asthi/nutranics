from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "sqlite:///./pract.db"

    # JWT
    secret_key: str = "change-me-in-production-use-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # SMTP (NHS.net for V1)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Clinic"

    # Business
    business_name: str = "Wellness Clinic"
    business_address: str = ""
    tax_rate: float = 0.0

    # Offline
    max_home_visits_per_day: int = 2


settings = Settings()
