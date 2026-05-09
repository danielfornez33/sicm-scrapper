"""
Rate Limiting Inteligente Adaptativo
Ajusta la velocidad automáticamente basándose en respuestas del servidor
"""
import asyncio
import time
from dataclasses import dataclass

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuración del rate limiter"""
    min_delay: float = 0.05   # 50ms mínimo
    max_delay: float = 2.0    # 2s máximo
    initial_delay: float = 0.05
    success_threshold: int = 100  # Éxitos consecutivos para reducir delay
    error_threshold: int = 5     # Errores consecutivos para aumentar delay
    increase_factor: float = 1.5  # Factor de aumento
    decrease_factor: float = 0.9  # Factor de disminución


class AdaptiveRateLimiter:
    """
    Rate limiter adaptativo que ajusta la velocidad automáticamente

    Comportamiento:
    - Reduce delay si hay muchos éxitos consecutivos
    - Aumenta delay si hay errores o rate limiting
    - Mantiene un balance entre velocidad y estabilidad
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self.current_delay = self.config.initial_delay

        # Contadores
        self.success_count = 0
        self.error_count = 0
        self.total_requests = 0
        self.total_delays = 0

        # Estado
        self.last_request_time = 0.0
        self.is_rate_limited = False
        self.rate_limit_until: float | None = None

    async def wait_if_needed(self) -> None:
        """Esperar el tiempo apropiado antes de hacer request"""
        # Verificar si estamos en rate limit
        if self.rate_limit_until and time.time() < self.rate_limit_until:
            wait_time = self.rate_limit_until - time.time()
            logger.info("rate_limited_waiting", wait_seconds=wait_time)
            await asyncio.sleep(wait_time)
            return

        # Calcular tiempo desde último request
        now = time.time()
        elapsed = now - self.last_request_time

        if elapsed < self.current_delay:
            wait_time = self.current_delay - elapsed
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    def on_success(self, status_code: int = 200) -> None:
        """Registrar éxito del request"""
        self.total_requests += 1
        self.success_count += 1
        self.error_count = 0  # Reset errores

        # Reducir delay si hay muchos éxitos consecutivos
        if self.success_count >= self.config.success_threshold:
            if self.current_delay > self.config.min_delay:
                new_delay = max(
                    self.config.min_delay,
                    self.current_delay * self.config.decrease_factor
                )
                if new_delay != self.current_delay:
                    logger.info(
                        "rate_limit_decreased",
                        old_delay=self.current_delay,
                        new_delay=new_delay,
                        consecutive_success=self.success_count
                    )
                    self.current_delay = new_delay
            self.success_count = 0

    def on_error(self, status_code: int, error_type: str = "unknown") -> None:
        """Registrar error del request"""
        self.total_requests += 1
        self.error_count += 1
        self.success_count = 0  # Reset éxitos

        # Aumentar delay si hay muchos errores consecutivos
        if status_code == 429:  # Too Many Requests
            self._handle_rate_limit()
        elif status_code >= 500:  # Server error
            self._handle_server_error()
        elif self.error_count >= self.config.error_threshold:
            self._handle_many_errors()

    def _handle_rate_limit(self) -> None:
        """Manejar rate limit (429)"""
        self.is_rate_limited = True
        # Aumentar delay significativamente
        old_delay = self.current_delay
        self.current_delay = min(
            self.config.max_delay,
            self.current_delay * 2
        )

        # Establecer cooldown
        self.rate_limit_until = time.time() + self.current_delay

        logger.warning(
            "rate_limit_detected",
            old_delay=old_delay,
            new_delay=self.current_delay,
            cooldown_seconds=self.current_delay
        )

        self.error_count = 0

    def _handle_server_error(self) -> None:
        """Manejar errores 5xx"""
        if self.current_delay < 1.0:  # Max 1s para server errors
            old_delay = self.current_delay
            self.current_delay = min(1.0, self.current_delay * 1.5)

            logger.warning(
                "server_error_increasing_delay",
                old_delay=old_delay,
                new_delay=self.current_delay,
                status_code=503
            )

    def _handle_many_errors(self) -> None:
        """Manejar muchos errores consecutivos"""
        if self.current_delay < self.config.max_delay:
            old_delay = self.current_delay
            self.current_delay = min(
                self.config.max_delay,
                self.current_delay * self.config.increase_factor
            )

            logger.warning(
                "many_errors_increasing_delay",
                old_delay=old_delay,
                new_delay=self.current_delay,
                consecutive_errors=self.error_count
            )

        self.error_count = 0

    @property
    def stats(self) -> dict:
        """Obtener estadísticas del rate limiter"""
        return {
            "current_delay": self.current_delay,
            "total_requests": self.total_requests,
            "consecutive_success": self.success_count,
            "consecutive_errors": self.error_count,
            "is_rate_limited": self.is_rate_limited,
            "rate_limit_until": self.rate_limit_until,
        }

    def reset(self) -> None:
        """Resetear el rate limiter"""
        self.current_delay = self.config.initial_delay
        self.success_count = 0
        self.error_count = 0
        self.is_rate_limited = False
        self.rate_limit_until = None
        logger.info("rate_limiter_reset")


class RateLimitMiddleware:
    """Middleware para integrar rate limiter con el spider"""

    def __init__(self, rate_limiter: AdaptiveRateLimiter):
        self.rate_limiter = rate_limiter

    async def before_request(self):
        """Called before each request"""
        await self.rate_limiter.wait_if_needed()

    def after_request(self, status_code: int, success: bool):
        """Called after each request"""
        if success:
            self.rate_limiter.on_success(status_code)
        else:
            self.rate_limiter.on_error(status_code)
