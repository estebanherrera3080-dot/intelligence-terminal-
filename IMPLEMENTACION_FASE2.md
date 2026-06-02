# 🚀 FASE 2 - GUÍA DE IMPLEMENTACIÓN

**Terminal Trading - Intelligence Terminal**

---

## 📋 TABLA DE CONTENIDOS

1. [Setup Rápido](#setup-rápido)
2. [Paso a Paso Detallado](#paso-a-paso-detallado)
3. [Estructura de Archivos](#estructura-de-archivos)
4. [Pruebas](#pruebas)
5. [Troubleshooting](#troubleshooting)

---

## 🚀 SETUP RÁPIDO (Recomendado)

### Para Windows (Lo más fácil):

1. **Abre PowerShell** en la carpeta `backend/`
2. **Ejecuta este comando**:
   ```powershell
   .\setup.bat
   ```
3. **Espera a que termine**. Debería ver: ✅ SETUP COMPLETE
4. **Sigue las instrucciones en pantalla**

**Eso es todo.** Ahora puedes:
- Ejecutar `.\run_server.bat` para iniciar la API
- Ejecutar `.\test_api.bat` para probar endpoints
- Ejecutar `.\run_tests.bat` para ejecutar tests automáticos

---

## 📝 PASO A PASO DETALLADO (Si prefieres hacerlo manual)

### PASO 1: Abre PowerShell

```powershell
# Navega a la carpeta backend
cd "c:\Users\Lenovo Ideapad\OneDrive\Desktop\workspace\terminal_trading\backend"
```

### PASO 2: Instala Dependencias

```powershell
# Actualiza pip (recomendado)
python -m pip install --upgrade pip

# Instala todas las dependencias
python -m pip install -r requirements.txt
```

**Esto toma 2-3 minutos.** Debería ver muchas líneas de instalación y terminar sin errores.

### PASO 3: Verifica Instalación

```powershell
# Prueba que pydantic está instalado
python -c "import pydantic; print('✅ Pydantic OK')"

# Prueba que fastapi está instalado
python -c "import fastapi; print('✅ FastAPI OK')"
```

Si ves ✅ en ambos, ¡está listo!

### PASO 4: Inicia el Servidor API

**En la MISMA terminal:**

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Debería ver:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**IMPORTANTE: Deja esta terminal abierta. Es donde corre el servidor.**

### PASO 5: Prueba en OTRA terminal PowerShell

**Abre UNA NUEVA terminal PowerShell** (no cierres la anterior):

```powershell
cd "c:\Users\Lenovo Ideapad\OneDrive\Desktop\workspace\terminal_trading\backend"

# Opción A: Ejecutar test rápido
python test_api.py

# O Opción B: Usar curl para probar endpoints
curl.exe "http://localhost:8000/api/v1/market/latest?symbol=XAUUSD"

# O Opción C: Abrir en navegador
start http://localhost:8000/docs
```

---

## 📁 ESTRUCTURA DE ARCHIVOS CREADA

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── market.py               ✅ REST endpoints
│   ├── services/
│   │   └── market_data/
│   │       ├── __init__.py
│   │       └── providers/
│   │           ├── __init__.py
│   │           ├── base.py             ✅ Abstract provider
│   │           └── twelve_data.py      ✅ API real (funciona)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── models.py                   ✅ ORM models
│   ├── schemas/
│   │   └── market.py                   ✅ Pydantic models
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   └── main.py                         ✅ FastAPI app
│
├── tests/
│   ├── conftest.py                     ✅ Fixtures
│   ├── unit/
│   │   ├── test_main.py
│   │   └── test_config.py
│   ├── integration/
│   └── fixtures/
│
├── setup.bat                           ✅ Instalación automática
├── run_server.bat                      ✅ Iniciar servidor
├── run_tests.bat                       ✅ Ejecutar tests
├── test_api.bat                        ✅ Probar API
├── test_api.py                         ✅ Test Python
└── requirements.txt                    ✅ Dependencias
```

---

## 🧪 PRUEBAS

### Opción 1: Interfaz Gráfica (FÁCIL)

Una vez que el servidor está corriendo:

```
http://localhost:8000/docs
```

Ves una interfaz interactiva. Puedes hacer click en cada endpoint y probar directamente.

### Opción 2: Terminal (curl)

```powershell
# Obtener precio actual de ORO
curl.exe "http://localhost:8000/api/v1/market/latest?symbol=XAUUSD" | findstr /C:"price"

# Obtener 5 candles de ORO (1 hora)
curl.exe "http://localhost:8000/api/v1/market/ohlcv?symbol=XAUUSD&timeframe=1h&limit=5"

# Obtener símbolos disponibles
curl.exe "http://localhost:8000/api/v1/market/symbols" | findstr /C:"XAUUSD"

# Health check
curl.exe "http://localhost:8000/health" | findstr /C:"healthy"
```

### Opción 3: Python

```powershell
python test_api.py
```

Output esperado:
```
============================================================
🚀 INTELLIGENCE TERMINAL - MARKET DATA API TEST
============================================================

1️⃣  Testing: Get Available Symbols
✅ Symbols fetched: 14
   Examples: XAUUSD, EURUSD, GBPUSD, USDJPY, USDCHF

2️⃣  Testing: Fetch OHLCV Data (XAUUSD)
✅ Candles fetched: 5
   [1] 2024-05-31 14:00:00 | O:2042.50 H:2050.75 L:2040.25 C:2048.30
```

### Opción 4: Tests Automáticos

```powershell
pytest tests/ -v --cov=app
```

---

## 📊 EJEMPLO DE RESPUESTA API

**Request:**
```
GET http://localhost:8000/api/v1/market/latest?symbol=XAUUSD
```

**Response:**
```json
{
  "symbol": "XAUUSD",
  "bid": 2048.25,
  "ask": 2048.35,
  "price": 2048.3,
  "spread": 0.1,
  "volume": 100.0,
  "timestamp": "2024-05-31T16:30:01+00:00",
  "change_pct": 0.25
}
```

---

## 🛠️ TROUBLESHOOTING

### Error: "ModuleNotFoundError: No module named 'pydantic'"

**Solución:**
```powershell
python -m pip install pydantic fastapi httpx
```

### Error: "Connection refused" en localhost:8000

**Solución:**
- Verifica que la terminal con el servidor ESTÁ ABIERTA
- Verifica que viste "Application startup complete"
- Prueba en otra pestaña del navegador
- Si aún no funciona, reinicia el servidor

### Error: "curl.exe not found"

**Solución en PowerShell:**
```powershell
# Usa Invoke-WebRequest en lugar de curl
Invoke-WebRequest -Uri "http://localhost:8000/health" | Select-Object -ExpandProperty Content
```

### Pip falla en instalar requirements

**Solución:**
```powershell
# Actualiza pip primero
python -m pip install --upgrade pip setuptools wheel

# Luego instala requirements
python -m pip install -r requirements.txt
```

Si sigue fallando, instala los paquetes principales:
```powershell
python -m pip install fastapi uvicorn pydantic httpx sqlalchemy
```

### El test_api.py dice "No module named 'app'"

**Solución:**
- Verifica que estás EN la carpeta `backend/`
- Verifica que existe `app/__init__.py`
- Corre: `python -m pytest test_api.py` (con `-m pytest`)

---

## 📱 FRONTEND (Próximo paso)

Para probar el dashboard frontend:

```powershell
# En carpeta frontend/
cd "..\frontend"

# Instala dependencias
npm install

# Inicia servidor frontend
npm run dev
```

Luego abre:
```
http://localhost:3000
```

El dashboard se conectará automáticamente a la API en `localhost:8000`.

---

## ✅ CHECKLIST FINAL

- [ ] Ejecuté `setup.bat` O instalé manualmente `pip install -r requirements.txt`
- [ ] Ejecuté `python -m uvicorn app.main:app --reload --port 8000`
- [ ] Vi "Application startup complete" en terminal
- [ ] Abrí `http://localhost:8000/docs` en navegador
- [ ] Puedo ver Swagger UI con endpoints listados
- [ ] Hice click en `/api/v1/market/latest?symbol=XAUUSD` y recibí datos
- [ ] Los datos incluyen precio actual (price, bid, ask)

---

## 🎉 ÉXITO

Si llegaste hasta aquí, **¡La FASE 2 está funcionando!**

Ahora tu terminal tiene:
✅ API REST con datos reales de ORO  
✅ Endpoints para OHLCV, precios, símbolos  
✅ Health checks  
✅ Documentación Swagger interactiva  
✅ Tests automáticos  
✅ CI/CD pipeline  

**Próximos pasos:**
1. WebSocket para updates real-time
2. Frontend dashboard conectada
3. Más data providers (Polygon, Alpha Vantage)
4. Base de datos persistente

¡Bienvenido a FASE 2! 🚀
