"""Tests del parser - Validación simple sin dependencias externas"""
import pytest


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


class TestParserBasic:
    """Tests básicos del parser sin dependencias de Scrapling"""

    def test_parser_module_imports(self):
        """Verify parser module can be imported"""
        from src import parser
        assert hasattr(parser, 'parse_guia_page')

    def test_parse_guia_page_invalid_id(self):
        """Test que falla con ID incorrecto"""
        from src.parser import parse_guia_page
        # El HTML tiene ID 42022341, probamos con otro
        guia = parse_guia_page(VALID_GUIDE_HTML, 99999999)
        assert guia is None

    def test_parse_invalid_status(self):
        """Test que rechaza estatus inválido"""
        from src.parser import parse_guia_page
        guia = parse_guia_page(INVALID_STATUS_HTML, 42022341)
        assert guia is None

    def test_parse_outlier_unidades(self):
        """Test que rechaza outliers de unidades"""
        from src.parser import parse_guia_page
        guia = parse_guia_page(OUTLIER_HTML, 42022341)
        assert guia is None


class TestModelsBasic:
    """Tests básicos de modelos"""

    def test_guia_model_imports(self):
        """Verify models can be imported"""
        from src import models
        assert hasattr(models, 'Guia')
        assert hasattr(models, 'Producto')

    def test_producto_model_valid(self):
        """Test modelo Producto válido"""
        from src.models import Producto
        p = Producto(nombre="Test", cantidad=100)
        assert p.nombre == "TEST"
        assert p.cantidad == 100

    def test_guia_model_valid(self):
        """Test modelo Guia válido"""
        from src.models import Guia
        g = Guia(
            id_guia=42022341,
            estatus="APROBADA",
            unidades=100
        )
        assert g.id_guia == 42022341
        assert g.estatus == "APROBADA"

    def test_guia_estatus_rejected(self):
        """Test que estatus inválido es rechazado"""
        from src.models import Guia
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Guia(id_guia=42022341, estatus="PENDIENTE", unidades=100)


class TestConfigBasic:
    """Tests básicos de configuración"""

    def test_config_imports(self):
        """Verify config can be imported"""
        from src import config
        assert hasattr(config, 'config')

    def test_config_values(self):
        """Verify config has expected attributes"""
        from src.config import config
        assert hasattr(config, 'START_ID')
        assert hasattr(config, 'END_ID')
        assert hasattr(config, 'CONCURRENCY')

    def test_config_has_worker_id(self):
        """Verify worker ID config exists"""
        from src.config import config
        # Esta variable debería existir ahora
        assert hasattr(config, 'WORKER_ID')

    def test_config_has_anti_block_options(self):
        """Verify anti-block options exist"""
        from src.config import config
        assert hasattr(config, 'DELAY_MIN_MS')
        assert hasattr(config, 'DELAY_MAX_MS')
        assert hasattr(config, 'ENABLE_UA_ROTATION')


class TestFingerprintModule:
    """Tests del módulo fingerprint"""

    def test_fingerprint_imports(self):
        """Verify fingerprint module can be imported"""
        from src import fingerprint
        assert hasattr(fingerprint, 'FingerprintManager')

    def test_fingerprint_basic(self):
        """Test básico del fingerprint"""
        from src.fingerprint import FingerprintManager
        fp = FingerprintManager(worker_id=1)
        headers = fp.get_headers()
        assert 'User-Agent' in headers
        assert 'Accept' in headers
        assert headers['User-Agent'] != ""


class TestAntiBlockModule:
    """Tests del módulo anti-block"""

    def test_anti_block_imports(self):
        """Verify anti-block module can be imported"""
        from src import anti_block
        assert hasattr(anti_block, 'AntiBlockDetector')
        assert hasattr(anti_block, 'BlockType')

    def test_block_type_enum(self):
        """Test BlockType enum"""
        from src.anti_block import BlockType
        assert BlockType.NONE.value == "none"
        assert BlockType.RATE_LIMIT.value == "rate_limit"
        assert BlockType.FORBIDDEN.value == "forbidden"

    def test_detector_basic(self):
        """Test básico del detector"""
        from src.anti_block import AntiBlockDetector
        detector = AntiBlockDetector(worker_id=1)
        assert detector.worker_id == 1
        assert detector.status.is_blocked == False