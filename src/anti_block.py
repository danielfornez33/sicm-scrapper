"""
Anti-Block System - Detección de bloqueos y auto-recovery
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Tipos de bloqueo detectados"""
    NONE = "none"
    RATE_LIMIT = "rate_limit"      # 429 Too Many Requests
    FORBIDDEN = "forbidden"        # 403 Forbidden
    CAPTCHA = "captcha"            # Página de CAPTCHA
    CLOUDFLARE = "cloudflare"     # Protection de Cloudflare
    TIMEOUT = "timeout"            # Timeout repetidos
    EMPTY_RESPONSE = "empty"       # Respuestas vacías


@dataclass
class BlockStatus:
    """Estado actual de bloqueo"""
    is_blocked: bool = False
    block_type: BlockType = BlockType.NONE
    consecutive_errors: int = 0
    consecutive_blocks: int = 0
    last_block_time: float = 0
    total_blocks: int = 0
    requests_since_last_block: int = 0
    cooldown_until: float = 0
    
    # Contadores
    total_requests: int = 0
    total_success: int = 0
    total_errors: int = 0
    
    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.total_errors / self.total_requests) * 100
    
    @property
    def is_in_cooldown(self) -> bool:
        return time.time() < self.cooldown_until


class AntiBlockDetector:
    """
    Detector de bloqueos con auto-recovery
    
    Detecta:
    - Rate limiting (429)
    - Forbidden (403)
    - CAPTCHA
    - Cloudflare
    - Timeouts repetidos
    - Respuestas vacías
    
    Acciones:
    - Reducir velocidad automáticamente
    - Esperar cooldown antes de reintentar
    - Notificar estado
    """
    
    # Thresholds configurables
    DEFAULT_CONFIG = {
        "consecutive_errors_threshold": 15,  # Errores consecutivos para bloquear
        "rate_limit_threshold": 3,         # Rate limits para bloquear
        "cooldown_seconds": 60,            # Tiempo de espera después de bloqueo
        "max_consecutive_blocks": 5,        # Bloques consecutivos antes de parar
        "success_threshold": 20,           # Éxitos para limpiar errores
        "reduce_speed_on_block": True,       # Reducir velocidad cuando se detecta bloqueo
        "speed_reduction_factor": 0.5,       # Multiplicador de velocidad
    }
    
    def __init__(self, worker_id: int = 0, config: Optional[Dict] = None):
        self.worker_id = worker_id
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.status = BlockStatus()
        self.speed_multiplier = 1.0
        
        # historial de bloqueos recientes (últimos 10)
        self.recent_blocks: list = []
    
    def record_response(
        self,
        status_code: int,
        content: Optional[str] = None,
        is_error: bool = False
    ) -> BlockType:
        """
        Analizar respuesta y detectar bloqueos
        
        Returns:
            BlockType: Tipo de bloqueo detectado
        """
        self.status.total_requests += 1
        self.status.requests_since_last_block += 1
        
        if is_error:
            self.status.total_errors += 1
            self.status.consecutive_errors += 1
        else:
            self.status.total_success += 1
            # Reset errores consecutivos si hay éxito
            if self.status.consecutive_errors > 0:
                # Reducir contador pero mantener algo de historia
                self.status.consecutive_errors = max(0, self.status.consecutive_errors - 2)
        
        # Analizar código de estado
        block_type = self._analyze_status_code(status_code, content)
        
        if block_type != BlockType.NONE:
            self._handle_block_detected(block_type, status_code)
        else:
            # No hay bloqueo, verificar si debemos limpiar estado
            self._check_recovery()
        
        return block_type
    
    def _analyze_status_code(self, status_code: int, content: Optional[str]) -> BlockType:
        """Analizar código de estado HTTP"""
        
        # Rate Limit
        if status_code == 429:
            logger.warning(f"[Worker {self.worker_id}] Rate limit detected (429)")
            return BlockType.RATE_LIMIT
        
        # Forbidden
        if status_code == 403:
            # Verificar si es CAPTCHA o Cloudflare
            if content:
                if "captcha" in content.lower() or "challenge" in content.lower():
                    logger.warning(f"[Worker {self.worker_id}] CAPTCHA detected")
                    return BlockType.CAPTCHA
                if "cloudflare" in content.lower() or "turnstile" in content.lower():
                    logger.warning(f"[Worker {self.worker_id}] Cloudflare protection detected")
                    return BlockType.CLOUDFLARE
            logger.warning(f"[Worker {self.worker_id}] Forbidden (403)")
            return BlockType.FORBIDDEN
        
        # Server errors
        if status_code >= 500:
            logger.warning(f"[Worker {self.worker_id}] Server error ({status_code})")
            return BlockType.TIMEOUT
        
        return BlockType.NONE
    
    def _handle_block_detected(self, block_type: BlockType, status_code: int):
        """Manejar bloqueo detectado"""
        self.status.is_blocked = True
        self.status.consecutive_blocks += 1
        self.status.total_blocks += 1
        self.status.last_block_time = time.time()
        self.status.consecutive_errors = 0
        self.status.requests_since_last_block = 0
        
        # Calcular cooldown
        cooldown = self._calculate_cooldown(block_type)
        self.status.cooldown_until = time.time() + cooldown
        
        # Reducir velocidad si está habilitado
        if self.config["reduce_speed_on_block"]:
            self.speed_multiplier = self.config["speed_reduction_factor"]
        
        # Guardar en historial
        self.recent_blocks.append({
            "type": block_type.value,
            "time": time.time(),
            "status_code": status_code,
            "cooldown": cooldown,
        })
        
        # Mantener solo últimos 10
        if len(self.recent_blocks) > 10:
            self.recent_blocks = self.recent_blocks[-10:]
        
        # Loggear
        logger.warning(
            f"[Worker {self.worker_id}] BLOCK DETECTED: {block_type.value} "
            f"(consecutive: {self.status.consecutive_blocks}, "
            f"total: {self.status.total_blocks}, "
            f"cooldown: {cooldown}s)"
        )
        
        # Verificar si hay demasiados bloqueos consecutivos
        if self.status.consecutive_blocks >= self.config["max_consecutive_blocks"]:
            logger.error(
                f"[Worker {self.worker_id}] DEMASIADOS BLOQUEOS - Deteniendo worker"
            )
    
    def _calculate_cooldown(self, block_type: BlockType) -> float:
        """Calcular tiempo de cooldown según tipo de bloqueo"""
        base_cooldown = self.config["cooldown_seconds"]
        
        multipliers = {
            BlockType.RATE_LIMIT: 1.0,      # 60s
            BlockType.FORBIDDEN: 1.5,      # 90s
            BlockType.CAPTCHA: 3.0,         # 180s
            BlockType.CLOUDFLARE: 2.0,      # 120s
            BlockType.TIMEOUT: 0.5,         # 30s
            BlockType.EMPTY_RESPONSE: 1.0,  # 60s
        }
        
        multiplier = multipliers.get(block_type, 1.0)
        
        # Aumentar cooldown si hay muchos bloqueos recientes
        if len(self.recent_blocks) >= 5:
            multiplier *= 1.5
        
        return base_cooldown * multiplier
    
    def _check_recovery(self):
        """Verificar si debemos recuperar velocidad"""
        
        # Si hay suficientes éxitos, recuperar
        if self.status.requests_since_last_block >= self.config["success_threshold"]:
            if self.status.consecutive_blocks > 0:
                logger.info(
                    f"[Worker {self.worker_id}] Recovery: "
                    f"{self.status.requests_since_last_block} requests successful"
                )
                self.status.consecutive_blocks = 0
            
            # Restaurar velocidad gradualmente
            if self.speed_multiplier < 1.0:
                self.speed_multiplier = min(1.0, self.speed_multiplier * 1.5)
    
    def should_continue(self) -> bool:
        """Determinar si el worker debe continuar"""
        
        # Si está en cooldown, no continuar
        if self.status.is_in_cooldown:
            remaining = int(self.status.cooldown_until - time.time())
            logger.info(
                f"[Worker {self.worker_id}] En cooldown: {remaining}s restantes"
            )
            return False
        
        # Si hay demasiados bloqueos,可以考虑 parar
        if self.status.consecutive_blocks >= self.config["max_consecutive_blocks"]:
            logger.error(
                f"[Worker {self.worker_id}] Demasiados bloqueos consecutivos. "
                f"Considera revisar la configuración."
            )
            return False
        
        return True
    
    async def wait_if_needed(self):
        """Esperar si hay cooldown activo"""
        if self.status.is_in_cooldown:
            wait_time = self.status.cooldown_until - time.time()
            if wait_time > 0:
                logger.info(
                    f"[Worker {self.worker_id}] Esperando cooldown: {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
    
    def get_effective_delay(self, base_delay_ms: float) -> float:
        """Obtener delay efectivo considerando el multiplicador de velocidad"""
        return base_delay_ms * self.speed_multiplier
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado actual del detector"""
        return {
            "worker_id": self.worker_id,
            "is_blocked": self.status.is_blocked,
            "block_type": self.status.block_type.value,
            "consecutive_errors": self.status.consecutive_errors,
            "consecutive_blocks": self.status.consecutive_blocks,
            "total_blocks": self.status.total_blocks,
            "total_requests": self.status.total_requests,
            "total_success": self.status.total_success,
            "total_errors": self.status.total_errors,
            "error_rate": f"{self.status.error_rate:.1f}%",
            "is_in_cooldown": self.status.is_in_cooldown,
            "speed_multiplier": f"{self.speed_multiplier:.2f}",
            "should_continue": self.should_continue(),
            "recent_blocks": len(self.recent_blocks),
        }
    
    def reset(self):
        """Resetear el detector"""
        self.status = BlockStatus()
        self.speed_multiplier = 1.0
        self.recent_blocks = []
        logger.info(f"[Worker {self.worker_id}] Anti-block detector reset")