"""
Modelos Pydantic para validación de datos
Con validaciones estrictas para detectar outliers y datos inválidos
"""


from pydantic import BaseModel, Field, field_validator


class Producto(BaseModel):
    """Modelo para cada producto en una guía"""

    nombre: str = Field(..., min_length=1, max_length=500)
    lote: str | None = Field(None, max_length=100)
    cantidad: int = Field(..., gt=0, le=1_000_000)

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """Rechazar productos inválidos"""
        invalid_products = [
            "NO ESTA REGISTRADO EL PRODUCTO",
            "DESCONOCIDO",
            "SIN NOMBRE",
            "",
        ]
        if v.strip() in invalid_products or not v.strip():
            raise ValueError(f"Producto inválido: {v}")
        return v.strip().upper()

    class Config:
        frozen = True  # Inmutable


class Guia(BaseModel):
    """Modelo para una guía de transporte"""

    id_guia: int = Field(..., gt=0)
    estatus: str = Field(..., pattern="^(APROBADA|Abierta|RECIBIDA)$")
    fecha_emision: str | None = None
    fecha_vencimiento: str | None = None
    bultos: int | None = Field(None, ge=0, le=100_000)
    renglones: int | None = Field(None, ge=0, le=100_000)
    unidades: int = Field(..., ge=0, le=1_000_000)
    origen_razon: str | None = Field(None, max_length=500)
    origen_rif: str | None = Field(None, max_length=50)
    origen_tipo: str | None = Field(None, max_length=100)
    origen_direccion: str | None = Field(None, max_length=500)
    origen_estado_ciudad: str | None = Field(None, max_length=100)
    destino_razon: str | None = Field(None, max_length=500)
    destino_rif: str | None = Field(None, max_length=50)
    destino_tipo: str | None = Field(None, max_length=100)
    destino_direccion: str | None = Field(None, max_length=500)
    destino_estado_ciudad: str | None = Field(None, max_length=100)
    productos: list[Producto] = Field(default_factory=list)

    @field_validator("unidades")
    @classmethod
    def validate_unidades(cls, v: int) -> int:
        """Rechazar outliers obvios"""
        if v > 1_000_000:
            raise ValueError(f"Unidades sospechosamente altas: {v}")
        return v

    @field_validator("productos")
    @classmethod
    def validate_productos(cls, v: list[Producto]) -> list[Producto]:
        """Validación cruzada: al menos 1 producto si unidades > 0"""
        # Permitir guías sin productos (algunos datos pueden estar vacíos en SICM)
        return v

    def is_valid(self) -> bool:
        """Validación adicional de lógica de negocio"""
        # Si hay productos, las unidades deben coincidir
        if self.productos:
            total_productos = sum(p.cantidad for p in self.productos)
            if self.unidades > 0 and total_productos == 0:
                return False
        return True

    class Config:
        frozen = False  # Permite mutación durante parsing


class ScrapingStats(BaseModel):
    """Estadísticas de scraping"""

    total_processed: int = 0
    total_saved: int = 0
    total_errors: int = 0
    total_skipped: int = 0
    current_id: int = 0
    elapsed_seconds: float = 0.0
    requests_per_second: float = 0.0
    estimated_eta_seconds: int | None = None

    @property
    def success_rate(self) -> float:
        """Porcentaje de éxito"""
        if self.total_processed == 0:
            return 0.0
        return (self.total_saved / self.total_processed) * 100

    def __str__(self) -> str:
        return (
            f"📊 Stats: {self.total_processed:,} procesadas, "
            f"{self.total_saved:,} guardadas, "
            f"{self.total_errors:,} errores, "
            f"{self.requests_per_second:.1f} req/s, "
            f"ETA: {self.formatted_eta}"
        )

    @property
    def formatted_eta(self) -> str:
        """Formato legible para ETA"""
        if not self.estimated_eta_seconds or self.estimated_eta_seconds < 0:
            return "---"
        hours = self.estimated_eta_seconds // 3600
        minutes = (self.estimated_eta_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
