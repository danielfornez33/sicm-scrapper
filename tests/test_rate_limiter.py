"""Tests para el rate limiter adaptativo"""
import pytest
import asyncio
import time
from src.rate_limiter import AdaptiveRateLimiter, RateLimitConfig


class TestAdaptiveRateLimiter:
    """Tests para el rate limiter adaptativo"""

    @pytest.fixture
    def limiter(self):
        """Fixture de rate limiter"""
        config = RateLimitConfig(
            min_delay=0.01,
            max_delay=0.5,
            initial_delay=0.01,
            success_threshold=10,
            error_threshold=3,
            increase_factor=2.0,
            decrease_factor=0.5
        )
        return AdaptiveRateLimiter(config)

    def test_initial_delay(self, limiter):
        """Test delay inicial"""
        assert limiter.current_delay == 0.01

    def test_on_success_reduces_delay(self, limiter):
        """Test que éxitos reducen el delay"""
        initial = limiter.current_delay
        
        # Simular muchos éxitos
        for _ in range(15):  # Más que success_threshold
            limiter.on_success()
        
        # Delay debería haber disminuido
        assert limiter.current_delay < initial

    def test_on_error_increases_delay(self, limiter):
        """Test que errores aumentan el delay"""
        initial = limiter.current_delay
        
        # Simular errores
        for _ in range(5):
            limiter.on_error(500)
        
        # Delay debería haber aumentado
        assert limiter.current_delay > initial

    def test_rate_limit_429_doubles_delay(self, limiter):
        """Test que 429 dobla el delay"""
        initial = limiter.current_delay
        
        limiter.on_error(429)
        
        # Delay debería duplicarse
        assert limiter.current_delay == initial * 2

    def test_rate_limit_max_delay_cap(self, limiter):
        """Test que el delay tiene un máximo"""
        # Forzar muchos errores 429
        for _ in range(20):
            limiter.on_error(429)
        
        # No debería pasar del máximo
        assert limiter.current_delay <= limiter.config.max_delay

    def test_reset(self, limiter):
        """Test que reset funciona"""
        # Modificar estado
        limiter.current_delay = 0.5
        limiter.success_count = 100
        limiter.error_count = 50
        
        # Resetear
        limiter.reset()
        
        # Verificar valores iniciales
        assert limiter.current_delay == 0.01
        assert limiter.success_count == 0
        assert limiter.error_count == 0

    def test_stats(self, limiter):
        """Test que stats retorna información correcta"""
        limiter.on_success()
        limiter.on_error(500)
        
        stats = limiter.stats
        
        assert 'current_delay' in stats
        assert 'total_requests' in stats
        assert stats['total_requests'] == 2
        assert stats['consecutive_success'] == 1
        assert stats['consecutive_errors'] == 1


@pytest.mark.asyncio
class TestRateLimiterAsync:
    """Tests asíncronos del rate limiter"""

    @pytest.fixture
    async def limiter(self):
        config = RateLimitConfig(min_delay=0.01, max_delay=0.5, initial_delay=0.01)
        return AdaptiveRateLimiter(config)

    @pytest.mark.asyncio
    async def test_wait_if_needed_waits(self, limiter):
        """Test que wait_if_needed espera el tiempo apropiado"""
        # Resetear last_request_time
        limiter.last_request_time = 0
        
        start = time.time()
        await limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Debería haber esperado al menos el delay inicial
        assert elapsed >= 0.005  # Un poco menos de 0.01 por overhead

    @pytest.mark.asyncio
    async def test_wait_if_needed_no_wait_when_enough_time(self, limiter):
        """Test que no espera si ya pasó el tiempo"""
        # Configurar último request reciente
        limiter.last_request_time = time.time() - 1  # 1 segundo atrás
        
        start = time.time()
        await limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # No debería esperar casi nada
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limit_wait_when_limited(self, limiter):
        """Test que espera cuando está rate limited"""
        # Simular rate limit
        limiter.rate_limit_until = time.time() + 0.1  # 100ms en el futuro
        
        start = time.time()
        await limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Debería esperar al menos 100ms
        assert elapsed >= 0.09


class TestRateLimitConfig:
    """Tests para RateLimitConfig"""

    def test_default_config(self):
        """Test valores por defecto"""
        config = RateLimitConfig()
        
        assert config.min_delay == 0.05
        assert config.max_delay == 2.0
        assert config.initial_delay == 0.05
        assert config.success_threshold == 100
        assert config.error_threshold == 5
        assert config.increase_factor == 1.5
        assert config.decrease_factor == 0.9

    def test_custom_config(self):
        """Test configuración personalizada"""
        config = RateLimitConfig(
            min_delay=0.1,
            max_delay=5.0,
            initial_delay=0.2,
            success_threshold=50,
            error_threshold=10,
            increase_factor=2.0,
            decrease_factor=0.8
        )
        
        assert config.min_delay == 0.1
        assert config.max_delay == 5.0
        assert config.initial_delay == 0.2
        assert config.success_threshold == 50
        assert config.error_threshold == 10