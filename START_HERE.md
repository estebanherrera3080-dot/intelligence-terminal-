# 🏛️ INTELLIGENCE TERMINAL - START HERE

**Terminal Institucional de Trading - FASE 2 Implementation**

---

## 🚀 LO MÁS RÁPIDO (3 clics)

### 1️⃣ Abre PowerShell en carpeta `backend/`

```
c:\Users\Lenovo Ideapad\OneDrive\Desktop\workspace\terminal_trading\backend
```

### 2️⃣ Ejecuta Setup

```powershell
.\setup.bat
```

Espera a que termine. Verás: ✅ SETUP COMPLETE

### 3️⃣ Ejecuta Servidor

```powershell
.\run_server.bat
```

Verás:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## ✅ LISTO

**Abre en navegador:**

```
http://localhost:8000/docs
```

Ves Swagger UI con todos los endpoints. **¡Prueba cualquiera!**

---

## 🧪 PROBAR ENDPOINTS

Abre **OTRA terminal PowerShell** (no cierres la anterior) en `backend/`:

```powershell
# Opción 1: Test rápido
python test_api.py

# Opción 2: Tests automáticos
pytest tests/ -v

# Opción 3: Probar API manual
curl.exe "http://localhost:8000/api/v1/market/latest?symbol=XAUUSD"
```

---

## 🎨 DASHBOARD FRONTEND (Opcional)

Abre **OTRA terminal PowerShell** en `frontend/`:

```powershell
npm install
npm run dev
```

Abre:
```
http://localhost:3000
```

Ve el dashboard conectado a la API. ¡Datos en tiempo real!

---

## 📊 LO QUE TIENES

✅ **Backend (FastAPI)**
- Datos reales de Oro (XAUUSD)
- REST API con endpoints
- Documentación Swagger
- Tests automáticos
- CI/CD pipeline

✅ **Frontend (Next.js)**
- Dashboard conectado
- Tabla de candles
- Precio actual
- Bid/ask spread
- Auto-refresh

---

## 📝 ARCHIVOS IMPORTANTES

### Backend Setup
- `backend/setup.bat` - Instalación automática
- `backend/run_server.bat` - Iniciar API
- `backend/run_tests.bat` - Tests
- `backend/test_api.bat` - Test endpoints
- `backend/test_api.py` - Test Python

### Documentación
- `IMPLEMENTACION_FASE2.md` - Guía detallada
- `frontend/README.md` - Frontend docs
- `backend/app/api/v1/routes/market.py` - Endpoints code
- `backend/app/services/market_data/providers/twelve_data.py` - Data provider

---

## 🆘 PROBLEMAS?

### Error: "ModuleNotFoundError"
```powershell
python -m pip install -r requirements.txt
```

### Error: "Connection refused"
- ¿Está el servidor corriendo? (ve la otra terminal)
- ¿Es http://localhost:8000? (no https)
- Prueba `http://localhost:8000/health`

### Error: "Port 8000 in use"
```powershell
# Mata el proceso en puerto 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## 🎯 SIGUIENTES PASOS

**Mañana o próxima semana:**
- [ ] WebSocket para updates real-time
- [ ] Más data providers (Polygon, Alpha Vantage)
- [ ] Charts con TradingView
- [ ] Database persistencia
- [ ] Macro analysis engine
- [ ] Trading signals

---

## 📞 RESUMEN ENDPOINTS

```
GET  /health                              → API health
GET  /api/v1/market/ohlcv                → OHLCV candles
GET  /api/v1/market/latest               → Precio actual
GET  /api/v1/market/symbols              → Símbolos disponibles
GET  /api/v1/market/health               → Market service health
```

**Documentación interactiva:** http://localhost:8000/docs

---

**¡Bienvenido a FASE 2! 🚀**

Tu terminal de trading ya está funcionando. Datos reales. API lista. Dashboard conectado.

*Ahora es cuando la magia comienza.*
