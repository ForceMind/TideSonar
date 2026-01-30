# GuanChao 观潮 (TideSonar) - A股实时资金流向监控系统

这是一个针对 A股市场（沪深300、中证500/1000/2000）的实时异动监控系统，旨在捕捉主力资金的“成交额放大”动作。

## 1. 项目结构

```
TideSonar/
├── backend/                 # Python FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 接口 (WebSocket)
│   │   ├── core/            # 核心配置与接口定义
│   │   ├── models/          # 数据模型 (Pydantic)
│   │   ├── services/        # 业务逻辑 (监控引擎, Mock数据源, Redis监听)
│   │   └── main.py          # 启动入口
│   └── requirements.txt
│
├── frontend/                # Vue 3 + Tailwind 前端
│   ├── src/
│   │   ├── components/      # UI 组件 (卡片)
│   │   └── App.vue          # 主布局 (四列瀑布流)
│   └── ...
```

## 2. 环境要求

- **Python 3.10+** (后端)
- **Node.js 16+** (前端)
- **Redis** (可选/推荐)。如果没有 Redis，系统会自动切换到“内存直连模式”，方便本地开发。

## 3. 常见问题 (FAQ)

**Q: 现在的行情数据是哪来的？**
A: 目前使用的是 `MockDataSource` (后端内置的模拟器)。它每隔 3 秒生成全市场 4000+ 只股票的随机涨跌和成交量数据，用于验证监控算法和前端界面。

**Q: 为什么界面有时候会闪烁？**
A: 因为这是**实时流 (Real-time Stream)**。
1. **Mock 频率高**: 为了演示效果，模拟数据生成各种“异动”的概率较高，导致瞬间推送大量卡片。
2. **入场动画**: 每个新卡片出现时都有下压动画。如果 1秒内来了 10个新卡片，列表就会频繁重排。
   *(注: 我已在最新代码中降低了 Mock 异动概率，闪烁感应已大幅减轻)*

**Q: 如何接入真实数据？**
A: 修改 `backend/app/services/producer_task.py`，将 `MockDataSource` 替换为您自己的数据源类（需继承 `BaseDataSource` 并实现 `get_snapshot` 接口）。参考 `real_source_example.py`。

## 4. 快速启动

提供了多种启动方式，请根据您的环境选择。

### 配置 (Configuration)
在项目根目录创建或修改 `.env` 文件来配置端口和 API Key：
```ini
BIYING_LICENSE=您的必盈License
SERVER_IP=您的服务器IP或域名
FRONTEND_PORT=3000
BACKEND_PORT=8000
```
*(如果没有 License，请保留默认值，系统将自动使用 Mock 模拟数据)*

### 方式 A: Windows 本地开发 (推荐)
双击运行 `scripts/start_win.bat` 即可同时启动前后端。

### 方式 B: Linux 服务器部署 (Docker 推荐)
需要安装 Docker 和 Docker Compose。
```bash
chmod +x scripts/deploy_server.sh
./scripts/deploy_server.sh
```

### 方式 C: 手动启动
**后端:**
```powershell
$env:PYTHONPATH="e:\Privy\TideSonar"; python -m backend.app.main
```
**前端:**
```bash
cd frontend
npm run dev
```
