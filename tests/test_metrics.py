"""Tests para el sistema de métricas Prometheus"""
import pytest
from src.metrics import MetricsCollector, metrics, get_metrics_summary


class TestMetricsCollector:
    """Tests para el colector de métricas"""

    def test_singleton(self):
        """Test que MetricsCollector es singleton"""
        m1 = MetricsCollector()
        m2 = MetricsCollector()
        assert m1 is m2

    def test_initial_state(self):
        """Test estado inicial"""
        m = MetricsCollector()
        assert m._initialized is True

    def test_uptime_positive(self):
        """Test que uptime es positivo"""
        m = MetricsCollector()
        assert m.uptime_seconds > 0

    def test_record_request_success(self):
        """Test registrar request exitoso"""
        initial_count = metrics.uptime_seconds  # Dummy check
        metrics.record_request("success")
        # Just verify no exception

    def test_record_error(self):
        """Test registrar error"""
        metrics.record_error("http")
        # Just verify no exception

    def test_record_batch_duration(self):
        """Test registrar duración de batch"""
        metrics.record_batch_duration(0.5)

    def test_set_current_id(self):
        """Test actualizar ID actual"""
        metrics.set_current_id(42022341)

    def test_set_batch_items(self):
        """Test actualizar items en batch"""
        metrics.set_batch_items(100)


class TestGetMetricsSummary:
    """Tests para función get_metrics_summary"""

    def test_returns_dict(self):
        """Test que retorna diccionario"""
        result = get_metrics_summary()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Test que tiene las claves requeridas"""
        result = get_metrics_summary()
        assert "uptime_seconds" in result
        assert "requests_total" in result
        assert "errors_total" in result