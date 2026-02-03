from typing import List
from fastapi import WebSocket
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_snapshot: List[str] = []
        self.last_update_time: datetime = datetime.min # Initialize with old time

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
        
        # Immediate PUSH: Send the last known state so the screen isn't empty (e.g. Closing Data)
        if self.last_snapshot:
             logger.info(f"Pushing cached state ({len(self.last_snapshot)} items, time: {self.last_update_time}) to new client.")
             # Send in bulk is better but our frontend handles stream. 
             # Let's send them rapidly.
             for msg in self.last_snapshot:
                 try:
                    await websocket.send_text(msg)
                 except:
                    pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    def update_snapshot(self, alerts_json_list: List[str]):
        """
        Update the cached state with the latest batch.
        """
        self.last_snapshot = alerts_json_list
        self.last_update_time = datetime.now()

    def has_data(self) -> bool:
        return len(self.last_snapshot) > 0
    
    def is_data_stale(self) -> bool:
        """
        Check if data is too old (e.g. from before today's close).
        Rules:
        - If now > 15:00, and data_time < 15:00 of same day -> Stale
        - If now > 15:00, and data_time is yesterday -> Stale
        """
        now = datetime.now()
        # Closing time today
        closing_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
        
        # If we are past closing time
        if now > closing_time:
            # If data is older than closing time (e.g. 13:00 vs 15:00), it's stale
            if self.last_update_time < closing_time:
                return True
        
        return False

    async def broadcast(self, message: str):
        # Broadcast message to all connected clients
        # Iterate over a copy to avoid modification issues during iteration if disconnects happen (though remove happened in storage)
        # Actually safe to iterate here usually, but try/except essential for stale connections
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                # Real cleanup might happen in the endpoint handler but safe to just log here

manager = ConnectionManager()
