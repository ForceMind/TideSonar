# 观潮 (GuanChao TideSonar) - 服务器部署指南

本文档适用于生产环境部署（Linux Server）。

## 1. 准备工作
- **Docker** 和 **Docker Compose** 必须预先安装。
- 确保你拥有一个可用的 **必盈 API Key**。

## 2. 一键部署 (推荐)
使用我们提供的交互式脚本，你可以轻松设置 API Key 和自定义端口，而无需手动修改代码。

```bash
# 1. 赋予脚本执行权限
chmod +x deploy.sh

# 2. 运行脚本
./deploy.sh
```

**脚本运行流程：**
1. 提示输入 API Key。
2. 询问是否修改默认端口 (默认: 前端 80, 后端 8000)。如有冲突，请输入 `y` 并指定新端口（例如 8080）。
3. 自动构建并启动容器。

## 3. 手动部署
如果你想手动修改配置 `.env` 文件来启动：

1. **复制模板**
   ```bash
   cp .env.template .env
   ```
2. **修改 .env**
   ```env
   BIYING_LICENSE=你的License
   FRONTEND_PORT=80
   BACKEND_PORT=8000
   ```
3. **启动服务**
   ```bash
   docker-compose up -d --build
   ```

## 4. 常见维护操作

### 更新代码
```bash
git pull
./deploy.sh
```

### 强制重置缓存
如果需要强制刷新股票的“行业/概念”信息（例如半年一次），请执行：
```bash
# 删除缓存文件
docker-compose exec backend rm backend/data/index_constituents.json

# 重启后端
docker-compose restart backend
```

### 查看日志
```bash
docker-compose logs -f backend
```

## 5. 高级配置：二级域名/子路径
系统默认配置了 Nginx 反向代理。
- 前端容器内部 Nginx 代理了 `/ws/` 和 `/api/` 路径到后端。
- **无需跨域配置**：前端代码会自动根据当前浏览器访问的 HOST 拼接 WebSocket 地址，因此你只需保证服务器防火墙放行了你配置的 `FRONTEND_PORT` 即可。 



# TideSonar Deployment Guide

## 1. Prerequisites
- Server (Ubuntu/Debian/CentOS)
- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed

## 2. One-Click Deploy (Script)

1. Upload the project folder to your server.
2. Run the deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

3. Follow the interactive prompts:
   - Enter your **Biying License Key**.
   - Choose ports (Default: **3001** for Web, **8000** for API).
   - Enter Server IP (e.g. `192.168.x.x` or domain).

## 3. Manual Build (Docker Compose)

If you prefer manual control:

1. Edit `.env` file:
   ```dotenv
   BIYING_LICENSE=your_key_here
   FRONTEND_PORT=3001
   BACKEND_PORT=8000
   SERVER_IP=your_server_ip
   ```

2. Run:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

## 4. Troubleshooting

- **Check Logs**:
  ```bash
  docker-compose logs -f backend
  ```
- **Redis Connection**:
  The script automatically sets up an internal network. You don't need to install Redis on the host.
- **Updates**:
  Simply run `./deploy.sh` again. It will `git pull` latest code and rebuild containers.
