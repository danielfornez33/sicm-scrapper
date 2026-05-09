"""Tests del parser - Validación de extracción HTML"""
import pytest
from src.parser import parse_guia_page, _extract_field, _parse_productos


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


class TestExtractField:
    """Tests para función _extract_field"""

    def test_extract_nro_guia(self):
        result = _extract_field(VALID_GUIDE_HTML, "Nro Guia")
        assert result == "42022341"

    def test_extract_estatus(self):
        result = _extract_field(VALID_GUIDE_HTML, "Estatus")
        assert result == "APROBADA"

    def test_extract_with_spaces(self):
        html = "<td><strong>Fecha de Emisión:</strong></td><td>2026-01-15 10:30:00</td>"
        result = _extract_field(html, "Fecha de Emisión")
        assert result == "2026-01-15 10:30:00"

    def test_field_not_found(self):
        result = _extract_field(VALID_GUIDE_HTML, "Campo Inexistente")
        assert result is None


class TestParseGuiaPage:
    """Tests para función parse_guia_page"""

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


class TestParseProductos:
    """Tests para función _parse_productos"""

    def test_parse_productos_with_selector(self):
        from scrapling.parser import Selector
        sel = Selector(VALID_GUIDE_HTML)
        productos = _parse_productos(sel)
        
        assert len(productos) == 2
        assert productos[0].nombre == "PARACETAMOL 500MG"
        assert productos[0].cantidad == 50
        assert productos[1].nombre == "IBUPROFENO 400MG"
        assert productos[1].cantidad == 100


class TestParseProductosRegex:
    """Tests para _parse_productos con HTML directo"""

    def test_parse_productos_from_html(self):
        from scrapling.parser import Selector
        html = """
        <table>
            <tr><td>Producto A</td><td>L001</td><td>10</td></tr>
            <tr><td>Producto B</td><td>L002</td><td>20</td></tr>
        </table>
        """
        sel = Selector(html)
        productos = _parse_productos(sel)
        
        assert len(productos) == 2
        assert productos[0].nombre == "PRODUCTO A"
        assert productos[1].nombre == "PRODUCTO B"