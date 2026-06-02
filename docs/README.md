# 📚 Intelligence Terminal - Documentación

## Estructura de Documentación

### 📐 Arquitectura & Diseño
- **[ARCHITECTURE.md](architecture/ARCHITECTURE.md)** - Diseño completo del sistema
- **[ROADMAP.md](architecture/ROADMAP.md)** - Plan de desarrollo en 10 fases
- **[PROJECT_STRUCTURE.md](architecture/PROJECT_STRUCTURE.md)** - Estructura del proyecto

### 📊 Reportes & Auditorías
- **[COMPLETION_REPORT.md](reports/COMPLETION_REPORT.md)** - Reporte de completitud (FASE 1)
- **[AUDIT_REPORT.md](reports/AUDIT_REPORT.md)** - Auditoría de código
- **[PHASE_1_SUMMARY.md](reports/PHASE_1_SUMMARY.md)** - Resumen FASE 1
- **[FINAL_SUMMARY.txt](reports/FINAL_SUMMARY.txt)** - Resumen final

### 📖 Guías de Instalación & Setup
Ver [SETUP.md](../SETUP.md) en la raíz del proyecto

## Navegación Rápida

| Componente | Ubicación | Descripción |
|-----------|-----------|------------|
| Backend | `/backend/` | FastAPI + Python 3.11 + Celery |
| Frontend | `/frontend/` | Next.js 15 + React 19 + TypeScript |
| Database | `/database/` | PostgreSQL 15 + TimescaleDB |
| Infrastructure | `/docker/` | Docker + Docker Compose |
| Scripts | `/backend/scripts/` | Scripts de setup y utilidades |
| Documentación | `/docs/` | Toda la documentación del proyecto |

## Próximos Pasos

1. **FASE 2**: Market Data Engine
   - Implementar ingesta de datos en tiempo real
   - Integrar APIs de proveedores de datos
   - Validar calidad de datos

2. **FASE 3**: Macro Engine
   - Detección automática de regímenes de mercado
   - Análisis macro fundamental

3. **FASE 4-7**: Engines de Análisis
   - Smart Money Concepts (SMC)
   - Análisis de volatilidad
   - Correlaciones de activos

## Contacto & Recursos

- 📧 Para consultas, revisar los documentos en `/docs/architecture/`
- 🐳 Docker está configurado en `docker-compose.yml`
- 🚀 Comandos de desarrollo en [SETUP.md](../SETUP.md)
