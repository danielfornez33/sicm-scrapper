"""
Métricas Prometheus para monitoreo del scraper
"""
import threading
import time

from prometheus_client import Counter, Gauge, Histogram, Info

# Contadores
REQUESTS_TOTAL = Counter(
    'scraper_requests_total',
    'Total de requests procesados',
    ['status']  # success, error, skipped
)

BATCH_OPERATIONS = Counter(
    'scraper_batch_operations_total',
    'Operaciones de batch',
    ['operation']  # insert, skip, flush
)

ERRORS_TOTAL = Counter(
    'scraper_errors_total',
    'Total de errores',
    ['type']  # http, parse, db
)

# Histogramas
BATCH_DURATION = Histogram(
    'scraper_batch_duration_seconds',
    'Tiempo de operación de batch',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

REQUEST_DURATION = Histogram(
    'scraper_request_duration_seconds',
    'Tiempo por request individual',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Gauges
ITEMS_IN_BATCH = Gauge(
    'scraper_batch_items',
    'Items actualmente en batch'
)

CURRENT_ID = Gauge(
    'scraper_current_id',
    'ID actual siendo procesado'
)

RATE_LIMIT_DELAY = Gauge(
    'scraper_rate_limit_delay_seconds',
    'Delay actual del rate limiter'
)

# Info
SCRAPER_INFO = Info('scraper', 'SICM Scraper information')


class MetricsCollector:
    """Coleccionador de métricas singleton"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.start_time = time.time()
        SCRAPER_INFO.info({
            'version': '2.0.0',
            'framework': 'scrapling'
        })

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time

    def record_request(self, status: str):
        """Registrar request completado"""
        REQUESTS_TOTAL.labels(status=status).inc()

    def record_batch_operation(self, operation: str):
        """Registrar operación de batch"""
        BATCH_OPERATIONS.labels(operation=operation).inc()

    def record_error(self, error_type: str):
        """Registrar error"""
        ERRORS_TOTAL.labels(type=error_type).inc()

    def record_batch_duration(self, seconds: float):
        """Registrar duración de batch"""
        BATCH_DURATION.observe(seconds)

    def record_request_duration(self, seconds: float):
        """Registrar duración de request"""
        REQUEST_DURATION.observe(seconds)

    def set_batch_items(self, count: int):
        """Actualizar gauge de items en batch"""
        ITEMS_IN_BATCH.set(count)

    def set_current_id(self, id_guia: int):
        """Actualizar gauge de ID actual"""
        CURRENT_ID.set(id_guia)

    def set_rate_limit_delay(self, seconds: float):
        """Actualizar delay del rate limiter"""
        RATE_LIMIT_DELAY.set(seconds)


# Instancia global
metrics = MetricsCollector()


def get_metrics_summary() -> dict:
    """Obtener resumen de métricas"""
    return {
        "uptime_seconds": metrics.uptime_seconds,
        "requests_total": REQUESTS_TOTAL.labels(status="success")._value.get() + REQUESTS_TOTAL.labels(status="error")._value.get(),
        "requests_success": REQUESTS_TOTAL.labels(status="success")._value.get(),
        "requests_error": REQUESTS_TOTAL.labels(status="error")._value.get(),
        "errors_total": ERRORS_TOTAL.labels(type="http")._value.get() + ERRORS_TOTAL.labels(type="parse")._value.get() + ERRORS_TOTAL.labels(type="db")._value.get(),
        "errors_http": ERRORS_TOTAL.labels(type="http")._value.get(),
        "errors_parse": ERRORS_TOTAL.labels(type="parse")._value.get(),
        "errors_db": ERRORS_TOTAL.labels(type="db")._value.get(),
    }
