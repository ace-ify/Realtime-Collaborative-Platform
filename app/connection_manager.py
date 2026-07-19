import pycrdt as Y
from fastapi import WebSocket

class DocumentConnectionManager:
    def __init__(self):
        self.active_connections: dict[str,list[WebSocket]] = {}
        self.documents: dict[str,Y.Doc]={}

    async def connect(self,document_id:str,ws:WebSocket):
        await ws.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id]=[]
        self.active_connections[document_id].append(ws)
        if document_id not in self.documents:
            self.documents[document_id] = Y.Doc()
        state_update = self.documents[document_id].get_update()
        await ws.send_bytes(b"\x00" + state_update)
        print(f"Client connected to document {document_id}. Active clients: {len(self.active_connections[document_id])}")

    async def disconnect(self,document_id:str,ws:WebSocket):
        if document_id in self.active_connections:
            self.active_connections[document_id].remove(ws)
            print(f"Client disconnected from {document_id}. Active: {len(self.active_connections[document_id])}")
            if not self.active_connections[document_id]: 
                del self.active_connections[document_id]
                if document_id in self.documents:
                    del self.documents[document_id]
            
    async def broadcast_bytes(self, document_id: str, message: bytes, sender: WebSocket):
        if document_id in self.active_connections:
            for ws in self.active_connections[document_id]:
                if ws != sender:
                    await ws.send_bytes(message)


manager = DocumentConnectionManager()
