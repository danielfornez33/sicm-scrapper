# EXPLICACIÓN DEL SCRAPER SICM - Guías de Venezuela

Este documento sirve como referencia para reescribir y optimizar el scraper del Sistema de Información de Comercialización de Medicamentos de Venezuela (SICM).

## 1. CONTEXTO DEL PROYECTO

### 1.1 Objetivo
Scrapear datos de guías de medicamentos del sitio web del SICM (www.sicm.gob.ve) y almacenarlos en PostgreSQL para análisis de inteligencia de negocios.

### 1.2 Estructura Actual del Proyecto

```
/home/scraper/
├── src/
│   ├── scraper.py          # Scraper principal asíncrono
│   ├── parser.py         # Parser HTML (BeautifulSoup + regex)
│   ├── config.py        # Configuración via environment variables
│   ├── cli.py          # Interfaz CLI básica
│   ├── cli_enhanced.py # CLI mejorado con web dashboard
│   ├── scraper/        # Módulos adicionales
│   │   ├── core.py        # Core del scraper mejorado
│   │   ├── proxy_manager.py # Gestión de proxies
│   │   └── ...
│   ├── database/       # Operaciones de base de datos
│   │   ├── db.py
│   │   ├── operations.py
│   │   └── models.py
│   └── monitoring/    # Dashboard web de monitoreo
│       ├── metrics.py
│       └── web_dashboard.py
├── scraper.log       # Log principal
└── scraper_*.log    # Logs de ejecuciones anteriores
```

### 1.3 Base de Datos
- **Host**: PostgreSQL en contenedor Docker
- **Database**: `farmapatria`
- **Tablas principales**:
  - `guias` - Guía de transporte (cabecera)
  - `guia_productos` - Productos de cada guía
  - `establecimientos` - Droguerías/farmacias
  - `progress` - Control de progreso del scrape

---

## 2. FUENTE DE DATOS: SICM

### 2.1 Endpoint Principal
```
URL: http://www.sicm.gob.ve/g_4cguia.php
Parámetro: id_guia (integer)
```

Ejemplo de request:
```
GET http://www.sicm.gob.ve/g_4cguia.php?id_guia=31594748
```

### 2.2 Estructura HTML de Respuesta
El HTML sigue un patrón de tabla con:
- `<strong>` para etiquetas
- `<td>` adjacent para valores

```html
<td><strong>Campo:</strong></td><td>VALOR</td>
```

### 2.3 Campos a Extraer
| Campo | Descripción | Tipo |
|-------|-----------|------|
| Nro Guia | ID único de la guía | integer |
| Estatus | Estado (APROBADA, Abierta, RECIBIDA, etc.) | string |
| Fecha de Emisión | Fecha de emisión | datetime |
| Fecha de Vencimiento | Fecha de vencimiento | date |
| Bultos | Número de bultos | integer |
| Renglones | Número de renglones | integer |
| Unidades | Total de unidades | integer |
| Origen - Razón | Razón social origen | string |
| Origen - RIF | RIF origen | string |
| Origen - Tipo | Tipo de establecimiento | string |
| Origen - Dirección | Dirección origen | string |
| Origen - Estado/Ciudad | Ubicación origen | string |
| Destino - Razón | Razón social destino | string |
| Destino - RIF | RIF destino | string |
| Destino - Tipo | Tipo de establecimiento | string |
| Destino - Dirección | Dirección destino | string |
| Destino - Estado/Ciudad | Ubicación destino | string |
| Productos | Lista de productos (nombre, lote, cantidad) | array |

### 2.4 Rangos de IDs Observados
- **Mínimo**: ~31,594,748
- **Máximo**: ~42,591,276
- **Último scrape**: 42,022,340 (checkpoint)

---

## 3. ERRORES Y PROBLEMAS IDENTIFICADOS

### 3.1 Errores Críticos

| # | Problema | Ubicación | Severidad | Descripción |
|---|---------|----------|----------|----------|------------|
| 1 | **Código muerto en parser** | `parser.py:18-20` | Baja | Líneas duplicadas e inalcanzables en `_clean()` |
| 2 | **ProxyManager sin proxies** | `scraper/proxy_manager.py` | Alta | Warning repetitivo cada Request; sin proxies disponibles |
| 3 | **Progreso negativo** | `scraper/core.py` | Alta | Cálculo de ETA muestra -7386% (error de math) |
| 4 | **Batch no guarda** | `scraper.py:131` | Alta | Batch llena pero no hace flush; pierde datos |
| 5 | **Memory leak** | Concurrency | Media | Acumula tareas sin completar en memoria |

### 3.2 Errores Menores

| # | Problema | Ubicación | Descripción |
|---|---------|----------|------------|
| 1 | **Logging excesivo** | Varios | 100+ warnings/segundo llena logs |
| 2 | **Regex ineficiente** | `parse_productos` | `<tr>.*?</tr>` puede faller con HTML malformado |
| 3 | **Sin cleanup de sesión** | `scraper.py:42` | Sesión no se cierra correctamente en errores |
| 4 | **Retry logic mala** | `scraper.py:79` | Usa `last_not_found` sin definir |

### 3.3温水煮青蛙 (Problemas Silentes)

1. **Sin validación de datos**: Se insertan guías con 0 productos
2. **Duplicados**: Mismo ID puede insertarse múltiples veces
3. **Outliers**: Guías con >1,000,000 unidades (errores de datos)
4. **Timeout muy corto**: 30s puede fallar en red lenta
5. **Sin chunking de IDs**: Processa todo en memoria

---

## 4. DATOS LIMPIOS REALIZADOS

### 4.1 Errores de Datos Encontrados
- **Guías con >100,000 unidades**: 607 registros (outliers)
- **"NO ESTA REGISTRADO EL PRODUCTO"**: 1,211,697 registros (producto desconocido)
- **Productos NULL o vacíos**: Múltiples entradas inválidas

### 4.2 Limpezas Aplicadas
```sql
-- Eliminar guías con más de 1M de unidades (outliers)
DELETE FROM guias WHERE unidades > 1000000;

-- Filtrar en consultas futuras
AND gp.producto IS NOT NULL 
AND gp.producto != ''
AND gp.producto != 'NO ESTA REGISTRADO EL PRODUCTO'
AND gp.cantidad < 1000000
```

### 4.3 Estatus Reales Encontrados
Los valores únicos en la tabla `estatus`:
- `APROBADA`
- `Abierta`
- `RECIBIDA`

**NO** usar: 'Activa', 'Pendiente', etc.

---

## 5. CONSULTAS ÚTILES DE ANÁLISIS

### 5.1 top 20 Productos (Últimos 3 Meses)
```sql
WITH total_market AS (
  SELECT SUM(gp.cantidad) as total
  FROM guia_productos gp
  INNER JOIN guias g ON gp.id_guia = g.id_guia
  WHERE g.estatus IN ('APROBADA', 'Abierta', 'RECIBIDA')
    AND g.fecha_emision >= NOW() - INTERVAL '3 months'
    AND gp.producto IS NOT NULL 
    AND gp.producto != ''
    AND gp.producto != 'NO ESTA REGISTRADO EL PRODUCTO'
    AND gp.cantidad < 1000000
),
top_products AS (
  SELECT gp.producto, SUM(gp.cantidad) as cantidad
  FROM guia_productos gp
  INNER JOIN guias g ON gp.id_guia = g.id_guia
  WHERE g.estatus IN ('APROBADA', 'Abierta', 'RECIBIDA')
    AND g.fecha_emision >= NOW() - INTERVAL '3 months'
    AND gp.producto IS NOT NULL 
    AND gp.producto != ''
    AND gp.producto != 'NO ESTA REGISTRADO EL PRODUCTO'
    AND gp.cantidad < 1000000
  GROUP BY gp.producto
  ORDER BY cantidad DESC
  LIMIT 20
)
SELECT tp.producto, tp.cantidad, ROUND(100.0 * tp.cantidad / tm.total, 2) as pct
FROM top_products tp, total_market tm
ORDER BY tp.cantidad DESC;
```

### 5.2 Clasificación de Droguerías por Comportamiento
```sql
WITH pharmacy_metrics AS (
  SELECT 
    destino_razon AS pharmacy,
    destino_estado_ciudad AS estado_ciudad,
    COUNT(*) AS total_compras,
    COUNT(DISTINCT DATE_TRUNC('month', fecha_emision)) AS meses_activos,
    MAX(fecha_emision) AS ultima_compra
  FROM guias 
  WHERE estatus IN ('APROBADA', 'Abierta', 'RECIBIDA')
    AND destino_tipo = 'Farmacias Comerciales'
    AND destino_razon IS NOT NULL
  GROUP BY destino_razon, destino_estado_ciudad
)
SELECT 
  pm.pharmacy,
  pm.estado_ciudad,
  pm.total_compras,
  pm.meses_activos,
  CASE 
    WHEN pm.total_compras >= 1000 AND pm.meses_activos >= 4 THEN '🟢 Top'
    WHEN pm.total_compras >= 300 AND pm.meses_activos >= 3 THEN '🔵 Estable'
    WHEN pm.total_compras >= 50 AND pm.meses_activos >= 2 THEN '🟡 Promedio'
    WHEN (NOW() - pm.ultima_compra) > INTERVAL '60 days' THEN '🟠 Riesgoso'
    ELSE 'Promedio'
  END AS clasificacion
FROM pharmacy_metrics pm
ORDER BY pm.total_compras DESC;
```

### 5.3 Score de Crédito de Cliente (1-1000)
```sql
WITH pharmacy_metrics AS (
  SELECT 
    destino_razon AS pharmacy,
    destino_estado_ciudad AS estado_ciudad,
    COUNT(*) AS total_compras,
    SUM(unidades) AS unidades_totales,
    COUNT(DISTINCT DATE_TRUNC('month', fecha_emision)) AS meses_activos,
    MAX(fecha_emision) AS ultima_compra,
    MIN(fecha_emision) AS primera_compra,
    AVG(unidades) AS promedio_unidades
  FROM guias 
  WHERE estatus IN ('APROBADA', 'Abierta', 'RECIBIDA')
    AND destino_tipo = 'Farmacias Comerciales'
    AND destino_razon IS NOT NULL
  GROUP BY destino_razon, destino_estado_ciudad
),
monthly_counts AS (
  SELECT destino_razon, DATE_TRUNC('month', fecha_emision) AS mes, COUNT(*) as c
  FROM guias 
  WHERE estatus IN ('APROBADA', 'Abierta', 'RECIBIDA')
    AND destino_tipo = 'Farmacias Comerciales'
  GROUP BY destino_razon, DATE_TRUNC('month', fecha_emision)
),
consistency AS (
  SELECT destino_razon, STDDEV(c) as std, AVG(c) as avg 
  FROM monthly_counts GROUP BY destino_razon
)
SELECT
  pm.pharmacy,
  pm.total_compras,
  pm.unidades_totales,
  GREATEST(1, LEAST(1000,
    LEAST(200, pm.total_compras / 10) +  -- Volumen
    GREATEST(0, 200 - COALESCE(c.std, 0) / NULLIF(c.avg, 0) * 100) +  -- Consistencia
    CASE WHEN NOW() - pm.ultima_compra < '15 days' THEN 200
         WHEN NOW() - pm.ultima_compra < '30 days' THEN 160
         WHEN NOW() - pm.ultima_compra < '60 days' THEN 100
         WHEN NOW() - pm.ultima_compra < '90 days' THEN 50
         ELSE 0 END  -- Recencia
  )) AS credit_score,
  CASE WHEN pm.total_compras >= 1000 THEN '🟢 Top'
       WHEN pm.total_compras >= 300 THEN '🔵 Estable'
       WHEN pm.total_compras >= 50 THEN '🟡 Promedio'
       ELSE '🟠 Riesgoso' END AS clasificacion
FROM pharmacy_metrics pm
LEFT JOIN consistency c ON pm.pharmacy = c.destino_razon
ORDER BY credit_score DESC;
```

---

## 6. RECOMENDACIONES PARA REESCRIBIR

### 6.1 Arquitectura Propuesta

```
scraper_v2/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py           # Configuración centralizada
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── client.py      # HTTP client (aiohttp)
│   │   ├── parser.py     # Parser HTML
│   │   ├── rate_limiter.py # Adaptive rate limiting
│   │   └── storage.py    # PostgreSQL storage
│   ├── models/            # Pydantic models
│   ├── tests/            # pytest
│   └── pyproject.toml
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

### 6.2 Mejoras Prioritarias

| # | Mejora | Beneficio | Dificult |
|---|-------|---------|---------|
| 1 | PostgreSQL COPY | 10x más rápido bulk insert | Media |
| 2 | Adaptive rate limiting | Evitar bloqueos | Alta |
| 3 | Circuit breaker | Detectar SICM caído | Media |
| 4 | Retry exponencial + jitter | Resistencia a errores | Baja |
| 5 | Shutdown graceful | Cleanup correcto | Baja |
| 6 | Tipado con mypy | Menos bugs | Baja |
| 7 | Tests unitarios | Confianza | Media |

### 6.3 Cosas a NO Cambiar

- **Parser de productos** (`parse_productos`): Funciona bien
- **Estructura de DB**: Ya optimizada
- **Filtros de estatus**: 'APROBADA', 'Abierta', 'RECIBIDA'

### 6.4 Configuración Recomendada

```env
# .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=farmapatria
DB_USER=postgres
DB_PASS=postgres

# Scraping
START_ID=42022341
END_ID=42591276
CONCURRENCY=20
DELAY_MS=50
REQUEST_TIMEOUT=60
MAX_RETRIES=5

# Rate limiting
RATE_LIMIT_RPS=10
CIRCUIT_BREAKER_THRESHOLD=10
```

---

## 7. ESTADO ACTUAL DE LOS DATOS

### 7.1 Resumen de Datos
| Métrica | Valor |
|--------|-------|
| Total guías scrapeadas | ~1,000,000+ |
| Total productos | ~10,000,000+ |
| Fecha más antigua | 2023-01-02 |
| Fecha más reciente | 2026-04-06 |
| checkpoint actual | 42,022,340 |

### 7.2 Rangos de Score de Clientes
| Clasificación | Cantidad | Descripción |
|---------------|----------|------------|
| 🟢 Top | ~12 | Compras ≥1000, ≥4 meses activos |
| 🔵 Estable | ~570 | Compras ≥300, ≥3 meses activos |
| 🟡 Promedio | ~4,896 | Compras ≥50, ≥2 meses activos |
| 🟠 Riesgoso | ~67 | Sin compras en >60 días |

---

## 8. CONTACTOS Y CREDENCIALES

- **Redash**: http://localhost:5001
- **Credenciales**: admin@example.com / empresa123
- **API Key Redash**: JROrjSVxOJgfIgwMOSQ8SuVVB8gEvpEAZoFQegMZ

---

*Documento generado para参考 en la reescritura del scraper. Actualizado: 2026-05-04*