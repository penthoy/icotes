"""
Discord Bot Service for ICUI Framework

Integrates Discord bot with the existing chat service to provide AI assistant functionality
through Discord messages. Works similar to the chat panel in the web app.
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

# Singleton instance
_discord_bot_service: Optional['DiscordBotService'] = None


class DiscordMessageFormatter:
    """
    Formats chat service streaming output for Discord.
    
    Parses tool call markers, image generation results, and other structured
    output from the AI agent, producing Discord embeds and cleaned text.
    """

    # Patterns emitted by ToolResultFormatter in helpers.py
    TOOL_START_RE = re.compile(r'📋\s*\*\*(\w+)\*\*:\s*(.+?)(?:\n|$)', re.DOTALL)
    TOOL_SUCCESS_RE = re.compile(r'✅\s*\*\*Success\*\*:\s*(.+?)(?:\n|$)', re.DOTALL)
    TOOL_ERROR_RE = re.compile(r'❌\s*\*\*Error\*\*:\s*(.+?)(?:\n|$)', re.DOTALL)

    # Status markers that should be stripped from Discord output
    STATUS_MARKERS_RE = re.compile(
        r'🔧\s*\*\*(?:Executing tools\.{3}|Tool execution complete\.\s*Continuing\.{3})\*\*\s*',
        re.DOTALL
    )
    # Markdown image links the LLM sometimes emits: ![alt](file:///path)
    MD_IMAGE_RE = re.compile(r'!\[[^\]]*\]\([^)]+\)\s*')

    @classmethod
    def parse_tool_calls(cls, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract tool call blocks from streamed text.

        Returns:
            (cleaned_text, list_of_tool_events)
            Each tool event dict has keys: type ('start'|'success'|'error'),
            tool_name (if start), raw (original match), data (parsed payload).
        """
        events: List[Dict[str, Any]] = []
        cleaned = text

        # Tool call starts
        for m in cls.TOOL_START_RE.finditer(text):
            tool_name = m.group(1)
            raw_args = m.group(2).strip()
            events.append({
                'type': 'start',
                'tool_name': tool_name,
                'raw': m.group(0),
                'data': raw_args,
            })
            cleaned = cleaned.replace(m.group(0), '')

        # Tool successes
        for m in cls.TOOL_SUCCESS_RE.finditer(text):
            raw_data = m.group(1).strip()
            parsed = None
            try:
                parsed = json.loads(raw_data)
            except (json.JSONDecodeError, ValueError):
                parsed = raw_data
            events.append({
                'type': 'success',
                'raw': m.group(0),
                'data': parsed,
            })
            cleaned = cleaned.replace(m.group(0), '')

        # Tool errors
        for m in cls.TOOL_ERROR_RE.finditer(text):
            events.append({
                'type': 'error',
                'raw': m.group(0),
                'data': m.group(1).strip(),
            })
            cleaned = cleaned.replace(m.group(0), '')

        # Strip status markers ("Executing tools...", "Tool execution complete. Continuing...")
        cleaned = cls.STATUS_MARKERS_RE.sub('', cleaned)
        # Strip markdown image links (already sent as embeds)
        cleaned = cls.MD_IMAGE_RE.sub('', cleaned)
        # Collapse excessive whitespace / blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        return cleaned.strip(), events

    @classmethod
    def build_image_embed(
        cls,
        tool_args: str,
        result_data: dict,
        author_name: str = 'icotes',
    ) -> Tuple[Optional[discord.Embed], Optional[discord.File]]:
        """
        Build a Discord embed + optional File for an image generation result.

        Args:
            tool_args: Raw argument string from tool call start
            result_data: Parsed JSON dict from tool success
            author_name: Bot display name

        Returns:
            (embed, file) – file may be None if image can't be read from disk
        """
        # Parse prompt from tool args (Python dict repr or JSON)
        prompt = ''
        try:
            # Try JSON first
            args_dict = json.loads(tool_args)
            prompt = args_dict.get('prompt', str(tool_args))
        except (json.JSONDecodeError, ValueError):
            # Fallback: try Python literal
            try:
                import ast
                args_dict = ast.literal_eval(tool_args)
                prompt = args_dict.get('prompt', str(tool_args))
            except Exception:
                prompt = tool_args

        # Resolve image path
        abs_path = None
        image_ref = result_data.get('imageReference', {}) if isinstance(result_data, dict) else {}
        if isinstance(image_ref, dict):
            abs_path = image_ref.get('absolute_path')
        if not abs_path and isinstance(result_data, dict):
            abs_path = result_data.get('absolutePath')

        # Build embed
        model = result_data.get('model', 'AI') if isinstance(result_data, dict) else 'AI'
        size = result_data.get('size', '') if isinstance(result_data, dict) else ''
        mode = result_data.get('mode', 'generate') if isinstance(result_data, dict) else 'generate'

        embed = discord.Embed(
            title='🎨 Image Generation',
            color=discord.Color.green(),
        )
        embed.add_field(name='Prompt', value=prompt[:1024], inline=False)
        if size:
            embed.add_field(name='Size', value=size, inline=True)
        if model:
            embed.add_field(name='Model', value=model, inline=True)
        if mode and mode != 'generate':
            embed.add_field(name='Mode', value=mode, inline=True)

        embed.set_footer(text=f'Generated by {author_name}')

        # Attach image file if available on disk
        file = None
        if abs_path:
            # Strip file:// prefix if present
            clean_path = abs_path
            if clean_path.startswith('file://'):
                clean_path = clean_path[len('file://'):]
            p = Path(clean_path)
            if p.is_file():
                filename = p.name
                file = discord.File(str(p), filename=filename)
                embed.set_image(url=f'attachment://{filename}')
            else:
                logger.warning(f"Image file not found on disk: {clean_path}")

        return embed, file

    @classmethod
    def build_video_embed(
        cls,
        tool_args: str,
        result_data: dict,
        author_name: str = 'icotes',
    ) -> Tuple[Optional[discord.Embed], Optional[discord.File]]:
        """
        Build a Discord embed + optional File for an image_to_video result.
        """
        # Parse prompt from tool args
        prompt = ''
        try:
            args_dict = json.loads(tool_args)
            prompt = args_dict.get('prompt', str(tool_args))
        except (json.JSONDecodeError, ValueError):
            try:
                import ast
                args_dict = ast.literal_eval(tool_args)
                prompt = args_dict.get('prompt', str(tool_args))
            except Exception:
                prompt = tool_args

        # Resolve video path
        abs_path = None
        if isinstance(result_data, dict):
            abs_path = result_data.get('absolute_path') or result_data.get('absolutePath')
        
        model = result_data.get('model', 'AI') if isinstance(result_data, dict) else 'AI'
        duration = ''
        try:
            args_dict = json.loads(tool_args) if isinstance(tool_args, str) else {}
            duration = str(args_dict.get('duration', ''))
        except Exception:
            pass

        embed = discord.Embed(
            title='🎬 Video Generation',
            color=discord.Color.blue(),
        )
        embed.add_field(name='Prompt', value=prompt[:1024], inline=False)
        if model:
            embed.add_field(name='Model', value=model, inline=True)
        if duration:
            embed.add_field(name='Duration', value=f'{duration}s', inline=True)
        embed.set_footer(text=f'Generated by {author_name}')

        # Attach video file if available on disk
        file = None
        if abs_path:
            clean_path = abs_path
            if clean_path.startswith('file://'):
                clean_path = clean_path[len('file://'):]
            p = Path(clean_path)
            if p.is_file():
                filename = p.name
                # Discord has 25MB file limit for non-Nitro servers
                file_size_mb = p.stat().st_size / (1024 * 1024)
                if file_size_mb <= 25:
                    file = discord.File(str(p), filename=filename)
                else:
                    embed.add_field(
                        name='⚠️ File too large',
                        value=f'Video is {file_size_mb:.1f}MB (Discord limit: 25MB)',
                        inline=False,
                    )
                    logger.warning(f"Video file too large for Discord: {file_size_mb:.1f}MB")
            else:
                logger.warning(f"Video file not found on disk: {clean_path}")

        return embed, file

    @classmethod
    def build_tool_result_embed(
        cls,
        tool_name: str,
        args_raw: str,
        result_data: Any,
        success: bool = True,
    ) -> discord.Embed:
        """
        Build a generic Discord embed for a non-image tool result.
        """
        color = discord.Color.green() if success else discord.Color.red()
        status = '✅ Success' if success else '❌ Error'

        embed = discord.Embed(
            title=f'🔧 {tool_name}',
            color=color,
        )

        # Truncate args for display
        args_display = str(args_raw)[:256]
        embed.add_field(name='Arguments', value=f'```\n{args_display}\n```', inline=False)

        # Format result
        if isinstance(result_data, dict):
            result_str = json.dumps(result_data, indent=2, ensure_ascii=False)
        else:
            result_str = str(result_data)
        if len(result_str) > 1024:
            result_str = result_str[:1020] + '...'
        embed.add_field(name=status, value=f'```\n{result_str}\n```', inline=False)

        return embed


class DiscordBotService:
    """
    Discord bot service that integrates with the ICUI chat service
    
    Routes Discord messages through the same AI agent pipeline as the web chat,
    providing a consistent experience across platforms.
    """
    
    def __init__(self, token: str):
        """
        Initialize Discord bot service
        
        Args:
            token: Discord bot token from environment
        """
        self.token = token
        self.chat_service = None
        self.bot_task: Optional[asyncio.Task] = None
        
        # Configure Discord bot intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.messages = True
        intents.guilds = True
        # Do not require privileged members intent; mention handling uses raw_mentions.
        
        # Create bot instance with command prefix
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # Track Discord user sessions (user_id -> chat_session_id)
        self.user_sessions: Dict[str, str] = {}

        # Track per-Discord websocket response state
        self._discord_messages: Dict[str, discord.Message] = {}
        self._discord_response_chunks: Dict[str, list[str]] = {}

        # Gate: set when bot is fully connected and self.bot.user is available
        self._ready = asyncio.Event()
        
        # Setup bot events
        self._setup_events()
        
        logger.info("Discord bot service initialized")
    
    def _setup_events(self):
        """Setup Discord bot event handlers"""
        
        @self.bot.event
        async def on_ready():
            """Called when bot is ready and connected to Discord"""
            logger.info(f'Discord bot logged in as {self.bot.user.name} (ID: {self.bot.user.id})')
            logger.info(f'Connected to {len(self.bot.guilds)} guilds')
            
            # Set bot status
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name="your messages | AI Assistant"
                )
            )
            # Signal that the bot is ready to handle messages
            self._ready.set()
        
        @self.bot.event
        async def on_message(message: discord.Message):
            """Called when a message is received"""
            # Wait until bot is fully ready (self.bot.user is populated)
            # Use a short timeout so we don't hang forever on broken startup
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=30)
            except asyncio.TimeoutError:
                logger.error("Discord bot did not become ready within 30s, ignoring message")
                return

            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Ignore messages that start with command prefix (for future commands)
            if message.content.startswith('!'):
                await self.bot.process_commands(message)
                return
            
            is_dm = isinstance(message.channel, discord.DMChannel)
            
            # Check for mentions: raw_mentions works reliably in guild channels
            # without requiring privileged members intent.
            is_mentioned = (
                self.bot.user.id in getattr(message, 'raw_mentions', [])
                or self.bot.user in message.mentions
                or f'<@{self.bot.user.id}>' in message.content
                or f'<@!{self.bot.user.id}>' in message.content
            )
            
            # Only respond to DMs or mentions
            if not is_dm and not is_mentioned:
                return
            
            logger.info(
                f"Discord message received: author={message.author.name}, "
                f"channel={'DM' if is_dm else getattr(message.channel, 'name', '?')}, "
                f"mentioned={is_mentioned}, content={message.content[:80]}"
            )
            
            try:
                await self._handle_discord_message(message)
            except Exception as e:
                logger.error(f"Error handling Discord message: {e}", exc_info=True)
                try:
                    await message.reply(f"Sorry, I encountered an error: {str(e)}")
                except Exception:
                    await message.channel.send(f"Sorry, I encountered an error: {str(e)}")
        
        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """Called when an error occurs"""
            logger.error(f'Discord bot error in {event}', exc_info=True)

    def _get_default_agent_type(self) -> Optional[str]:
        """Resolve default agent type from agents.json settings (if configured)."""
        try:
            from .agent_config_service import get_agent_config_service
            config_service = get_agent_config_service()
            settings = config_service.get_menu_settings()
            return settings.default_agent or None
        except Exception as e:
            logger.debug(f"Failed to resolve default agent from agents.json: {e}")
            return None
    
    async def _handle_discord_message(self, message: discord.Message):
        """
        Handle incoming Discord message and route through chat service
        
        Args:
            message: Discord message object
        """
        if not self.chat_service:
            await message.channel.send("⚠️ Chat service not initialized. Please try again later.")
            return
        
        # Get or create session for this Discord user
        user_id = str(message.author.id)
        session_id = self.user_sessions.get(user_id)
        
        if not session_id:
            # Create new session for this user
            try:
                # create_session returns session_id string directly, not a dict
                session_id = await self.chat_service.create_session(f"Discord: {message.author.name}")
                self.user_sessions[user_id] = session_id
                logger.info(f"Created new chat session {session_id} for Discord user {user_id} ({message.author.name})")
            except Exception as e:
                logger.error(f"Failed to create session for Discord user {user_id}: {e}", exc_info=True)
                await message.channel.send("⚠️ Failed to create chat session. Please try again.")
                return
        
        # Extract message content (remove bot mention in all formats)
        content = message.content
        # Strip <@ID> and <@!ID> mention formats
        content = content.replace(f'<@{self.bot.user.id}>', '').replace(f'<@!{self.bot.user.id}>', '').strip()
        
        if not content:
            await message.reply("Please provide a message for me to respond to.")
            return
        
        # Track whether this is a channel message (for reply threading)
        is_channel = not isinstance(message.channel, discord.DMChannel)
        
        # Show typing indicator while processing
        async with message.channel.typing():
            try:
                # Create a temporary websocket ID for Discord messages
                discord_ws_id = f"discord_{user_id}_{message.id}"
                
                logger.info(f"Processing Discord message from {message.author.name} (session: {session_id}, channel={'guild' if is_channel else 'DM'})")
                
                # Connect this Discord session to chat service
                await self.chat_service.connect_websocket(discord_ws_id)
                
                # Process message through chat service
                # Note: We'll collect the response via a custom callback
                self._discord_messages[discord_ws_id] = message
                self._discord_response_chunks[discord_ws_id] = []
                
                logger.debug(f"Sending message to chat service: {content[:50]}...")

                # Set platform context so agent knows this request came from Discord
                from icpy.agent.helpers import set_platform_context
                platform_context = {
                    'channel': 'discord',
                    'bot_name': self.bot.user.name if self.bot and self.bot.user else 'icotes',
                    'is_dm': isinstance(message.channel, discord.DMChannel),
                    'channel_name': None if isinstance(message.channel, discord.DMChannel) else getattr(message.channel, 'name', None),
                    'guild_name': getattr(getattr(message, 'guild', None), 'name', None),
                    'sender_name': message.author.name,
                    'sender_id': str(message.author.id),
                }
                set_platform_context(platform_context)
                
                # Send message to chat service with default agent
                metadata = {
                    'session_id': session_id,
                    'platformContext': platform_context,
                }
                default_agent = self._get_default_agent_type()
                if default_agent:
                    # Use default agent configured in .icotes/agents.json
                    metadata['agentType'] = default_agent

                await self.chat_service.handle_user_message(
                    websocket_id=discord_ws_id,
                    content=content,
                    metadata=metadata
                )
                
                # Wait a bit for the response to be processed
                # The actual response will be sent via the websocket message callback
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing Discord message through chat service: {e}", exc_info=True)
                await message.channel.send(f"⚠️ Error processing message: {str(e)}")
    
    async def initialize(self):
        """Initialize the Discord bot service"""
        try:
            # Import and get chat service
            from .chat_service import get_chat_service
            self.chat_service = get_chat_service()
            
            # Override the websocket message sending to capture responses for Discord
            self._original_send_websocket_message = self.chat_service._send_websocket_message
            self.chat_service._send_websocket_message = self._intercept_websocket_message
            
            logger.info("Discord bot service initialized and connected to chat service")
            
        except Exception as e:
            logger.error(f"Failed to initialize Discord bot service: {e}", exc_info=True)
            raise
    
    async def _intercept_websocket_message(self, websocket_id: str, message_data: dict):
        """
        Intercept websocket messages to send AI responses to Discord.

        Collects streaming chunks, then parses tool call output and formats
        it using Discord embeds (images attached as files, other tools as
        rich embeds) before sending.
        """
        # Check if this is a Discord websocket
        if websocket_id.startswith('discord_'):
            parts = websocket_id.split('_')
            if len(parts) >= 2:
                message_type = message_data.get('type', '')

                if message_type == 'message_stream':
                    # Streaming chunk - collect it
                    if message_data.get('stream_chunk'):
                        content = message_data.get('chunk', '')
                        if content and websocket_id in self._discord_response_chunks:
                            self._discord_response_chunks[websocket_id].append(content)

                    # Stream end - format and send the full response
                    if message_data.get('stream_end'):
                        full_response = ''.join(self._discord_response_chunks.get(websocket_id, []))
                        discord_message = self._discord_messages.get(websocket_id)
                        if discord_message and full_response:
                            await self._send_formatted_response(discord_message, full_response)

                        # Clean up
                        self._discord_response_chunks.pop(websocket_id, None)
                        self._discord_messages.pop(websocket_id, None)

                elif message_type == 'message':
                    # Non-streaming message
                    content = message_data.get('content', '')
                    discord_message = self._discord_messages.get(websocket_id)
                    if discord_message and content:
                        await self._send_formatted_response(discord_message, content)
                        self._discord_response_chunks.pop(websocket_id, None)
                        self._discord_messages.pop(websocket_id, None)

                elif message_type == 'error':
                    error_msg = message_data.get('message', 'An error occurred')
                    discord_message = self._discord_messages.get(websocket_id)
                    if discord_message:
                        await discord_message.channel.send(f"⚠️ {error_msg}")
                        self._discord_response_chunks.pop(websocket_id, None)
                        self._discord_messages.pop(websocket_id, None)

        # Only call original method for non-Discord websocket IDs
        if not websocket_id.startswith('discord_') and hasattr(self, '_original_send_websocket_message'):
            await self._original_send_websocket_message(websocket_id, message_data)

    async def _send_formatted_response(self, discord_message: discord.Message, full_response: str):
        """
        Parse the full AI response, extract tool calls, and send formatted
        Discord messages with embeds for images and other tool results.
        In channels, uses reply() for the first message to thread the response.
        """
        channel = discord_message.channel
        is_channel = not isinstance(channel, discord.DMChannel)
        first_sent = False  # Track if we've sent the first message (for reply threading)
        fmt = DiscordMessageFormatter

        # Parse out tool call blocks
        cleaned_text, events = fmt.parse_tool_calls(full_response)

        # Pair tool starts with their results
        # Events come in order: start, success/error, start, success/error, …
        pending_tool_name: Optional[str] = None
        pending_tool_args: Optional[str] = None

        for ev in events:
            if ev['type'] == 'start':
                pending_tool_name = ev.get('tool_name', 'tool')
                pending_tool_args = ev.get('data', '')

            elif ev['type'] == 'success':
                result_data = ev['data']

                if pending_tool_name == 'generate_image' and isinstance(result_data, dict):
                    embed, file = fmt.build_image_embed(
                        tool_args=pending_tool_args or '',
                        result_data=result_data,
                        author_name=self.bot.user.name if self.bot.user else 'icotes',
                    )
                    try:
                        send_kwargs = {'embed': embed}
                        if file:
                            send_kwargs['file'] = file
                        if is_channel and not first_sent:
                            await discord_message.reply(**send_kwargs)
                            first_sent = True
                        else:
                            await channel.send(**send_kwargs)
                    except Exception as e:
                        logger.error(f"Failed to send image embed to Discord: {e}")
                        await channel.send("🎨 Image was generated but could not be sent to Discord.")

                elif pending_tool_name == 'image_to_video' and isinstance(result_data, dict):
                    embed, file = fmt.build_video_embed(
                        tool_args=pending_tool_args or '',
                        result_data=result_data,
                        author_name=self.bot.user.name if self.bot.user else 'icotes',
                    )
                    try:
                        send_kwargs = {'embed': embed}
                        if file:
                            send_kwargs['file'] = file
                        if is_channel and not first_sent:
                            await discord_message.reply(**send_kwargs)
                            first_sent = True
                        else:
                            await channel.send(**send_kwargs)
                    except Exception as e:
                        logger.error(f"Failed to send video embed to Discord: {e}")
                        await channel.send("🎬 Video was generated but could not be sent to Discord.")
                else:
                    embed = fmt.build_tool_result_embed(
                        tool_name=pending_tool_name or 'tool',
                        args_raw=pending_tool_args or '',
                        result_data=result_data,
                        success=True,
                    )
                    try:
                        if is_channel and not first_sent:
                            await discord_message.reply(embed=embed)
                            first_sent = True
                        else:
                            await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Failed to send tool embed to Discord: {e}")

                pending_tool_name = None
                pending_tool_args = None

            elif ev['type'] == 'error':
                embed = fmt.build_tool_result_embed(
                    tool_name=pending_tool_name or 'tool',
                    args_raw=pending_tool_args or '',
                    result_data=ev['data'],
                    success=False,
                )
                try:
                    if is_channel and not first_sent:
                        await discord_message.reply(embed=embed)
                        first_sent = True
                    else:
                        await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send error embed to Discord: {e}")

                pending_tool_name = None
                pending_tool_args = None

        # Send remaining cleaned text (the LLM's natural language response)
        if cleaned_text:
            # Discord 2000 char limit
            if len(cleaned_text) > 2000:
                chunks = [cleaned_text[i:i + 1900] for i in range(0, len(cleaned_text), 1900)]
                for i, chunk in enumerate(chunks):
                    try:
                        if is_channel and not first_sent and i == 0:
                            await discord_message.reply(chunk)
                            first_sent = True
                        else:
                            await channel.send(chunk)
                    except Exception:
                        # Fallback if reply/send fails due channel permissions/threading
                        await channel.send(chunk)
            else:
                try:
                    if is_channel and not first_sent:
                        await discord_message.reply(cleaned_text)
                        first_sent = True
                    else:
                        await channel.send(cleaned_text)
                except Exception:
                    await channel.send(cleaned_text)
    
    async def start(self):
        """Start the Discord bot"""
        if self.bot_task and not self.bot_task.done():
            logger.warning("Discord bot is already running")
            return
        
        logger.info("Starting Discord bot...")
        
        # Run bot in background task
        self.bot_task = asyncio.create_task(self._run_bot())
        
        logger.info("Discord bot started")
    
    async def _run_bot(self):
        """Run the Discord bot (internal method)"""
        try:
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Discord bot error: {e}", exc_info=True)
    
    async def stop(self):
        """Stop the Discord bot"""
        logger.info("Stopping Discord bot...")
        
        if self.bot_task and not self.bot_task.done():
            # Close bot connection
            await self.bot.close()
            
            # Cancel task
            self.bot_task.cancel()
            try:
                await self.bot_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Discord bot stopped")
    
    def is_running(self) -> bool:
        """Check if the Discord bot is running"""
        return self.bot_task is not None and not self.bot_task.done()


async def get_discord_bot_service() -> Optional[DiscordBotService]:
    """Get the global Discord bot service instance"""
    global _discord_bot_service
    
    if _discord_bot_service is None:
        # Check if Discord token is configured
        token = os.getenv('DISCORD_BOT_TOKEN')
        
        if not token:
            logger.warning("DISCORD_BOT_TOKEN not configured, Discord bot service disabled")
            return None
        
        # Create and initialize service
        _discord_bot_service = DiscordBotService(token)
        await _discord_bot_service.initialize()
    
    return _discord_bot_service


async def start_discord_bot():
    """Start the Discord bot service"""
    service = await get_discord_bot_service()
    if service:
        await service.start()
        logger.info("Discord bot service started")
    else:
        logger.warning("Discord bot service not available (token not configured)")


async def stop_discord_bot():
    """Stop the Discord bot service"""
    global _discord_bot_service
    
    if _discord_bot_service:
        await _discord_bot_service.stop()
        _discord_bot_service = None
        logger.info("Discord bot service stopped")
