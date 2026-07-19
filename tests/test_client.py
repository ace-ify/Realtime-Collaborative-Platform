import asyncio
import websockets
import json
import pycrdt as Y


WS_URL = "ws://localhost:8000/ws/doc_test_python"

async def client_a():
    async with websockets.connect(WS_URL) as ws:
        print("[Client A] Connected to WebSocket.")
        
        # 1. Receive initial server state vector
        initial_state = await ws.recv()
        doc_a = Y.Doc()
        doc_a.apply_update(initial_state)
        
        # 2. Wait a bit, then edit document locally
        await asyncio.sleep(1)
        text_a = doc_a.get("text", type=Y.Text)
        with doc_a.transaction():
            text_a += "Alice "
        
        # 3. Get binary update of this change and send to server
        update_bytes = doc_a.get_update()
        print("[Client A] Sending binary update...")
        await ws.send(update_bytes)
    
        # 4. Receive concurrent update from Client B
        b_update = await ws.recv()
        doc_a.apply_update(b_update)
        
        # 5. Print merged output on Client A side
        print(f"[Client A] Merged State: '{str(text_a)}'")

        
        await asyncio.sleep(2)
        return str(text_a)


async def client_b():
    """Simulates Client B sending a concurrent edit."""
    async with websockets.connect(WS_URL) as ws:
        print("[Client B] Connected to WebSocket.")
        
        # 1. Receive initial server state vector
        initial_state = await ws.recv()
        doc_b = Y.Doc()
        doc_b.apply_update(initial_state)
        
        # 2. Wait a bit, then edit document locally (concurrently with A)
        await asyncio.sleep(1)
        text_b = doc_b.get("text", type=Y.Text)
        with doc_b.transaction():
            text_b += "Bob "
            
        # 3. Get binary update of this change and send to server
        update_bytes = doc_b.get_update()
        print("[Client B] Sending binary update...")
        await ws.send(update_bytes)
        
        # 4. Receive concurrent update from Client A
        a_update = await ws.recv()
        doc_b.apply_update(a_update)
        
        # 5. Print merged output on Client B side
        print(f"[Client B] Merged State: '{str(text_b)}'")
        
        await asyncio.sleep(2)
        return str(text_b) # <--- Return final text for verification


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
