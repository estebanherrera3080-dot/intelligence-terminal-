#!/usr/bin/env pwsh
# Quick Reference - Intelligence Terminal
# Comandos más frecuentes

Write-Host "🎯 INTELLIGENCE TERMINAL - QUICK REFERENCE" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# Mostrar menú de opciones
Write-Host "`n📋 OPCIONES DISPONIBLES:`n" -ForegroundColor Yellow

Write-Host "1. 🚀 INICIAR CON DOCKER"
Write-Host "   docker-compose up -d"

Write-Host "`n2. 🔧 BACKEND (FastAPI)"
Write-Host "   cd backend"
Write-Host "   python -m venv venv"
Write-Host "   venv\Scripts\activate"
Write-Host "   pip install -r requirements.txt"
Write-Host "   uvicorn app.main:app --reload"

Write-Host "`n3. 🎨 FRONTEND (Next.js)"
Write-Host "   cd frontend"
Write-Host "   npm install"
Write-Host "   npm run dev          # http://localhost:3000"

Write-Host "`n4. 📚 DOCUMENTACIÓN"
Write-Host "   Architecture: docs/architecture/ARCHITECTURE.md"
Write-Host "   Roadmap:      docs/architecture/ROADMAP.md"
Write-Host "   Reportes:     docs/reports/"

Write-Host "`n5. 🗂️ ESTRUCTURA"
Write-Host "   Backend:   backend/app/"
Write-Host "   Frontend:  frontend/app/"
Write-Host "   Database:  database/init.sql"
Write-Host "   Docker:    docker-compose.yml"

Write-Host "`n6. ⚙️ STATUS"
Write-Host "   ✅ FASE 1: Arquitectura & Setup - COMPLETADA"
Write-Host "   🎯 FASE 2: Market Data Engine  - PRÓXIMA"

Write-Host "`n💡 COMANDOS ÚTILES`n" -ForegroundColor Green

Write-Host "Ver estructura:      Get-ChildItem -Recurse | Where-Object { -not `$_.PSIsContainer } | Select-Object FullName"
Write-Host "Limpiar contenedores: docker-compose down"
Write-Host "Logs Docker:         docker-compose logs -f"
Write-Host "Base de datos:       docker-compose exec postgres psql -U postgres"

Write-Host "`n📍 UBICACIONES CLAVE`n" -ForegroundColor Magenta

Write-Host "Raíz:         $(Get-Location)"
Write-Host "Backend:      $(Get-Location)\backend"
Write-Host "Frontend:     $(Get-Location)\frontend"
Write-Host "Documentación: $(Get-Location)\docs"

Write-Host "`n" -ForegroundColor Green
