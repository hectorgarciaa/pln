#!/bin/bash

echo "=================================================="
echo "🤖 Instalador del Bot Negociador con Ollama"
echo "=================================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Verificar Python
echo "📋 Verificando Python..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python encontrado: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 no encontrado. Por favor instálalo primero."
    exit 1
fi

# 2. Verificar/Instalar Ollama
echo ""
echo "📋 Verificando Ollama..."
if command_exists ollama; then
    OLLAMA_VERSION=$(ollama --version)
    echo -e "${GREEN}✓${NC} Ollama ya instalado: $OLLAMA_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Ollama no encontrado. ¿Deseas instalarlo? (s/n)"
    read -r install_ollama
    if [[ $install_ollama == "s" || $install_ollama == "S" ]]; then
        echo "Instalando Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${NC} Ollama instalado correctamente"
        else
            echo -e "${RED}✗${NC} Error al instalar Ollama"
            exit 1
        fi
    else
        echo "Ollama es necesario para ejecutar el bot. Instalación cancelada."
        exit 1
    fi
fi

# 3. Verificar si Ollama está corriendo
echo ""
echo "📋 Verificando servicio Ollama..."
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama está corriendo"
else
    echo -e "${YELLOW}⚠${NC} Ollama no está corriendo. Iniciando..."
    ollama serve &
    sleep 3
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Ollama iniciado correctamente"
    else
        echo -e "${RED}✗${NC} No se pudo iniciar Ollama"
        exit 1
    fi
fi

# 4. Verificar/Descargar modelo Qwen
echo ""
echo "📋 Verificando modelo Qwen..."
if ollama list | grep -q "qwen2.5"; then
    echo -e "${GREEN}✓${NC} Modelo Qwen ya descargado"
else
    echo -e "${YELLOW}⚠${NC} Descargando modelo Qwen2.5 (esto puede tardar varios minutos)..."
    ollama pull qwen2.5:latest
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Modelo descargado correctamente"
    else
        echo -e "${RED}✗${NC} Error al descargar el modelo"
        exit 1
    fi
fi

# 5. Instalar dependencias Python
echo ""
echo "📋 Instalando dependencias Python..."
pip3 install --user requests
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Dependencias instaladas"
else
    echo -e "${YELLOW}⚠${NC} Hubo un problema instalando dependencias, pero puede que ya estén instaladas"
fi

# 6. Verificar conectividad con la API
echo ""
echo "📋 Verificando conectividad con la API..."
if curl -s --max-time 5 http://147.96.81.252:8000/info >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API accesible"
else
    echo -e "${YELLOW}⚠${NC} No se puede conectar a la API (puede estar offline o tener restricciones de red)"
fi

# 7. Resumen final
echo ""
echo "=================================================="
echo -e "${GREEN}✓ INSTALACIÓN COMPLETADA${NC}"
echo "=================================================="
echo ""
echo "🚀 Para ejecutar el bot:"
echo "   cd app"
echo "   python3 bot_negociador.py"
echo ""
echo "📚 Para más información, lee:"
echo "   NEGOCIADOR_README.md"
echo ""
echo "💡 Consejos:"
echo "   - Usa 'ollama list' para ver modelos instalados"
echo "   - Usa 'ollama pull <modelo>' para descargar más modelos"
echo "   - El bot funcionará mejor con modelos grandes (14b)"
echo ""
echo "=================================================="
