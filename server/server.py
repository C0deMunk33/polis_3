from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from tools.chat import Chat, ChatMessageDBO
from libs.agent import AgentStateDBO, Agent
from sqlmodel import Session, select
from datetime import datetime
import json

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="server/web"), name="static")
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
# Initialize chat instance
chat_instance = Chat(init_keys=init_keys)
dummy_agent_state = AgentStateDBO(id="dummy", created_at=datetime.now())

class MessageRequest(BaseModel):
    user_name: str
    message: str

class MessageResponse(BaseModel):
    id: str
    user_id: str
    content: str
    created_at: datetime

class AgentResponse(BaseModel):
    id: str
    description: str
    created_at: datetime
    base_system_prompt: Optional[str] = None
    next_instruction: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    vision_model: Optional[str] = None

class AgentDetailsResponse(BaseModel):
    available_tools: List[Dict[str, Any]] = []
    app_keys: Dict[str, str] = {}

@app.get("/")
async def read_root():
    return FileResponse("server/web/index.html")

@app.get("/agent_state")
async def agent_state_page():
    return FileResponse("server/web/agent_state.html")

@app.post("/api/messages", response_model=MessageResponse)
async def send_message(message_request: MessageRequest):
    try:
        # Send message using the chat tool
        chat_instance.send_message(
            agent_state=dummy_agent_state,
            user_name=message_request.user_name,
            message=message_request.message
        )
        
        # Get the last message to return
        with Session(chat_instance.chat_vector_storage.sqlite_engine) as session:
            last_message = session.exec(
                select(ChatMessageDBO)
                .where(ChatMessageDBO.user_id == message_request.user_name)
                .order_by(ChatMessageDBO.created_at.desc())
            ).first()
            
            if not last_message:
                raise HTTPException(status_code=404, detail="Message not found")
                
            return MessageResponse(
                id=last_message.id,
                user_id=last_message.user_id,
                content=last_message.content,
                created_at=last_message.created_at
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages", response_model=List[MessageResponse])
async def get_messages(limit: int = 10, offset: int = 0):
    try:
        with Session(chat_instance.chat_vector_storage.sqlite_engine) as session:
            messages = session.exec(
                select(ChatMessageDBO)
                .order_by(ChatMessageDBO.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            
            return [
                MessageResponse(
                    id=msg.id,
                    user_id=msg.user_id,
                    content=msg.content,
                    created_at=msg.created_at
                ) for msg in messages
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat_history")
async def get_chat_history(limit: int = 10, offset: int = 0):
    try:
        # Use the read_chat method from the Chat class
        history = chat_instance.read_chat(
            agent_state=dummy_agent_state,
            limit=limit,
            offset=offset
        )
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New endpoints for agent state UI
@app.get("/api/agents", response_model=List[AgentResponse])
async def get_agents(limit: int = 10):
    try:
        # Get all agents from the database
        agent_ids = Agent.get_agent_ids(init_keys, limit=limit)
        agents = []
        
        for agent_id in agent_ids:
            agent_state = Agent.get_agent(init_keys, agent_id)
            if agent_state:
                agents.append(AgentResponse(
                    id=agent_state.id,
                    description=agent_state.description or "No description",  # Ensure description is never None
                    created_at=agent_state.created_at,
                    base_system_prompt=agent_state.base_system_prompt,
                    next_instruction=agent_state.next_instruction,
                    llm_model=agent_state.llm_model,
                    embedding_model=agent_state.embedding_model,
                    vision_model=agent_state.vision_model
                ))
        
        return agents  # This should return a list/array
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    try:
        agent_state = Agent.get_agent(init_keys, agent_id)
        if not agent_state:
            raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
        
        return AgentResponse(
            id=agent_state.id,
            description=agent_state.description,
            created_at=agent_state.created_at,
            base_system_prompt=agent_state.base_system_prompt,
            next_instruction=agent_state.next_instruction,
            llm_model=agent_state.llm_model,
            embedding_model=agent_state.embedding_model,
            vision_model=agent_state.vision_model
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/{agent_id}/details", response_model=AgentDetailsResponse)
async def get_agent_details(agent_id: str):
    try:
        agent_state = Agent.get_agent(init_keys, agent_id)
        if not agent_state:
            raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
        
        # Parse available tools
        available_tools = []
        if agent_state.available_tools_str:
            try:
                tools_data = json.loads(agent_state.available_tools_str)
                for tool_json in tools_data:
                    if isinstance(tool_json, str):
                        tool = json.loads(tool_json)
                    else:
                        tool = tool_json
                    available_tools.append(tool)
            except json.JSONDecodeError:
                # If there's an error parsing the JSON, return an empty list
                available_tools = []
        
        # Get app keys
        app_keys = agent_state.app_keys
        
        return AgentDetailsResponse(
            available_tools=available_tools,
            app_keys=app_keys
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
