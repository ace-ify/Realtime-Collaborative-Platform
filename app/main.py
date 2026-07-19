from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.connection_manager import manager
import pycrdt as Y
from dotenv import load_dotenv
from pydantic import BaseModel

from app.diff_utils import apply_diff_to_ytext
from app.ai_editor import generate_llm_edit

load_dotenv()

class AIEditRequest(BaseModel):
    prompt: str


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
            if not data:
                continue
            tag = data[0]
            payload = data[1:]
                
            if tag == 0:
                manager.documents[document_id].apply_update(payload)
                await manager.broadcast_bytes(document_id, data, sender=websocket)
            elif tag == 1:
                await manager.broadcast_bytes(document_id, data, sender=websocket)

    except WebSocketDisconnect:
        await manager.disconnect(document_id, websocket)

@app.post("/documents/{document_id}/ai-edit")
async def ai_edit(document_id: str, request: AIEditRequest):
    # 1. Check karein ki document memory me active hai ya nahi
    if document_id not in manager.documents:
        return {"error": "Document not active or not found"}
        
    ytext = manager.documents[document_id].get("text", type=Y.Text)
    old_text = str(ytext)
    
    # 2. Async non-blocking LLM response generate karein
    new_text = await generate_llm_edit(old_text, request.prompt)
    
    # 3. Smart diff calculate karke changes apply karein
    apply_diff_to_ytext(ytext, old_text, new_text, manager.documents[document_id])
    
    # 4. Pure state update generate karein aur use broadcast kar dein
    # sender=None ensures ki ye server-side trigger sabhi clients ko mile
    new_update = manager.documents[document_id].get_update()
    await manager.broadcast_bytes(document_id, b"\x00" + new_update, sender=None)
    
    return {"status": "AI edit applied", "new_text": new_text}
