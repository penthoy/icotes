import asyncio, json, os, sys

async def main():
    """
    Start a minimal WebSocket client: connect to a configured URI, send a ping message, and keep the connection open.
    
    Determines the WebSocket URI from the WS_URI environment variable (defaults to 'ws://127.0.0.1:8000/ws'), dynamically imports the `websockets` library, opens an asynchronous connection, sends a JSON `{"type": "ping"}` message, and then awaits for 120 seconds to keep the connection alive.
    
    Notes:
    - If importing the `websockets` package fails, the function prints an error to stderr and exits the process with status code 1.
    - This coroutine does not return a value.
    """
    try:
        import websockets
    except Exception as e:
        print("websockets import error:", e, file=sys.stderr)
        sys.exit(1)
    uri = os.environ.get('WS_URI', 'ws://127.0.0.1:8000/ws')
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({'type':'ping'}))
        # stay connected for 120s
        await asyncio.sleep(120)

if __name__ == '__main__':
    asyncio.run(main())
