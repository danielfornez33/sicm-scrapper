# ⚡ Setup Rápido - SICM Scraper v2.0

**Para los impacientes que solo quieren que funcione en 5 minutos.**

## Opción 1: Docker (Recomendado)

```bash
# 1. Clonar/descargar
git clone <REPO_URL> sicm-scraper
cd sicm-scraper

# 2. Copiar configuración
cp .env.example .env

# 3. IMPORTANTE: Cambiar contraseña en .env
nano .env
# Cambiar: DB_PASS=changeme → DB_PASS=tu_password_aqui

# 4. Iniciar
docker-compose up -d

# 5. Monitorear
docker-compose logs -f scraper
```

**Listo.** Puede tomar ~10 segundos en iniciar. Busca en los logs:
```
✓ "spider_starting: start_id=42022341"
✓ "batch_flushed: inserted=1000"
```

## Opción 2: Local (Sin Docker)

```bash
# 1. Python 3.10+
python3 --version

# 2. Dependencias
pip install -e ".[all]"
scrapling install

# 3. PostgreSQL corriendo
sudo service postgresql start

# 4. Base de datos
createdb farmapatria

# 5. Variables de entorno
cp .env.example .env
# Editar .env si es necesario

# 6. Ejecutar
python src/main.py
```

## Verificar que Funciona

```bash
# Opción Docker
docker-compose exec postgres psql -U postgres -d farmapatria \
  -c "SELECT COUNT(*) FROM guias;"

# Opción Local
psql -U postgres -d farmapatria -c "SELECT COUNT(*) FROM guias;"
```

Debería incrementarse cada 5-10 segundos.

## Pausar/Reanudar

```bash
# Docker
docker-compose pause scraper    # Pausa (sin perder datos)
docker-compose unpause scraper  # Continúa

# Local
Ctrl+C                          # Pausa
python src/main.py             # Continúa
```

## Si Algo Falla

### Error: "Connection refused"
```bash
# Docker
docker-compose restart postgres
docker-compose logs postgres

# Local
sudo service postgresql restart
```

### Error: "Out of memory"
Editar `.env`:
```env
CONCURRENCY=5       # De 20 a 5
BATCH_SIZE=100      # De 1000 a 100
```

### Scraper muy lento
Aumentar concurrencia en `.env`:
```env
CONCURRENCY=40
```

## Estadísticas

```bash
# Después de 1 hora
docker-compose exec postgres psql -U postgres -d farmapatria \
  -c "SELECT COUNT(*), SUM(unidades) FROM guias;"

# Después de 24 horas (esperado)
# ~480,000 guías
# ~45,000,000 unidades
# ~1,200 farmacias únicas
```

## URLs de Monitoreo (Opcional)

```
Prometheus: http://localhost:9091
Grafana:    http://localhost:3000
```

Iniciar con:
```bash
docker-compose --profile monitoring up -d
```

## Datos Guardados

```
logs/              - Logs del scraper
checkpoints/       - Progreso (puedes eliminar para resetear)
PostgreSQL         - Datos persistentes en volumen Docker
```

---

**¿Más detalles?** Lee `README.md` o `DEPLOYMENT.md`

**¿Problemas?** Revisa `TROUBLESHOOTING.md`
