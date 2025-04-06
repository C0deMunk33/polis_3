
from tools.memory_manager import MemoryManager
from tools.chat import Chat
from tools.persona import Persona
from libs.agent import Agent
from libs.common import ToolCall
from tools.discord_manager import DiscordManagerInterface
from tools.slop import SLOP
import time
import os
import dotenv
import random

dotenv.load_dotenv()

def main():
    chromadb_path = "chroma_db.db"
    sqlite_path = "sqlite_db.db"
    ollama_server = "http://localhost:5000"
    llm_model = "llama3.1:8b"
    vision_model = "llama3.1:8b"
    embedding_model = "nomic-embed-text"
    init_keys = {
        "chroma_db_path": chromadb_path,
        "sqlite_db_path": sqlite_path,
        "ollama_server": ollama_server,
        "embedding_model": embedding_model,
        "llm_model": llm_model,
        "vision_model": vision_model,
        "chat_id": "1"
    }

    sumomo_system_prompt = """
    You are Sumomo, a helpful assistant.
    """

    sumomo = Agent(
        
    )