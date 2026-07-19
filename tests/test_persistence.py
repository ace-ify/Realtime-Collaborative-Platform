import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import websockets
import pycrdt as Y
from app.database import SessionLocal
from app.models import DocumentUpdate, DocumentSnapshot

WS_URL = "ws://127.0.0.1:8000/ws/doc_persist_test"

async def test_persistence_flow():
    print("🚀 Starting Database Persistence & Snapshotting Test...")
    
    # 0. Database cleanup for clean test run
    db = SessionLocal()
    db.query(DocumentUpdate).filter(DocumentUpdate.document_id == "doc_persist_test").delete()
    db.query(DocumentSnapshot).filter(DocumentSnapshot.document_id == "doc_persist_test").delete()
    db.commit()
    db.close()
    
    # --- PHASE 1: Connect Client A and send 6 edits ---
    async with websockets.connect(WS_URL) as ws:
        # Receive initial empty sync
        await ws.recv()
        
        doc_a = Y.Doc()
        text_a = doc_a.get("text", type=Y.Text)
        
        # We will send 6 incremental edits to trigger 1 snapshot (limit is 5)
        for i in range(1, 7):
            with doc_a.transaction():
                text_a += f"{i}"
            
            print(f"[Client A] Sending edit {i}: '{str(text_a)}'")
            await ws.send(b"\x00" + doc_a.get_update())
            await asyncio.sleep(0.3)  # Small gap to ensure sequential DB writes
            
    print("[Client A] Disconnected. Document unloaded from RAM.")
    await asyncio.sleep(1) # wait for cleanup
    
    # --- PHASE 2: Connect Client B and verify reconstruction from DB ---
    async with websockets.connect(WS_URL) as ws:
        print("[Client B] Connecting to doc_persist_test...")
        
        # Server should load from DB and send converged state
        initial_message = await ws.recv()
        tag = initial_message[0]
        payload = initial_message[1:]
        
        doc_b = Y.Doc()
        doc_b.apply_update(payload)
        text_b = doc_b.get("text", type=Y.Text)
        
        final_text = str(text_b)
        print(f"[Client B] Reconstructed Document state from DB: '{final_text}'")
        
        # Assert check: The document should be "123456"
        assert final_text == "123456"
        print("✅ Success: State successfully reconstructed from DB!")
        
    # --- PHASE 3: Verify DB Table counts ---
    db = SessionLocal()
    updates_count = db.query(DocumentUpdate).filter(DocumentUpdate.document_id == "doc_persist_test").count()
    snapshots_count = db.query(DocumentSnapshot).filter(DocumentSnapshot.document_id == "doc_persist_test").count()
    db.close()
    
    print("\n--- DB Table Counts Check ---")
    print(f"Total Updates in DB  : {updates_count} (Expected: 6)")
    print(f"Total Snapshots in DB: {snapshots_count} (Expected: 1)")
    
    assert updates_count == 6
    assert snapshots_count == 1
    print("✅ Success: DB layout matches Strategy C hybrid specification!")

if __name__ == "__main__":
    asyncio.run(test_persistence_flow())
