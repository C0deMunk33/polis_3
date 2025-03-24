import asyncio
from typing import List, Dict, Any, Optional
import os
import logging
import time
from dotenv import load_dotenv
from datetime import datetime
# Pycord imports instead of discord.py
import discord
from discord.commands import SlashCommandGroup, Option

from libs.agent_interface import AgentInterface
from libs.common import ToolCall, ToolCallResult, ToolSchema, ToolsetDetails, get_tool_schemas_from_class
from libs.agent import AgentStateDBO

logger = logging.getLogger(__name__)

class DiscordManagerInterface(AgentInterface):
    def __init__(self, init_keys: Optional[Dict[str, str]] = None):
        self.app_id = None
        self.public_key = None
        self.token = None
        self.client = None
        
        self.is_running = False
        self.event_loop = None

        if init_keys is not None:
            if "app_id" in init_keys:
                self.app_id = init_keys["app_id"]
            if "public_key" in init_keys:
                self.public_key = init_keys["public_key"]
            if "token" in init_keys:
                self.token = init_keys["token"]

        self.toolset_name = "discord_manager"
        self.all_tools = get_tool_schemas_from_class(self)

    def send_message(self, agent_state: AgentStateDBO, channel_id: str, content: str, reply_to_message_id: Optional[str] = None) -> ToolCallResult:
        """{
            "toolset_id": "discord_manager",
            "name": "send_message",
            "description": "Send a message to a Discord channel",
            "is_long_running": false,
            "expose_to_agent": true,
            "arguments": [
                {"name": "channel_id", "type": "str", "description": "The ID of the Discord channel to send the message to (required)"},
                {"name": "content", "type": "str", "description": "The content of the message to send (required)"},
                {"name": "reply_to_message_id", "type": "str", "description": "The ID of the message to reply to (optional)"}
            ]
        }"""
        if not self.is_running or not self.client:
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="send_message",
                    arguments={"channel_id": channel_id, "content": content, "reply_to_message_id": reply_to_message_id}
                ),
                error="Discord bot is not running. Start it first with start_discord_bot."
            )
        
        try:
            # Create a future to get the result from the async function
            future = asyncio.run_coroutine_threadsafe(
                self._async_send_message(channel_id, content, reply_to_message_id), 
                self.event_loop
            )
            # Wait for the result with a timeout
            result = future.result(timeout=10)
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="send_message",
                    arguments={"channel_id": channel_id, "content": content, "reply_to_message_id": reply_to_message_id}
                ),
                result=result
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="send_message",
                    arguments={"channel_id": channel_id, "content": content, "reply_to_message_id": reply_to_message_id}
                ),
                error=f"Error sending message: {str(e)}"
            )
    def get_channels(self, agent_state: AgentStateDBO) -> ToolCallResult:
        """{
            "toolset_id": "discord_manager",
            "name": "get_channels",
            "description": "Get all channels in the Discord server",
            "is_long_running": false,
            "expose_to_agent": true,
            "arguments": []
        }"""
        if not self.is_running or not self.client:
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="get_channels",
                    arguments={}
                ),
                error="Discord bot is not running. Start it first with start_discord_bot."
            )
        
        try:
            # Create a future to get the result from the async function
            future = asyncio.run_coroutine_threadsafe(
                self._async_get_channels(), 
                self.event_loop
            )
            # Wait for the result with a timeout
            result = future.result(timeout=10)
            result_str = "Discord Channels:\n"
            for channel in result:
                if channel['type'] == 'text':
                    result_str += f"    - {channel['name']} ({channel['id']})\n"
            print("~"*100)
            print(result_str)
            print("~"*100)
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="get_channels",
                    arguments={}
                ),
                result=result_str
            )
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="get_channels",
                    arguments={}
                ),
                error=f"Error getting channels: {str(e)}"
            )

    def read_discord_messages(self, agent_state: AgentStateDBO, channel_id: str, limit: int = 15, offset: int = 0) -> ToolCallResult:
        """{
            "toolset_id": "discord_manager",
            "name": "read_discord_messages",
            "description": "Read messages from a Discord channel",
            "is_long_running": false,
            "expose_to_agent": true,
            "arguments": [
                {"name": "channel_id", "type": "str", "description": "The ID of the Discord channel to read messages from (required)"},
                {"name": "limit", "type": "int", "description": "The number of messages to read (optional, default is 15)"},
                {"name": "offset", "type": "int", "description": "The number of messages to offset by (optional, default is 0)"}
            ]
        }"""
        if not self.is_running or not self.client:
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="read_discord_messages",
                    arguments={"channel_id": channel_id, "limit": limit, "offset": offset}
                ),
                error="Discord bot is not running. Start it first with start_discord_bot."
            )
        
        try:
            # Create a future to get the result from the async function
            future = asyncio.run_coroutine_threadsafe(
                self._async_read_discord_messages(channel_id, limit, offset), 
                self.event_loop
            )
            # Wait for the result with a timeout
            result = future.result(timeout=10)

            result_str = "Discord Messages (channel: " + channel_id + "):\n"
            for message in result:
                # Get the created_at time from the message
                created_at = message['created_at']
                
                # Calculate time difference
                if isinstance(created_at, datetime):
                    # If it's already a datetime object, use it directly
                    message_time = created_at
                    # Ensure the datetime is timezone-aware if needed
                    if message_time.tzinfo is None:
                        # If it's naive, assume it's in UTC
                        from datetime import timezone
                        message_time = message_time.replace(tzinfo=timezone.utc)
                        
                    # Get current time with the same timezone awareness
                    now = datetime.now(message_time.tzinfo)
                    time_ago = now - message_time
                else:
                    # Fallback for string representation (should not happen with the fix above)
                    try:
                        message_time = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                        now = datetime.now(message_time.tzinfo)
                        time_ago = now - message_time
                    except (ValueError, TypeError):
                        # If parsing fails, use a placeholder
                        time_ago_str = "unknown time ago"
                        logger.warning(f"Could not parse datetime: {created_at}")
                
                # Format the time ago string
                if 'time_ago_str' not in locals():
                    if time_ago.total_seconds() < 60:
                        time_ago_str = f"{max(0, int(time_ago.total_seconds()))} seconds ago"
                    elif time_ago.total_seconds() < 3600:
                        time_ago_str = f"{max(0, int(time_ago.total_seconds() // 60))} minutes ago"
                    else:
                        time_ago_str = f"{max(0, int(time_ago.total_seconds() // 3600))} hours ago"
                
                result_str += f"    - {message['author']} ({time_ago_str}): {message['content']}\n"
                # Reset time_ago_str for next iteration
                if 'time_ago_str' in locals():
                    del time_ago_str

            print("~"*100)
            print(result_str)
            print("~"*100)
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="read_discord_messages",
                    arguments={"channel_id": channel_id, "limit": limit, "offset": offset}
                ),
                result=result_str
            )
        except Exception as e:
            logger.error(f"Error reading discord messages: {e}")
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="read_discord_messages",
                    arguments={"channel_id": channel_id, "limit": limit, "offset": offset}
                ),
                error=f"Error reading discord messages: {str(e)}"
            )
        
    async def _async_get_channels(self) -> str:
        if not self.client or not self.client.guilds:
            return "No guilds available or client not connected"
        
        channels = []
        for guild in self.client.guilds:
            for channel in guild.channels:
                channels.append({
                    "id": channel.id,
                    "name": channel.name,
                    "type": str(channel.type)
                })
        return channels

    async def _async_send_message(self, channel_id: str, content: str, reply_to_message_id: Optional[str] = None) -> str:
        channel = await self.client.fetch_channel(int(channel_id))
        
        if reply_to_message_id:
            try:
                reply_message = await channel.fetch_message(int(reply_to_message_id))
                message = await channel.send(content, reference=reply_message)
            except Exception as e:
                logger.error(f"Error fetching message to reply to: {e}")
                message = await channel.send(content)
        else:
            message = await channel.send(content)
            
        return f"Message sent with ID: {message.id}"

    async def _async_read_discord_messages(self, channel_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        channel = await self.client.fetch_channel(int(channel_id))
        
        messages = []
        async for message in channel.history(limit=limit):
            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "created_at": message.created_at,  # Store the actual datetime object instead of string
                "attachments": [{"url": a.url, "filename": a.filename} for a in message.attachments]
            })
        
        # Apply offset if needed
        if offset > 0:
            messages = messages[offset:]
        
        return messages

    def start_discord_bot(self, agent_state: AgentStateDBO) -> ToolCallResult:
        """{
            "toolset_id": "discord_manager",
            "name": "start_discord_bot",
            "description": "Start the Discord bot",
            "is_long_running": false,
            "expose_to_agent": false,
            "arguments": []
        }"""
        if self.is_running:
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="start_discord_bot",
                    arguments={}
                ),
                result="Discord bot running."
            )
        
        try:
            # Create a new event loop in a separate thread
            self.event_loop = asyncio.new_event_loop()
            
            # Create the Discord client - using Pycord Bot instead of Client
            intents = discord.Intents.default()
            intents.message_content = True  # This requires privileged intent in Discord Developer Portal
            self.client = discord.Bot(intents=intents)
            
            # Set up event handlers
            @self.client.event
            async def on_ready():
                logger.info(f"Logged in as {self.client.user}")
                # Set is_running to True when the bot is ready
                self.is_running = True
            
            @self.client.event
            async def on_message(message):
                if message.author == self.client.user:
                    return
                
                # Pass the message to the agent
                if agent_state and hasattr(agent_state, "on_discord_message"):
                    await agent_state.on_discord_message(message)
            
            # Start the bot in a separate thread
            def run_bot():
                asyncio.set_event_loop(self.event_loop)
                try:
                    self.event_loop.run_until_complete(self.client.start(self.token))
                except discord.errors.PrivilegedIntentsRequired:
                    logger.error("Privileged intents are required but not enabled in the Discord Developer Portal.")
                    logger.error("Please go to https://discord.com/developers/applications/ and enable the 'Message Content Intent' for your bot.")
                    self.is_running = False
                except Exception as e:
                    logger.error(f"Error in Discord bot thread: {e}")
                    self.is_running = False
            
            import threading
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            
            # Give the bot a moment to connect before returning
            time.sleep(2)
            
            # Remove this check and set is_running to True temporarily
            # We'll let the on_ready event set it permanently when the bot is actually ready
            self.is_running = True
            
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="start_discord_bot",
                    arguments={}
                ),
                result="Discord bot starting up. It will be fully operational when the on_ready event fires."
            )
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="start_discord_bot",
                    arguments={}
                ),
                error=f"Error starting Discord bot: {str(e)}"
            )

    def stop_discord_bot(self, agent_state: AgentStateDBO) -> ToolCallResult:
        """{
            "toolset_id": "discord_manager",
            "name": "stop_discord_bot",
            "description": "Stop the Discord bot",
            "is_long_running": false,
            "expose_to_agent": false,
            "arguments": []
        }"""
        if not self.is_running:
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="stop_discord_bot",
                    arguments={}
                ),
                result="Discord bot is not running."
            )
        
        try:
            if not self.event_loop or not self.client:
                self.is_running = False
                return ToolCallResult(
                    toolset_id=self.toolset_name,
                    tool_call=ToolCall(
                        toolset_id=self.toolset_name,
                        name="stop_discord_bot",
                        arguments={}
                    ),
                    result="Discord bot was not properly initialized."
                )
            
            # Create a future to close the client
            future = asyncio.run_coroutine_threadsafe(
                self.client.close(), 
                self.event_loop
            )
            
            try:
                # Wait for the result with a timeout
                future.result(timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Timeout while closing Discord client, forcing shutdown")
            except Exception as e:
                logger.warning(f"Error while closing Discord client: {e}")
            
            # Clean up regardless of errors
            self.is_running = False
            self.client = None
            
            # Give event loop a chance to clean up
            time.sleep(1)
            
            # Close the event loop
            if self.event_loop and self.event_loop.is_running():
                self.event_loop.stop()
            
            self.event_loop = None
            
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="stop_discord_bot",
                    arguments={}
                ),
                result="Discord bot stopped successfully."
            )
        except Exception as e:
            logger.error(f"Error stopping Discord bot: {e}")
            self.is_running = False  # Mark as stopped even if there was an error
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="stop_discord_bot",
                    arguments={}
                ),
                error=f"Error stopping Discord bot: {str(e)}"
            )

    # Example method to add a slash command (Pycord-specific)
    def add_slash_command(self, agent_state: AgentStateDBO, command_name: str, description: str, options: List[Dict[str, Any]] = None) -> ToolCallResult:
        """{
            "toolset_id": "discord_manager",
            "name": "add_slash_command",
            "description": "Add a slash command to the Discord bot",
            "is_long_running": false,
            "expose_to_agent": false,
            "arguments": [
                {"name": "command_name", "type": "str", "description": "The name of the command (required)"},
                {"name": "description", "type": "str", "description": "The description of the command (required)"},
                {"name": "options", "type": "list", "description": "List of command options (optional)"}
            ]
        }"""
        if not self.is_running or not self.client:
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="add_slash_command",
                    arguments={"command_name": command_name, "description": description, "options": options}
                ),
                result="Discord bot is not running. Start it first with start_discord_bot."
            )
        
        try:
            # Create a future to get the result from the async function
            future = asyncio.run_coroutine_threadsafe(
                self._async_add_slash_command(command_name, description, options, agent_state), 
                self.event_loop
            )
            # Wait for the result with a timeout
            result = future.result(timeout=10)
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="add_slash_command",
                    arguments={"command_name": command_name, "description": description, "options": options}
                ),
                result=f"Slash command added successfully: {result}"
            )
        except Exception as e:
            logger.error(f"Error adding slash command: {e}")
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=ToolCall(
                    toolset_id=self.toolset_name,
                    name="add_slash_command",
                    arguments={"command_name": command_name, "description": description, "options": options}
                ),
                error=f"Error adding slash command: {str(e)}"
            )
    
    async def _async_add_slash_command(self, command_name: str, description: str, options: List[Dict[str, Any]], agent_state) -> str:
        # Define the command callback
        async def command_callback(ctx, **kwargs):
            # Pass to agent for handling
            if agent_state and hasattr(agent_state, "on_slash_command"):
                await agent_state.on_slash_command(ctx, command_name, kwargs)
            else:
                await ctx.respond(f"Command {command_name} received with arguments: {kwargs}")

        # Create command options if provided
        command_options = []
        if options:
            for opt in options:
                command_options.append(
                    Option(
                        name=opt.get("name", "option"),
                        description=opt.get("description", "An option"),
                        type=opt.get("type", 3),  # 3 is STRING type
                        required=opt.get("required", False)
                    )
                )

        # Register the command
        @self.client.command(name=command_name, description=description)
        async def dynamic_command(ctx, *args, **kwargs):
            await command_callback(ctx, *args, **kwargs)

        return f"Command '{command_name}' registered"

    ################# AGENT INTERFACE METHODS #################

    def get_tool_schemas(self) -> List[ToolSchema]:
        return self.all_tools

    def get_toolset_details(self) -> ToolsetDetails:
        return ToolsetDetails(
            toolset_id=self.toolset_name,
            name=self.toolset_name,
            description="Discord toolset"
        )

    def agent_tool_callback(self, agent_state: AgentStateDBO, tool_call: ToolCall) -> ToolCallResult:
        try:
            result = getattr(self, tool_call.name)(agent_state, **tool_call.arguments)
            print("~"*100)
            print(result)
            print("~"*100)
            return result
        except Exception as e:
            logger.error(f"Error in agent_tool_callback: {e}")
            return ToolCallResult(
                toolset_id=self.toolset_name,
                tool_call=tool_call,
                error=f"Error in agent_tool_callback: {str(e)}"
            )