import asyncio
import websockets
import json
import pycrdt as Y


WS_URL = "ws://localhost:8000/ws/doc_test_python"

async def client_a():
    async with websockets.connect(WS_URL) as ws:
        print("[Client A] Connected.")
        
        # 1. Receive initial sync state (Starts with 0x00)
        initial_message = await ws.recv()
        tag = initial_message[0]
        initial_state = initial_message[1:]
        
        doc_a = Y.Doc()
        doc_a.apply_update(initial_state)
        
        # 2. Wait a bit, then edit document locally
        await asyncio.sleep(1)
        text_a = doc_a.get("text", type=Y.Text)
        with doc_a.transaction():
            text_a += "Alice "
        
        # 3. Send CRDT edit with Tag 0x00 prefix
        update_bytes = doc_a.get_update()
        print("[Client A] Sending binary edit update (Tag 0x00)...")
        await ws.send(b"\x00" + update_bytes)
        
        # 4. Simultaneously, send Ephemeral Presence data with Tag 0x01 prefix
        presence_info = json.dumps({"user": "Alice", "cursor": 6, "color": "red"})
        print("[Client A] Sending ephemeral presence (Tag 0x01)...")
        await ws.send(b"\x01" + presence_info.encode('utf-8'))
        
        # 5. Receive concurrent updates from Client B
        # (We will look for B's binary edits or presence updates)
        for _ in range(2):
            msg = await ws.recv()
            msg_tag = msg[0]
            msg_payload = msg[1:]
            
            if msg_tag == 0:
                doc_a.apply_update(msg_payload)
            elif msg_tag == 1:
                presence_data = json.loads(msg_payload.decode('utf-8'))
                print(f"[Client A] Received presence event: {presence_data}")
        
        print(f"[Client A] Merged State: '{str(text_a)}'")
        await asyncio.sleep(1)
        return str(text_a)

async def client_b():
    """Simulates Client B sending a concurrent edit."""
    async with websockets.connect(WS_URL) as ws:
        print("[Client B] Connected.")
        
        # 1. Receive initial sync state (Starts with 0x00)
        initial_message = await ws.recv()
        tag = initial_message[0]
        initial_state = initial_message[1:]
        
        doc_b = Y.Doc()
        doc_b.apply_update(initial_state)
        
        # 2. Wait a bit, then edit document locally (concurrently with A)
        await asyncio.sleep(1)
        text_b = doc_b.get("text", type=Y.Text)
        with doc_b.transaction():
            text_b += "Bob "
            
        # 3. Send CRDT edit with Tag 0x00 prefix
        update_bytes = doc_b.get_update()
        print("[Client B] Sending binary edit update (Tag 0x00)...")
        await ws.send(b"\x00" + update_bytes)
        
        # 4. Simultaneously, send Ephemeral Presence data with Tag 0x01 prefix
        presence_info = json.dumps({"user": "Bob", "cursor": 4, "color": "blue"})
        print("[Client B] Sending ephemeral presence (Tag 0x01)...")
        await ws.send(b"\x01" + presence_info.encode('utf-8'))
        
        # 5. Receive concurrent updates from Client A
        for _ in range(2):
            msg = await ws.recv()
            msg_tag = msg[0]
            msg_payload = msg[1:]
            
            if msg_tag == 0:
                doc_b.apply_update(msg_payload)
            elif msg_tag == 1:
                presence_data = json.loads(msg_payload.decode('utf-8'))
                print(f"[Client B] Received presence event: {presence_data}")
        
        print(f"[Client B] Merged State: '{str(text_b)}'")
        await asyncio.sleep(1)
        return str(text_b)


async def main():
    # Run both clients concurrently
    # Dono clients se return hone wale states ko capture karein
    state_b, state_a = await asyncio.gather(client_b(), client_a())
    
    print("\n--- Final Convergence Check ---")
    print(f"Client A final state: '{state_a}'")
    print(f"Client B final state: '{state_b}'")
        
    # Assert check
    assert state_a == state_b
    print("✅ Success: States are perfectly converged!")

if __name__ == "__main__":
    asyncio.run(main())
