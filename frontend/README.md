# 🎨 Frontend - Intelligence Terminal

Next.js 15 + React 19 + TypeScript Dashboard

---

## 🚀 Quickstart

### 1. Asegúrate que el backend está corriendo

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Instala dependencias frontend

```powershell
cd frontend
npm install
```

### 3. Inicia servidor frontend

```powershell
npm run dev
```

### 4. Abre en navegador

```
http://localhost:3000
```

---

## 📁 Estructura

```
frontend/
├── app/
│   ├── page.tsx                # Dashboard main
│   ├── layout.tsx              # Root layout
│   └── globals.css             # Global styles
├── lib/
│   └── api.ts                  # API client para conectar con backend
├── components/                 # React components (extensible)
├── public/                     # Static assets
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
└── next.config.js              # Next.js config
```

---

## 🔌 Conexión con Backend

El archivo `lib/api.ts` conecta con la API del backend:

```typescript
// Obtener OHLCV
const data = await marketDataClient.getOHLCV('XAUUSD', '1h', 100);

// Obtener precio actual
const tick = await marketDataClient.getLatestTick('XAUUSD');

// Obtener símbolos
const symbols = await marketDataClient.getSymbols();
```

El dashboard automáticamente:
- ✅ Conecta a `http://localhost:8000`
- ✅ Obtiene datos en tiempo real
- ✅ Refresca cada 10 segundos
- ✅ Muestra precio, bid/ask, spread
- ✅ Tabla con último 20 candles

---

## 🛠️ Desarrollo

### Scripts disponibles

```bash
npm run dev          # Start dev server (port 3000)
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript check
npm run format       # Format code with Prettier
npm run test         # Run Jest tests
npm run test:watch   # Watch mode tests
```

---

## 📦 Dependencies

### Core
- **Next.js 15** - React framework
- **React 19** - UI library
- **TypeScript 5.4** - Type safety

### UI & Styling
- **TailwindCSS 3.4** - Utility CSS framework
- **Headless UI 1.7** - Headless components
- **Heroicons 2.0** - Icon library

### Data & State
- **Axios 1.6** - HTTP client
- **Zustand 4.4** - State management
- **date-fns 2.30** - Date utilities

### Charts
- **Recharts 2.10** - React charts
- **lightweight-charts 4.1** - TradingView charts

### Real-time
- **socket.io-client 4.7** - WebSocket (ready for future)
- **react-hot-toast 2.4** - Toast notifications

### Development
- **Jest 29.7** - Testing framework
- **ESLint 8.55** - Linting
- **Prettier 3.1** - Code formatting

---

## 🎯 Features

✅ Real-time market data from backend  
✅ Multiple symbol selection (XAUUSD, EURUSD, etc)  
✅ Timeframe selector (1m - 1d)  
✅ Live price with bid/ask spread  
✅ Historical OHLCV candlestick table  
✅ Responsive dark theme  
✅ Error handling and loading states  
✅ Auto-refresh every 10 seconds  

---

## 🔮 Coming Soon

⏳ Interactive charts with lightweight-charts  
⏳ WebSocket for real-time updates  
⏳ Advanced order placement  
⏳ Portfolio management  
⏳ Macro indicators  
⏳ Trading signals  

---

## 🚀 Deployment

### Build for production

```bash
npm run build
npm start
```

### Deploy to Vercel

```bash
# Make sure you have Vercel CLI
npm i -g vercel

# Deploy
vercel
```

---

**Happy trading! 🚀**
└── package.json
```

## Comandos Principales

```bash
# Instalación
cd frontend
npm install

# Desarrollo
npm run dev      # http://localhost:3000

# Build producción
npm run build
npm run start

# Linting
npm run lint
```

## Stack Técnico

- **Framework**: Next.js 15
- **React**: 19
- **TypeScript**: Latest
- **Styling**: Tailwind CSS (recomendado)
- **HTTP Client**: Fetch / Axios
- **State Management**: Context API o Zustand

## Características Principales

### Dashboard
- Visualización de datos de mercado en tiempo real
- Gráficos interactivos (TradingView chart)
- Panel de análisis técnico
- Herramientas de trading

### Herramientas Integradas
- **Herramienta API** - Documentación e integración API
- **Herramienta Pro** - Herramientas avanzadas de análisis
- **Para Ti** - Recomendaciones personalizadas

## Status

✅ FASE 1: Estructura base completada
🎯 FASE 9: Dashboards avanzados (próximo)

Para conexión al backend, usar variables de entorno:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Para más detalles, ver [/docs/architecture/ARCHITECTURE.md](/docs/architecture/ARCHITECTURE.md)
