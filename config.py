#
# Pipecat Voice Bot Configuration
# Environment-based settings with validation
#
"""Centralized configuration for Pipecat Voice Bot using pydantic-settings."""
import os
from typing import Dict, Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# TAREA 21: Función auxiliar para leer archivos de secrets
def _read_secret_file(env_var: str, default: str = "") -> str:
    """
    Leer secret desde archivo de Docker secrets o variable de entorno.

    Primero busca {ENV_VAR}_FILE, si existe lee el archivo.
    Si no, usa la variable de entorno directamente.
    Si no existe ninguna, retorna el default.

    Args:
        env_var: Nombre de la variable de entorno (ej: "OPENAI_API_KEY")
        default: Valor por defecto si no se encuentra

    Returns:
        El valor del secret o el default
    """
    file_path = os.getenv(f"{env_var}_FILE")
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read().strip()
        except (IOError, OSError) as e:
            # Si falla la lectura del archivo, loggear y continuar con env var
            print(f"⚠️ Warning: Could not read secret file {file_path}: {e}")

    # Si no hay archivo, intentar variable de entorno
    env_value = os.getenv(env_var, default)
    return env_value


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Keys - Required (loaded from secrets files or env vars)
    # TAREA 21: Default empty strings, loaded from secrets in model_validator
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""
    CARTESIA_API_KEY: str = ""

    # API Configuration
    RESERVATIONS_API_URL: str = "http://localhost:3000/api/voice-bridge"
    VOICE_BRIDGE_API_KEY: str | None = None
    API_TIMEOUT: int = Field(default=10, ge=1, le=60, description="API timeout in seconds")
    MAX_RETRIES: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts for API calls")

    # Bot Configuration
    BOT_NAME: str = "El Pòsit Assistant"
    DEFAULT_LANGUAGE: str = Field(default="es", pattern="^(es|ca|en)$")
    AVAILABLE_VOICES: Dict[str, str] = Field(default_factory=lambda: {
        "emilio": "b0689631-eee7-4a6c-bb86-195f1d267c2e",      # Friendly Optimist
        "catalina": "162e0f37-8504-474c-bb33-c606c01890dc",  # Neighborly Guide
        "andrea": "59b37da2-92ba-401a-9e4e-b1d16898d9bc",    # Clear Communicator
        "paola": "e361b786-2768-4308-9369-a09793d4dd73",     # Expressive Performer
        "mariana": "ae823354-f9be-4aef-8543-f569644136b4",  # Nurturing Guide
        "pedro": "15d0c2e2-8d29-44c3-be23-d585d5f154a1",    # Formal Speaker
        "maria": "de38f545-c574-44e8-9b54-a7d6fec1c6b1",    # Marta voice
    })
    DEFAULT_VOICE: str = Field(default="maria")

    # Restaurant Configuration
    RESTAURANT_LOCATIONS: Dict[str, str] = Field(default_factory=lambda: {
        "cambrils": "El Pòsit de Cambrils",
        "tarragona": "El Pòsit de Tarragona",
        "vila-seca": "El Pòsit de Vila-seca",
    })

    # Performance Settings
    VAD_SILENCE_MS_ACTIVE: int = Field(default=450, ge=100, le=2000, description="Silence duration during active conversation (ms)")
    VAD_SILENCE_MS_RELAXED: int = Field(default=700, ge=100, le=2000, description="Silence duration at conversation start (ms)")
    VAD_PROBABILITY_ACTIVE: float = Field(default=0.60, ge=0.1, le=1.0)
    VAD_PROBABILITY_RELAXED: float = Field(default=0.55, ge=0.1, le=1.0)
    VAD_MIN_VOLUME: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum volume threshold for speech detection")
    CALL_TIMEOUT_SECONDS: int = Field(default=8, ge=3, le=30, description="Timeout in seconds to end call when user doesn't speak")
    TTS_SPEED: float = Field(default=1.1, ge=0.5, le=2.0)
    TTS_EMOTION: Literal["neutral", "happy", "excited", "content", "calm"] = "neutral"

    # LLM Configuration
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = Field(default=512, ge=128, le=4096)
    LLM_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=7860, ge=1024, le=65535)
    LOG_LEVEL: Literal["debug", "info", "warning", "error", "critical"] = "info"

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = "https://voice.microbts.online,https://microbts.online"

    # Cache Configuration
    # TURN/STUN Configuration
    TURN_SERVER_URL: str = ""
    TURN_USERNAME: str = ""
    TURN_CREDENTIAL: str = ""

    CACHE_TTL_SECONDS: int = Field(default=300, ge=0, le=3600, description="Cache TTL for availability checks")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # TAREA 21: Model validator para leer secrets desde archivos
    @model_validator(mode='after')
    def load_secrets_from_files(self) -> 'Settings':
        """
        Cargar credenciales desde archivos de secrets si están disponibles.

        Este método se ejecuta después de que pydantic lea las variables de entorno.
        Busca archivos *_FILE y los usa para sobrescribir los valores de las credenciales.
        """
        # Lista de credenciales que pueden estar en archivos de secrets
        secret_keys = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "DEEPGRAM_API_KEY",
            "CARTESIA_API_KEY",
            "VOICE_BRIDGE_API_KEY",
            "TURN_USERNAME",
            "TURN_CREDENTIAL",
        ]

        for key in secret_keys:
            secret_value = _read_secret_file(key)
            if secret_value:
                # Usar setattr para actualizar el valor después de la inicialización
                setattr(self, key, secret_value)

        # Validar que los campos requeridos tengan un valor
        required_keys = ["OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"]
        for key in required_keys:
            if not getattr(self, key):
                raise ValueError(f"{key} is required but not found in environment or secret files")

        return self

    @field_validator("DEFAULT_VOICE")
    @classmethod
    def validate_voice(cls, v: str, info) -> str:
        """Validate that the default voice exists in available voices."""
        available_voices = info.data.get("AVAILABLE_VOICES", {})
        if v not in available_voices:
            raise ValueError(f"Voice '{v}' not found in AVAILABLE_VOICES. Available: {list(available_voices.keys())}")
        return v

    @property
    def voice_id(self) -> str:
        """Get the voice ID for the default voice."""
        return self.AVAILABLE_VOICES[self.DEFAULT_VOICE]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string to list."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def restaurant_ids(self) -> list[str]:
        """Get list of available restaurant IDs."""
        return list(self.RESTAURANT_LOCATIONS.keys())

    @property
    def restaurant_names(self) -> list[str]:
        """Get list of available restaurant names."""
        return list(self.RESTAURANT_LOCATIONS.values())


# Global settings instance
settings = Settings()


class ConversationState:
    """Manages conversation state for contextual prompts and VAD."""

    def __init__(self):
        self.state: str = "greeting"
        self.location: str | None = None
        self.date: str | None = None
        self.time: str | None = None
        self.party_size: int | None = None
        self.customer_name: str | None = None
        self.language: str = "es"

    @property
    def is_active(self) -> bool:
        """Check if conversation is in active data capture mode."""
        return self.state in ("capturing_location", "capturing_details", "confirming")

    @property
    def is_greeting(self) -> bool:
        """Check if conversation is at greeting phase."""
        return self.state == "greeting"

    def transition_to(self, new_state: str):
        """Transition to a new conversation state."""
        valid_states = {"greeting", "capturing_location", "capturing_details", "confirming", "completed", "error"}
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}. Valid states: {valid_states}")
        self.state = new_state

    def reset(self):
        """Reset conversation state."""
        self.__init__()


# Global conversation state instance
conversation_state = ConversationState()
