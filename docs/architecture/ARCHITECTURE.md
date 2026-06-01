# 🏛️ ARQUITECTURA INSTITUCIONAL - TERMINAL CUANTITATIVA DE ORO

**Estado**: FASE 1 - Diseño y Setup ✅
**Versión**: 0.1.0  
**Última actualización**: 2026-05-31

---

## 📊 VISIÓN GENERAL

Terminal institucional especializada en análisis cuantitativo de oro (XAUUSD, GC), con capacidades de análisis macroeconómico, detección de patrones Smart Money y análisis impulsado por IA.

### Objetivo Institucional
- Trading cuantitativo profesional enfocado en oro
- Análisis macroeconómico en tiempo real
- Detección automática de oportunidades
- Interfaz tipo Bloomberg/Reuters para traders quant

---

## 🏗️ ARQUITECTURA DE SISTEMA

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │  Executive   │     Macro    │     Gold     │     SMC      │  │
│  │  Dashboard   │   Dashboard  │  Dashboard   │  Dashboard   │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                               │
                    WebSocket (Real-time)
                               │
┌──────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Auth & Validation                                       │   │
│  │ • Rate Limiting                                           │   │
│  │ • WebSocket Handler                                       │   │
│  │ • Event Router                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
    │                    │                    │                    │
    │                    │                    │                    │
┌───▼──────────┐  ┌──────▼─────────┐ ┌──────▼──────────┐ ┌──────▼───────────┐
│ Market Data  │  │  Macro Engine  │ │ Analysis Svc   │ │   AI Service     │
│  Service     │  │                │ │                │ │                  │
│              │  │ • Risk Regimes │ │ • SMC Detector │ │ • LLM Analysis   │
│ • Gold (GC)  │  │ • Fed Bias     │ │ • Volatility   │ │ • Predictions    │
│ • XAUUSD     │  │ • Liquidity    │ │ • Correls      │ │ • Sentiments     │
│ • DXY        │  │ • Risk Score   │ │ • Events       │ │                  │
│ • Bonds      │  │                │ │                │ │                  │
│ • Equities   │  │ Data: Redis    │ │ Data: PG       │ │ Data: PG         │
│ • VIX        │  │                │ │                │ │                  │
│              │  └────────────────┘ └────────────────┘ └──────────────────┘
└───┬──────────┘
    │
    ├─ WebSocket consumers
    ├─ Event stream
    └─ Data processors
```

---

## 🔌 COMPONENTES PRINCIPALES

### 1. **MARKET DATA SERVICE**
**Responsabilidad**: Ingesta y normalización de datos

```
Fuentes de Datos:
├─ Brokers (IB, OANDA, Binance)
├─ Data Providers (Polygon, Twelve Data)
├─ Feeds históricos (CSV, databases)
└─ WebSockets (realtimé)

Procesamiento:
├─ Normalización
├─ Validación de calidad
├─ Deduplicación
└─ Almacenamiento

Almacenamiento:
├─ OHLCV → TimescaleDB
├─ Ticks → TimescaleDB
├─ Metadatos → PostgreSQL
└─ Cache → Redis
```

**Características**:
- Ingesta tiempo real sin downtime
- Datos históricos pre-poblados
- Fallback automático entre fuentes
- Rate limiting y batching

---

### 2. **MACRO ENGINE SERVICE**
**Responsabilidad**: Identificación de regímenes macro e indicadores

```
Inputs:
├─ DXY (USD Index)
├─ US10Y-US02Y (Yield Curve)
├─ SP500 (Equity Risk)
├─ Nasdaq (Tech Risk)
├─ VIX (Fear Index)
├─ Gold (Safe Haven)
└─ Noticias & Calendarios

Outputs:
├─ Market Regime (Risk On / Risk Off / Transitional)
├─ Macro Regime (Hawkish / Dovish / Neutral)
├─ Liquidity Conditions (High / Medium / Low)
├─ Risk Score (0-100)
├─ Macro Score (0-100)
├─ Gold Bias (Bullish / Neutral / Bearish)
└─ Confidence (0-100%)
```

---

### 3. **ANALYSIS SERVICE**
**Responsabilidad**: Análisis técnico avanzado

```
Módulos:
├─ Smart Money Detector (SMC)
│  ├─ Break of Structure (BOS)
│  ├─ Change of Character (CHOCH)
│  ├─ Fair Value Gaps (FVG)
│  ├─ Order Blocks
│  ├─ Liquidity Sweeps
│  └─ Key Levels
│
├─ Volatility Analyzer
│  ├─ ATR (Average True Range)
│  ├─ Realized Volatility
│  ├─ Range Analysis
│  └─ Volatility Regimes
│
└─ Correlation Analyzer
   ├─ Pairwise Correlations
   ├─ Rolling Correlations
   ├─ Correlation Breakdowns
   └─ Exotic Correlations
```

---

### 4. **AI SERVICE**
**Responsabilidad**: Análisis inteligente y predicciones

```
Modelos:
├─ OpenAI GPT-4
│  └─ Executive Summaries
│  └─ Market Scenarios
│
├─ Claude API
│  └─ Institutional Analysis
│  └─ Reasoning Chains
│
└─ Scikit-Learn (Local)
   ├─ Classifiers (BOS/CHOCH detection)
   ├─ Regressors (Price prediction)
   └─ Clustering (Market regimes)

Outputs:
├─ Executive Summary
├─ Institutional Bias
├─ Bullish/Bearish Probability
├─ Risk Assessment
├─ Scenario Analysis
└─ Confidence Levels
```

---

## 💾 MODELO DE DATOS

### TimescaleDB (Series Temporales)
```sql
-- OHLCV Data
market_data
├─ timestamp (hypertable key)
├─ symbol (XAUUSD, GC, DXY, etc)
├─ open, high, low, close, volume
├─ timeframe (1m, 5m, 1h, 1d, etc)
└─ indexes (symbol, timestamp)

-- Ticks
ticks
├─ timestamp (hypertable key)
├─ symbol
├─ bid, ask, mid
├─ volume
└─ source
```

### PostgreSQL (Datos Transaccionales)
```sql
-- Información de símbolos
symbols
├─ id, symbol (XAUUSD, GC)
├─ description, type (futures, forex, etc)
├─ contract_specs
└─ data_sources

-- Análisis guardados
market_regimes
├─ id, timestamp
├─ regime (risk_on, risk_off, etc)
├─ confidence, features
└─ created_at

-- Alertas
alerts
├─ id, symbol, type
├─ condition, threshold
├─ status (active, triggered, dismissed)
└─ created_at

-- Histórico de predicciones
predictions
├─ id, timestamp, symbol
├─ model_id, prediction
├─ confidence, outcome
└─ created_at
```

### Redis (Cache & Real-time)
```
Channels:
├─ market:XAUUSD:ticks
├─ market:DXY:ohlcv
├─ regime:macro
├─ regime:market
├─ alerts:active
└─ analysis:live

Keys:
├─ symbol:{symbol}:last_price
├─ symbol:{symbol}:indicators
├─ regime:current
├─ correlation:matrix
└─ risk:score
```

---

## 🔄 FLUJOS DE DATOS

### Flujo 1: Ingesta de Datos en Tiempo Real
```
Data Source
    ↓
Market Data Service (validates, normalizes)
    ├→ TimescaleDB (OHLCV storage)
    ├→ Redis (cache & broadcast)
    └→ Event Stream (publish)
        ├→ Macro Engine (consume)
        ├→ Analysis Service (consume)
        └→ WebSocket Subscribers (consume)
```

### Flujo 2: Análisis Macro
```
Market Data (Redis cache)
    ↓
Macro Engine (processes indicators)
    ├→ PostgreSQL (save regime)
    ├→ Redis (publish updates)
    └→ Event Stream
        ├→ AI Service (consume)
        └→ WebSocket Subscribers
```

### Flujo 3: Análisis IA
```
Market Data + Analysis + Macro Regime
    ↓
AI Service
    ├→ OpenAI/Claude APIs
    ├→ Local ML models
    └→ PostgreSQL (save predictions)
        └→ WebSocket Subscribers
```

---

## 📡 COMUNICACIÓN

### Síncrona (REST)
```
GET    /api/v1/market/gold/ohlcv
GET    /api/v1/analysis/macro-regime
GET    /api/v1/analysis/smart-money/{symbol}
POST   /api/v1/analysis/correlations
```

### Asíncrona (WebSocket)
```
ws://localhost:8000/ws/market/XAUUSD
ws://localhost:8000/ws/analysis/live
ws://localhost:8000/ws/alerts/active
```

### Event-Driven (Redis Pub/Sub)
```
Services subscribe to:
├─ market:*:updates
├─ analysis:*:events
└─ alerts:*:triggered
```

---

## 🐳 INFRAESTRUCTURA

### Stack Tecnológico
```
Frontend:
├─ Next.js 15 (App Router)
├─ React 19 (Server Components)
├─ TypeScript 5.4
├─ TailwindCSS 3.4
├─ TradingView Lightweight Charts

Backend:
├─ FastAPI (async, type hints)
├─ Python 3.11+
├─ Pydantic (validation)
├─ SQLAlchemy (ORM)
├─ APScheduler (background jobs)
├─ Celery (async tasks)

Bases de Datos:
├─ PostgreSQL 15
├─ TimescaleDB 2.13
├─ Redis 7.2

Infrastructure:
├─ Docker & Docker Compose
├─ nginx (reverse proxy)
├─ Prometheus (metrics)
├─ Grafana (dashboards)
```

### Docker Compose Services
```yaml
services:
  - postgres (database)
  - redis (cache)
  - fastapi (backend API)
  - celery-worker (async jobs)
  - celery-beat (scheduled jobs)
  - next-frontend (React app)
  - nginx (reverse proxy)
  - prometheus (monitoring)
  - grafana (dashboards)
```

---

## 🔐 SEGURIDAD

- **Authentication**: JWT tokens
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: TLS in transit, encrypted at rest
- **Rate Limiting**: DDoS protection, per-user limits
- **Input Validation**: Pydantic schemas, SQL injection prevention
- **Secrets Management**: Environment variables, secret manager

---

## 📈 ESCALABILIDAD

### Horizontal Scaling
```
Market Data Service
├─ Multiple workers (round-robin)
├─ Load balanced via nginx
└─ Shared Redis/DB

Analysis Services
├─ Auto-scaled based on queue depth
├─ Celery workers with concurrency
└─ Database connection pooling

Frontend
├─ Next.js servers (stateless)
├─ Load balanced
└─ CDN for static assets
```

### Vertical Scaling
- FastAPI: async/await, uvicorn workers
- Database: connection pooling, query optimization
- Redis: memory optimization, eviction policies

---

## 🚀 DEPLOYMENT

### Desarrollo
```bash
docker-compose up -d
# Services available at localhost
```

### Staging/Producción
```
- Kubernetes cluster
- Auto-scaling based on metrics
- Blue-green deployments
- Monitoring + alerting
- Regular backups
```

---

## 📋 MATRIZ DE DECISIONES

| Decisión | Opción Elegida | Alternativa | Razón |
|----------|----------------|-------------|-------|
| DB Series Temporales | TimescaleDB | InfluxDB | 100x faster, PostgreSQL ecosystem |
| Framework Backend | FastAPI | Django | Async, type-hints, speed |
| Frontend | Next.js | React | SSR, API routes, better UX |
| Cache | Redis | Memcached | Pub/Sub, data structures |
| Broker Tareas | Celery | RQ | Flexibility, reliability |
| Contenedores | Docker | VMs | Reproducibility, efficiency |

---

## 🎯 PRINCIPIOS DE DISEÑO

1. **Modularidad**: Cada servicio independiente, reemplazable
2. **Escalabilidad**: Sin punto único de fallo
3. **Observabilidad**: Logs, métricas, traces en todo
4. **Testabilidad**: Unit tests, integration tests, E2E tests
5. **Documentación**: Código autodocumentado + guías
6. **Seguridad**: Defense in depth
7. **Performance**: Optimización desde el diseño

---

## 📞 CONTACTO & GOVERNANCE

**Arquitecto Principal**: CTO Hedge Fund Cuantitativo  
**Última Revisión**: 2026-05-31  
**Próxima Revisión**: Post-FASE 1

---

**ESTADO ACTUAL**: Arquitectura aprobada ✅  
**PRÓXIMO PASO**: Implementación FASE 2 - Market Data Service
