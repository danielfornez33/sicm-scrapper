"""Configuración de pytest"""
import pytest
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_guia_html():
    """HTML de guía válido para tests"""
    return """
    <html><body>
    <tr><td><strong>Nro Guia:</strong></td><td>42022341</td></tr>
    <tr><td><strong>Estatus:</strong></td><td>APROBADA</td></tr>
    <tr><td><strong>Fecha de Emisión:</strong></td><td>2026-01-15</td></tr>
    <tr><td><strong>Unidades:</strong></td><td>100</td></tr>
    <tr><td><strong>Origen - Razón:</strong></td><td>Origen Test</td></tr>
    <tr><td><strong>Destino - Razón:</strong></td><td>Destino Test</td></tr>
    </body></html>
    """