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
