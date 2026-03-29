from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    webhook_secret: str
    groq_api_key: str
    resend_api_key: str
    resend_from_email: str = "supportdesk@ericholt.dev"

    class Config:
        env_file = ".env"


settings = Settings()
