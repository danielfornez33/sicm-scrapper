"""Tests del parser - Validación con Scrapling Selector"""
import pytest
from scrapling.parser import Selector
from src.parser import parse_guia_page, _extract_xpath, _parse_productos


# HTML de prueba válido
VALID_GUIDE_HTML = """
<html>
<body>
<table>
<tr><td><strong>Nro Guia:</strong></td><td>42022341</td></tr>
<tr><td><strong>Estatus:</strong></td><td>APROBADA</td></tr>
<tr><td><strong>Fecha de Emisión:</strong></td><td>2026-01-15 10:30:00</td></tr>
<tr><td><strong>Fecha de Vencimiento:</strong></td><td>2026-01-20</td></tr>
<tr><td><strong>Bultos:</strong></td><td>5</td></tr>
<tr><td><strong>Renglones:</strong></td><td>3</td></tr>
<tr><td><strong>Unidades:</strong></td><td>150</td></tr>
<tr><td><strong>Origen - Razón:</strong></td><td>Distribuidora Central</td></tr>
<tr><td><strong>Origen - RIF:</strong></td><td>J123456789</td></tr>
<tr><td><strong>Origen - Tipo:</strong></td><td>Droguería</td></tr>
<tr><td><strong>Origen - Dirección:</strong></td><td>Av. Principal 123</td></tr>
<tr><td><strong>Origen - Estado/Ciudad:</strong></td><td>Caracas</td></tr>
<tr><td><strong>Destino - Razón:</strong></td><td>Farmacia Popular</td></tr>
<tr><td><strong>Destino - RIF:</strong></td><td>J987654321</td></tr>
<tr><td><strong>Destino - Tipo:</strong></td><td>Farmacias Comerciales</td></tr>
<tr><td><strong>Destino - Dirección:</strong></td><td>Calle Comercio 456</td></tr>
<tr><td><strong>Destino - Estado/Ciudad:</strong></td><td>Maracaibo</td></tr>
</table>
<table class="productos">
<tr><td>Paracetamol 500mg</td><td>L2024-001</td><td>50</td></tr>
<tr><td>Ibuprofeno 400mg</td><td>L2024-002</td><td>100</td></tr>
</table>
</body>
</html>
"""


INVALID_STATUS_HTML = """
<html><body>
<tr><td><strong>Nro Guia:</strong></td><td>42022341</td></tr>
<tr><td><strong>Estatus:</strong></td><td>PENDIENTE</td></tr>
<tr><td><strong>Unidades:</strong></td><td>100</td></tr>
</body></html>
"""


OUTLIER_HTML = """
<html><body>
<tr><td><strong>Nro Guia:</strong></td><td>42022341</td></tr>
<tr><td><strong>Estatus:</strong></td><td>APROBADA</td></tr>
<tr><td><strong>Unidades:</strong></td><td>2000000</td></tr>
</body></html>
"""


class TestExtractXPath:
    """Tests para función _extract_xpath con Scrapling Selector"""

    def test_extract_nro_guia(self):
        sel = Selector(VALID_GUIDE_HTML)
        result = _extract_xpath(sel, "Nro Guia")
        assert result == "42022341"

    def test_extract_estatus(self):
        sel = Selector(VALID_GUIDE_HTML)
        result = _extract_xpath(sel, "Estatus")
        assert result == "APROBADA"

    def test_extract_with_spaces(self):
        sel = Selector(VALID_GUIDE_HTML)
        result = _extract_xpath(sel, "Fecha de Emisión")
        assert result == "2026-01-15 10:30:00"

    def test_field_not_found(self):
        sel = Selector(VALID_GUIDE_HTML)
        result = _extract_xpath(sel, "Campo Inexistente")
        assert result is None


class TestParseGuiaPage:
    """Tests para función parse_guia_page con Scrapling Selector"""

    def test_parse_valid_guia(self):
        guia = parse_guia_page(VALID_GUIDE_HTML, 42022341)
        
        assert guia is not None
        assert guia.id_guia == 42022341
        assert guia.estatus == "APROBADA"
        assert guia.unidades == 150
        assert guia.bultos == 5
        assert guia.renglones == 3
        assert guia.origen_razon == "Distribuidora Central"
        assert guia.destino_razon == "Farmacia Popular"
        assert len(guia.productos) == 2

    def test_parse_invalid_id(self):
        guia = parse_guia_page(VALID_GUIDE_HTML, 99999999)
        assert guia is None

    def test_parse_invalid_status(self):
        guia = parse_guia_page(INVALID_STATUS_HTML, 42022341)
        assert guia is None

    def test_parse_outlier_unidades(self):
        guia = parse_guia_page(OUTLIER_HTML, 42022341)
        assert guia is None

    def test_parse_empty_html(self):
        guia = parse_guia_page("", 42022341)
        assert guia is None

    def test_parse_with_extra_spaces(self):
        html = """
        <html><body>
        <tr><td><strong>Nro Guia:</strong></td><td>   42022341   </td></tr>
        <tr><td><strong>Estatus:</strong></td><td>   APROBADA   </td></tr>
        <tr><td><strong>Unidades:</strong></td><td>100</td></tr>
        </body></html>
        """
        guia = parse_guia_page(html, 42022341)
        assert guia is not None
        assert guia.estatus == "APROBADA"


class TestParseProductos:
    """Tests para función _parse_productos con Scrapling Selector"""

    def test_parse_productos_basic(self):
        sel = Selector(VALID_GUIDE_HTML)
        productos = _parse_productos(sel)
        
        assert len(productos) == 2
        assert productos[0].nombre == "PARACETAMOL 500MG"
        assert productos[0].cantidad == 50
        assert productos[1].nombre == "IBUPROFENO 400MG"
        assert productos[1].cantidad == 100

    def test_parse_productos_with_comma_decimal(self):
        html = """
        <table class="productos">
            <tr><td>Producto A</td><td>L001</td><td>1,500</td></tr>
            <tr><td>Producto B</td><td>L002</td><td>2.000</td></tr>
        </table>
        """
        sel = Selector(html)
        productos = _parse_productos(sel)
        
        # Should handle both comma and dot as thousand separators
        assert len(productos) >= 1