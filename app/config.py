from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    firebase_collection: str

    class Config:
        env_file = ".env"

settings = Settings()
