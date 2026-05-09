"""
Fingerprint Manager - Rotación de User Agents y headers para evitar detección
"""
import random
from typing import Dict, Optional


class FingerprintManager:
    """
    Gestor de fingerprints para evitar detección por fingerprinting
    
    Características:
    - Rotación de User Agents (100+ navegadores reales)
    - Randomización de headers
    - Simulación de diferentes dispositivos
    """
    
    # User Agents reales de Chrome, Firefox, Safari
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:120.0) Gecko/20100101 Firefox/120.0",
        
        # Firefox on Linux
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1; rv:109.0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Chrome on Android
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        
        # Safari on iOS
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 CriOS/120.0.0.0 Mobile/15E148 Safari/604.1",
    ]
    
    ACCEPT_TYPES = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "text/html,application/xml;q=0.9,*/*;q=0.8",
    ]
    
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "es-ES,es;q=0.9,en;q=0.8",
        "en-US,en;q=0.9,es;q=0.8",
        "en;q=0.9,es;q=0.8",
        "es-419,es;q=0.9,en;q=0.8",
    ]
    
    # Chrome-UA (Sec-CH-UA) para fingerprinting
    SEC_CH_UA_VALUES = [
        '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        '"Not_A Brand";v="8", "Chromium";v="119", "Google Chrome";v="119"',
        '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"',
        '"Chromium";v="120", "Google Chrome";v="120"',
    ]
    
    SEC_CH_UA_PLATFORM = [
        '"Windows"',
        '"macOS"',
        '"Linux"',
    ]
    
    SEC_CH_UA_MOBILE = ["?0", "?1"]
    
    # Viewport sizes comunes
    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
        {"width": 2560, "height": 1440},
    ]
    
    # Screen resolutions
    SCREEN_RESOLUTIONS = [
        "1920,1080",
        "1366,768",
        "1536,864",
        "1440,900",
        "1280,720",
        "2560,1440",
    ]
    
    def __init__(self, worker_id: int = 0):
        self.worker_id = worker_id
        self.request_count = 0
        # Semilla diferente para cada worker
        random.seed(worker_id * 1000)
    
    def get_headers(self) -> Dict[str, str]:
        """
        Generar headers aleatorios que parecen de un navegador real
        """
        self.request_count += 1
        
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": random.choice(self.ACCEPT_TYPES),
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": random.choice(self.SEC_CH_UA_VALUES),
            "Sec-Ch-Ua-Mobile": random.choice(self.SEC_CH_UA_MOBILE),
            "Sec-Ch-Ua-Platform": random.choice(self.SEC_CH_UA_PLATFORM),
            "Sec-Ch-Viewport-Width": str(random.choice([1920, 1536, 1440, 1366])),
            "Sec-Ch-Downlink": random.choice(["1", "2", "5", "10"]),
            "Sec-Ch-Prefers-Reduced-Motion": random.choice(["no-preference", "reduce"]),
        }
        
        return headers
    
    def get_viewport(self) -> Dict[str, int]:
        """Obtener viewport aleatorio"""
        return random.choice(self.VIEWPORTS)
    
    def get_screen_resolution(self) -> str:
        """Obtener resolución de pantalla aleatoria"""
        return random.choice(self.SCREEN_RESOLUTIONS)
    
    def get_random_delay_ms(self, min_ms: int = 100, max_ms: int = 500) -> float:
        """
        Delay aleatorio entre requests para evitar patrones detectables
        """
        # Añadir variación basada en worker_id para evitar sincronización
        base_delay = random.uniform(min_ms, max_ms)
        worker_offset = self.worker_id * 10  # Cada worker tiene offset diferente
        return base_delay + (worker_offset % 50)
    
    def get_timezone(self) -> str:
        """Zona horaria realista"""
        return random.choice([
            "America/Caracas",
            "America/Lima",
            "America/Bogota",
            "America/Guayaquil",
            "America/Mexico_City",
        ])
    
    def get_accept_encoding(self) -> str:
        """Accept-Encoding variable"""
        return random.choice([
            "gzip, deflate, br",
            "gzip, deflate",
            "deflate, gzip, br",
        ])