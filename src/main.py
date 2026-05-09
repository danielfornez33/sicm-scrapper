"""
Punto de entrada principal del scraper SICM
Inicializa logging, valida configuración y arranca el spider
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from src.logger import setup_logging, get_logger
from src.config import config
from src.spider import main as run_spider

logger: Optional[logging.Logger] = None


def main() -> int:
    """Entry point principal"""
    global logger

    # Crear directorio de logs
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    # Crear directorio de checkpoints
    config.CHECKPOINT_DIR.mkdir(exist_ok=True, parents=True)

    # Configurar logging
    setup_logging()
    logger = get_logger(__name__)

    try:
        logger.info("Iniciando SICM Scraper v2.0.0")
        logger.info(f"Configuración: {config}")

        # Validar configuración
        config.validate()
        logger.info("✓ Configuración validada")

        # Ejecutar spider
        run_spider()

        logger.info("✓ Scraper completado exitosamente")
        return 0

    except KeyboardInterrupt:
        logger.info("⚠ Scraper interrumpido por usuario")
        return 130
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
