#!/bin/bash

# TideSonar 服务器部署脚本 (中文版)

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   观潮 TideSonar - 服务器一键部署   ${NC}"
echo -e "${BLUE}========================================${NC}"

# 0. 检查 Docker 环境
if ! command -v docker &> /dev/null
then
    echo -e "${RED}警告: 未检测到 Docker 环境。${NC}"
    echo "Linux 服务器需要 Docker 来运行这一套系统（包含后端、数据库、网页服务）。"
    echo "如果没有 Docker，你需要手动安装 Python, Redis, Nginx 并配置几十个文件，非常麻烦。"
    echo ""
    read -p "是否需要脚本尝试自动安装 Docker? (y/n): " INSTALL_DOCKER
    
    if [[ "$INSTALL_DOCKER" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}正在尝试自动安装 Docker...${NC}"
        
        # 检测包管理器
        if command -v yum &> /dev/null; then
            # CentOS / Alibaba Cloud Linux
            echo "检测到系统: CentOS / RHEL / Alibaba Cloud"
            echo "正在切换至阿里云镜像源以加速安装..."
            sudo yum update -y
            sudo yum install -y yum-utils
            # 使用阿里云的 Docker 镜像源，解决国内连接 docker.com 失败的问题
            sudo yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            sudo systemctl start docker
            sudo systemctl enable docker
        elif command -v apt-get &> /dev/null; then
            # Ubuntu / Debian
            echo "检测到系统: Ubuntu / Debian"
            # 使用阿里云镜像源设置
            sudo apt-get update
            sudo apt-get install -y ca-certificates curl gnupg
            # 尝试使用 DaoCloud 镜像脚本或直接重试(暂时保持官方，Ubuntu 通常可以用 apt 换源)
            curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
        else
            echo -e "${RED}无法识别的系统，请手动安装 Docker！${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}Docker 安装尝试完成。${NC}"
    else
        echo "已取消。请手动安装 Docker 后再运行此脚本。"
        exit 1
    fi
fi

if ! command -v docker-compose &> /dev/null
then
    # 尝试检查 docker compose (v2) 插件
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}错误: 未检测到 Docker Compose。${NC}"
        echo "请安装 docker-compose 或使用包含 Compose 插件的 Docker 版本。"
        echo "尝试: sudo curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
        exit 1
    fi
fi

# 0.5 代码更新 (Git Pull)
echo ""
echo -e "${GREEN}[0/3] 代码同步${NC}"
if [ -d ".git" ]; then
    echo "检测到 Git 仓库，正在拉取最新代码..."
    git pull origin main || git pull 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 代码已更新至最新。${NC}"
    else
        echo -e "${RED}⚠️ 代码拉取失败 (可能是因为本地有修改冲突，或者没有设置 upstream)。${NC}"
        echo "将继续使用当前本地代码进行部署..."
    fi
else
    echo "未检测到 Git 仓库 (可能是直接上传的 zip 包)，跳过代码更新。"
fi

# 1. 密钥配置与更新
echo ""
echo -e "${GREEN}[1/3] 参数配置${NC}"

# 1.1 加载现有配置
CURRENT_LICENSE=""
CURRENT_FE_PORT="80"
CURRENT_BE_PORT="8000"

if [ -f ".env" ]; then
    echo "检测到现有配置文件 (.env)，正在加载..."
    # 加载变量但不导出，避免污染 Shell
    if grep -q "BIYING_LICENSE=" ".env"; then
        CURRENT_LICENSE=$(grep "BIYING_LICENSE=" ".env" | cut -d '=' -f2)
    fi
    if grep -q "FRONTEND_PORT=" ".env"; then
        CURRENT_FE_PORT=$(grep "FRONTEND_PORT=" ".env" | cut -d '=' -f2)
    fi
    if grep -q "BACKEND_PORT=" ".env"; then
        CURRENT_BE_PORT=$(grep "BACKEND_PORT=" ".env" | cut -d '=' -f2)
    fi
fi

# 1.2 交互配置
echo ""
echo "------------------------------------------------"
echo -e "当前配置:"
if [ -z "$CURRENT_LICENSE" ]; then
    echo -e "  License: [无 / 模拟模式]"
else
    echo -e "  License: ${CURRENT_LICENSE:0:5}******"
fi
echo -e "  前端端口: $CURRENT_FE_PORT"
echo -e "  后端端口: $CURRENT_BE_PORT"
echo "------------------------------------------------"

read -p "是否需要修改上述配置? (输入 y 修改，直接回车保持不变): " MODIFY_CONFIG

USER_LICENSE=$CURRENT_LICENSE
FRONTEND_PORT=$CURRENT_FE_PORT
BACKEND_PORT=$CURRENT_BE_PORT

if [[ "$MODIFY_CONFIG" =~ ^[Yy]$ ]]; then
    # 修改 License
    read -p "请输入 Biying API 密钥 (按回车保持不变): " INPUT_LICENSE
    if [ ! -z "$INPUT_LICENSE" ]; then USER_LICENSE=$INPUT_LICENSE; fi
    
    # 修改端口
    read -p "请输入 前端 WEB 端口 (当前: $FRONTEND_PORT, 按回车保持): " INPUT_FE
    if [ ! -z "$INPUT_FE" ]; then FRONTEND_PORT=$INPUT_FE; fi
    
    read -p "请输入 后端 API 端口 (当前: $BACKEND_PORT, 按回车保持): " INPUT_BE
    if [ ! -z "$INPUT_BE" ]; then BACKEND_PORT=$INPUT_BE; fi
fi

# 写入 .env 文件
echo "BIYING_LICENSE=$USER_LICENSE" > .env
echo "FRONTEND_PORT=$FRONTEND_PORT" >> .env
echo "BACKEND_PORT=$BACKEND_PORT" >> .env
# 如果需要，也可以写入 IP，但目前我们用自适应方案
# echo "SERVER_IP=..." >> .env

echo ""
echo -e "${BLUE}配置确认 (已保存至 .env):${NC}"
echo -e "License密钥: ${USER_LICENSE:0:5}******"
echo -e "WEB访问地址: http://localhost:$FRONTEND_PORT"
echo -e "API监听端口: $BACKEND_PORT"

# 3. 构建与运行
echo ""
echo -e "${GREEN}[2/3] 正在构建并启动服务...${NC}"

# --- 自动配置 Docker 镜像加速 (解决国内无法拉取镜像的问题) ---
if [ ! -f /etc/docker/daemon.json ]; then
    echo "检测到未配置 Docker 镜像加速，正在自动配置..."
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://huecker.io",
    "https://mirror.baidubce.com",
    "https://docker.nju.edu.cn"
  ]
}
EOF
    echo "重启 Docker 服务以应用配置..."
    systemctl daemon-reload
    systemctl restart docker
    echo "Docker 镜像加速配置完成。"
fi
# -------------------------------------------------------

echo "(初次运行需要下载镜像，可能需要几分钟，请喝杯咖啡稍等)"

# 兼容 docker-compose 和 docker compose
COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# 停止旧服务
$COMPOSE_CMD down --remove-orphans

# 启动新服务 (捕获错误)
if ! $COMPOSE_CMD up -d --build; then
    echo ""
    echo -e "${RED}[错误] 部署失败！${NC}"
    echo "Docker 无法拉取镜像 (Connection Timeout)。"
    echo "这通常是因为国内服务器网络无法连接 Docker Hub。"
    echo "请尝试手动修改 /etc/docker/daemon.json 添加可用的加速镜像源。"
    exit 1
fi

# 4. 成功提示
echo ""
echo -e "${GREEN}[3/3] ✅ 部署成功!${NC}"
echo -e "${BLUE}----------------------------------------${NC}"
echo -e "访问你的网站:   http://<你的服务器IP>:$FRONTEND_PORT"
echo -e "查看后台日志:   $COMPOSE_CMD logs -f backend"
echo -e "${BLUE}----------------------------------------${NC}"
