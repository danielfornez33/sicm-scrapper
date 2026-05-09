"""Tests para modelos Pydantic"""
import pytest
from pydantic import ValidationError
from src.models import Producto, Guia, ScrapingStats


class TestProducto:
    """Tests para modelo Producto"""

    def test_producto_valido(self):
        p = Producto(nombre="Paracetamol", lote="L001", cantidad=100)
        assert p.nombre == "PARACETAMOL"
        assert p.lote == "L001"
        assert p.cantidad == 100

    def test_producto_cantidad_cero(self):
        with pytest.raises(ValidationError):
            Producto(nombre="Test", cantidad=0)

    def test_producto_cantidad_negativa(self):
        with pytest.raises(ValidationError):
            Producto(nombre="Test", cantidad=-10)

    def test_producto_cantidad_excesiva(self):
        with pytest.raises(ValidationError):
            Producto(nombre="Test", cantidad=2_000_000)

    def test_producto_nombre_invalido(self):
        with pytest.raises(ValidationError):
            Producto(nombre="NO ESTA REGISTRADO EL PRODUCTO", cantidad=10)

    def test_producto_nombre_vacio(self):
        with pytest.raises(ValidationError):
            Producto(nombre="   ", cantidad=10)


class TestGuia:
    """Tests para modelo Guia"""

    def test_guia_valida(self):
        g = Guia(
            id_guia=42022341,
            estatus="APROBADA",
            unidades=100,
            productos=[Producto(nombre="Test", cantidad=10)]
        )
        assert g.id_guia == 42022341
        assert g.estatus == "APROBADA"

    def test_guia_estatus_invalido(self):
        with pytest.raises(ValidationError):
            Guia(id_guia=42022341, estatus="PENDIENTE", unidades=100)

    def test_guia_unidades_excesivas(self):
        with pytest.raises(ValidationError):
            Guia(id_guia=42022341, estatus="APROBADA", unidades=2_000_000)

    def test_guia_sin_productos(self):
        g = Guia(id_guia=42022341, estatus="Abierta", unidades=50)
        assert g.productos == []

    def test_guia_is_valid(self):
        g = Guia(
            id_guia=42022341,
            estatus="APROBADA",
            unidades=100,
            productos=[Producto(nombre="Test", cantidad=100)]
        )
        assert g.is_valid() is True


class TestScrapingStats:
    """Tests para modelo ScrapingStats"""

    def test_stats_inicial(self):
        s = ScrapingStats()
        assert s.total_processed == 0
        assert s.total_saved == 0
        assert s.success_rate == 0.0

    def test_success_rate(self):
        s = ScrapingStats()
        s.total_processed = 100
        s.total_saved = 90
        assert s.success_rate == 90.0

    def test_formatted_eta(self):
        s = ScrapingStats()
        assert s.formatted_eta == "---"
        
        s.estimated_eta_seconds = 3661  # 1h 1m
        assert s.formatted_eta == "1h 1m"