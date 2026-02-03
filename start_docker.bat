@echo off
setlocal EnableDelayedExpansion

REM ==============================================
REM   GuanChao TideSonar - Windows Docker Launcher
REM ==============================================

echo.
echo ==============================================
echo    观潮 TideSonar - 本地 Docker 启动脚本
echo ==============================================
echo.

REM 1. Check Docker
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到 Docker 正在运行。
    echo.
    echo 请确认：
    echo 1. 已安装 Docker Desktop for Windows (https://www.docker.com/products/docker-desktop/)
    echo 2. Docker Desktop 已经启动并运行中。
    echo.
    pause
    exit /b 1
)

REM 2. License Input
echo [1/3] 参数配置
set /p USER_LICENSE="请输入 Biying API 密钥 (按回车使用模拟模式): "
set "BIYING_LICENSE=%USER_LICENSE%"

REM 3. Port Configuration
echo.
echo 默认端口: 前端 WEB = 80, 后端 API = 8000
set /p PORT_CHOICE="是否自定义端口? (y/n, 默认 n): "

set "FRONTEND_PORT=80"
set "BACKEND_PORT=8000"

if /i "%PORT_CHOICE%"=="y" (
    set /p "FRONTEND_PORT=请输入前端端口 (比如 8080): "
    set /p "BACKEND_PORT=请输入后端端口 (比如 9000): "
)

REM 4. Create .env file for docker-compose to read
echo.
echo [2/3] 生成环境配置...
(
echo BIYING_LICENSE=!BIYING_LICENSE!
echo FRONTEND_PORT=!FRONTEND_PORT!
echo BACKEND_PORT=!BACKEND_PORT!
) > .env

echo 配置已保存至 .env 文件。

REM 5. Run Docker Compose
echo.
echo [3/3] 正在构建并启动容器...
echo (初次运行可能需要几分钟下载镜像，请耐心等待)
echo.

docker-compose down --remove-orphans
docker-compose up -d --build

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [出错] 启动失败。
    echo 请检查 Docker Desktop 是否正常，或端口是否被占用。
    pause
    exit /b 1
)

echo.
echo ==============================================
echo  ✅ 启动成功!
echo ==============================================
echo  WEB 访问地址: http://localhost:!FRONTEND_PORT!
echo  API 接口地址: http://localhost:!BACKEND_PORT!
echo.
echo  正在显示后端日志 (按 Ctrl+C 退出日志查看，不会停止服务)...
echo ==============================================
echo.

docker-compose logs -f backend

pause