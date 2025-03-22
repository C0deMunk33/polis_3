from typing import List, Optional, Dict
from libs.common import Message, ToolCallResult, ToolCall, ToolSchema, call_ollama_chat
from libs.agent_interface import AgentInterface
from libs.vector_storage import VectorStorage
from pydantic import BaseModel, Field
from libs.app_manager import AppManager
from datetime import datetime
import asyncio
import uuid
from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict

from typing import List, Dict, Optional
import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
import json

class AgentStateDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)
    base_system_prompt: Optional[str] = None
    next_instruction: Optional[str] = None
    llm_server_url: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    vision_model: Optional[str] = None
    available_tools_str: Optional[str] = Field(default="[]")
    pre_inference_tool_calls_str: Optional[str] = Field(default="[]")
    post_inference_tool_calls_str: Optional[str] = Field(default="[]")
    standing_tool_call_results_str: Optional[str] = Field(default="[]")
    tool_call_results_str: Optional[str] = Field(default="[]")
    pending_tool_calls_str: Optional[str] = Field(default="[]")
    app_keys_str: Optional[str] = Field(default="{}")
    
    @property
    def available_tools(self) -> List:
        return json.loads(self.available_tools_str) if self.available_tools_str else []
    
    @available_tools.setter
    def available_tools(self, value: List):
        self.available_tools_str = json.dumps([tool.model_dump_json() for tool in value])
    
    def append_available_tool(self, tool: ToolSchema):
        tools = self.available_tools
        tools.append(tool)
        self.available_tools = tools
    
    def remove_available_tool(self, tool_name: str, toolset_id: str = None):
        tools = self.available_tools
        if toolset_id:
            tools = [tool for tool in tools if not (tool.name == tool_name and tool.toolset_id == toolset_id)]
        else:
            tools = [tool for tool in tools if tool.name != tool_name]
        self.available_tools = tools
    
    @property
    def pre_inference_tool_calls(self) -> List:
        return json.loads(self.pre_inference_tool_calls_str) if self.pre_inference_tool_calls_str else []
    
    @pre_inference_tool_calls.setter
    def pre_inference_tool_calls(self, value: List):
        self.pre_inference_tool_calls_str = json.dumps([tool.model_dump_json() for tool in value])
    
    def append_pre_inference_tool_call(self, tool_call: ToolCall):
        calls = self.pre_inference_tool_calls
        calls.append(tool_call)
        self.pre_inference_tool_calls = calls
    
    def remove_pre_inference_tool_call(self, tool_name: str, toolset_id: str = None):
        calls = self.pre_inference_tool_calls
        if toolset_id:
            calls = [call for call in calls if not (call.name == tool_name and call.toolset_id == toolset_id)]
        else:
            calls = [call for call in calls if call.name != tool_name]
        self.pre_inference_tool_calls = calls
    
    @property
    def post_inference_tool_calls(self) -> List:
        return json.loads(self.post_inference_tool_calls_str) if self.post_inference_tool_calls_str else []
    
    @post_inference_tool_calls.setter
    def post_inference_tool_calls(self, value: List):
        self.post_inference_tool_calls_str = json.dumps([tool.model_dump_json() for tool in value])
    
    def append_post_inference_tool_call(self, tool_call: ToolCall):
        calls = self.post_inference_tool_calls
        calls.append(tool_call)
        self.post_inference_tool_calls = calls
    
    def remove_post_inference_tool_call(self, tool_name: str, toolset_id: str = None):
        calls = self.post_inference_tool_calls
        if toolset_id:
            calls = [call for call in calls if not (call.name == tool_name and call.toolset_id == toolset_id)]
        else:
            calls = [call for call in calls if call.name != tool_name]
        self.post_inference_tool_calls = calls
    
    @property
    def standing_tool_call_results(self) -> List:
        return json.loads(self.standing_tool_call_results_str) if self.standing_tool_call_results_str else []
    
    @standing_tool_call_results.setter
    def standing_tool_call_results(self, value: List):
        
        results = []
        for tool_result in value:
            if isinstance(tool_result, ToolCallResult):
                results.append(tool_result.model_dump_json())
            else:
                results.append(tool_result)
        
        self.standing_tool_call_results_str = json.dumps(results)
    
    def append_standing_tool_call_result(self, tool_result: ToolCallResult):
        results = self.standing_tool_call_results
        results.append(tool_result)
        self.standing_tool_call_results = results
    
    def remove_standing_tool_call_result(self, tool_name: str, toolset_id: str = None):
        results = self.standing_tool_call_results
        if toolset_id:
            results = [result for result in results 
                      if not (result.tool_call.name == tool_name and result.tool_call.toolset_id == toolset_id)]
        else:
            results = [result for result in results if result.tool_call.name != tool_name]
        self.standing_tool_call_results = results
    
    def clear_standing_tool_call_results(self):
        self.standing_tool_call_results = []
    
    @property
    def tool_call_results(self) -> List:
        return json.loads(self.tool_call_results_str) if self.tool_call_results_str else []
    
    @tool_call_results.setter
    def tool_call_results(self, value: List):
        results = []
        for tool_result in value:
            if isinstance(tool_result, ToolCallResult):
                results.append(tool_result.model_dump_json())
            else:
                results.append(tool_result)
        self.tool_call_results_str = json.dumps(results)
    
    def append_tool_call_result(self, tool_result: ToolCallResult):
        results = self.tool_call_results
        results.append(tool_result.model_dump_json())
        self.tool_call_results = results
    
    def remove_tool_call_result(self, tool_name: str, toolset_id: str = None):
        results = self.tool_call_results
        if toolset_id:
            results = [result for result in results 
                      if not (result.tool_call.name == tool_name and result.tool_call.toolset_id == toolset_id)]
        else:
            results = [result for result in results if result.tool_call.name != tool_name]
        self.tool_call_results = results
    
    def clear_tool_call_results(self):
        self.tool_call_results = []
    
    @property
    def pending_tool_calls(self) -> List:
        return json.loads(self.pending_tool_calls_str) if self.pending_tool_calls_str else []
    
    @pending_tool_calls.setter
    def pending_tool_calls(self, value: List):
        self.pending_tool_calls_str = json.dumps([tool.model_dump_json() for tool in value])
    
    def append_pending_tool_call(self, tool_call: ToolCall):
        calls = self.pending_tool_calls
        calls.append(tool_call)
        self.pending_tool_calls = calls
    
    def remove_pending_tool_call(self, tool_name: str, toolset_id: str = None):
        calls = []
        for call in self.pending_tool_calls:
            if isinstance(call, str):
                call = ToolCall.model_validate_json(call)
            if toolset_id:
                if call.name == tool_name and call.toolset_id == toolset_id:
                    continue
            else:
                if call.name == tool_name:
                    continue
            calls.append(call)
        self.pending_tool_calls = calls
    
    def clear_pending_tool_calls(self):
        self.pending_tool_calls = []
    
    @property
    def app_keys(self) -> Dict:
        return json.loads(self.app_keys_str) if self.app_keys_str else {}
    
    @app_keys.setter
    def app_keys(self, value: Dict):
        self.app_keys_str = json.dumps(value)
    
    def update_app_key(self, key: str, value: str):
        keys = self.app_keys
        keys[key] = value
        self.app_keys = keys
    
    def remove_app_key(self, key: str):
        keys = self.app_keys
        if key in keys:
            del keys[key]
            self.app_keys = keys
    
    @staticmethod
    def new_agent_state(base_system_prompt: str):
        agent_state = AgentStateDBO()
        agent_state.base_system_prompt = base_system_prompt
        return agent_state

class AgentRunSchema(BaseModel):
    thoughts: str = Field(description="Your thoughts about the task at hand")
    tool_calls: List[ToolCall] = Field(description="The tool calls to be called")
    follow_up_thoughts: str = Field(description="Your thoughts about the next pass")
    detailed_next_instruction: str = Field(description="Detailed instruction to yourself for the next pass")

class Agent:
    def __init__(self, 
                 llm_server_url: str, 
                 llm_model: str, 
                 embedding_model: str, 
                 vision_model: str, 
                 base_system_prompt: str, 
                 apps: List[AgentInterface], 
                 pre_inference_tool_calls: List[ToolCall], 
                 post_inference_tool_calls: List[ToolCall],
                 initial_instruction: str,
                 app_keys: Dict[str, str],
                 init_keys: Dict[str, str]):
        
        self.chroma_db_path = "chroma_db.db"
        self.sqlite_db_path = "sqlite_db.db"
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
            if "persona_name" in init_keys:
                self.persona_name = init_keys["persona_name"]
            if "persona_description" in init_keys:
                self.persona_description = init_keys["persona_description"]
        self.state = AgentStateDBO.new_agent_state(base_system_prompt)
        self.app_manager = AppManager()   
        self.state.llm_server_url = llm_server_url
        self.state.llm_model = llm_model
        self.state.embedding_model = embedding_model
        self.state.vision_model = vision_model
        self.state.app_keys = app_keys
        self.state.next_instruction = initial_instruction
        # add apps
        for app in apps:
            self.app_manager.add_app(app)

        # add standing tool calls
        self.state.pre_inference_tool_calls = pre_inference_tool_calls
        self.state.post_inference_tool_calls = post_inference_tool_calls

        # create agent database
        self.agent_vector_storage = VectorStorage(
            model_class=AgentStateDBO,
            chroma_db_path=self.chroma_db_path,
            sqlite_db_path=self.sqlite_db_path,
            ollama_server=self.ollama_server,
            embed_field="description",
            id_field="id",
            collection_name="agent_state",
            default_embedding_model=self.embedding_model,
        )
        
    def save_state(self):
        # add or update the agent state
        self.agent_vector_storage.add(self.state, metadata_fields=["id", "created_at"])

    
    def load_state(self, agent_id: str):
        self.state = self.agent_vector_storage.get_by_id(agent_id)

    @staticmethod
    def get_agents(init_keys: Dict[str, str]):
        agent_vector_storage = VectorStorage(
            model_class=AgentStateDBO,
            chroma_db_path=init_keys["chroma_db_path"],
            sqlite_db_path=init_keys["sqlite_db_path"],
            ollama_server=init_keys["ollama_server"],
            default_embedding_model=init_keys["embedding_model"],
        )
        return agent_vector_storage.get_all()
    
    @staticmethod
    def get_agent(init_keys: Dict[str, str], agent_id: str):
        agent_vector_storage = VectorStorage(
            model_class=AgentStateDBO,
            chroma_db_path=init_keys["chroma_db_path"],
            sqlite_db_path=init_keys["sqlite_db_path"],
            ollama_server=init_keys["ollama_server"],
            default_embedding_model=init_keys["embedding_model"],
        )
        return agent_vector_storage.get(agent_id)
    
    @staticmethod
    def get_agent_ids(init_keys: Dict[str, str], limit: int = 10):
        agent_vector_storage = VectorStorage(
            model_class=AgentStateDBO,
            chroma_db_path=init_keys["chroma_db_path"],
            sqlite_db_path=init_keys["sqlite_db_path"],
            embed_field="description",
            id_field="id",
            collection_name="agent_state",
            ollama_server=init_keys["ollama_server"],
            default_embedding_model=init_keys["embedding_model"],
        )
        return [agent.id for agent in agent_vector_storage.get_all(limit=limit)]

    @staticmethod
    def get_message_buffer(state: AgentStateDBO) -> List[Message]:
        message_buffer = []
        
        # available tools
        message_buffer.append(Message(role="assistant", content=state.available_tools_str))

        # standing tool call results
        if len(state.standing_tool_call_results) > 0:
            for tool_result in state.standing_tool_call_results:
                if type(tool_result) == str:
                    tool_result = ToolCallResult.model_validate_json(tool_result)
                    
                if tool_result.result and len(tool_result.result) > 0:
                    message_buffer.append(Message(role="assistant", content=f"{tool_result.result}"))

        # tool call results
        if len(state.tool_call_results) > 0:
            for tool_result in state.tool_call_results:
                if type(tool_result) == str:
                    tool_result = ToolCallResult.model_validate_json(tool_result)
                    
                if tool_result.result and len(tool_result.result) > 0:
                    message_buffer.append(Message(role="assistant", content=f"Called: {tool_result.tool_call.toolset_id} {tool_result.tool_call.name}({tool_result.tool_call.arguments})"))
                    message_buffer.append(Message(role="tool", content=f"Tool result: {tool_result.result}"))

        # pending tool calls
        if len(state.pending_tool_calls) > 0:
            for tool_call in state.pending_tool_calls:
                if type(tool_call) == str:
                    tool_call = ToolCall.model_validate_json(tool_call)
                message_buffer.append(Message(role="assistant", content=f"Pending tool call: {tool_call.toolset_id} {tool_call.name}({tool_call.arguments})"))

        return message_buffer

    async def run_background_tool(self, tool_call: ToolCall):
        # if tool is already pending, by name and toolset_id, skip
        # otherwise these would stack up
        if any(call.name == tool_call.name and call.toolset_id == tool_call.toolset_id for call in self.state.pending_tool_calls):
            return None
        else:
            self.state.append_pending_tool_call(tool_call)

        tool_result = self.app_manager.run_tool(tool_call, self.state)
        self.state.append_tool_call_result(tool_result)
        self.state.remove_pending_tool_call(tool_call.name, tool_call.toolset_id)
        return tool_result  # Return the tool result so it can be awaited

    async def run_pass_async(self):
        print("~"*100)
        print("Running pass")
        self.state.available_tools = self.app_manager.get_available_tools()
        self.state.available_tools_str = self.app_manager.list_apps() + "\n" + self.app_manager.get_loaded_apps()

        # run pre-inference tool calls
        for tool_call in self.state.pre_inference_tool_calls:
            
            if type(tool_call) == str:
                tool_call = ToolCall.model_validate_json(tool_call)

            print(f"Pre-inference tool call: {tool_call.name} {tool_call.toolset_id} {tool_call.arguments}")
            # note: if tool is long running, it will block the main thread

            tool_result = self.app_manager.run_tool(tool_call, self.state)

            self.state.append_standing_tool_call_result(tool_result)

        final_message_buffer = []
        final_system_prompt = self.state.base_system_prompt

        final_message_buffer.append(Message(role="system", content=final_system_prompt))

        # get message buffer
        final_message_buffer.extend(self.get_message_buffer(self.state))
        # clear standing_tool_call_results
        self.state.standing_tool_call_results = []
        # next instruction
        if self.state.next_instruction:
            final_next_instruction = "Instructions you wrote for yourself from your previous pass:\n"
            final_next_instruction += self.state.next_instruction
            final_next_instruction += "\n\n" + f"Please respond in the following format: \n{AgentRunSchema.model_json_schema()}"
            final_message_buffer.append(Message(role="user", content=f"{final_next_instruction}"))

        # inference:
        llm_response = call_ollama_chat(self.state.llm_server_url, self.state.llm_model, final_message_buffer, json_schema=AgentRunSchema.model_json_schema())
        agent_run_schema = AgentRunSchema.model_validate_json(llm_response)
        print()
        print("="*100)
        print(f"Agent run result:")
        print(f"    Thoughts: {agent_run_schema.thoughts}")
        print()
        print(f"    Follow up thoughts: {agent_run_schema.follow_up_thoughts}")
        print()
        print(f"    Detailed next instruction: {agent_run_schema.detailed_next_instruction}")
        print("="*100)
        print()
        # post-inference:
        self.state.next_instruction = agent_run_schema.detailed_next_instruction

        tool_schemas = self.app_manager.get_all_tool_schemas()
        background_tasks = []

        # Create background tasks for agent's tool calls
        for tool_call in agent_run_schema.tool_calls:
            print(f"Tool call: {tool_call.name} {tool_call.toolset_id} {tool_call.arguments}")
            
            tool_schema = next((schema for schema in tool_schemas if (schema.name == tool_call.name and schema.toolset_id == tool_call.toolset_id)), None)
            if not tool_schema:
                print(f"Tool call {tool_call.name} not found")
                continue
            
            if tool_schema and tool_schema.is_long_running:
                background_tasks.append(self.run_background_tool(tool_call))
            else:
                tool_result = self.app_manager.run_tool(tool_call, self.state)
                self.state.append_tool_call_result(tool_result)

        # Create background tasks for post-inference tool calls
        for tool_call in self.state.post_inference_tool_calls:
            if type(tool_call) == str:
                tool_call = ToolCall.model_validate_json(tool_call)
            tool_schema = next((schema for schema in tool_schemas if (schema.name == tool_call.name and schema.toolset_id == tool_call.toolset_id)), None)
            if not tool_schema:
                print(f"Tool call {tool_call} not found")
                continue
            print(f"Post-inference tool call: {tool_call.name} {tool_call.toolset_id} {tool_call.arguments}")
            if tool_schema.is_long_running:
                background_tasks.append(self.run_background_tool(tool_call))
            else:
                tool_result = self.app_manager.run_tool(tool_call, self.state)
                self.state.append_standing_tool_call_result(tool_result)
                
        # Await all background tasks to complete
        if background_tasks:
            # Using gather instead of as_completed to wait for all tasks to complete
            await asyncio.gather(*background_tasks)
            # Note: No need to add results here as they are already added in run_background_tool
    def run_pass(self):
        """
        Synchronous wrapper for the asynchronous run_pass_async method.
        This ensures we properly create and manage the event loop.
        """
        # Get or create an event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If there's no event loop in this thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async method until complete
        loop.run_until_complete(self.run_pass_async())

# Example modification to the main orchestrator.py file:
"""
import asyncio
from libs.agent import Agent

async def main_async():
    # Your initialization code here
    agent = Agent(...)
    
    # Run multiple passes if needed
    await agent.run_pass_async()
    # ... more code

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
"""