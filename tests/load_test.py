import asyncio
import time
import websockets

WS_URL = "ws://localhost:8000/ws/load_test_doc"
CONCURRENT_CONNECTIONS = 50
TEST_DURATION = 5  # seconds

async def mock_client(client_id: int, results: list):
    """Simulates a single client connecting, sending periodic updates, and measuring success."""
    try:
        start_connect = time.time()
        async with websockets.connect(WS_URL) as ws:
            connect_latency = time.time() - start_connect
            results.append({"type": "connect_success", "latency": connect_latency})
            
            # Send message every 1 second
            for i in range(TEST_DURATION):
                send_start = time.time()
                payload = f"Client {client_id} edit {i}"
                await ws.send(payload)
                send_latency = time.time() - send_start
                results.append({"type": "send_success", "latency": send_latency})
                
                await asyncio.sleep(1)
                
    except Exception as e:
        results.append({"type": "failure", "error": str(e)})

async def main():
    print(f"🚀 Starting Load Test with {CONCURRENT_CONNECTIONS} concurrent WebSocket clients...")
    print(f"Target URL: {WS_URL}")
    
    results = []
    
    # Create N concurrent client tasks
    tasks = [mock_client(i, results) for i in range(CONCURRENT_CONNECTIONS)]
    
    start_time = time.time()
    # Run all client connections concurrently
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # --- Analyse Metrics ---
    connects = [r["latency"] for r in results if r["type"] == "connect_success"]
    sends = [r["latency"] for r in results if r["type"] == "send_success"]
    failures = [r for r in results if r["type"] == "failure"]
    
    print("\n" + "="*40)
    print("📊 LOAD TEST REPORT")
    print("="*40)
    print(f"Total Test Duration: {total_time:.2f} seconds")
    print(f"Total Attempted Connections: {CONCURRENT_CONNECTIONS}")
    print(f"Successful Connections: {len(connects)}")
    print(f"Failed Connections: {len(failures)}")
    
    if connects:
        avg_connect = sum(connects) / len(connects)
        max_connect = max(connects)
        print(f"Average Connection Latency: {avg_connect*1000:.2f} ms")
        print(f"Max Connection Latency: {max_connect*1000:.2f} ms")
        
    if sends:
        avg_send = sum(sends) / len(sends)
        print(f"Average Message Send Latency: {avg_send*1000:.2f} ms")
        
    if failures:
        print("\n❌ Errors Encountered:")
        for f in failures[:5]:  # print first 5 errors
            print(f"- {f['error']}")
            
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
