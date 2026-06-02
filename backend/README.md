# Backend - Trading Terminal

## Estructura

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada FastAPI
│   ├── tasks.py             # Tareas Celery
│   ├── api/                 # Rutas de API
│   ├── core/                # Configuración core
│   ├── db/                  # Acceso a base de datos
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Schemas Pydantic
│   ├── services/            # Lógica de negocio
│   ├── utils/               # Utilidades
│   └── trading/             # Módulo de trading
├── scripts/                 # Scripts de setup y utils
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## Comandos Principales

```bash
# Instalación local
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt

# Correr servidor dev
uvicorn app.main:app --reload

# Correr Celery worker
celery -A app.tasks worker --loglevel=info

# Correr Celery beat (scheduler)
celery -A app.tasks beat --loglevel=info
```

## Stack Técnico

- **Framework**: FastAPI
- **Python**: 3.11+
- **Base de Datos**: PostgreSQL + TimescaleDB
- **Cache**: Redis
- **Async Jobs**: Celery
- **ORM**: SQLAlchemy
- **Validación**: Pydantic

## Servicios Principales

1. **Market Data Service** - Ingesta y procesamiento de datos de mercado
2. **Macro Engine** - Análisis de regímenes y contexto macro
3. **Analysis Service** - SMC, volatilidad, correlaciones
4. **AI Service** - Análisis impulsado por IA

## Status

✅ FASE 1: Arquitectura & Setup completada
🎯 FASE 2: Market Data Engine (próximo)

Para más detalles, ver [/docs/architecture/ARCHITECTURE.md](/docs/architecture/ARCHITECTURE.md)
