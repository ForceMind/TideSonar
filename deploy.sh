#!/bin/bash
# TideSonar 一键部署脚本
# 支持：初始安装、更新、配置、重启

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}        TideSonar 部署脚本 v1.0             ${NC}"
echo -e "${GREEN}=============================================${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误：未安装 Docker。${NC}"
    echo "请先安装 Docker 和 Docker Compose。"
    exit 1
fi

# 1. 更新代码（如果是 git 仓库）
if [ -d ".git" ]; then
    echo -e "${YELLOW}[1/4] 正在检查更新...${NC}"
    git pull
else
    echo -e "${YELLOW}[1/4] 非 git 仓库，跳过更新。${NC}"
fi

# 2. 配置（.env）
echo -e "${YELLOW}[2/4] 正在配置环境...${NC}"

if [ ! -f .env ]; then
    echo "正在根据默认值创建 .env 文件..."
    cp .env.example .env 2>/dev/null || touch .env
fi

# 载入当前环境变量
source .env 2>/dev/null

# 交互式 License Key 设置
if [[ -z "$BIYING_LICENSE" || "$BIYING_LICENSE" == *"YOUR_LICENSE"* ]]; then
    echo -e "${RED}License Key 缺失！${NC}"
    read -p "请输入你的 Biying License Key: " input_key
    if [[ -n "$input_key" ]]; then
        # 使用 sed 更新 .env（兼容 Linux/Mac）
        if grep -q "BIYING_LICENSE=" .env; then
             # 若有特殊字符，进行简单处理
             sed -i "s|BIYING_LICENSE=.*|BIYING_LICENSE=$input_key|g" .env
        else
             echo "BIYING_LICENSE=$input_key" >> .env
        fi
        export BIYING_LICENSE=$input_key
    else
        echo "未输入密钥，后端将使用受限/模拟模式。"
    fi
else
    echo -e "License Key：${GREEN}已设置${NC}"
fi

# 端口配置
read -p "请输入前端端口（默认 3001）： " input_front
PROD_FRONT=${input_front:-3001}

read -p "请输入后端端口（默认 8000）： " input_back
PROD_BACK=${input_back:-8000}

read -p "请输入服务器公网 IP/域名（默认 localhost）： " input_ip
PROD_IP=${input_ip:-localhost}

# 更新 .env 中的端口
# 我们直接导出变量供 docker-compose 使用，并回写到 .env
export FRONTEND_PORT=$PROD_FRONT
export BACKEND_PORT=$PROD_BACK
export SERVER_IP=$PROD_IP

# 同时回写到 .env 以便持久化
if grep -q "FRONTEND_PORT=" .env; then
    sed -i "s|FRONTEND_PORT=.*|FRONTEND_PORT=$PROD_FRONT|g" .env
else
    echo "FRONTEND_PORT=$PROD_FRONT" >> .env
fi

if grep -q "BACKEND_PORT=" .env; then
    sed -i "s|BACKEND_PORT=.*|BACKEND_PORT=$PROD_BACK|g" .env
else
    echo "BACKEND_PORT=$PROD_BACK" >> .env
fi

if grep -q "SERVER_IP=" .env; then
    sed -i "s|SERVER_IP=.*|SERVER_IP=$PROD_IP|g" .env
else
    echo "SERVER_IP=$PROD_IP" >> .env
fi


# 3. 清理并构建
echo -e "${YELLOW}[3/4] 正在构建 Docker 容器...${NC}"
docker-compose down --remove-orphans
docker-compose build

# 4. 启动
echo -e "${YELLOW}[4/4] 正在启动服务...${NC}"
docker-compose up -d

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN} 部署完成！ ${NC}"
echo -e "前端：http://$PROD_IP:$PROD_FRONT"
echo -e "后端：http://$PROD_IP:$PROD_BACK"
echo -e "${GREEN}=============================================${NC}"
