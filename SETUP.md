# 🔧 GUÍA DE SETUP - INTELLIGENCE TERMINAL

**Última actualización**: 31-May-2026  
**Versión**: 0.1.0

---

## 📋 REQUISITOS PREVIOS

### Sistema
- Windows 10/11, macOS 12+, o Linux (Ubuntu 20.04+)
- 8GB RAM mínimo (16GB recomendado)
- 50GB espacio en disco

### Software
- **Docker Desktop** 4.20+
- **Git** 2.40+
- **Python 3.11+** (si desarrollas localmente)
- **Node.js 20+** (si desarrollas frontend)
- **PostgreSQL 15+** (si ejecutas sin Docker)

---

## 🐳 OPCIÓN A: SETUP CON DOCKER (Recomendado)

### 1. Preparar Ambiente

```bash
# Clonar repositorio
git clone <your-repo-url> intelligence_terminal
cd intelligence_terminal

# Crear archivo .env desde template
cp .env.example .env

# Editar .env con tus valores
# Windows: notepad .env
# macOS/Linux: nano .env
```

### 2. Iniciar Servicios

```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f fastapi
```

### 3. Verificar Setup

```bash
# Health check
curl http://localhost:8000/health

# Acceder a servicios
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090
```

### 4. Seed Data (Opcional)

```bash
# Cargar datos iniciales
docker-compose exec postgres psql -U postgres -d intelligence_terminal \
  -f /docker-entrypoint-initdb.d/init.sql

# Verificar
docker-compose exec postgres psql -U postgres -d intelligence_terminal \
  -c "SELECT COUNT(*) FROM symbols;"
```

---

## 💻 OPCIÓN B: SETUP LOCAL (Desarrollo Avanzado)

### 1. PostgreSQL + TimescaleDB

```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu
sudo apt-get install postgresql-15 postgresql-15-timescaledb

# Windows
# Descargar https://www.postgresql.org/download/windows/

# Crear base de datos
psql -U postgres -c "CREATE DATABASE intelligence_terminal;"

# Cargar schema
psql -U postgres -d intelligence_terminal -f database/init.sql

# Habilitar TimescaleDB
psql -U postgres -d intelligence_terminal \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### 2. Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis-server

# Windows (usar WSL2 o Docker solo para Redis)
docker run -d -p 6379:6379 redis:7.2-alpine
```

### 3. Backend (FastAPI)

```bash
cd backend

# Crear virtual environment
python -m venv venv

# Activar venv
# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env
cp ../.env.example .env
# Editar con valores locales

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend (Next.js)

```bash
cd frontend

# Instalar dependencias
npm install

# Crear .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Ejecutar en dev
npm run dev
```

### 5. Verificar Setup

```bash
# Backend health
curl http://localhost:8000/health

# Frontend
open http://localhost:3000
```

---

## 🐛 TROUBLESHOOTING

### Docker Issues

```bash
# Limpiar todo y reiniciar
docker-compose down -v
docker-compose up -d

# Ver logs específicos
docker-compose logs postgres
docker-compose logs fastapi
docker-compose logs redis

# Rebuild images
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection

```bash
# Probar conexión PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/intelligence_terminal

# Probar conexión Redis
redis-cli ping
# Debe responder: PONG

# Ver estado de base de datos
docker-compose exec postgres psql -U postgres -d intelligence_terminal \
  -c "\dt;"  # Ver tablas
```

### API Issues

```bash
# Ver logs de FastAPI
docker-compose logs -f fastapi

# Probar endpoint
curl -v http://localhost:8000/docs

# Probar con datos
curl -X GET http://localhost:8000/health
```

### Frontend Issues

```bash
# Limpiar cache Next.js
rm -rf frontend/.next
npm run build

# Reinstalar node_modules
rm -rf frontend/node_modules
npm install
```

---

## 🔑 Configuración Importante

### Variables de Entorno Críticas

```env
# OBLIGATORIO para desarrollo
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/intelligence_terminal
REDIS_URL=redis://localhost:6379

# APIs (dejar vacío = funciones deshabilitadas)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=claude-...

# JWT (cambiar en producción)
JWT_SECRET_KEY=your-secret-key-change-in-production

# Development
DEBUG=True
ENVIRONMENT=development
```

### Credenciales Iniciales

```
Grafana:
- Usuario: admin
- Contraseña: admin
(Cambiar en primera entrada)

PostgreSQL:
- Usuario: postgres
- Contraseña: postgres
(Cambiar en producción)

Redis:
- No requiere auth por defecto
```

---

## 📊 Verificar Instalación Completa

```bash
# Script de verificación
./scripts/verify_setup.sh  # En desarrollo

# Manual
# 1. PostgreSQL
psql -U postgres -d intelligence_terminal -c "SELECT version();"

# 2. TimescaleDB
psql -U postgres -d intelligence_terminal \
  -c "SELECT default_version, installed_version FROM pg_available_extensions WHERE name='timescaledb';"

# 3. Redis
redis-cli INFO server

# 4. FastAPI
curl http://localhost:8000/health

# 5. Frontend
curl http://localhost:3000

# 6. All tables exist
docker-compose exec postgres psql -U postgres -d intelligence_terminal \
  -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';"
```

---

## 🚀 Próximos Pasos

1. **Verificar acceso a todos los servicios** (como se muestra arriba)
2. **Leer [ARCHITECTURE.md](../ARCHITECTURE.md)** para entender el diseño
3. **Iniciar FASE 2**: Implementar Market Data Service
4. **Crear primer endpoint REST** para mercado de oro

---

## 📞 Ayuda

Si encuentras problemas:

1. Revisar logs: `docker-compose logs -f [servicio]`
2. Verificar variables de entorno: `grep POSTGRES_DB .env`
3. Reinstalar servicios: `docker-compose down -v && docker-compose up -d`
4. Ver troubleshooting section arriba

---

## ✅ Checklist de Setup Completado

- [ ] Docker Desktop instalado y funcionando
- [ ] Git clonado
- [ ] .env creado y configurado
- [ ] docker-compose up -d ejecutado
- [ ] Todos los servicios corriendo (docker-compose ps)
- [ ] http://localhost:8000 accesible
- [ ] http://localhost:3000 accesible
- [ ] Database tables creadas
- [ ] FastAPI documentación en /docs
- [ ] Listo para FASE 2 ✅

---

**¡Setup completado! Ahora pasamos a FASE 2: Market Data Engine** 🚀
