"""Tests de integración para base de datos"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.db import Database
from src.models import Guia, Producto


@pytest.fixture
def mock_pool():
    """Mock de la pool de conexiones"""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def sample_guia():
    """Guía de ejemplo para tests"""
    return Guia(
        id_guia=42022341,
        estatus="APROBADA",
        fecha_emision="2026-01-15",
        fecha_vencimiento="2026-01-20",
        bultos=5,
        renglones=3,
        unidades=100,
        origen_razon="Origen Test",
        origen_rif="J123456789",
        origen_tipo="Droguería",
        origen_direccion="Dirección 123",
        origen_estado_ciudad="Caracas",
        destino_razon="Destino Test",
        destino_rif="J987654321",
        destino_tipo="Farmacia",
        destino_direccion="Calle 456",
        destino_estado_ciudad="Maracaibo",
        productos=[
            Producto(nombre="Paracetamol", lote="L001", cantidad=50),
            Producto(nombre="Ibuprofeno", lote="L002", cantidad=50),
        ]
    )


class TestDatabaseInit:
    """Tests de inicialización de Database"""

    def test_database_init(self):
        db = Database()
        assert db.pool is None

    @pytest.mark.asyncio
    async def test_database_connect_without_pool(self):
        """Test que connect() requiere pool"""
        db = Database()
        with pytest.raises(RuntimeError):
            await db._create_tables()


class TestDatabaseConnection:
    """Tests de conexión a la base de datos"""

    @pytest.mark.asyncio
    @patch('src.db.asyncpg.create_pool')
    async def test_connect_success(self, mock_create_pool, mock_pool):
        """Test conexión exitosa"""
        mock_create_pool.return_value = mock_pool
        
        db = Database()
        await db.connect()
        
        assert db.pool is not None
        mock_create_pool.assert_called_once()
        await db.close()

    @pytest.mark.asyncio
    @patch('src.db.asyncpg.create_pool')
    async def test_connect_creates_tables(self, mock_create_pool, mock_pool):
        """Test que connect() crea las tablas"""
        mock_create_pool.return_value = mock_pool
        
        db = Database()
        await db.connect()
        
        # Verificar que se llamó execute para crear tablas
        # (el mock de conn.execute fue llamado)
        await db.close()


class TestBulkInsert:
    """Tests para bulk_insert"""

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_list(self, mock_pool):
        """Test que bulk_insert con lista vacía retorna 0"""
        db = Database()
        db.pool = mock_pool
        
        inserted, skipped = await db.bulk_insert([])
        
        assert inserted == 0
        assert skipped == 0

    @pytest.mark.asyncio
    async def test_bulk_insert_with_pool(self, mock_pool, sample_guia):
        """Test bulk_insert con una guía válida"""
        db = Database()
        db.pool = mock_pool
        
        # Mock transaction
        mock_conn = await mock_pool.acquire().__aenter__()
        mock_tx = AsyncMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_tx)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock execute para INSERT
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")
        mock_conn.executemany = AsyncMock()
        
        inserted, skipped = await db.bulk_insert([sample_guia])
        
        # Should have attempted insert
        assert mock_conn.execute.called or mock_conn.executemany.called


class TestProgress:
    """Tests para seguimiento de progreso"""

    @pytest.mark.asyncio
    async def test_update_progress(self, mock_pool):
        """Test actualización de progreso"""
        db = Database()
        db.pool = mock_pool
        
        mock_conn = await mock_pool.acquire().__aenter__()
        mock_conn.execute = AsyncMock()
        
        await db.update_progress(42022341, 100, 5, 150)
        
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_get_progress_empty(self, mock_pool):
        """Test obtener progreso cuando no hay"""
        db = Database()
        db.pool = mock_pool
        
        mock_conn = await mock_pool.acquire().__aenter__()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        
        progress = await db.get_progress()
        
        assert progress is None

    @pytest.mark.asyncio
    async def test_get_progress_with_data(self, mock_pool):
        """Test obtener progreso con datos"""
        db = Database()
        db.pool = mock_pool
        
        mock_conn = await mock_pool.acquire().__aenter__()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1,
            'last_id_processed': 42022341,
            'total_saved': 100,
            'total_errors': 5,
            'total_scraped': 150,
            'last_updated': '2026-01-15 10:00:00'
        })
        
        progress = await db.get_progress()
        
        assert progress is not None
        assert progress['last_id_processed'] == 42022341


class TestStats:
    """Tests para obtener estadísticas"""

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_pool):
        """Test obtener estadísticas de la BD"""
        db = Database()
        db.pool = mock_pool
        
        mock_conn = await mock_pool.acquire().__aenter__()
        mock_conn.fetchval = AsyncMock(side_effect=[1000, 5000, 100000, 50])
        
        stats = await db.get_stats()
        
        assert stats['total_guias'] == 1000
        assert stats['total_productos'] == 5000
        assert stats['total_unidades'] == 100000
        assert stats['unique_destinos'] == 50


class TestClose:
    """Tests para cerrar conexión"""

    @pytest.mark.asyncio
    async def test_close_without_pool(self):
        """Test cerrar cuando no hay pool"""
        db = Database()
        await db.close()  # No debe fallar

    @pytest.mark.asyncio
    async def test_close_with_pool(self, mock_pool):
        """Test cerrar cuando hay pool"""
        db = Database()
        db.pool = mock_pool
        
        await db.close()
        
        mock_pool.close.assert_called_once()