"""
Capa de base de datos con asyncpg
Optimizado para VPS con pool management y bulk operations
"""


import asyncpg

from src.config import config
from src.logger import get_logger
from src.models import Guia

logger = get_logger(__name__)


class Database:
    """Manejo de conexiones y operaciones a PostgreSQL"""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Establecer conexión al pool de PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASS,
                min_size=config.DB_POOL_MIN,
                max_size=config.DB_POOL_MAX,
                max_queries=50000,  # Max queries before connection reset
                max_cached_statement_lifetime=300,
                max_cacheable_statement_size=15000,
                command_timeout=config.REQUEST_TIMEOUT,
                timeout=config.DB_POOL_TIMEOUT,
            )
            await self._create_tables()
            logger.info(
                "db_connected",
                host=config.DB_HOST,
                pool_min=config.DB_POOL_MIN,
                pool_max=config.DB_POOL_MAX,
            )
        except Exception as e:
            logger.error("db_connection_failed", error=str(e))
            raise

    async def _create_tables(self) -> None:
        """Crear tablas si no existen"""
        if not self.pool:
            raise RuntimeError("Pool no inicializado")

        async with self.pool.acquire() as conn:
            # Tabla de guías
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guias (
                    id_guia INTEGER PRIMARY KEY,
                    estatus TEXT NOT NULL,
                    fecha_emision TIMESTAMP,
                    fecha_vencimiento DATE,
                    bultos INTEGER,
                    renglones INTEGER,
                    unidades INTEGER NOT NULL DEFAULT 0,
                    origen_razon TEXT,
                    origen_rif TEXT,
                    origen_tipo TEXT,
                    origen_direccion TEXT,
                    origen_estado_ciudad TEXT,
                    destino_razon TEXT,
                    destino_rif TEXT,
                    destino_tipo TEXT,
                    destino_direccion TEXT,
                    destino_estado_ciudad TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )

            # Índices para optimización de queries
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_guias_estatus
                ON guias(estatus)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_guias_fecha_emision
                ON guias(fecha_emision)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_guias_destino_razon
                ON guias(destino_razon)
                """
            )

            # Tabla de productos
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guia_productos (
                    id SERIAL PRIMARY KEY,
                    id_guia INTEGER NOT NULL REFERENCES guias(id_guia) ON DELETE CASCADE,
                    producto TEXT NOT NULL,
                    lote TEXT,
                    cantidad INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )

            # Índices para productos
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_guia_productos_id_guia
                ON guia_productos(id_guia)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_guia_productos_producto
                ON guia_productos(producto)
                """
            )

            # Tabla de progreso para resumir scrapes
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS progress (
                    id SERIAL PRIMARY KEY,
                    last_id_processed INTEGER,
                    total_scraped INTEGER DEFAULT 0,
                    total_saved INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT NOW()
                )
                """
            )

            logger.info("db_tables_created")

    async def bulk_insert(self, guias: list[Guia]) -> tuple[int, int]:
        """
        Insertar lote de guías en una transacción
        Retorna: (total_inserted, total_skipped)
        """
        if not self.pool or not guias:
            return 0, 0

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                inserted = 0
                skipped = 0

                try:
                    # Preparar datos de guías
                    for guia in guias:
                        if not guia.is_valid():
                            skipped += 1
                            logger.warning(
                                "guia_validation_failed",
                                id_guia=guia.id_guia,
                                reason="cross_validation",
                            )
                            continue

                        try:
                            # Upsert guía (ON CONFLICT para evitar duplicados)
                            await conn.execute(
                                """
                                INSERT INTO guias (
                                    id_guia, estatus, fecha_emision, fecha_vencimiento,
                                    bultos, renglones, unidades,
                                    origen_razon, origen_rif, origen_tipo,
                                    origen_direccion, origen_estado_ciudad,
                                    destino_razon, destino_rif, destino_tipo,
                                    destino_direccion, destino_estado_ciudad
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                                ON CONFLICT (id_guia) DO UPDATE SET updated_at = NOW()
                                """,
                                guia.id_guia,
                                guia.estatus,
                                guia.fecha_emision,
                                guia.fecha_vencimiento,
                                guia.bultos,
                                guia.renglones,
                                guia.unidades,
                                guia.origen_razon,
                                guia.origen_rif,
                                guia.origen_tipo,
                                guia.origen_direccion,
                                guia.origen_estado_ciudad,
                                guia.destino_razon,
                                guia.destino_rif,
                                guia.destino_tipo,
                                guia.destino_direccion,
                                guia.destino_estado_ciudad,
                            )
                            inserted += 1

                            # Insertar productos (delete old ones first)
                            if guia.productos:
                                await conn.execute(
                                    "DELETE FROM guia_productos WHERE id_guia = $1",
                                    guia.id_guia,
                                )

                                prod_records = [
                                    (guia.id_guia, p.nombre, p.lote, p.cantidad)
                                    for p in guia.productos
                                ]

                                await conn.executemany(
                                    """
                                    INSERT INTO guia_productos (id_guia, producto, lote, cantidad)
                                    VALUES ($1, $2, $3, $4)
                                    """,
                                    prod_records,
                                )

                        except asyncpg.IntegrityError as e:
                            logger.warning(
                                "guia_integrity_error", id_guia=guia.id_guia, error=str(e)
                            )
                            skipped += 1
                        except Exception as e:
                            logger.error("guia_insert_error", id_guia=guia.id_guia, error=str(e))
                            skipped += 1

                    logger.info(
                        "batch_inserted",
                        inserted=inserted,
                        skipped=skipped,
                        total=len(guias),
                    )

                except Exception as e:
                    logger.error("bulk_insert_transaction_failed", error=str(e))
                    raise

        return inserted, skipped

    async def update_progress(self, last_id: int, saved: int, errors: int, total: int) -> None:
        """Actualizar progreso del scrape"""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM progress;
                INSERT INTO progress (last_id_processed, total_saved, total_errors, total_scraped)
                VALUES ($1, $2, $3, $4)
                """,
                last_id,
                saved,
                errors,
                total,
            )

    async def get_progress(self) -> dict | None:
        """Obtener último progreso guardado"""
        if not self.pool:
            return None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM progress ORDER BY id DESC LIMIT 1")
            if row:
                return dict(row)
        return None

    async def get_stats(self) -> dict:
        """Obtener estadísticas de la BD"""
        if not self.pool:
            return {}

        async with self.pool.acquire() as conn:
            guias = await conn.fetchval("SELECT COUNT(*) FROM guias")
            productos = await conn.fetchval("SELECT COUNT(*) FROM guia_productos")
            total_unidades = await conn.fetchval("SELECT SUM(unidades) FROM guias")
            unique_destinos = await conn.fetchval(
                "SELECT COUNT(DISTINCT destino_razon) FROM guias WHERE destino_razon IS NOT NULL"
            )

        return {
            "total_guias": guias or 0,
            "total_productos": productos or 0,
            "total_unidades": total_unidades or 0,
            "unique_destinos": unique_destinos or 0,
        }

    async def close(self) -> None:
        """Cerrar conexiones"""
        if self.pool:
            await self.pool.close()
            logger.info("db_closed")
