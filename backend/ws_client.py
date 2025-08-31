import asyncio, json, os, sys

async def main():
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
