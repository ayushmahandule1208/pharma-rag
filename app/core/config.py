"""Configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    RAW_DIR: Path = DATA_DIR / "raw"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    
    # API Keys (loaded from environment)
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Multiple API keys for rotation
API_KEYS = [
    os.getenv("OPENAI_API_KEY", ""),
    os.getenv("OPENAI_API_KEY_2", ""),
    os.getenv("OPENAI_API_KEY_3", ""),
    os.getenv("OPENAI_API_KEY_4", ""),
    os.getenv("OPENAI_API_KEY_5", ""),
]
API_KEYS = [k for k in API_KEYS if k]  # Filter empty

# Sections that should never be split
PROTECTED_SECTIONS = {"Indications And Usage", "Boxed Warning", "Contraindications"}

# Section classification
SECTION_KEYWORDS = {
    "indication": ["indication", "use"],
    "dosing": ["dosage", "administration"],
    "safety": ["warning", "precaution", "contraindication"],
    "efficacy": ["clinical studies", "clinical trial"],
    "adverse_events": ["adverse", "reaction"],
    "pharmacology": ["pharmacology", "pharmacokinetic"],
}
