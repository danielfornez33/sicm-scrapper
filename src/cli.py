"""
CLI - Interfaz de Línea de Comandos para SICM Scraper
Permite ejecutar el scraper con argumentos personalizables
"""
import argparse
import asyncio
import sys
from pathlib import Path

from src.config import config
from src.db import Database
from src.logger import setup_logging
from src.spider import SICMSpider


def create_parser() -> argparse.ArgumentParser:
    """Crear parser de argumentos CLI"""
    parser = argparse.ArgumentParser(
        prog="sicm-scraper",
        description="SICM Venezuela Medicines Scraper - Adaptive Web Scraping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s                              # Ejecutar con config por defecto
  %(prog)s --start-id 42022350          # Iniciar desde ID específico
  %(prog)s --end-id 42022400            # Terminar en ID específico
  %(prog)s --dry-run                    # Modo pruebas (solo 10 guías)
  %(prog)s --resume                     # Reanudar desde checkpoint
  %(prog)s --status                     # Ver estado actual
  %(prog)s --stats                      # Ver estadísticas de BD
  %(prog)s --clear-checkpoint          # Limpiar checkpoint y reiniciar
        """
    )

    # Rango de IDs
    parser.add_argument(
        "--start-id", "-s",
        type=int,
        default=None,
        help="ID inicial de guías a scrapear"
    )
    parser.add_argument(
        "--end-id", "-e",
        type=int,
        default=None,
        help="ID final de guías a scrapear"
    )

    # Performance
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=None,
        help="Número de requests simultáneos (default: 20)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=None,
        help="Tamaño del batch para guardar a BD (default: 1000)"
    )

    # Modos
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo de prueba: solo scrapear 10 guías"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Reanudar desde último checkpoint"
    )

    # Diagnóstico
    parser.add_argument(
        "--status",
        action="store_true",
        help="Mostrar estado del scraper (sin ejecutar)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostrar estadísticas de la base de datos"
    )
    parser.add_argument(
        "--clear-checkpoint",
        action="store_true",
        help="Limpiar checkpoint y reiniciar desde START_ID"
    )

    # Debug
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Modo verbose (DEBUG logging)"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Mostrar versión"
    )

    return parser


def print_status():
    """Mostrar estado actual del scraper"""
    print("📊 Estado del Scraper:")
    print(f"   Rango configurado: {config.START_ID:,} → {config.END_ID:,}")
    print(f"   Concurrency: {config.CONCURRENCY}")
    print(f"   Batch size: {config.BATCH_SIZE}")
    print(f"   Timeout: {config.REQUEST_TIMEOUT}s")
    print(f"   Checkpoint dir: {config.CHECKPOINT_DIR}")

    # Verificar si hay checkpoint
    checkpoint_file = config.CHECKPOINT_DIR / "progress.pkl"
    if checkpoint_file.exists():
        print("   ✓ Checkpoint existe")
    else:
        print("   ✗ Sin checkpoint")

    print(f"   DB: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")


async def print_stats():
    """Mostrar estadísticas de la base de datos"""
    db = Database()
    try:
        await db.connect()
        stats = await db.get_stats()
        progress = await db.get_progress()

        print("📈 Estadísticas de la Base de Datos:")
        print(f"   Total guías: {stats.get('total_guias', 0):,}")
        print(f"   Total productos: {stats.get('total_productos', 0):,}")
        print(f"   Total unidades: {stats.get('total_unidades', 0):,}")
        print(f"   Destinos únicos: {stats.get('unique_destinos', 0):,}")

        if progress:
            print("\n📍 Progreso del Scrape:")
            print(f"   Último ID procesado: {progress.get('last_id_processed', 'N/A'):,}")
            print(f"   Total guardados: {progress.get('total_saved', 0):,}")
            print(f"   Total errores: {progress.get('total_errors', 0):,}")
            print(f"   Total procesados: {progress.get('total_scraped', 0):,}")

        await db.close()
    except Exception as e:
        print(f"❌ Error al conectar a BD: {e}")
        sys.exit(1)


async def clear_checkpoint():
    """Limpiar checkpoint"""
    checkpoint_file = config.CHECKPOINT_DIR / "progress.pkl"
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print("✓ Checkpoint eliminado")

    # Limpiar también el directorio de checkpoints de Scrapling
    scrapling_checkpoint = Path(config.CHECKPOINT_DIR)
    if scrapling_checkpoint.exists():
        for f in scrapling_checkpoint.glob("*"):
            if f.is_file() and f.name != "progress.pkl":
                f.unlink()

    print("✓ Checkpoints limpiados")


async def run_scraper(args) -> int:
    """Ejecutar el scraper con los argumentos dados"""
    # Aplicar overrides de argumentos
    start_id = args.start_id or config.START_ID
    end_id = args.end_id or config.END_ID

    if args.dry_run:
        print("🔍 Modo DRY RUN: solo 10 guías")
        end_id = min(start_id + 9, end_id)

    # Crear spider
    spider = SICMSpider(crawldir=str(config.CHECKPOINT_DIR))

    # Override concurrency si se especificó
    if args.concurrency:
        spider.concurrent_requests = args.concurrency

    # Override batch size si se especificó
    if args.batch_size:
        spider.batch_size = args.batch_size

    # Conectar a BD
    await spider.db.connect()

    # Ejecutar
    try:
        spider.start()
        return 0
    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido por usuario")
        await spider._flush_batch()
        await spider.db.close()
        return 130
    except Exception as e:
        print(f"❌ Error: {e}")
        await spider.db.close()
        return 1


def main_cli():
    """Entry point CLI"""
    parser = create_parser()
    args = parser.parse_args()

    # Version
    if args.version:
        print("SICM Scraper v2.0.0")
        return 0

    # Configurar logging
    log_level = "DEBUG" if args.verbose else config.LOG_LEVEL
    import os
    os.environ["LOG_LEVEL"] = log_level
    setup_logging()

    # Configurar overrides
    if args.start_id:
        config.START_ID = args.start_id
    if args.end_id:
        config.END_ID = args.end_id

    # Comandos de diagnóstico
    if args.status:
        print_status()
        return 0

    if args.stats:
        asyncio.run(print_stats())
        return 0

    if args.clear_checkpoint:
        asyncio.run(clear_checkpoint())
        return 0

    # Validar configuración
    try:
        config.validate()
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        return 1

    # Ejecutar scraper
    return asyncio.run(run_scraper(args))


if __name__ == "__main__":
    sys.exit(main_cli())
