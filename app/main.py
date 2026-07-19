from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.connection_manager import manager

app=FastAPI(title="Realtime Collaborative Platform")

@app.get("/")
def health():
    return {"status": "Real-time sync gateway running"}

@app.websocket("/ws/{document_id}")
async def socketpoint(websocket: WebSocket, document_id: str):
    try:
        await manager.connect(document_id, websocket)
        while True:
            data = await websocket.receive_bytes()
            manager.documents[document_id].apply_update(data)
            await manager.broadcast_bytes(document_id, data, sender=websocket)

    except WebSocketDisconnect:
        await manager.disconnect(document_id, websocket)
