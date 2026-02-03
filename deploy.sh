#!/bin/bash

# TideSonar Interactive Deployment Script (Server)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   GuanChao TideSonar - Server Deploy   ${NC}"
echo -e "${BLUE}========================================${NC}"

# Check Docker
if ! command -v docker &> /dev/null
then
    echo "Error: Docker not found. Please install Docker first."
    exit 1
fi

# 1. License Configuration
echo ""
echo -e "${GREEN}[1/3] Configuration${NC}"
read -p "Enter Biying License Key (Leave empty for Mock Mode): " USER_LICENSE
export BIYING_LICENSE=${USER_LICENSE}

# 2. Port Configuration
echo ""
echo "Current Ports: Frontend=80, Backend=8000"
read -p "Do you want to customize ports? (y/N): " MODIFY_PORTS

# Defaults
export FRONTEND_PORT=80
export BACKEND_PORT=8000

if [[ "$MODIFY_PORTS" =~ ^[Yy]$ ]]; then
    read -p "Enter Frontend Port (e.g. 8080): " INPUT_FE
    if [ ! -z "$INPUT_FE" ]; then export FRONTEND_PORT=$INPUT_FE; fi
    
    read -p "Enter Backend Port (e.g. 9000): " INPUT_BE
    if [ ! -z "$INPUT_BE" ]; then export BACKEND_PORT=$INPUT_BE; fi
fi

echo ""
echo -e "Settings saved:"
echo -e "License: ${BIYING_LICENSE:0:5}******"
echo -e "Frontend: http://localhost:$FRONTEND_PORT"
echo -e "Backend:  http://localhost:$BACKEND_PORT"

# 3. Build & Run
echo ""
echo -e "${GREEN}[2/3] Building & Starting Containers...${NC}"
echo "(This may take a few minutes on first run)"

# Stop old containers
docker-compose down --remove-orphans

# Start new
docker-compose up -d --build

# 4. Success
echo ""
echo -e "${GREEN}[3/3] Deployment Complete!${NC}"
echo -e "${BLUE}----------------------------------------${NC}"
echo -e "Frontend Access: http://<YOUR-SERVER-IP>:$FRONTEND_PORT"
echo -e "API Status:      docker-compose logs -f backend"
echo -e "${BLUE}----------------------------------------${NC}"
