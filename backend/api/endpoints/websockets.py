from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.websocket import manager
from core.security import validate_token_string
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # 1. Validate token from query param since standard Authorization header is not supported by native WebSockets
    try:
        validate_token_string(token)
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008) # 1008: Policy Violation (often used for auth errors)
        return
        
    # 2. Connect
    await manager.connect(websocket)
    
    # 3. Listen for disconnects
    try:
        while True:
            # We don't expect client to send messages, just listen for disconnects
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
