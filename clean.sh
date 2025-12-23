#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════"
echo "  LIMPEZA COMPLETA"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Passo 1: Matar processos
echo "1️⃣  Matando todos os processos Python..."
killall -9 python 2>/dev/null || true
killall -9 python3 2>/dev/null || true
pkill -9 -f multiscope 2>/dev/null || true
pkill -9 -f gamescope 2>/dev/null || true
pkill -9 -f wine 2>/dev/null || true
sleep 1
echo "   ✅ Processos finalizados"

# Passo 2: Limpar cache
echo "2️⃣  Limpar cache..."
find . -type d -name "__pycache__" -exec rm -rf {} \;
sleep 1
echo "   ✅ Cache limpo"


# Passo 4: Finalizar
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ TUDO PRONTO!"
echo "═══════════════════════════════════════════════════════════"
