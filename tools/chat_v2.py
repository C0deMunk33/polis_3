from sqlmodel import SQLModel, Field, select
from libs.vector_storage import VectorStorage
from libs.agent_interface import AgentInterface
from libs.common import get_tool_schemas_from_class
from libs.agent import AgentStateDBO
from typing import Optional, Dict
import uuid
from datetime import datetime
from sqlmodel import Session
from libs.common import ToolCall, ToolCallResult, ToolSchema, ToolsetDetails
from typing import List

class ChatMessageDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    content: str
    user_id: str
    chat_id: str

class Chat(AgentInterface):
    def __init__(self, init_keys: Optional[Dict[str, str]] = None):
        self.chroma_db_path = "memory_manager_chroma_db.db"
        self.sqlite_db_path = "memory_manager_sqlite_db.db"
        self.ollama_server = "http://localhost:11434"
        self.embedding_model = "nomic-embed-text"
        self.chat_id = "1"

        if init_keys is not None:
            if "chroma_db_path" in init_keys:
                self.chroma_db_path = init_keys["chroma_db_path"]
            if "sqlite_db_path" in init_keys:
                self.sqlite_db_path = init_keys["sqlite_db_path"]
            if "ollama_server" in init_keys:
                self.ollama_server = init_keys["ollama_server"]
            if "embedding_model" in init_keys:
                self.embedding_model = init_keys["embedding_model"]
            if "chat_id" in init_keys:
                self.chat_id = init_keys["chat_id"]

        self.toolset_name = "chat"
        self.all_tools = get_tool_schemas_from_class(self)

        self.chat_vector_storage = VectorStorage(
            model_class=ChatMessageDBO,
            sqlite_db_path=self.sqlite_db_path,
            chroma_db_path=self.chroma_db_path,
            ollama_server=self.ollama_server,
            default_embedding_model=self.embedding_model,
            embed_field="content",
            id_field="id",
            collection_name=f"chat_{self.chat_id}"
        )
        
    def send_message(self, agent_state: AgentStateDBO, user_name: str, message: str):
        """{
            "toolset_id": "chat",
            "name": "send_message",
            "description": "Send a message to the chat",
            "is_long_running": false,
            "expose_to_agent": true,
            "arguments": [
                {"name": "user_name", "type": "str", "description": "Your name (required)"},
                {"name": "message", "type": "str", "description": "The message to send (required)"}
            ]
        }"""
        # add the message to the chat
        chat_message = ChatMessageDBO(content=message, user_id=user_name, chat_id=self.chat_id)
        self.chat_vector_storage.add(chat_message, metadata_fields=["id", "created_at"])
        return f"Message sent: {user_name}: {message}"
    
    def read_chat(self, agent_state: AgentStateDBO, limit: int = 10, offset: int = 0):
        """
        {
            "toolset_id": "chat",
            "name": "read_chat",
            "description": "Read the chat history",
            "is_long_running": false,
            "expose_to_agent": false,
            "arguments": [
                {"name": "limit", "type": "int", "description": "The number of messages to return, newest first (default: 10)"},
                {"name": "offset", "type": "int", "description": "The number of messages to skip, newest first (default: 0)"}
            ]
        }
        """
        with Session(self.chat_vector_storage.sqlite_engine) as session:
            messages = session.exec(select(ChatMessageDBO).order_by(ChatMessageDBO.created_at.desc()).offset(offset).limit(limit)).all()
            messages_str = f"Chat History:\n"
            # step backwards through the messages
            for i in range(len(messages) - 1, -1, -1):
                message = messages[i]
                # get time ago string
                time_ago = datetime.now() - message.created_at
                # x seconds ago, x minutes ago, x hours ago, x days ago 
                if time_ago.seconds < 60:
                    time_ago_str = f"{time_ago.seconds} seconds ago"
                elif time_ago.seconds < 3600:
                    time_ago_str = f"{time_ago.seconds // 60} minutes ago"
                else:
                    time_ago_str = f"{time_ago.seconds // 3600} hours ago"
                messages_str += f"{message.user_id}({time_ago_str}): {message.content} \n"
            return messages_str


    ########### AGENT INTERFACE ###########    
    def get_toolset_details(self) -> ToolsetDetails:
        return ToolsetDetails(
            toolset_id=self.toolset_name,
            name=self.toolset_name,
            description="Chat toolset"
        )
    
    def get_tool_schemas(self) -> List[ToolSchema]:
        return self.all_tools
    
    def agent_tool_callback(self, agent_state: AgentStateDBO, tool_call: ToolCall) -> ToolCallResult:
        result = getattr(self, tool_call.name)(agent_state, **tool_call.arguments)
        return ToolCallResult(
            toolset_id=self.toolset_name,
            tool_call=tool_call,
            result=result
        )
