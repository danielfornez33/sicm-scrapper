# 🤝 Guía de Contribuciones

¡Gracias por tu interés en contribuir al SICM Scraper!

## 📋 Código de Conducta

Este proyecto sigue el [Contributor Covenant](https://www.contributor-covenant.org/).
Al participar, se espera que mantengas este código.

## 🚀 Cómo Contribuir

### 1. Reportar Bugs

Usa GitHub Issues para reportar bugs. Incluye:
- Descripción clara del problema
- Pasos para reproducir
- Comportamiento esperado vs actual
- Screenshots si aplica

### 2. Sugerir Features

Usa GitHub Issues para sugerir features. Incluye:
- Descripción del problema que resuelve
- Propuesta de solución
- Alternativas consideradas

### 3. Pull Requests

#### Proceso:
1. Fork el repo
2. Crea una rama (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'feat: add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

#### Standards de Código:
- Usamos **ruff** para linting
- Usamos **mypy** para type checking
- Usamos **pytest** para tests
- follow **Black** formatting (line-length: 100)

#### Commits:
Seguimos [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add new feature
fix: fix a bug
docs: update documentation
style: code style changes
refactor: code refactoring
test: add tests
chore: maintenance
```

### 4. Desarrollo Local

```bash
# Clonar repo
git clone https://github.com/danielfornez33/sicm-scrapper.git
cd sicm-scrapper

# Crear virtualenv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -e ".[dev]"

# Instalar browsers para Scrapling
scrapling install

# Correr tests
pytest tests/ -v

# Correr linter
ruff check src/

# Correr type checker
mypy src/
```

### 5. Testing

- Escribe tests para nuevas funcionalidades
- Mantén la cobertura de código
- Ejecuta todos los tests antes de hacer PR

```bash
# Tests con coverage
pytest tests/ --cov=src --cov-report=html
```

## 📝 Documentación

- Actualiza README.md si agregas features
- Agrega docstrings a nuevas funciones
- Mantén los docs claros y concisos

## 🏷️ Etiquetas de Issues

| Etiqueta | Descripción |
|----------|-------------|
| `bug` | Bug reportado |
| `feature` | Nueva feature |
| `enhancement` | Mejora de feature existente |
| `documentation` | Cambios en documentación |
| `good first issue` | Ideal para principiantes |
| `help wanted` | Necesita ayuda |

## 💬 Canales de Comunicación

- GitHub Issues para bugs y features
- GitHub Discussions para preguntas

## ⚖️ Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo BSD-3-Clause.

---

¡Gracias por tu contribución! 🎉