from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    PROXY_API_KEY: str | None = None # Optional: if set, clients must provide this key
    DEEPSEEK_API_KEY: str | None = None # Optional: if set, overrides client key
    
    # Retry settings
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 60

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "proxy_logs"

    class Config:
        env_file = ".env"

settings = Settings()
