# GuanChao (TideSonar) - A-Share Capital Flow Monitor

A real-time anomaly detection system for A-Share market, focusing on identifying "High Volume" events across major indices (HS300, ZZ500, ZZ1000, ZZ2000).

## 1. Project Structure

```
TideSonar/
├── backend/                 # Python FastAPI Backend
│   ├── app/
│   │   ├── api/             # API Endpoints (WebSocket)
│   │   ├── core/            # Config & Interfaces
│   │   ├── models/          # Data Models (Pydantic)
│   │   ├── services/        # Business Logic (Monitor, MockSource, Redis)
│   │   └── main.py          # Entry Point
│   └── requirements.txt
│
├── frontend/                # Vue 3 + Tailwind Frontend
│   ├── src/
│   │   ├── components/      # UI Components (StockCard)
│   │   └── App.vue          # Main Layout (4 Columns)
│   └── ...
```

## 2. Prerequisites

- **Python 3.10+**
- **Node.js 16+**
- **Redis** (Optional but recommended. System falls back to in-memory mode if missing.)

## 3. How to Run

### Backend (Server)
1. Open terminal 1.
2. Navigate to root `TideSonar/`
3. Set PYTHONPATH and run:
   ```powershell
   $env:PYTHONPATH="e:\Privy\TideSonar"; python -m backend.app.main
   ```
   *The server will start at `http://localhost:8000` and begin generating mock alerts.*

### Frontend (UI)
1. Open terminal 2.
2. Navigate to `TideSonar/frontend`
3. Install dependencies (first time only):
   ```bash
   npm install
   ```
4. Run dev server:
   ```bash
   npm run dev
   ```
5. Open browser at `http://localhost:3000` (or the port shown/assigned by Vite).

## 4. Customization (Switching to Real Data)

To use real market data:
1. Open `backend/app/services/producer_task.py`.
2. Replace `MockDataSource` with your own implementation of `BaseDataSource`.
3. An example implementation structure is provided in `backend/app/services/real_source_example.py`.

## 5. Deployment

- Backend: Use `gunicorn` with `uvicorn` workers behind Nginx.
- Frontend: Run `npm run build` and serve the `dist/` folder via Nginx.
- Redis: Ensure persistence is enabled if you want to save alert history (not currently implemented, but prepared for).
