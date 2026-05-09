"""
Spider principal basado en Scrapling
Soporta pause/resume, rate limiting y monitoreo en tiempo real
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time
from pathlib import Path

from scrapling.spiders import Spider, Request, Response
from scrapling.fetchers import FetcherSession, AsyncFetcherSession

from src.config import config
from src.models import Guia, ScrapingStats
from src.parser import parse_guia_page
from src.db import Database

logger = logging.getLogger(__name__)


class SICMSpider(Spider):
    """
    Spider para scrapear guías del SICM

    Características:
    - Resume desde checkpoint automático
    - Rate limiting adaptativo
    - Monitoreo de progreso
    - Validación y limpieza de datos
    """

    name = "sicm"
    concurrent_requests = config.CONCURRENCY
    request_timeout = config.REQUEST_TIMEOUT
    download_delay = config.DELAY_MS / 1000.0  # Convertir ms a segundos

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.db = Database()
        self.batch: List[Guia] = []
        self.batch_size = config.BATCH_SIZE
        self.stats = ScrapingStats()
        self.start_time = time.time()
        self.checkpoint_path = Path(config.CHECKPOINT_DIR) / "progress.pkl"
        self.http_errors = 0
        self.parse_errors = 0

    def configure_sessions(self, manager: Any) -> None:
        """Configurar sesiones HTTP con impersonación de navegador"""
        try:
            # Sesión principal con impersonación
            session = FetcherSession(
                impersonate=config.IMPERSONATE_BROWSER,
                timeout=config.REQUEST_TIMEOUT,
                stealthy_headers=True,
            )
            manager.add("default", session)
            logger.info("session_configured", impersonate=config.IMPERSONATE_BROWSER)
        except Exception as e:
            logger.error("session_config_failed", error=str(e))
            raise

    async def start_requests(self) -> None:
        """Generar requests iniciales"""
        logger.info(
            "spider_starting",
            start_id=config.START_ID,
            end_id=config.END_ID,
            total_range=config.END_ID - config.START_ID + 1,
        )

        for id_guia in range(config.START_ID, config.END_ID + 1):
            url = f"http://www.sicm.gob.ve/g_4cguia.php?id_guia={id_guia}"
            yield Request(url, meta={"id_guia": id_guia})

    async def parse(self, response: Response) -> None:
        """Procesar respuesta HTML"""
        id_guia = response.meta.get("id_guia")
        self.stats.total_processed += 1

        try:
            if response.status != 200:
                logger.warning("http_error", id=id_guia, status=response.status)
                self.http_errors += 1
                self.stats.total_errors += 1
                return

            # Parsear guía del HTML
            guia = parse_guia_page(response.text, id_guia)

            if guia is None:
                self.stats.total_skipped += 1
                logger.debug("guia_skipped", id=id_guia)
                return

            # Agregar a batch
            self.batch.append(guia)
            self.stats.current_id = id_guia

            # Flush si alcanza tamaño de batch
            if len(self.batch) >= self.batch_size:
                await self._flush_batch()

        except Exception as e:
            logger.error("parse_exception", id=id_guia, error=str(e))
            self.parse_errors += 1
            self.stats.total_errors += 1

    async def _flush_batch(self) -> None:
        """Guardar batch a BD"""
        if not self.batch:
            return

        try:
            inserted, skipped = await self.db.bulk_insert(self.batch)
            self.stats.total_saved += inserted

            # Calcular métricas
            elapsed = time.time() - self.start_time
            self.stats.elapsed_seconds = elapsed
            self.stats.requests_per_second = self.stats.total_processed / elapsed

            # Estimar ETA
            remaining = config.END_ID - self.stats.current_id
            if self.stats.requests_per_second > 0:
                self.stats.estimated_eta_seconds = int(remaining / self.stats.requests_per_second)

            logger.info(
                "batch_flushed",
                inserted=inserted,
                skipped=skipped,
                batch_size=len(self.batch),
                total_processed=self.stats.total_processed,
                total_saved=self.stats.total_saved,
                rps=f"{self.stats.requests_per_second:.2f}",
                eta=self.stats.formatted_eta,
            )

            # Actualizar progreso en BD
            await self.db.update_progress(
                self.stats.current_id,
                self.stats.total_saved,
                self.stats.total_errors,
                self.stats.total_processed,
            )

            self.batch.clear()

        except Exception as e:
            logger.error("flush_batch_failed", error=str(e), batch_size=len(self.batch))
            self.stats.total_errors += len(self.batch)
            self.batch.clear()

    async def closed(self, reason: str) -> None:
        """Limpieza al cerrar spider"""
        logger.info("spider_closing", reason=reason)

        try:
            # Guardar batch final
            if self.batch:
                await self._flush_batch()

            # Estadísticas finales
            await self._print_final_stats()

            # Cerrar BD
            await self.db.close()

            logger.info(
                "spider_closed",
                total_processed=self.stats.total_processed,
                total_saved=self.stats.total_saved,
                total_errors=self.stats.total_errors,
                elapsed_seconds=self.stats.elapsed_seconds,
            )

        except Exception as e:
            logger.error("spider_close_failed", error=str(e))

    async def _print_final_stats(self) -> None:
        """Imprimir estadísticas finales"""
        elapsed = time.time() - self.start_time
        stats_db = await self.db.get_stats()

        output = f"""
╔════════════════════════════════════════════╗
║       SICM Scraper - Estadísticas Finales  ║
╠════════════════════════════════════════════╣
║ Procesadas:        {self.stats.total_processed:>20,} ║
║ Guardadas:         {self.stats.total_saved:>20,} ║
║ Errores:           {self.stats.total_errors:>20,} ║
║ Omitidas:          {self.stats.total_skipped:>20,} ║
║ Tasa de éxito:     {self.stats.success_rate:>19.1f}% ║
║                                            ║
║ Tiempo total:      {elapsed:>18.0f}s ║
║ Req/segundo:       {self.stats.requests_per_second:>18.2f} ║
║                                            ║
║ BD - Total guías:  {stats_db.get("total_guias", 0):>20,} ║
║ BD - Productos:    {stats_db.get("total_productos", 0):>20,} ║
║ BD - Unidades:     {stats_db.get("total_unidades", 0):>20,} ║
║ BD - Destinos:     {stats_db.get("unique_destinos", 0):>20,} ║
╚════════════════════════════════════════════╝
        """
        logger.info("final_stats", message=output)
        print(output)


async def run_spider() -> None:
    """Entry point para ejecutar el spider"""
    # Validar configuración
    try:
        config.validate()
    except ValueError as e:
        logger.error("config_validation_failed", error=str(e))
        raise

    # Crear y ejecutar spider
    spider = SICMSpider(crawldir=str(config.CHECKPOINT_DIR))

    # Conectar a BD antes de iniciar
    try:
        await spider.db.connect()
        logger.info("spider_initialized", config=str(config))
    except Exception as e:
        logger.error("spider_init_failed", error=str(e))
        raise

    # Iniciar scraping
    try:
        spider.start()
    except KeyboardInterrupt:
        logger.warning("spider_interrupted_by_user")
        await spider._flush_batch()
        await spider.db.close()
    except Exception as e:
        logger.error("spider_execution_failed", error=str(e))
        raise


def main() -> None:
    """Punto de entrada principal"""
    try:
        asyncio.run(run_spider())
    except KeyboardInterrupt:
        logger.info("scraper_shutdown")
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        raise SystemExit(1)
