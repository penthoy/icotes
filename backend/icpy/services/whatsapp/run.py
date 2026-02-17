#!/usr/bin/env python3
"""
WhatsApp Bot Standalone Runner

Single-command launcher that boots the WhatsApp bot with the chat service
so it can receive messages, route them through the AI agent, and reply.

Usage:
    cd backend
    PYTHONPATH=. uv run python -m icpy.services.whatsapp.run

Or use the convenience script:
    ./run_whatsapp.sh
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure backend is on PYTHONPATH
backend_dir = str(Path(__file__).resolve().parents[3])  # backend/
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(backend_dir, "..", ".env"))

# Configure logging to show info-level messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Suppress noisy loggers
for noisy in ("httpx", "httpcore", "openai", "urllib3", "watchdog", "watchfiles"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("whatsapp.runner")


async def main():
    """Boot chat service + WhatsApp bot, then wait until interrupted."""

    owner_phone = os.getenv("WHATSAPP_OWNER_PHONE")
    if not owner_phone:
        print("❌ WHATSAPP_OWNER_PHONE not set in .env — cannot start bot")
        sys.exit(1)

    dm_policy = os.getenv("WHATSAPP_DM_POLICY", "pairing")

    print("=" * 60)
    print("  WhatsApp Bot — Standalone Runner")
    print("=" * 60)
    print(f"  Owner phone:  {owner_phone}")
    print(f"  DM policy:    {dm_policy}")
    print("=" * 60)
    print()

    # Import and initialise the chat service (AI brain)
    logger.info("Initialising chat service...")
    from icpy.services.chat_service import get_chat_service
    chat_service = get_chat_service()
    logger.info("Chat service ready")

    # Import and start the WhatsApp bot service
    from icpy.services.whatsapp import start_whatsapp_bot, stop_whatsapp_bot

    logger.info("Starting WhatsApp bot service...")
    await start_whatsapp_bot()

    # Set up graceful shutdown
    stop_event = asyncio.Event()

    def _signal_handler():
        print("\n⏹️  Shutting down...", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    print("Bot running — press Ctrl+C to stop\n", flush=True)

    # Wait until interrupted
    await stop_event.wait()

    # Cleanup
    await stop_whatsapp_bot()
    logger.info("WhatsApp bot stopped cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
