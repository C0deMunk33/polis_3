import os
import logging
import asyncio
import time
from dotenv import load_dotenv

# Import the DiscordManagerInterface
from libs.agent_interface import AgentInterface
from libs.agent import AgentStateDBO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Load environment variables
    load_dotenv()
    
    # Get Discord credentials from environment variables
    app_id = os.getenv("DISCORD_APP_ID")
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    token = os.getenv("DISCORD_TOKEN")
    
    if not all([app_id, public_key, token]):
        logger.error("Missing Discord credentials in .env file")
        return
    
    # Import here to avoid circular imports if necessary
    from tools.discord_manager import DiscordManagerInterface
    
    logger.info("Initializing Discord interface...")
    discord_interface = DiscordManagerInterface(
        init_keys={
            "app_id": app_id,
            "public_key": public_key,
            "token": token
        }
    )
    
    # Create a mock agent state (since it's required by the methods)
    agent_state = AgentStateDBO()
    
    # Start the Discord bot
    logger.info("Starting Discord bot...")
    result = discord_interface.start_discord_bot(agent_state)
    
    if result.error:
        logger.error(f"Failed to start Discord bot: {result.error}")
        return
    
    logger.info(f"Start result: {result.result}")
    
    # Wait for the bot to connect
    logger.info("Waiting for bot to connect...")
    await asyncio.sleep(5)
    
    try:
        # Only proceed with tests if the bot is running
        if discord_interface.is_running:
            # Get channels
            logger.info("Getting channels...")
            channels_result = discord_interface.get_channels(agent_state)
            
            if channels_result.error:
                logger.error(f"Failed to get channels: {channels_result.error}")
                return
            
            logger.info(f"Channels result: {channels_result.result}")
                
                # read the messages in the channel
            logger.info("Reading messages in the channel...")
           
            channel_id = 1067898719267201118  # Get the first text channel
            messages_result = discord_interface.read_discord_messages(agent_state, channel_id=channel_id)
            logger.info(f"Messages result: {messages_result.result}")
            
            logger.info(f"Sending test message to text channel ID: {channel_id}")
            message_result = discord_interface.send_message(
                agent_state,
                channel_id=channel_id,
                content="This is a test message from the Discord bot!"
            )
            logger.info(f"Message result: {message_result.result}")
    
            
    finally:
        # Stop the Discord bot
        logger.info("Stopping Discord bot...")
        stop_result = discord_interface.stop_discord_bot(agent_state)
        
        if stop_result.error:
            logger.error(f"Failed to stop Discord bot: {stop_result.error}")
        else:
            logger.info(f"Stop result: {stop_result.result}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())