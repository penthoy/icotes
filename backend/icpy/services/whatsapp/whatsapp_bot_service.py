"""
WhatsApp Bot Service for ICUI Framework

Integrates a WhatsApp bot (via Baileys Node.js bridge) with the existing chat service
to provide AI assistant functionality through WhatsApp messages. Follows the same
patterns as the Discord bot service — singleton pattern, chat service monkey-patch
for intercepting AI responses, and session management per user.

Architecture:
  Python (this service) ←── stdin/stdout JSON ──→ Node.js (bridge.js / Baileys)

The Node.js subprocess handles the actual WhatsApp protocol. This service:
  - Manages the subprocess lifecycle
  - Routes inbound WhatsApp messages through the chat service AI pipeline
  - Intercepts AI responses and sends them back to WhatsApp
  - Handles access control (pairing codes, allowlists)
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _mask_phone(value: str) -> str:
    """Mask phone numbers for log output, keeping last 4 digits."""
    if not value:
        return value
    visible = value[-4:] if len(value) > 4 else value
    return f"***{visible}"

logger = logging.getLogger(__name__)

# Singleton instance
_whatsapp_bot_service: Optional["WhatsAppBotService"] = None


class WhatsAppMessageFormatter:
    """
    Formats chat service streaming output for WhatsApp.

    Strips tool-call markers and status indicators, keeping clean text
    for the WhatsApp reply. Image/video results are described textually
    since WhatsApp doesn't support rich embeds like Discord.
    """

    import re

    # Same patterns as Discord formatter — tool call markers from AI output
    TOOL_START_RE = re.compile(r"📋\s*\*\*(\w+)\*\*:\s*(.+?)(?:\n|$)", re.DOTALL)
    TOOL_SUCCESS_RE = re.compile(r"✅\s*\*\*Success\*\*:\s*(.+?)(?:\n|$)", re.DOTALL)
    TOOL_ERROR_RE = re.compile(r"❌\s*\*\*Error\*\*:\s*(.+?)(?:\n|$)", re.DOTALL)
    STATUS_MARKERS_RE = re.compile(
        r"🔧\s*\*\*(?:Executing tools\.{3}|Tool execution complete\.\s*Continuing\.{3})\*\*\s*",
        re.DOTALL,
    )
    MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)\s*")

    @classmethod
    def clean_for_whatsapp(cls, text: str) -> str:
        """
        Strip tool call markers and status indicators from AI output.
        Returns clean text suitable for WhatsApp.
        """
        cleaned = text

        # Remove tool call blocks
        cleaned = cls.TOOL_START_RE.sub("", cleaned)
        cleaned = cls.TOOL_SUCCESS_RE.sub("", cleaned)
        cleaned = cls.TOOL_ERROR_RE.sub("", cleaned)
        cleaned = cls.STATUS_MARKERS_RE.sub("", cleaned)
        cleaned = cls.MD_IMAGE_RE.sub("", cleaned)

        # Collapse excessive whitespace
        import re
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def extract_media_paths(cls, text: str) -> list:
        """
        Extract file paths from tool success events for media sending.

        Returns list of dicts: [{ "type": "image"|"video", "path": "...", "prompt": "..." }]
        """
        media = []

        # Find tool start/success pairs
        starts = list(cls.TOOL_START_RE.finditer(text))
        successes = list(cls.TOOL_SUCCESS_RE.finditer(text))

        success_idx = 0
        for start_match in starts:
            tool_name = start_match.group(1)
            if success_idx >= len(successes):
                break

            success_match = successes[success_idx]
            success_idx += 1

            try:
                result_data = json.loads(success_match.group(1).strip())
            except (json.JSONDecodeError, ValueError):
                continue

            if not isinstance(result_data, dict):
                continue

            # Extract image path
            if tool_name == "generate_image":
                abs_path = None
                image_ref = result_data.get("imageReference", {})
                if isinstance(image_ref, dict):
                    abs_path = image_ref.get("absolute_path")
                if not abs_path:
                    abs_path = result_data.get("absolutePath")
                if abs_path:
                    # Strip file:// prefix
                    if abs_path.startswith("file://"):
                        abs_path = abs_path[7:]
                    media.append({
                        "type": "image",
                        "path": abs_path,
                        "prompt": start_match.group(2).strip()[:200],
                    })

            # Extract video path
            elif tool_name == "image_to_video":
                abs_path = result_data.get("absolute_path") or result_data.get("absolutePath")
                if abs_path:
                    if abs_path.startswith("file://"):
                        abs_path = abs_path[7:]
                    media.append({
                        "type": "video",
                        "path": abs_path,
                        "prompt": start_match.group(2).strip()[:200],
                    })

        return media


class WhatsAppBotService:
    """
    WhatsApp bot service that integrates with the ICUI chat service.

    Routes WhatsApp messages through the same AI agent pipeline as the web chat,
    providing a consistent experience across platforms. Spawns a Node.js subprocess
    running Baileys for the actual WhatsApp protocol handling.
    """

    def __init__(self, owner_phone: str, dm_policy: str = "pairing"):
        """
        Initialize WhatsApp bot service.

        Args:
            owner_phone: Owner's phone number in E164 format (e.g. "+16047193142")
            dm_policy: Access control mode ("open", "pairing", "allowlist", "disabled")
        """
        self.owner_phone = owner_phone
        self.dm_policy = dm_policy
        self.chat_service = None

        # Node.js bridge subprocess
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._running = False

        # Track WhatsApp user sessions (sender_jid → chat_session_id)
        self.user_sessions: Dict[str, str] = {}

        # Track per-message response state (ws_id → chunks)
        self._wa_response_chunks: Dict[str, List[str]] = {}
        self._wa_pending_messages: Dict[str, dict] = {}  # ws_id → message_data

        # Connection state
        self.connected = False
        self.self_jid: Optional[str] = None
        self.self_name: Optional[str] = None
        self.latest_qr: Optional[str] = None  # Base64 QR for web UI

        # Access control
        self.access_control = None

        # Debounce: coalesce rapid messages from same sender
        self._message_buffer: Dict[str, dict] = {}  # sender → { texts, timer }
        self._debounce_ms = 2.0  # seconds

        logger.info("WhatsApp bot service initialized")

    # ─── Lifecycle ──────────────────────────────────────────

    async def initialize(self):
        """Initialize chat service integration and access control."""
        try:
            from ..chat_service import get_chat_service
            self.chat_service = get_chat_service()

            # Monkey-patch websocket message sending (same pattern as Discord)
            self._original_send_ws = self.chat_service._send_websocket_message
            self.chat_service._send_websocket_message = self._intercept_websocket_message

            # Initialize access control
            from .access_control import WhatsAppAccessControl
            data_dir = os.path.join(
                os.path.dirname(__file__), "data"
            )
            self.access_control = WhatsAppAccessControl(data_dir, self.dm_policy)
            await self.access_control.load()

            # Pre-approve the owner
            if self.owner_phone:
                await self.access_control.add_allowed(self.owner_phone)

            logger.info("WhatsApp bot service initialized and connected to chat service")

        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp bot service: {e}", exc_info=True)
            raise

    async def start(self):
        """Start the Node.js bridge subprocess."""
        if self._running:
            logger.warning("WhatsApp bot is already running")
            return

        bridge_dir = Path(__file__).parent
        bridge_script = bridge_dir / "bridge.js"
        node_modules = bridge_dir / "node_modules"

        # Check if node_modules exist, install if not
        if not node_modules.exists():
            logger.info("Installing WhatsApp bridge dependencies...")
            await self._install_deps(bridge_dir)

        if not bridge_script.exists():
            logger.error(f"Bridge script not found: {bridge_script}")
            return

        # Find node binary — prefer nvm Node 20+ over system Node
        node_bin = self._find_node_binary()
        if not node_bin:
            logger.error("Node.js 20+ not found — WhatsApp bot requires Node.js 20+")
            return

        # Set auth dir via env
        env = os.environ.copy()
        env["WA_AUTH_DIR"] = str(bridge_dir / "auth_store")
        env["WA_BOT_NAME"] = "icotes"
        env["WA_LOG_LEVEL"] = os.getenv("WA_LOG_LEVEL", "error")

        logger.info(f"Starting WhatsApp bridge: {node_bin} {bridge_script}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                node_bin, str(bridge_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(bridge_dir),
                env=env,
            )
            self._running = True

            # Start reading stdout (events from bridge)
            self._reader_task = asyncio.create_task(self._read_bridge_events())
            # Start reading stderr (logs from bridge)
            asyncio.create_task(self._read_bridge_logs())

            logger.info(f"WhatsApp bridge started (PID: {self._process.pid})")

        except Exception as e:
            logger.error(f"Failed to start WhatsApp bridge: {e}", exc_info=True)
            self._running = False

    async def stop(self):
        """Stop the WhatsApp bridge subprocess."""
        logger.info("Stopping WhatsApp bot...")
        self._running = False

        if self._process and self._process.returncode is None:
            # Send stop command
            try:
                await self._send_command("stop", {})
                # Give it a moment to shut down gracefully
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        self.connected = False
        logger.info("WhatsApp bot stopped")

    def is_running(self) -> bool:
        """Check if the WhatsApp bot is running."""
        return self._running and self._process is not None and self._process.returncode is None

    # ─── Bridge communication ────────────────────────────────

    async def _send_command(self, cmd_type: str, data: dict):
        """Send a JSON command to the Node.js bridge via stdin."""
        if not self._process or self._process.stdin is None:
            logger.warning("Cannot send command: bridge not running")
            return

        msg = json.dumps({"type": cmd_type, "data": data}) + "\n"
        try:
            self._process.stdin.write(msg.encode())
            await self._process.stdin.drain()
        except Exception as e:
            logger.error(f"Failed to send command to bridge: {e}")

    async def _read_bridge_events(self):
        """Read JSON events from the bridge stdout."""
        if not self._process or self._process.stdout is None:
            return

        try:
            async for line in self._process.stdout:
                if not self._running:
                    break

                decoded = line.decode().strip()
                if not decoded:
                    continue

                try:
                    event = json.loads(decoded)
                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON output from bridge: {decoded[:200]}")
                    continue

                await self._handle_bridge_event(event)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading bridge events: {e}", exc_info=True)
        finally:
            self._running = False
            logger.info("Bridge event reader stopped")

    async def _read_bridge_logs(self):
        """Read stderr logs from the bridge and forward to Python logger."""
        if not self._process or self._process.stderr is None:
            return

        try:
            async for line in self._process.stderr:
                decoded = line.decode().strip()
                if decoded:
                    # Print bridge logs to console so user sees QR, connection status, etc.
                    print(decoded, flush=True)
                    logger.debug(f"[WA-Bridge] {decoded}")
        except Exception:
            pass

    async def _handle_bridge_event(self, event: dict):
        """Handle an event from the Node.js bridge."""
        event_type = event.get("type", "")
        data = event.get("data", {})

        if event_type == "ready":
            logger.info("WhatsApp bridge ready")

        elif event_type == "qr":
            self.latest_qr = data.get("qr")
            logger.info("QR code received — scan with WhatsApp to connect")
            print("\n📱 QR code ready — scan with WhatsApp > Linked Devices > Link a Device\n", flush=True)

        elif event_type == "connected":
            self.connected = True
            self.self_jid = data.get("jid")
            self.self_name = data.get("name")
            self.latest_qr = None  # Clear QR once connected
            logger.info(f"WhatsApp connected as {self.self_name} ({self.self_jid})")

            # Clear visual signal that the bot is linked and ready
            jid_short = self.self_jid.split("@")[0] if self.self_jid else "?"
            print(flush=True)
            print("╔══════════════════════════════════════════════════╗", flush=True)
            print("║  ✅  WhatsApp Bot Linked Successfully            ║", flush=True)
            print(f"║  Name: {self.self_name:<41} ║", flush=True)
            print(f"║  JID:  {jid_short:<41} ║", flush=True)
            print("║  Status: Online & listening for messages         ║", flush=True)
            print("╚══════════════════════════════════════════════════╝", flush=True)
            print(flush=True)

        elif event_type == "disconnected":
            self.connected = False
            reason = data.get("reason", "unknown")
            logger.warning(f"WhatsApp disconnected: {reason}")

        elif event_type == "message":
            await self._handle_whatsapp_message(data)

        elif event_type == "error":
            logger.error(f"WhatsApp bridge error: {data.get('message', 'unknown')}")

        else:
            logger.debug(f"Unknown bridge event: {event_type}")

    # ─── Inbound message handling ────────────────────────────

    async def _handle_whatsapp_message(self, msg_data: dict):
        """
        Handle an incoming WhatsApp message. Applies access control,
        then routes through the chat service AI pipeline.
        """
        sender = msg_data.get("sender", "")
        sender_e164 = msg_data.get("senderE164") or ""
        text = msg_data.get("text", "").strip()
        is_group = msg_data.get("isGroup", False)
        chat_jid = msg_data.get("from", "")
        message_id = msg_data.get("messageId", "")

        # Fallback: extract E164 from sender JID if bridge didn't provide it
        if not sender_e164 and sender:
            number = sender.split(":")[0].split("@")[0]
            if number.isdigit():
                sender_e164 = f"+{number}"
        bot_mentioned = msg_data.get("botMentioned", False)
        media = msg_data.get("media")

        if (not text and not media) or not chat_jid:
            return

        # For group messages, only respond if bot was mentioned
        if is_group and not bot_mentioned:
            return

        # Access control (skip for groups — group gating is mention-based)
        if not is_group and self.access_control and self.dm_policy != "open":
            if not self.access_control.is_allowed(sender_e164):
                if self.dm_policy == "pairing":
                    code = await self.access_control.generate_pairing_code(sender_e164)
                    if code:
                        await self._send_command("send", {
                            "jid": chat_jid,
                            "text": (
                                f"🔐 Access not configured.\n\n"
                                f"Your pairing code: *{code}*\n\n"
                                f"Ask the bot owner to approve this code."
                            ),
                        })
                    else:
                        await self._send_command("send", {
                            "jid": chat_jid,
                            "text": "⚠️ Too many pending requests. Please try again later.",
                        })
                else:
                    # Allowlist mode — silently ignore or send a rejection
                    await self._send_command("send", {
                        "jid": chat_jid,
                        "text": "⚠️ You are not authorized to use this bot.",
                    })
                return

        # Owner CLI commands via WhatsApp DM
        if sender_e164 == self.owner_phone and text.startswith("/"):
            handled = await self._handle_owner_command(chat_jid, text)
            if handled:
                return

        masked = self._mask_phone(sender_e164 or sender)
        logger.info(
            f"WhatsApp message: sender={masked}, "
            f"group={is_group}, text={text[:80]}"
        )
        print(f"💬 Message from {masked}: {text[:100]}", flush=True)

        # Route through chat service
        await self._process_through_chat(
            chat_jid, sender, text, message_id,
            is_group=is_group,
            group_name=msg_data.get("groupName"),
            sender_name=msg_data.get("senderName"),
            sender_e164=sender_e164,
            media=media,
        )

    async def _handle_owner_command(self, chat_jid: str, text: str) -> bool:
        """
        Handle owner slash commands via WhatsApp DM.

        Commands:
          /approve <code>  — Approve a pairing code
          /revoke <phone>  — Revoke access for a phone number
          /pending         — List pending pairing requests
          /status          — Show bot status

        Returns True if the command was handled.
        """
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/approve" and arg:
            phone = await self.access_control.approve(arg)
            if phone:
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": f"✅ Approved: {phone}",
                })
            else:
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": f"❌ Code not found or expired: {arg}",
                })
            return True

        elif cmd == "/revoke" and arg:
            revoked = await self.access_control.revoke(arg)
            if revoked:
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": f"✅ Revoked access for {arg}",
                })
            else:
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": f"❌ {arg} was not in the allowlist",
                })
            return True

        elif cmd == "/pending":
            pending = await self.access_control.list_pending()
            if pending:
                lines = ["📋 *Pending pairing requests:*\n"]
                for p in pending:
                    lines.append(f"  • {p['phone']} — code: *{p['code']}*")
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": "\n".join(lines),
                })
            else:
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": "No pending pairing requests.",
                })
            return True

        elif cmd == "/status":
            status_lines = [
                f"*WhatsApp Bot Status*",
                f"Connected: {'✅' if self.connected else '❌'}",
                f"JID: {self.self_jid or 'N/A'}",
                f"DM Policy: {self.dm_policy}",
                f"Allowed numbers: {len(self.access_control.allowlist)}",
                f"Active sessions: {len(self.user_sessions)}",
            ]
            await self._send_command("send", {
                "jid": chat_jid,
                "text": "\n".join(status_lines),
            })
            return True

        return False

    async def _process_through_chat(
        self, chat_jid: str, sender: str, text: str, message_id: str,
        *, is_group: bool = False, group_name: str = None,
        sender_name: str = None, sender_e164: str = None,
        media: dict = None,
    ):
        """
        Route a WhatsApp message through the chat service AI pipeline.
        Same approach as the Discord bot — create virtual websocket ID,
        intercept AI responses via monkey-patched send method.

        Sets platform context so the AI agent knows it's responding on WhatsApp
        and can identify itself correctly when @mentioned.
        """
        if not self.chat_service:
            await self._send_command("send", {
                "jid": chat_jid,
                "text": "⚠️ Chat service not initialized. Please try again later.",
            })
            return

        # Set platform context for AI self-awareness
        # This propagates to child async tasks via ContextVar copy
        from icpy.agent.helpers import set_platform_context
        set_platform_context({
            'channel': 'whatsapp',
            'bot_name': self.self_name or 'Icotes',
            'bot_jid': self.self_jid,
            'is_group': is_group,
            'group_name': group_name,
            'sender_name': sender_name,
            'sender_phone': sender_e164,
        })

        # Get or create session for this sender
        session_id = self.user_sessions.get(sender)
        if not session_id:
            try:
                session_id = await self.chat_service.create_session(f"WhatsApp: {sender}")
                self.user_sessions[sender] = session_id
                logger.info(f"Created chat session {session_id} for WhatsApp user {sender}")
            except Exception as e:
                logger.error(f"Failed to create session for {sender}: {e}", exc_info=True)
                await self._send_command("send", {
                    "jid": chat_jid,
                    "text": "⚠️ Failed to create chat session.",
                })
                return

        # Create virtual websocket ID (same naming convention as Discord)
        wa_ws_id = f"whatsapp_{sender}_{message_id}"

        # Show typing indicator
        await self._send_command("typing", {"jid": chat_jid})

        try:
            # Register virtual websocket
            await self.chat_service.connect_websocket(wa_ws_id)

            # Store context for when the response arrives
            self._wa_pending_messages[wa_ws_id] = {
                "chat_jid": chat_jid,
                "sender": sender,
            }
            self._wa_response_chunks[wa_ws_id] = []

            # Handle media attachments from WhatsApp (images, videos)
            attachments = []
            if media and isinstance(media, dict):
                media_path = media.get('path')
                if media_path and os.path.isfile(media_path):
                    stored_abs_path = media_path
                    stored_rel_path = None

                    # Copy media into workspace/.icotes/media/files so chat_service can embed it
                    try:
                        ws_root = getattr(self.chat_service, 'workspace_root', None)
                        if ws_root:
                            media_files_dir = Path(ws_root) / '.icotes' / 'media' / 'files'
                            media_files_dir.mkdir(parents=True, exist_ok=True)

                            source_name = os.path.basename(media_path)
                            dest_name = f"wa_{message_id}_{source_name}"
                            dest_path = media_files_dir / dest_name
                            shutil.copy2(media_path, dest_path)

                            stored_abs_path = str(dest_path)
                            stored_rel_path = f"files/{dest_name}"
                    except Exception as copy_err:
                        logger.warning(f"Failed to copy WhatsApp media into workspace store: {copy_err}")

                    media_type = media.get('type', 'image')
                    kind = 'images' if media_type == 'image' else 'files'

                    attachments.append({
                        'kind': kind,
                        'mime_type': media.get('mime', 'image/jpeg'),
                        'filename': os.path.basename(stored_abs_path),
                        'absolute_path': stored_abs_path,
                        'relative_path': stored_rel_path,
                        'path': stored_abs_path,
                        'size_bytes': media.get('size', 0),
                    })
                    logger.info(f"WhatsApp media attachment prepared: {stored_abs_path}")

            # If there's media but no text, provide a default prompt
            content = text or ("[Image received — please describe or analyze this image]" if media else "")

            # Resolve default agent type
            metadata = {"session_id": session_id}
            if attachments:
                metadata["attachments"] = attachments
            default_agent = self._get_default_agent_type()
            if default_agent:
                metadata["agentType"] = default_agent

            # Send message through chat service
            logger.debug(f"Sending to chat service: {content[:50]}...")
            await self.chat_service.handle_user_message(
                websocket_id=wa_ws_id,
                content=content,
                metadata=metadata,
            )

            # Wait briefly for streaming to start
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
            await self._disconnect_virtual_ws(wa_ws_id)
            await self._send_command("send", {
                "jid": chat_jid,
                "text": f"⚠️ Error processing message: {str(e)}",
            })

    @staticmethod
    def _mask_phone(value: str) -> str:
        """Mask phone numbers for log output."""
        return _mask_phone(value)

    async def _disconnect_virtual_ws(self, websocket_id: str) -> None:
        """Disconnect a virtual WebSocket to prevent connection-manager leaks."""
        try:
            await self.chat_service.disconnect_websocket(websocket_id)
        except Exception:
            pass  # Best-effort cleanup

    # ─── Response interception (same pattern as Discord) ─────

    async def _intercept_websocket_message(self, websocket_id: str, message_data: dict):
        """
        Intercept websocket messages to capture AI responses for WhatsApp.
        Non-WhatsApp messages are passed through to the original handler.
        """
        if websocket_id.startswith("whatsapp_"):
            msg_type = message_data.get("type", "")

            if msg_type == "message_stream":
                # Collect streaming chunks
                if message_data.get("stream_chunk"):
                    content = message_data.get("chunk", "")
                    if content and websocket_id in self._wa_response_chunks:
                        self._wa_response_chunks[websocket_id].append(content)

                # Stream end — format and send
                if message_data.get("stream_end"):
                    full_response = "".join(
                        self._wa_response_chunks.get(websocket_id, [])
                    )
                    pending = self._wa_pending_messages.get(websocket_id)
                    if pending and full_response:
                        await self._send_formatted_response(
                            pending["chat_jid"], full_response
                        )
                    # Cleanup
                    self._wa_response_chunks.pop(websocket_id, None)
                    self._wa_pending_messages.pop(websocket_id, None)
                    await self._disconnect_virtual_ws(websocket_id)

            elif msg_type == "message":
                # Non-streaming response
                content = message_data.get("content", "")
                pending = self._wa_pending_messages.get(websocket_id)
                if pending and content:
                    await self._send_formatted_response(pending["chat_jid"], content)
                self._wa_response_chunks.pop(websocket_id, None)
                self._wa_pending_messages.pop(websocket_id, None)
                await self._disconnect_virtual_ws(websocket_id)

            elif msg_type == "error":
                error_msg = message_data.get("message", "An error occurred")
                pending = self._wa_pending_messages.get(websocket_id)
                if pending:
                    await self._send_command("send", {
                        "jid": pending["chat_jid"],
                        "text": f"⚠️ {error_msg}",
                    })
                self._wa_response_chunks.pop(websocket_id, None)
                self._wa_pending_messages.pop(websocket_id, None)
                await self._disconnect_virtual_ws(websocket_id)

            return  # Don't pass WhatsApp messages to original handler

        # Non-WhatsApp messages — pass through
        if hasattr(self, "_original_send_ws"):
            await self._original_send_ws(websocket_id, message_data)

    async def _send_formatted_response(self, chat_jid: str, full_response: str):
        """
        Format and send the AI response to WhatsApp.
        Extracts media paths for image/video results and sends them as media messages.
        Cleans remaining text of tool markers before sending.
        """
        fmt = WhatsAppMessageFormatter

        # Extract media files to send
        media_items = fmt.extract_media_paths(full_response)
        for media in media_items:
            media_path = media["path"]
            if os.path.isfile(media_path):
                media_type = media["type"]
                caption = media.get("prompt", "")
                await self._send_command("send_media", {
                    "jid": chat_jid,
                    "filePath": media_path,
                    "caption": caption,
                    "mediaType": media_type,
                })
                await asyncio.sleep(0.3)  # Small delay between media sends

        # Send cleaned text
        cleaned = fmt.clean_for_whatsapp(full_response)
        if cleaned:
            await self._send_command("send", {"jid": chat_jid, "text": cleaned})

    # ─── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _find_node_binary() -> Optional[str]:
        """
        Find a Node.js 20+ binary. Checks nvm installations first,
        then falls back to system PATH.
        """
        # Check nvm installations (prefer highest version >= 20)
        nvm_dir = os.environ.get("NVM_DIR", os.path.expanduser("~/.nvm"))
        nvm_versions = Path(nvm_dir) / "versions" / "node"
        if nvm_versions.is_dir():
            versions = sorted(nvm_versions.iterdir(), reverse=True)
            for v in versions:
                # Parse version number (v20.20.0 → 20)
                name = v.name.lstrip("v")
                try:
                    major = int(name.split(".")[0])
                except (ValueError, IndexError):
                    continue
                if major >= 20:
                    node_bin = v / "bin" / "node"
                    if node_bin.is_file():
                        logger.info(f"Using nvm Node.js: {node_bin}")
                        return str(node_bin)

        # Fallback to system PATH
        node_bin = shutil.which("node")
        if node_bin:
            # Check version
            try:
                result = subprocess.run(
                    [node_bin, "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                version_str = result.stdout.strip().lstrip("v")
                major = int(version_str.split(".")[0])
                if major >= 20:
                    return node_bin
                else:
                    logger.warning(f"System Node.js is v{version_str}, need 20+")
            except Exception:
                pass

        return None

    def _get_default_agent_type(self) -> Optional[str]:
        """Resolve default agent type from agents.json settings."""
        try:
            from ..agent_config_service import get_agent_config_service
            config_service = get_agent_config_service()
            settings = config_service.get_menu_settings()
            return settings.default_agent or None
        except Exception as e:
            logger.debug(f"Failed to resolve default agent: {e}")
            return None

    @staticmethod
    async def _install_deps(bridge_dir: Path):
        """Install Node.js dependencies for the bridge."""
        npm_bin = shutil.which("npm")
        if not npm_bin:
            logger.error("npm not found — cannot install WhatsApp bridge dependencies")
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                npm_bin, "install", "--production",
                cwd=str(bridge_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                logger.info("WhatsApp bridge dependencies installed successfully")
            else:
                logger.error(f"npm install failed: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Failed to install bridge deps: {e}")

    # ─── Public API for web UI ───────────────────────────────

    def get_qr_code(self) -> Optional[str]:
        """Get the latest QR code as base64 data URL (for web UI display)."""
        return self.latest_qr

    def get_status(self) -> dict:
        """Get current bot status."""
        return {
            "running": self.is_running(),
            "connected": self.connected,
            "jid": self.self_jid,
            "name": self.self_name,
            "dm_policy": self.dm_policy,
            "active_sessions": len(self.user_sessions),
            "allowed_numbers": len(self.access_control.allowlist) if self.access_control else 0,
        }


# ─── Module-level functions (same pattern as Discord) ────────

async def get_whatsapp_bot_service() -> Optional[WhatsAppBotService]:
    """Get the global WhatsApp bot service instance."""
    global _whatsapp_bot_service

    if _whatsapp_bot_service is None:
        owner_phone = os.getenv("WHATSAPP_OWNER_PHONE")
        if not owner_phone:
            logger.warning("WHATSAPP_OWNER_PHONE not configured, WhatsApp bot disabled")
            return None

        dm_policy = os.getenv("WHATSAPP_DM_POLICY", "pairing")
        _whatsapp_bot_service = WhatsAppBotService(owner_phone, dm_policy)
        await _whatsapp_bot_service.initialize()

    return _whatsapp_bot_service


async def start_whatsapp_bot():
    """Start the WhatsApp bot service."""
    service = await get_whatsapp_bot_service()
    if service:
        await service.start()
        logger.info("WhatsApp bot service started")
    else:
        logger.warning("WhatsApp bot service not available (owner phone not configured)")


async def stop_whatsapp_bot():
    """Stop the WhatsApp bot service."""
    global _whatsapp_bot_service

    if _whatsapp_bot_service:
        await _whatsapp_bot_service.stop()
        _whatsapp_bot_service = None
        logger.info("WhatsApp bot service stopped")
