"""
Orchestrator - Coordinador de múltiples workers de scraping
"""
import asyncio
import logging
import os
import multiprocessing
from typing import List, Dict, Optional
from dataclasses import dataclass
import subprocess
import signal
import time

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuración de un worker"""
    worker_id: int
    start_id: int
    end_id: int
    concurrency: int
    process: Optional[subprocess.Popen] = None
    status: str = "pending"  # pending, running, stopped, completed
    progress: int = 0
    errors: int = 0


class ScrapingOrchestrator:
    """
    Orquestador que coordina múltiples workers de scraping
    
    Características:
    - Auto-detectar número de CPU cores
    - Asignar rangos de IDs a cada worker
    - Monitorear estado de cada worker
    - Reiniciar workers que fallen
    - Recolectar estadísticas agregadas
    """
    
    def __init__(
        self,
        start_id: int,
        end_id: int,
        workers: Optional[int] = None,
        concurrency: int = 40,
    ):
        self.start_id = start_id
        self.end_id = end_id
        self.total_ids = end_id - start_id + 1
        
        # Auto-detectar workers si no se especifica
        if workers is None or workers == "auto" or workers == 0:
            self.num_workers = self._detect_cores() * 2
        else:
            self.num_workers = workers
        
        self.concurrency = concurrency
        
        # Calcular IDs por worker
        self.ids_per_worker = self.total_ids // self.num_workers
        
        # Lista de workers
        self.workers: List[WorkerConfig] = []
        
        # Estado del orchestrator
        self.is_running = False
        self.start_time = 0.0
        self.stats = {
            "total_processed": 0,
            "total_errors": 0,
            "workers_running": 0,
            "workers_completed": 0,
        }
    
    def _detect_cores(self) -> int:
        """Detectar número de CPU cores"""
        try:
            cores = multiprocessing.cpu_count()
            logger.info(f"Detectados {cores} CPU cores")
            return cores
        except Exception:
            logger.warning("No se pudo detectar CPU cores, usando 4 por defecto")
            return 4
    
    def create_workers(self) -> List[WorkerConfig]:
        """Crear configuración de workers"""
        workers = []
        
        for i in range(self.num_workers):
            start = self.start_id + (i * self.ids_per_worker)
            
            # El último worker obtiene los IDs restantes
            if i == self.num_workers - 1:
                end = self.end_id
            else:
                end = start + self.ids_per_worker - 1
            
            worker = WorkerConfig(
                worker_id=i + 1,
                start_id=start,
                end_id=end,
                concurrency=self.concurrency,
            )
            workers.append(worker)
        
        logger.info(
            f"Creados {self.num_workers} workers: "
            f"{self.ids_per_worker:,} IDs por worker"
        )
        
        return workers
    
    async def start(self):
        """Iniciar todos los workers"""
        self.is_running = True
        self.start_time = time.time()
        self.workers = self.create_workers()
        
        logger.info(
            f"Iniciando orchestrator: {self.num_workers} workers, "
            f"{self.num_workers * self.concurrency} requests concurrentes totales"
        )
        
        # Iniciar cada worker como proceso separado
        for worker in self.workers:
            await self._start_worker(worker)
        
        # Monitorear workers
        await self._monitor_workers()
    
    async def _start_worker(self, worker: WorkerConfig):
        """Iniciar un worker individual"""
        env = os.environ.copy()
        env.update({
            "WORKER_ID": str(worker.worker_id),
            "START_ID": str(worker.start_id),
            "END_ID": str(worker.end_id),
            "CONCURRENCY": str(worker.concurrency),
            "LOG_LEVEL": "INFO",
        })
        
        try:
            # Iniciar proceso del spider
            process = subprocess.Popen(
                ["python", "-m", "src.main"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            worker.process = process
            worker.status = "running"
            self.stats["workers_running"] += 1
            
            logger.info(
                f"Worker {worker.worker_id} iniciado: "
                f"IDs {worker.start_id:,} - {worker.end_id:,}"
            )
            
        except Exception as e:
            logger.error(f"Error al iniciar worker {worker.worker_id}: {e}")
            worker.status = "stopped"
    
    async def _monitor_workers(self):
        """Monitorear estado de todos los workers"""
        logger.info("Iniciando monitoreo de workers...")
        
        while self.is_running:
            running_count = 0
            completed_count = 0
            
            for worker in self.workers:
                if worker.process is None:
                    continue
                
                # Verificar si el proceso sigue corriendo
                return_code = worker.process.poll()
                
                if return_code is None:
                    # Still running
                    running_count += 1
                elif return_code == 0:
                    # Completed successfully
                    if worker.status != "completed":
                        worker.status = "completed"
                        completed_count += 1
                        logger.info(
                            f"Worker {worker.worker_id} completado: "
                            f"{worker.end_id - worker.start_id + 1:,} IDs"
                        )
                else:
                    # Error - restart
                    logger.warning(
                        f"Worker {worker.worker_id} murió (exit code: {return_code})"
                    )
                    worker.errors += 1
                    worker.status = "stopped"
                    
                    # Reiniciar después de delay
                    if worker.errors < 3:
                        await asyncio.sleep(5)
                        await self._start_worker(worker)
            
            self.stats["workers_running"] = running_count
            self.stats["workers_completed"] = completed_count
            
            # Log progreso cada 30 segundos
            logger.info(
                f"Estado: {running_count} running, {completed_count} completed, "
                f"{self.stats['total_processed']:,} processed"
            )
            
            # Verificar si todos completaron
            if completed_count == self.num_workers:
                logger.info("¡Todos los workers completados!")
                break
            
            # Esperar antes de siguiente chequeo
            await asyncio.sleep(30)
    
    async def stop(self):
        """Detener todos los workers"""
        logger.info("Deteniendo todos los workers...")
        self.is_running = False
        
        for worker in self.workers:
            if worker.process:
                try:
                    worker.process.terminate()
                    worker.process.wait(timeout=10)
                except Exception as e:
                    logger.error(f"Error al detener worker {worker.worker_id}: {e}")
                    try:
                        worker.process.kill()
                    except:
                        pass
        
        elapsed = time.time() - self.start_time
        logger.info(
            f"Orchestrator detenido. Tiempo total: {elapsed/60:.1f} minutos"
        )
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas agregadas"""
        return {
            "num_workers": self.num_workers,
            "total_ids": self.total_ids,
            "ids_per_worker": self.ids_per_worker,
            "total_concurrency": self.num_workers * self.concurrency,
            "workers_running": self.stats["workers_running"],
            "workers_completed": self.stats["workers_completed"],
            "elapsed_seconds": time.time() - self.start_time if self.start_time > 0 else 0,
        }


async def run_orchestrator(
    start_id: int,
    end_id: int,
    workers: Optional[int] = None,
    concurrency: int = 40,
):
    """Función de entrada para ejecutar el orchestrator"""
    orchestrator = ScrapingOrchestrator(
        start_id=start_id,
        end_id=end_id,
        workers=workers,
        concurrency=concurrency,
    )
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Interrumpido por usuario")
        await orchestrator.stop()
    except Exception as e:
        logger.error(f"Error en orchestrator: {e}")
        await orchestrator.stop()
        raise


def main():
    """CLI para el orchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SICM Scraper Orchestrator")
    parser.add_argument("--start-id", type=int, required=True)
    parser.add_argument("--end-id", type=int, required=True)
    parser.add_argument("--workers", type=int, default=0, help="0 = auto-detectar")
    parser.add_argument("--concurrency", type=int, default=40)
    
    args = parser.parse_args()
    
    asyncio.run(run_orchestrator(
        start_id=args.start_id,
        end_id=args.end_id,
        workers=args.workers if args.workers > 0 else None,
        concurrency=args.concurrency,
    ))


if __name__ == "__main__":
    main()