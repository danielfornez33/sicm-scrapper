"""
Configuración centralizada del scraper SICM
Soporta variables de entorno con valores por defecto seguros
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Config:
    """Configuración principal del scraper"""

    # ==================== DATABASE ====================
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "farmapatria")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "postgres")
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", 5))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", 20))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", 30))

    # ==================== SCRAPING RANGE ====================
    START_ID: int = int(os.getenv("START_ID", 42022341))
    END_ID: int = int(os.getenv("END_ID", 42591276))

    # ==================== PERFORMANCE ====================
    CONCURRENCY: int = int(os.getenv("CONCURRENCY", 20))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", 1000))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", 60))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", 5))
    DELAY_MS: int = int(os.getenv("DELAY_MS", 50))

    # ==================== RATE LIMITING ====================
    RATE_LIMIT_RPS: float = float(os.getenv("RATE_LIMIT_RPS", 15))
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", 10))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", 300))

    # ==================== MONITORING ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", 9090))
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", 30))

    # ==================== ADVANCED ====================
    ENABLE_ADAPTIVE_PARSING: bool = os.getenv("ENABLE_ADAPTIVE_PARSING", "true").lower() == "true"
    ENABLE_ROBOTS_TXT: bool = os.getenv("ENABLE_ROBOTS_TXT", "false").lower() == "true"
    IMPERSONATE_BROWSER: str = os.getenv("IMPERSONATE_BROWSER", "chrome")
    USE_PROXIES: bool = os.getenv("USE_PROXIES", "false").lower() == "true"
    PROXY_LIST: str = os.getenv("PROXY_LIST", "")
    CHECKPOINT_DIR: Path = Path(os.getenv("CHECKPOINT_DIR", "./checkpoints"))
    
    # ==================== WORKERS (Multi-Worker) ====================
    WORKER_ID: int = int(os.getenv("WORKER_ID", 0))  # ID del worker (0 = single mode)
    NUM_WORKERS: int = int(os.getenv("NUM_WORKERS", 0))  # 0 = auto-detectar
    
    # ==================== ANTI-BLOCK ====================
    ENABLE_UA_ROTATION: bool = os.getenv("ENABLE_UA_ROTATION", "true").lower() == "true"
    ENABLE_FINGERPRINT_RANDOMIZATION: bool = os.getenv("ENABLE_FINGERPRINT_RANDOMIZATION", "true").lower() == "true"
    DELAY_MIN_MS: int = int(os.getenv("DELAY_MIN_MS", 100))  # Delay mínimo entre requests
    DELAY_MAX_MS: int = int(os.getenv("DELAY_MAX_MS", 500))  # Delay máximo entre requests
    BLOCK_DETECTION: bool = os.getenv("BLOCK_DETECTION", "true").lower() == "true"
    COOLDOWN_SECONDS: int = int(os.getenv("COOLDOWN_SECONDS", 60))  # Cooldown después de bloqueo

    @property
    def db_url(self) -> str:
        """Construcción de URL de conexión PostgreSQL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def proxies(self) -> list[str]:
        """Parsing de lista de proxies"""
        if not self.PROXY_LIST:
            return []
        return [p.strip() for p in self.PROXY_LIST.split(",") if p.strip()]

    def validate(self) -> None:
        """Validar configuración al startup"""
        errors = []

        if self.START_ID >= self.END_ID:
            errors.append("START_ID debe ser menor que END_ID")

        if self.CONCURRENCY < 1 or self.CONCURRENCY > 100:
            errors.append("CONCURRENCY debe estar entre 1 y 100")

        if self.BATCH_SIZE < 1 or self.BATCH_SIZE > 10000:
            errors.append("BATCH_SIZE debe estar entre 1 y 10000")

        if not self.DB_PASS or len(self.DB_PASS) < 3:
            errors.append("DB_PASS no puede estar vacía (¡cambiar en .env!)")

        if errors:
            raise ValueError("\n".join(f"❌ {e}" for e in errors))

    def __repr__(self) -> str:
        """Debug info sin mostrar credenciales"""
        return (
            f"<Config>\n"
            f"  DB: {self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}\n"
            f"  Range: {self.START_ID:,} → {self.END_ID:,}\n"
            f"  Concurrency: {self.CONCURRENCY}\n"
            f"  Batch: {self.BATCH_SIZE}\n"
            f"</Config>"
        )


# Instancia global
config = Config()
