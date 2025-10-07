from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    ANCHOR_API_KEY_SANDBOX: str
    BREVO_API_KEY: str
    HOST: str
    PORT: int
    USERNAME: str
    PASSWORD: str
    DATABASE: str
    SSLMODE: str
    ALGORITHM: str
    SECRET_KEY: str
    ALPACA_API_KEY: str
    PASSWORD_CHANGE_MINUTES: int
    ANCHOR_API_KEY_SANDBOX: str
    ALPACA_API_KEY: str
    ALPACA_API_SECRET: str
    MONNIFY_KEY: str
    MONNIFY_SECRECT: str
    MONNIFY_CONTRACT_CODE: str
    VANTAGE_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    RABBITMQ_URL: str
    REDIS_URL: str


settings = Settings(
  _env_file='.env',
  _env_file_encoding='utf-8',
)