# 📁 Estructura del Proyecto SICM Scraper v2.0

## Árbol de Archivos Completo

```
sicm-scraper/
│
├── 📄 Configuración & Build
│   ├── pyproject.toml              # Metadata del proyecto + dependencias
│   ├── .env.example                # Template de variables de entorno
│   ├── Dockerfile                  # Multi-stage build para VPS
│   ├── docker-compose.yml          # Stack: PostgreSQL + Scraper + Prometheus (opcional)
│   └── README.md                   # Documentación principal
│
├── 📝 Documentación
│   ├── SETUP_RÁPIDO.md            # Para empezar en 5 minutos
│   ├── DEPLOYMENT.md               # Paso a paso para VPS (muy detallado)
│   ├── OPTIMIZATION_GUIDE.md       # Tuning de performance y escalado
│   ├── SUMMARY.md                  # Resumen ejecutivo
│   ├── STRUCTURE.md                # Este archivo
│   └── EXPLICACION.md              # Referencia de requirements (del cliente)
│
├── 📦 Código Principal (src/)
│   ├── __init__.py                 # Versión del paquete
│   ├── main.py                     # Entry point: inicializa logging y spider
│   ├── config.py                   # Variables de entorno centralizadas
│   ├── logger.py                   # Sistema de logging estructurado
│   │
│   ├── spider.py                   # ⭐ Spider Scrapling (pause/resume)
│   │   └── SICMSpider (clase)
│   │       ├── configure_sessions() - Setup HTTP con impersonación
│   │       ├── start_requests()    - Genera requests para cada ID
│   │       ├── parse()             - Procesa respuestas HTML
│   │       ├── _flush_batch()      - Guarda batch a BD
│   │       └── closed()            - Cleanup al terminar
│   │
│   ├── parser.py                   # ⭐ Extracción de HTML
│   │   ├── parse_guia_page()       - Parser principal (HTML → Guia)
│   │   ├── _extract_field()        - Busca patrón <strong>Campo:</strong>
│   │   ├── _parse_productos()      - Tabla de productos
│   │   └── _clean_text()           - Limpia HTML entities
│   │
│   ├── db.py                       # ⭐ Gestión de BD
│   │   └── Database (clase)
│   │       ├── connect()           - Pool de asyncpg (min=5, max=20)
│   │       ├── _create_tables()    - Crea tablas e índices
│   │       ├── bulk_insert()       - Insert batch (10x rápido)
│   │       ├── update_progress()   - Guarda checkpoint
│   │       ├── get_stats()         - Estadísticas
│   │       └── close()             - Cleanup
│   │
│   ├── models.py                   # ⭐ Validación Pydantic
│   │   ├── Producto               - Validaciones: nombre, lote, cantidad
│   │   ├── Guia                   - Validaciones: id, estatus, campos
│   │   └── ScrapingStats          - Métricas en tiempo real
│   │
│   └── config.py                   # ⭐ Configuración centralizada
│       └── Config (dataclass)
│           ├── DB_* (conexión)
│           ├── START_ID, END_ID (rango)
│           ├── CONCURRENCY, BATCH_SIZE (performance)
│           ├── RATE_LIMIT, CIRCUIT_BREAKER (seguridad)
│           └── LOG_LEVEL, CHECKPOINT_DIR (ops)
│
├── 📊 Base de Datos
│   ├── Tablas creadas automáticamente:
│   │   ├── guias (id_guia PK)
│   │   │   ├── estatus (APROBADA, Abierta, RECIBIDA)
│   │   │   ├── fecha_emision, fecha_vencimiento
│   │   │   ├── bultos, renglones, unidades
│   │   │   ├── origen_* (razon, rif, tipo, direccion, estado_ciudad)
│   │   │   ├── destino_* (razon, rif, tipo, direccion, estado_ciudad)
│   │   │   └── created_at, updated_at
│   │   │
│   │   ├── guia_productos (FK → guias)
│   │   │   ├── id_guia
│   │   │   ├── producto (nombre medicamento)
│   │   │   ├── lote (número de lote)
│   │   │   └── cantidad
│   │   │
│   │   └── progress (checkpoint)
│   │       ├── last_id_processed
│   │       ├── total_saved, total_errors, total_scraped
│   │       └── last_updated
│   │
│   └── Índices automáticos:
│       ├── idx_guias_estatus
│       ├── idx_guias_fecha_emision
│       ├── idx_guias_destino_razon
│       ├── idx_guia_productos_id_guia
│       └── idx_guia_productos_producto
│
├── 📁 Directorios (se crean automáticamente)
│   ├── logs/                       # Logs de ejecución (rotación diaria)
│   │   └── scraper.log
│   ├── checkpoints/                # Progreso del scrape (pause/resume)
│   │   └── progress.pkl
│   └── data/                       # Backups/exports (opcional)
│
└── 🐳 Docker
    ├── Dockerfile                  # Multi-stage: builder + runtime
    │   ├── Stage 1: Compilar deps
    │   └── Stage 2: Runtime slim
    └── docker-compose.yml          # Orquestación
        ├── postgres                # PostgreSQL 16
        ├── scraper                 # Python 3.11 + deps
        ├── prometheus (optional)   # Métricas
        └── grafana (optional)      # Dashboards
```

## 🔄 Flujo de Ejecución

```
python src/main.py
    ↓
main() [main.py]
    ├─ setup_logging()
    ├─ config.validate()
    └─ run_spider()
        ↓
        run_spider() [spider.py]
            ├─ SICMSpider.__init__()
            │   └─ Database().connect()  → Pool asyncpg creado
            │       ├─ _create_tables()
            │       └─ _create_indices()
            ├─ spider.start()  ← Scrapling maneja el loop
            │   ├─ start_requests()  → Genera tasks (42M IDs)
            │   ├─ parse()  (llamado x cada response)
            │   │   ├─ parse_guia_page() [parser.py]
            │   │   │   ├─ _extract_field() 
            │   │   │   └─ _parse_productos()
            │   │   ├─ Validación Pydantic [models.py]
            │   │   └─ Añadir a batch
            │   └─ Cuando batch.size >= 1000:
            │       ├─ _flush_batch()
            │       │   └─ db.bulk_insert()  [db.py]
            │       │       ├─ INSERT guias
            │       │       ├─ DELETE old productos
            │       │       └─ INSERT productos
            │       └─ db.update_progress()
            └─ closed()
                ├─ _print_final_stats()
                └─ db.close()
```

## 📊 Flujo de Datos

```
HTTP Request
    ↓
Scrapling FetcherSession (impersonate=chrome)
    ↓
HTML Response (200 bytes - 100 KB)
    ↓
parse_guia_page() 
    ├─ Regex búsqueda de patrones
    ├─ Extracción de campos
    └─ _parse_productos()
        ↓
Guia (Pydantic model)
    ├─ Validaciones automáticas
    ├─ Filtro de outliers
    └─ Rechazo de inválidos
        ↓
En memoria (batch list)
    ├─ Cuando size >= BATCH_SIZE (1000)
    │
    ↓
PostgreSQL Pool
    ├─ Transacción atómica
    ├─ UPSERT guias
    ├─ INSERT productos
    └─ UPDATE progress
        ↓
Persistencia
```

## 🚀 Modos de Ejecución

### Opción 1: Docker (Recomendado)
```bash
docker-compose up -d
# Inicia: postgres + scraper
# Datos persisten en volumen
# Logs en archivo y stdout
```

### Opción 2: Local
```bash
python src/main.py
# Requiere: PostgreSQL corriendo en localhost:5432
# Requiere: Navegadores de Scrapling (scrapling install)
```

### Opción 3: Docker + Monitoring
```bash
docker-compose --profile monitoring up -d
# Inicia: postgres + scraper + prometheus + grafana
# Grafana en: http://localhost:3000
```

## 📈 Puntos de Optimización

### Performance (en orden de impacto)
1. **Pool de conexiones** (asyncpg)
   - Default: min=5, max=20
   - Impacto: 5-10x en BD

2. **Batch size**
   - Default: 1000 items
   - Impacto: 3-5x en throughput

3. **Concurrencia HTTP**
   - Default: 20 requests simultáneos
   - Impacto: 4-8x en latencia

4. **Índices de BD**
   - 5 índices preconfigurados
   - Impacto: 2-3x en queries

5. **Delay entre requests**
   - Default: 50ms
   - Impacto: Evita bloqueos de SICM

### Observabilidad
- Logs estructurados (JSON en prod)
- Métricas Prometheus (RPS, latency, errors)
- Estadísticas en tiempo real (ETA, success_rate)
- Health checks HTTP

## 🔧 Ficheros Configurables

```
.env                    # Variables de entorno (gitignored)
src/config.py          # Valores por defecto
src/logger.py          # Nivel de logging
docker-compose.yml     # Recursos de contenedores
```

## 📊 Versiones de Dependencias Importantes

```toml
scrapling >= 0.4.7     # Web scraping adaptativo
asyncpg >= 0.29.0      # PostgreSQL async
pydantic >= 2.5.0      # Validación de datos
python >= 3.10         # Type hints modernos
```

## 🎯 Casos de Uso

### Caso 1: Datos Limpios Iniciales
```bash
# Scraper desde START_ID (limpio desde BD antes)
TRUNCATE guias CASCADE;
START_ID=42022341
docker-compose up -d
```

### Caso 2: Retomar desde Checkpoint
```bash
# Arranca automáticamente desde last_id_processed
docker-compose up -d
```

### Caso 3: Múltiples Rangos en Paralelo
```bash
# docker-compose.prod.yml con 3 servicios scraper
docker-compose -f docker-compose.yml \
               -f docker-compose.prod.yml up -d
```

## 📞 Puntos de Contacto

| Pregunta | Archivo |
|----------|---------|
| ¿Cómo empiezo? | SETUP_RÁPIDO.md |
| ¿Cómo despliego? | DEPLOYMENT.md |
| ¿Cómo optimizo? | OPTIMIZATION_GUIDE.md |
| ¿Qué cambió? | SUMMARY.md |
| ¿Cómo funciona? | README.md |
| ¿Errores? | TROUBLESHOOTING.md (próx) |

---

**Última actualización**: 2026-05-04
