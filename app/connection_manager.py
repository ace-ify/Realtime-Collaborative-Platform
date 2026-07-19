import pycrdt as Y
from fastapi import WebSocket

class DocumentConnectionManager:
    def __init__(self):
        self.active_connections: dict[str,list[WebSocket]] = {}
        self.documents: dict[str,Y.Doc]={}
        # Keypress/Edit tracking counter: document_id -> int
        self.update_counters: dict[str, int] = {}

    async def load_document_from_db(self, document_id: str) -> Y.Doc:
        """
        Loads the latest snapshot from DB (if any) and applies
        subsequent incremental updates to reconstruct the full document state.
        """
        from app.database import SessionLocal
        from app.models import DocumentUpdate, DocumentSnapshot
        
        doc = Y.Doc()
        db = SessionLocal()
        try:
            # 1. Latest snapshot retrieve karein (if exists)
            latest_snapshot = db.query(DocumentSnapshot).filter(
                DocumentSnapshot.document_id == document_id
            ).order_by(DocumentSnapshot.created_at.desc()).first()
            
            snapshot_time = None
            if latest_snapshot:
                print(f"[DB] Loading snapshot from {latest_snapshot.created_at}")
                doc.apply_update(latest_snapshot.snapshot_data)
                snapshot_time = latest_snapshot.created_at
                
            # 2. Latest snapshot ke time ke BAAD ke updates fetch karein
            query = db.query(DocumentUpdate).filter(
                DocumentUpdate.document_id == document_id
            )
            if snapshot_time:
                query = query.filter(DocumentUpdate.created_at > snapshot_time)
                
            updates = query.order_by(DocumentUpdate.created_at.asc()).all()
            print(f"[DB] Reconstructing YDoc {document_id} using {len(updates)} incremental updates.")
            
            # 3. YDoc me saare fetch updates apply karein
            for update in updates:
                doc.apply_update(update.update_data)
                
        except Exception as e:
            print(f"[DB Error] Failed to load YDoc from DB: {str(e)}")
        finally:
            db.close()
            
        return doc

    async def save_update_to_db(self, document_id: str, update_bytes: bytes):
        """
        Saves an incremental edit (bytes) to the DB and triggers
        a full document snapshot save every 5 edits.
        """
        from app.database import SessionLocal
        from app.models import DocumentUpdate, DocumentSnapshot
        
        db = SessionLocal()
        try:
            # 1. Save incremental edit to DB
            db_update = DocumentUpdate(document_id=document_id, update_data=update_bytes)
            db.add(db_update)
            db.commit()
            
            # 2. Increment memory update counter
            self.update_counters[document_id] = self.update_counters.get(document_id, 0) + 1
            print(f"[DB] Saved update for {document_id}. Count: {self.update_counters[document_id]}")
            
            # 3. Agar count >= 5, toh periodic snapshot trigger karein
            if self.update_counters[document_id] >= 5:
                print(f"[DB] Triggering periodic snapshot for {document_id}...")
                doc = self.documents[document_id]
                snapshot_data = doc.get_update()
                
                db_snapshot = DocumentSnapshot(
                    document_id=document_id,
                    snapshot_data=snapshot_data
                )
                db.add(db_snapshot)
                db.commit()
                
                # Reset counter
                self.update_counters[document_id] = 0
                print(f"[DB] Snapshot saved successfully for {document_id}. Counter reset.")
                
        except Exception as e:
            print(f"[DB Error] Failed to save update or snapshot: {str(e)}")
        finally:
            db.close()


    async def connect(self, document_id: str, ws: WebSocket):
        await ws.accept()
        
        if document_id not in self.active_connections:
            self.active_connections[document_id] = []
        self.active_connections[document_id].append(ws)
        
        # 1. YDoc initialize/load karein database se (Strategy C)
        if document_id not in self.documents:
            self.documents[document_id] = await self.load_document_from_db(document_id)
            self.update_counters[document_id] = 0
            
        # 2. Get current state and send to client
        state_update = self.documents[document_id].get_update()
        await ws.send_bytes(b"\x00" + state_update)
        
        print(f"Client connected to document {document_id}. Active: {len(self.active_connections[document_id])}")

    async def disconnect(self,document_id:str,ws:WebSocket):
        if document_id in self.active_connections:
            self.active_connections[document_id].remove(ws)
            print(f"Client disconnected from {document_id}. Active: {len(self.active_connections[document_id])}")
            if not self.active_connections[document_id]: 
                del self.active_connections[document_id]
                if document_id in self.documents:
                    del self.documents[document_id]
                if document_id in self.update_counters:
                    del self.update_counters[document_id]
            
    async def broadcast_bytes(self, document_id: str, message: bytes, sender: WebSocket):
        if document_id in self.active_connections:
            for ws in self.active_connections[document_id]:
                if ws != sender:
                    await ws.send_bytes(message)


manager = DocumentConnectionManager()
