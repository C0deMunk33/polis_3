from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict

from libs.agent_interface import AgentInterface
from libs.common import ToolsetDetails, ToolSchema, ToolCall, ToolCallResult, get_tool_schemas_from_class, Message, call_ollama_chat, embed_with_ollama
from libs.agent import AgentStateDBO, Agent
from libs.vector_storage import VectorStorage
import uuid
from sqlmodel import Field, Session, SQLModel, create_engine
import os

class MemoryDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime
    content: str

class MemorySummary(BaseModel):
    memory_ids: List[str]
    created_at: datetime
    content: str

class MemoryManagerDBO(BaseModel):
    memory_set_id: str
    memory_store: List[MemoryDBO]
    memory_summary_store: List[MemorySummary]

class MemoryExtractionSchema(BaseModel):
    thoughts: str
    memories: List[str]

class QueryExtractionSchema(BaseModel):
    thoughts: str
    queries: List[str]

class MemoryApprovalSchema(BaseModel):
    thoughts: str
    relevant_memory_ids: List[str]

class MemoryManager(AgentInterface):
    def __init__(self, memory_manager_dbo: Optional[MemoryManagerDBO] = None, init_keys: Optional[Dict[str, str]] = None):
        self.chroma_db_path = "memory_manager_chroma_db.db"
        self.sqlite_db_path = "memory_manager_sqlite_db.db"
        self.ollama_server = "http://localhost:11434"
        self.embedding_model = "nomic-embed-text"

        if init_keys is not None:
            if "chroma_db_path" in init_keys:
                self.chroma_db_path = init_keys["chroma_db_path"]
            if "sqlite_db_path" in init_keys:
                self.sqlite_db_path = init_keys["sqlite_db_path"]
            if "ollama_server" in init_keys:
                self.ollama_server = init_keys["ollama_server"]
            if "embedding_model" in init_keys:
                self.embedding_model = init_keys["embedding_model"]



        if memory_manager_dbo is None:
            self.memory_manager_dbo = MemoryManagerDBO(memory_set_id=str(uuid.uuid4()), memory_store=[], memory_summary_store=[])
        else:
            self.memory_manager_dbo = memory_manager_dbo
        self.toolset_name = "memory_manager"

        self.all_tools = get_tool_schemas_from_class(self)
        
        self.memory_vector_storage = VectorStorage(
            model_class=MemoryDBO,
            sqlite_db_path=self.sqlite_db_path,
            chroma_db_path=self.chroma_db_path,
            ollama_server=self.ollama_server,
            default_embedding_model=self.embedding_model,
            embed_field="content",
            id_field="id",
            collection_name=f"memory_{self.memory_manager_dbo.memory_set_id}"
        )
        

    def extract_memories(self, agent_state: AgentStateDBO):
        """
        {
            "toolset_id": "memory_manager",
            "name": "extract_memories",
            "description": "Extract memories from the memory store",
            "is_long_running": true,
            "expose_to_agent": false,
            "arguments": []
        }
        """
        # get last 10 memories from the memory store
        memories = self.memory_manager_dbo.memory_store[-10:]

        memories_str = ""
        for memory in memories:
            memories_str += f"{memory.id}: {memory.content}\n"

        memory_extraction_prompt = f"""
        Given all the conext available to you, extract the most relevant memories that have not already been extracted.

        extract only information that is relevant long term, not every specific action and detail.
        Reply with JSON in the following format:
        {MemoryExtractionSchema.model_json_schema()}
        """
        # ask llm to extract memories from the agent state
        message_buffer = Agent.get_message_buffer(agent_state)
        message_buffer.append(Message(role="assistant", content=f"Recently extracted memories:\n{memories_str}"))
        message_buffer.append(Message(role="user", content=memory_extraction_prompt))
        response = call_ollama_chat(agent_state.llm_server_url, agent_state.llm_model, message_buffer, json_schema=MemoryExtractionSchema.model_json_schema())
        try:
            extracted_memories = MemoryExtractionSchema.model_validate_json(response)
        except Exception as e:
            print(f"Error validating memory extraction response: {e}")
            print(f"Response: {response}")
            raise e
        
        
        for memory in extracted_memories.memories:
            mem = MemoryDBO(id=str(uuid.uuid4()), 
                            content=memory,
                              created_at=datetime.now())
            self.memory_vector_storage.add(mem, metadata_fields=["id", "created_at"])

        return ""

    def get_relevant_memories(self, agent_state: AgentStateDBO):
        """
        {
            "toolset_id": "memory_manager",
            "name": "get_relevant_memories",
            "description": "Get relevant memories from the memory store",
            "is_long_running": true,
            "expose_to_agent": false,
            "arguments": []
        }
        """

        # if there are fewer than 10 memories, return an empty string
        if len(self.memory_manager_dbo.memory_store) < 10:
            print("Not enough memories to query")
            return ""

        query_prompt = f"""
        Given the context available to you, create a list of queries for a vector database of memories that will most likely return the most relevant memories.
        
        Reply with JSON in the following format:
        {QueryExtractionSchema.model_json_schema()}
        """
        # ask llm to extract memories from the agent state
        raw_message_buffer = Agent.get_message_buffer(agent_state)
        query_message_buffer = raw_message_buffer.copy()
        query_message_buffer.append(Message(role="user", content=query_prompt))
        query_response = call_ollama_chat(agent_state.llm_server_url, agent_state.llm_model, query_message_buffer, json_schema=QueryExtractionSchema.model_json_schema())
        queries = QueryExtractionSchema.model_validate_json(query_response)
        raw_memory_results = []
        for query in queries.queries:
            results = self.memory_vector_storage.query_similar(query, n_results=10)
            # add the results to the message buffer
            raw_memory_results.append(results)
        
        approval_prompt = f"""
        Given the context available to you, return a list of memory IDs that are relevant to the query.

        Reply with JSON in the following format:
        {MemoryApprovalSchema.model_json_schema()}
        """
        approval_message_buffer = raw_message_buffer.copy()

        memory_results_str = ""
        for i, results in enumerate(raw_memory_results):
            memory_results_str += f"Query {i+1}:\n"
            for result in results:
                memory_results_str += f"{result['id']}: {result['content']}\n"

        approval_message_buffer.append(Message(role="user", content=f"Memory results:\n{memory_results_str}"))
        approval_message_buffer.append(Message(role="user", content=approval_prompt))
        approval_response = call_ollama_chat(agent_state.llm_server_url, agent_state.llm_model, approval_message_buffer, json_schema=MemoryApprovalSchema.model_json_schema())
        relevant_memory_ids = MemoryApprovalSchema.model_validate_json(approval_response)
        relevant_memories = [raw_memory_results[i][relevant_memory_ids.relevant_memory_ids[i]] for i in range(len(relevant_memory_ids.relevant_memory_ids))]
        relevant_memories_str = ""
        for memory in relevant_memories:
            relevant_memories_str += f"{memory['id']}: {memory['content']}\n"
        print(f"Relevant memories: {relevant_memories_str}")
        return relevant_memories_str

    def query_memories(self, agent_state: AgentStateDBO, query: str, limit: int = 10):
        """
        {
            "toolset_id": "memory_manager",
            "name": "query_memories",
            "description": "Query the memory store",
            "is_long_running": true,
            "expose_to_agent": false,
            "arguments": [
                {"name": "query", "type": "str", "description": "The query to search for"},
                {"name": "limit", "type": "int", "description": "The number of memories to return"}
            ]
        }
        """
        # query the memory store
        results = self.memory_vector_storage.query_similar(query, n_results=limit)
        pass

    def get_recent_contextual_summaries(self, agent_state: AgentStateDBO):
        """
        {
            "toolset_id": "memory_manager",
            "name": "get_recent_contextual_summaries",
            "description": "Get recent contextual summaries from the memory store",
            "is_long_running": false,
            "expose_to_agent": false,
            "arguments": []
        }
        """
        context_summary_str = ""
        for memory in self.memory_manager_dbo.memory_summary_store[-10:]:
            context_summary_str += f"{memory.content}\n"
        return context_summary_str

    ### AgentInterface
    def get_toolset_details(self) -> ToolsetDetails:
        return ToolsetDetails(
            toolset_id=self.toolset_name,
            name=self.toolset_name,
            description="Memory management toolset"
        )

    def get_tool_schemas(self) -> List[ToolSchema]:
        return self.all_tools
    
    def agent_tool_callback(self, agent_state: AgentStateDBO, tool_call: ToolCall) -> ToolCallResult:
        # call the tool
       
        result = getattr(self, tool_call.name)(agent_state, **tool_call.arguments)

        return ToolCallResult(
            toolset_id=self.toolset_name,
            tool_call=tool_call,
            result=result
        )

    