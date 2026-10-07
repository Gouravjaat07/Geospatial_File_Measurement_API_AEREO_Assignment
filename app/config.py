from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Geospatial File Measurement API"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/geospatial_db"
    max_upload_size_mb: int = 25
    max_extracted_size_mb: int = 100
    upload_directory: Path = Path("uploads")
    allowed_file_extensions: Annotated[list[str], NoDecode] = [".kml", ".zip"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("allowed_file_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, value: object) -> list[str]:
        if isinstance(value, str):
            value = value.split(",")
        return [str(item).strip().lower() if str(item).strip().startswith(".") else f".{str(item).strip().lower()}" for item in value]  # type: ignore[union-attr]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_extracted_size_bytes(self) -> int:
        return self.max_extracted_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_directory.mkdir(parents=True, exist_ok=True)
    return settings
