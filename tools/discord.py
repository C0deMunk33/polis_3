import discord
from discord import app_commands
import asyncio
from typing import List, Dict, Any, Optional
import os
import logging
from dotenv import load_dotenv

from libs.agent_interface import AgentInterface
from libs.common import ToolCall, ToolCallResult, ToolSchema, ToolsetDetails

logger = logging.getLogger(__name__)

class DiscordInterface(AgentInterface):
    def __init__(self, app_id: str, public_key: str, token: str):
        self.app_id = app_id
        self.public_key = public_key
        self.token = token
        self.client = None
        self.tree = None
        self.is_running = False
        self.event_loop = None

    def get_toolset_details(self) -> ToolsetDetails:
        return ToolsetDetails(
            title="Discord Bot Interface",
            description="Tools for interacting with Discord as a bot",
            instructions="Use these tools to send messages, respond to commands, and interact with Discord users."
        )

    def _send_message(self, channel_id: str, content: str) -> ToolCallResult:
        if not self.is_running or not self.client:
            return ToolCallResult(
                success=False,
                result="Discord bot is not running. Start it first with start_discord_bot."
            )
        
        try:
            # Create a future to get the result from the async function
            future = asyncio.run_coroutine_threadsafe(
                self._async_send_message(channel_id, content), 
                self.event_loop
            )
            # Wait for the result with a timeout
            result = future.result(timeout=10)
            return ToolCallResult(
                success=True,
                result=f"Message sent successfully: {result}"
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return ToolCallResult(
                success=False,
                result=f"Error sending message: {str(e)}"
            )

    async def _async_send_message(self, channel_id: str, content: str) -> str:
        channel = await self.client.fetch_channel(int(channel_id))
        message = await channel.send(content)
        return f"Message sent with ID: {message.id}"

    def _start_discord_bot(self, agent_state) -> ToolCallResult:
        if self.is_running:
            return ToolCallResult(
                success=False,
                result="Discord bot is already running."
            )
        
        try:
            # Create a new event loop in a separate thread
            self.event_loop = asyncio.new_event_loop()
            
            # Create the Discord client
            intents = discord.Intents.default()
            intents.message_content = True
            self.client = discord.Client(intents=intents)
            self.tree = app_commands.CommandTree(self.client)
            
            # Set up event handlers
            @self.client.event
            async def on_ready():
                logger.info(f"Logged in as {self.client.user}")
                await self.tree.sync()
            
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
                self.event_loop.run_until_complete(self.client.start(self.token))
            
            import threading
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            
            self.is_running = True
            
            return ToolCallResult(
                success=True,
                result=f"Discord bot started successfully. Application ID: {self.app_id}"
            )
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
            return ToolCallResult(
                success=False,
                result=f"Error starting Discord bot: {str(e)}"
            )

    def _stop_discord_bot(self) -> ToolCallResult:
        if not self.is_running:
            return ToolCallResult(
                success=False,
                result="Discord bot is not running."
            )
        
        try:
            # Create a future to close the client
            future = asyncio.run_coroutine_threadsafe(
                self.client.close(), 
                self.event_loop
            )
            # Wait for the result with a timeout
            future.result(timeout=10)
            
            # Clean up
            self.is_running = False
            self.client = None
            self.tree = None
            self.event_loop = None
            
            return ToolCallResult(
                success=True,
                result="Discord bot stopped successfully."
            )
        except Exception as e:
            logger.error(f"Error stopping Discord bot: {e}")
            return ToolCallResult(
                success=False,
                result=f"Error stopping Discord bot: {str(e)}"
            )

    def _register_command(self, name: str, description: str) -> ToolCallResult:
        if not self.is_running or not self.client:
            return ToolCallResult(
                success=False,
                result="Discord bot is not running. Start it first with start_discord_bot."
            )
        
        try:
            # Create a future to register the command
            future = asyncio.run_coroutine_threadsafe(
                self._async_register_command(name, description), 
                self.event_loop
            )
            # Wait for the result with a timeout
            future.result(timeout=10)
            
            return ToolCallResult(
                success=True,
                result=f"Command '{name}' registered successfully."
            )
        except Exception as e:
            logger.error(f"Error registering command: {e}")
            return ToolCallResult(
                success=False,
                result=f"Error registering command: {str(e)}"
            )

    async def _async_register_command(self, name: str, description: str):
        @self.tree.command(name=name, description=description)
        async def dynamic_command(interaction: discord.Interaction):
            # Acknowledge the interaction
            await interaction.response.defer(thinking=True)
            
            # Process the command with the agent
            response = f"Command '{name}' received. This is a default response."
            
            # Send the response
            await interaction.followup.send(response)
        
        # Sync the command tree
        await self.tree.sync()

# Add main function for testing
def main():
    # Load environment variables
    load_dotenv()
    
    # Get Discord configuration from environment variables
    app_id = os.getenv("DISCORD_APP_ID")
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    token = os.getenv("DISCORD_BOT_TOKEN")
    
    if not all([app_id, public_key, token]):
        print("Error: Missing Discord configuration in .env file")
        print("Required variables: DISCORD_APP_ID, DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN")
        return
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create Discord interface
    discord_interface = DiscordInterface(app_id, public_key, token)
    
    # Define a simple agent state for testing
    class TestAgentState:
        async def on_discord_message(self, message):
            print(f"Received message: {message.content}")
            if message.content.startswith('!echo '):
                content = message.content[6:]  # Remove '!echo ' prefix
                channel = message.channel
                await channel.send(f"Echo: {content}")
    
    # Start the Discord bot
    result = discord_interface._start_discord_bot(TestAgentState())
    print(result.result)
    
    # Register a test command
    if result.success:
        cmd_result = discord_interface._register_command("test", "A test command")
        print(cmd_result.result)
    
    try:
        # Keep the main thread running
        print("Bot is running. Press Ctrl+C to exit.")
        while True:
            # Sleep to prevent high CPU usage
            asyncio.run(asyncio.sleep(1))
    except KeyboardInterrupt:
        # Stop the bot when Ctrl+C is pressed
        print("Stopping bot...")
        stop_result = discord_interface._stop_discord_bot()
        print(stop_result.result)

if __name__ == "__main__":
    main()
