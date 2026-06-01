# Frontend - Trading Terminal UI

## Estructura

```
frontend/
├── app/                     # App Router (Next.js 15)
│   └── dashboard/          # Dashboard principal
├── components/             # Componentes React reutilizables
├── lib/                    # Utilidades y helpers
├── public/                 # Archivos estáticos
│   ├── tools/             # Herramientas HTML interactivas
│   │   ├── herramienta_api.html
│   │   ├── herramienta_pro.html
│   │   └── parati.html
│   ├── assets/            # Assets multimedia
│   │   └── musica.mp3
│   └── index.html         # Landing page
├── next.config.js
├── tsconfig.json
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
