import asyncio
import websockets
import json
import time

async def test_websocket_client():
    uri = "ws://localhost:8000/ws/alerts"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for alerts...")
            
            # Listen for a few messages
            count = 0
            while count < 5:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    print(f"[{time.strftime('%H:%M:%S')}] Received Alert: {data['code']} {data['name']} ({data['pct_chg']}%)")
                    count += 1
                except asyncio.TimeoutError:
                    print("Waiting for data...")
            
            print("Received 5 alerts. Test Passed.")
            
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure the backend is running: python -m backend.app.main")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_client())
    except KeyboardInterrupt:
        pass
