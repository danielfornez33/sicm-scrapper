# 🚀 Guía de Deployment en VPS

Instrucciones paso a paso para desplegar el scraper SICM en un VPS (recomendado: Ubuntu 22.04 LTS).

## Requisitos Previos

- VPS con mínimo 4GB RAM, 2 CPU cores
- Acceso root o sudo
- Puerto 5432 abierto (PostgreSQL - red interna)
- Puerto 9090 abierto (Prometheus metrics - opcional)

## Paso 1: Preparar el Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias base
sudo apt install -y \
  curl \
  wget \
  git \
  net-tools \
  htop \
  vim

# Crear usuario dedicado (opcional pero recomendado)
sudo useradd -m -s /bin/bash sicm_user
sudo usermod -aG sudo sicm_user
```

## Paso 2: Instalar Docker

```bash
# Descargar e instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker (evita usar sudo cada vez)
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalación
docker --version
docker-compose --version
```

## Paso 3: Clonar Repositorio

```bash
# Navegar a directorio de aplicaciones
cd /opt
sudo mkdir -p sicm-scraper
sudo chown $USER:$USER sicm-scraper

# Clonar repo
cd sicm-scraper
git clone <REPO_URL> .

# O descargar directamente si no está en git
# wget -O scraper.tar.gz <TAR_URL>
# tar -xzf scraper.tar.gz
```

## Paso 4: Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env

# Editar con tus valores (usar vim o nano)
nano .env
```

Asegúrate de cambiar especialmente:

```env
# ⚠️ CRÍTICO - Cambiar contraseña
DB_PASS=tu_password_super_seguro_aqui

# Rango de IDs (ajustar según necesidad)
START_ID=42022341
END_ID=42591276

# Performance (ajustar según CPU/RAM disponible)
CONCURRENCY=20        # 2 CPUs → 10-20
BATCH_SIZE=1000
```

## Paso 5: Crear Volúmenes de Persistencia

```bash
# Crear directorios para datos
mkdir -p logs checkpoints data

# Cambiar permisos
chmod 755 logs checkpoints data

# Verificar estructura
tree -L 1 -a
```

## Paso 6: Iniciar Servicios

```bash
# Iniciar PostgreSQL + Scraper
docker-compose up -d

# Esperar a que PostgreSQL esté listo (30s)
sleep 30

# Verificar estado
docker-compose ps
```

Debería mostrar:
```
NAME                COMMAND                  SERVICE             STATUS
sicm_postgres       "docker-entrypoint..."   postgres            Up (healthy)
sicm_scraper        "python -m src.main"     scraper             Up
```

## Paso 7: Monitorear Progreso

```bash
# Ver logs en tiempo real
docker-compose logs -f scraper

# Ver últimas 100 líneas
docker-compose logs --tail 100 scraper

# Filtrar por nivel (ERROR, WARNING, INFO)
docker-compose logs scraper | grep ERROR
```

### Indicadores de Éxito

```
✓ "spider_starting: start_id=42022341 end_id=42591276 total_range=568935"
✓ "batch_flushed: inserted=1000 skipped=5 rps=125.34 eta=6h 30m"
✓ "DB - Total guías: 1,250,000"
```

## Paso 8: Verificar Base de Datos

```bash
# Acceder a psql
docker-compose exec postgres psql -U postgres -d farmapatria

# Contar guías scrapeadas
SELECT COUNT(*) FROM guias;

# Ver progreso
SELECT * FROM progress;

# Ver últimas guías insertadas
SELECT id_guia, estatus, created_at FROM guias ORDER BY id_guia DESC LIMIT 5;

# Salir
\q
```

## 📊 Monitoreo en Producción

### Opción 1: Logs Básicos (Recomendado para VPS pequeños)

```bash
# Crear cron para verificar cada hora
crontab -e

# Agregar:
0 * * * * docker-compose -f /opt/sicm-scraper/docker-compose.yml logs --tail 1 scraper >> /opt/sicm-scraper/monitoring.log 2>&1
```

### Opción 2: Prometheus + Grafana (Para VPS 8GB+)

```bash
# Iniciar con profile de monitoring
docker-compose --profile monitoring up -d

# Acceder a dashboards
# Prometheus: http://SERVIDOR_IP:9091
# Grafana: http://SERVIDOR_IP:3000 (admin/admin)
```

## 🛑 Gestión del Scraper

### Pausar Scraper (sin perder datos)

```bash
docker-compose pause scraper
```

### Reanudar desde Checkpoint

```bash
docker-compose unpause scraper
# o
docker-compose start scraper
```

### Detener Completamente

```bash
docker-compose down
```

**Nota**: Los datos en PostgreSQL y checkpoints se preservan.

### Reiniciar (clean slate)

```bash
# ⚠️ CUIDADO: Esto borra TODOS los datos
docker-compose down -v
docker-compose up -d
```

## 🔍 Troubleshooting

### Error: "Cannot connect to Docker daemon"

```bash
# Verificar que Docker está corriendo
sudo systemctl restart docker
sudo systemctl status docker

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker
```

### Error: "Connection refused" a PostgreSQL

```bash
# Verificar que PostgreSQL está corriendo
docker-compose ps postgres

# Ver logs de PostgreSQL
docker-compose logs postgres

# Reiniciar PostgreSQL
docker-compose restart postgres
```

### Scraper se detiene frecuentemente

```bash
# Revisar logs de error
docker-compose logs scraper | grep ERROR

# Posibles causas:
# 1. Timeout de conexión → aumentar REQUEST_TIMEOUT a 90s
# 2. SICM bloqueando → reducir CONCURRENCY a 10
# 3. OOM (Out of Memory) → reducir BATCH_SIZE a 500
```

### Base de datos está llena

```bash
# Ver tamaño de BD
docker-compose exec postgres psql -U postgres -d farmapatria \
  -c "SELECT pg_size_pretty(pg_database_size('farmapatria'));"

# Limpiar índices no usados
docker-compose exec postgres psql -U postgres -d farmapatria \
  -c "VACUUM FULL ANALYZE;"
```

## 🔐 Seguridad en Producción

### 1. Cambiar Contraseñas

```bash
# En .env
DB_PASS=contraseña_fuerte_de_20_caracteres

# En PostgreSQL
docker-compose exec postgres psql -U postgres -d farmapatria
ALTER ROLE postgres WITH PASSWORD 'nueva_contraseña';
\q
```

### 2. Firewall (UFW en Ubuntu)

```bash
# Permitir SSH
sudo ufw allow 22/tcp

# Permitir SOLO PostgreSQL desde red interna
sudo ufw allow from 10.0.0.0/8 to any port 5432

# Permitir Prometheus (red interna)
sudo ufw allow from 10.0.0.0/8 to any port 9090

# Habilitar firewall
sudo ufw enable
```

### 3. Backup Automático

```bash
# Crear script de backup
cat > /opt/sicm-scraper/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/sicm-scraper/backups"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
docker-compose exec -T postgres pg_dump -U postgres farmapatria | \
  gzip > $BACKUP_DIR/farmapatria_$TIMESTAMP.sql.gz
# Mantener solo los últimos 30 backups
find $BACKUP_DIR -name "farmapatria_*.sql.gz" -mtime +30 -delete
EOF

chmod +x /opt/sicm-scraper/backup.sh

# Agregar a cron (diario a las 2 AM)
crontab -e
# Agregar: 0 2 * * * /opt/sicm-scraper/backup.sh
```

## 📈 Optimización de Performance

### Ajustar según CPU/RAM

| Specs | CONCURRENCY | BATCH_SIZE | DB_POOL |
|-------|-------------|------------|---------|
| 2 CPU / 4GB | 10 | 500 | 5-10 |
| 4 CPU / 8GB | 20 | 1000 | 10-20 |
| 8 CPU / 16GB | 40 | 2000 | 20-30 |

### Monitoreo de Recursos

```bash
# Ver uso de CPU/RAM en tiempo real
watch -n 1 'docker stats'

# Si MEMORY% > 80% → reducir BATCH_SIZE
# Si CPU% > 70% constantemente → reducir CONCURRENCY
```

### Índices de Base de Datos

Los índices ya están creados automáticamente:
- `idx_guias_estatus`
- `idx_guias_fecha_emision`
- `idx_guias_destino_razon`
- `idx_guia_productos_id_guia`
- `idx_guia_productos_producto`

Para queries frecuentes, agregar más:

```bash
docker-compose exec postgres psql -U postgres -d farmapatria << 'EOF'
CREATE INDEX idx_guias_unidades ON guias(unidades);
CREATE INDEX idx_guias_origen_razon ON guias(origen_razon);
ANALYZE;
EOF
```

## 📞 Mantenimiento

### Limpiar Logs Antiguos

```bash
# Mantener solo últimos 7 días
find logs/ -name "*.log" -mtime +7 -delete

# O agregar a cron
cat >> /var/spool/cron/crontabs/$USER << 'EOF'
0 3 * * * find /opt/sicm-scraper/logs -name "*.log" -mtime +7 -delete
EOF
```

### Ver Estadísticas de Scraping

```bash
# Conectarse a BD
docker-compose exec postgres psql -U postgres -d farmapatria

# Guías totales
SELECT COUNT(*) as total_guias FROM guias;

# Distribución por estatus
SELECT estatus, COUNT(*) FROM guias GROUP BY estatus;

# Unidades por destino (top 10)
SELECT destino_razon, SUM(unidades) FROM guias 
GROUP BY destino_razon ORDER BY 2 DESC LIMIT 10;

# Último ID procesado
SELECT last_id_processed FROM progress;
```

## ✅ Checklist de Deployment

- [ ] VPS con 4GB RAM mínimo
- [ ] Docker instalado y corriendo
- [ ] Repositorio clonado en `/opt/sicm-scraper`
- [ ] `.env` configurado con DB_PASS seguro
- [ ] PostgreSQL iniciado y saludable
- [ ] Scraper iniciado sin errores críticos
- [ ] Logs mostrando "spider_starting"
- [ ] Base de datos con primeras guías insertadas
- [ ] Firewall configurado
- [ ] Backup automático configurado
- [ ] Monitoreo en lugar (logs o Prometheus)

---

**Para soporte**: Revisar TROUBLESHOOTING.md o contactar al equipo.
