# SICM Scraper v2.0.0

Scraper robusto y optimizado para datos del Sistema de Información de Comercialización de Medicamentos (SICM) de Venezuela. Diseñado para VPS con PostgreSQL centralizada.

## 🚀 Características

- **Pause & Resume**: Guarda progreso automáticamente, reanuda desde el último checkpoint
- **Alto rendimiento**: Hasta 20 requests concurrentes, 1000 items/batch
- **Validación de datos**: Pydantic models con validaciones estrictas
- **Limpieza automática**: Filtra outliers, duplicados y datos inválidos
- **Monitoreo**: Métricas Prometheus, logs estructurados
- **Docker**: Multi-stage build optimizado para VPS
- **Manejo de errores**: Retry exponencial, circuit breaker
- **Impersonación de navegador**: Evita bloqueos anti-bot

## 📋 Requisitos

- Python 3.10+
- PostgreSQL 12+
- Docker & Docker Compose (opcional)

## 🔧 Instalación Local

```bash
# Clonar repositorio
git clone <repo>
cd sicm-scraper

# Crear virtualenv
python3.10 -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -e ".[all]"

# Descargar navegadores
scrapling install
```

## ⚙️ Configuración

Copiar y editar `.env`:

```bash
cp .env.example .env
```

Variables críticas:

```env
# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=farmapatria
DB_USER=postgres
DB_PASS=changeme  # ⚠️ CAMBIAR

# Rango de guías a scrapear
START_ID=42022341
END_ID=42591276

# Performance
CONCURRENCY=20        # Requests simultáneos
BATCH_SIZE=1000      # Items antes de guardar
REQUEST_TIMEOUT=60   # Segundos por request

# Rate limiting (evitar bloqueos)
RATE_LIMIT_RPS=15    # Requests por segundo
CIRCUIT_BREAKER_THRESHOLD=10
```

## 🐳 Docker Compose (Recomendado para VPS)

```bash
# Crear y arrancar servicios
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f scraper

# Detener scraper
docker-compose down

# Pausar (preserva datos)
docker-compose pause scraper

# Reanudar desde checkpoint
docker-compose unpause scraper
```

## 📊 Ejecución

### Local

```bash
python src/main.py
```

### Docker

```bash
docker-compose up scraper
```

### Con monitoring (Prometheus + Grafana)

```bash
docker-compose --profile monitoring up -d
```

- Prometheus: http://localhost:9091
- Grafana: http://localhost:3000 (admin/admin)

## 📈 Estructura de Datos

### Tabla `guias`
```sql
id_guia (PK)              -- Identificador único
estatus                   -- APROBADA, Abierta, RECIBIDA
fecha_emision             -- Fecha/hora
fecha_vencimiento         -- Fecha
bultos, renglones, unidades
origen_* / destino_*      -- Razón social, RIF, tipo, dirección
```

### Tabla `guia_productos`
```sql
id_guia (FK)
producto                  -- Nombre del medicamento
lote                      -- Número de lote
cantidad                  -- Unidades
```

### Tabla `progress`
```sql
last_id_processed
total_saved / total_errors / total_scraped
```

## 🔍 Queries Útiles

### Top 20 Productos (últimos 3 meses)
```sql
SELECT gp.producto, SUM(gp.cantidad) as total
FROM guia_productos gp
INNER JOIN guias g ON gp.id_guia = g.id_guia
WHERE g.fecha_emision >= NOW() - INTERVAL '3 months'
  AND gp.producto != 'NO ESTA REGISTRADO EL PRODUCTO'
  AND gp.cantidad < 1000000
GROUP BY gp.producto
ORDER BY total DESC
LIMIT 20;
```

### Score de Crédito (Clasificación de farmacias)
```sql
WITH pharmacy_metrics AS (
  SELECT 
    destino_razon,
    COUNT(*) as compras,
    SUM(unidades) as unidades_totales,
    COUNT(DISTINCT DATE_TRUNC('month', fecha_emision)) as meses_activos,
    MAX(fecha_emision) as ultima_compra
  FROM guias 
  WHERE destino_tipo = 'Farmacias Comerciales'
  GROUP BY destino_razon
)
SELECT 
  destino_razon,
  compras,
  unidades_totales,
  GREATEST(1, LEAST(1000,
    LEAST(200, compras / 10) +
    CASE WHEN NOW() - ultima_compra < '15 days' THEN 200 ELSE 0 END
  )) as credit_score
FROM pharmacy_metrics
ORDER BY credit_score DESC;
```

## 📝 Logs

Los logs se guardan en `./logs/scraper.log`:

```
2026-05-04 10:30:15 [INFO] spider_starting: start_id=42022341 end_id=42591276
2026-05-04 10:30:20 [INFO] batch_flushed: inserted=1000 skipped=5 rps=125.34
2026-05-04 10:35:00 [WARNING] outlier_detected: id=42023456 unidades=2000000
```

## 🚨 Troubleshooting

### "Connection refused"
```bash
# Verificar que PostgreSQL está corriendo
docker-compose ps postgres

# Conectar directamente
psql -h localhost -U postgres -d farmapatria
```

### "Out of memory"
Reducir concurrencia en `.env`:
```env
CONCURRENCY=5      # De 20 a 5
BATCH_SIZE=100     # De 1000 a 100
```

### Scraper lento
Aumentar concurrencia (si CPU/RAM lo permite):
```env
CONCURRENCY=40
```

### Checkpoint corrupto
```bash
rm -rf checkpoints/
# Reiniciar, comenzará desde START_ID
```

## 🔐 Seguridad en Producción

1. **Cambiar credenciales DB**
   ```env
   DB_PASS=tu_password_fuerte_aqui
   ```

2. **Usar secretos en lugar de `.env`**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
   ```

3. **Limitar acceso a PostgreSQL**
   ```sql
   REVOKE ALL PRIVILEGES ON DATABASE farmapatria FROM PUBLIC;
   GRANT CONNECT ON DATABASE farmapatria TO scraper_user;
   ```

4. **Firewall**
   - Solo permitir acceso a puerto 5432 desde IP del scraper
   - Puerto 9090 (metrics) solo desde red interna

## 📦 VPS Deployment

### Recomendaciones de servidor

- **CPU**: 2-4 cores
- **RAM**: 4-8 GB
- **Storage**: 100+ GB (PostgreSQL)
- **OS**: Ubuntu 22.04 LTS

### Setup en VPS

```bash
# 1. Clonar repo
git clone <repo>
cd sicm-scraper

# 2. Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. Crear .env desde ejemplo
cp .env.example .env
# Editar .env con valores correctos

# 4. Iniciar servicios
docker-compose up -d

# 5. Verificar estado
docker-compose ps
docker-compose logs scraper
```

### Monitoreo continuo

```bash
# Ver si scraper está corriendo
docker-compose ps

# Ver últimas guías procesadas
docker exec -it sicm_postgres psql -U postgres -d farmapatria \
  -c "SELECT last_id_processed FROM progress LIMIT 1;"

# Calcular ETA
docker compose logs scraper | grep "eta="
```

## 🛑 Pausar/Reanudar

```bash
# Pausar (NO pierde datos)
docker-compose pause scraper

# Reanudar desde checkpoint
docker-compose unpause scraper

# Para y guarda checkpoint
docker-compose stop scraper
docker-compose start scraper
```

## 📊 Performance Esperado

Con configuración estándar (CONCURRENCY=20, BATCH_SIZE=1000):

- **Velocidad**: 100-150 guías/segundo
- **Range 42M-42.5M**: ~6-10 horas
- **Tiempo total**: Depende de network latency y carga de SICM

## 🧪 Testing

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Ejecutar tests
pytest -v tests/

# Con coverage
pytest --cov=src tests/
```

## 📞 Soporte

Problemas frecuentes: ver TROUBLESHOOTING.md

## 📜 Licencia

BSD-3-Clause (ver LICENSE)

---

**Última actualización**: 2026-05-04
