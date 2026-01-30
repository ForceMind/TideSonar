#!/bin/bash

# TideSonar Deployment Script for Linux Server
# Supports: Ubuntu, Debian, CentOS, AlmaLinux (Assuming Docker is available or can be installed)

echo "🌊 Starting GuanChao TideSonar Deployment..."

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check Docker
if ! command_exists docker; then
    echo "⚠️  Docker not found. Attempting to install..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    echo "✅ Docker installed."
else
    echo "✅ Docker is already installed."
fi

# 2. Check Docker Compose
if ! command_exists docker-compose; then
    echo "ℹ️  Checking for 'docker compose' plugin..."
    if ! docker compose version >/dev/null 2>&1; then
       echo "❌ Docker Compose not found. Please install docker-compose or docker-compose-plugin."
       exit 1
    fi
fi

# 3. Data Source Configuration
echo ""
echo "🔐 Security Configuration"
echo "Please enter your Biying API License Key (Leave empty to use Mock Data/Env):"
read -r INPUT_LICENSE

if [ -z "$INPUT_LICENSE" ]; then
    echo "⚠️  No license provided. System will default to MOCK DATA or .env setting."
else
    echo "✅ License key captured for this session."
    export BIYING_LICENSE="$INPUT_LICENSE"
fi
echo ""

# 4. Build and Run
echo "🚀 Building and Starting Services..."

# Adapt to older docker-compose or new docker compose
if command_exists docker-compose; then
    docker-compose up --build -d
else
    docker compose up --build -d
fi

echo "-----------------------------------"
echo "✅ Deployment Complete!"
echo "-----------------------------------"
echo "📡 Frontend: http://<YOUR_SERVER_IP>:3000"
echo "🔌 Backend : http://<YOUR_SERVER_IP>:8000"
echo "-----------------------------------"
echo "To stop: docker-compose down"
