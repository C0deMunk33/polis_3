import uuid
from datetime import datetime
from typing import Optional, Dict, List
from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from libs.agent_interface import AgentInterface
from libs.agent import AgentStateDBO
from libs.vector_storage import VectorStorage
from libs.common import get_tool_schemas_from_class, ToolsetDetails, ToolSchema, ToolCall, ToolCallResult, Message, call_ollama_chat
from libs.demographic_seeds import DemographicSeedManager
import random
import string


class PersonaDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    name: str
    description: str


class PersonaNameSelectorSchema(BaseModel):
    name: str

class PersonaDescriptionSchema(BaseModel):
    description: str

class Persona(AgentInterface):
    def __init__(self, init_keys: Optional[Dict[str, str]] = None):
        self.current_persona = None

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

        # todo: add default persona
        self.persona_vector_storage = VectorStorage(
            model_class=PersonaDBO,
            chroma_db_path=self.chroma_db_path,
            sqlite_db_path=self.sqlite_db_path,
            ollama_server=self.ollama_server,
            default_embedding_model=self.embedding_model,
            embed_field="description",
            id_field="id",
            collection_name="persona"
        )

        self.toolset_name = "persona"

        self.all_tools = get_tool_schemas_from_class(self)

    def create_persona(self, agent_state: AgentStateDBO, name: Optional[str] = None, description: Optional[str] = None) -> str:
        """
        {
            "toolset_id": "persona",
            "name": "create_persona",
            "description": "Create a persona for the user",
            "is_long_running": true,
            "expose_to_agent": false,
            "arguments": [{
                "name": "name",
                "type": "string",
                "description": "The name of the persona (optional)"
            }, {
                "name": "description",
                "type": "string",
                "description": "The description of the persona (optional)"
            }]
        }
        """
        if description is None:
            description = "[no description provided]"

        if name is None:
            # pick a random letter A-Z (capital)
            first_letter = random.choice(string.ascii_uppercase)
            name_selector_prompt = f"""
            Given this description of a persona:
            {description}
            
            Please select a name for the persona that begins with the letter {first_letter}.

            Please reply in the following JSON format:
            {PersonaNameSelectorSchema.model_json_schema()}
            """
            # get the name
            name_message_buffer = [
                Message(role="user", content=name_selector_prompt)
            ]
            name_selection = call_ollama_chat(agent_state.llm_server_url, agent_state.llm_model, name_message_buffer, json_schema=PersonaNameSelectorSchema.model_json_schema())
            name_selection = PersonaNameSelectorSchema.model_validate_json(name_selection)
            name = name_selection.name

        persona_description_prompt = f"""
        Given this name for a persona:
        {name}

        And this rough description of a persona:
        {description}
        
        Please create a more detailed description for the persona. Be creative and detailed.

        Please reply in the following JSON format:
        {PersonaDescriptionSchema.model_json_schema()}
        """
        description_message_buffer = [
            Message(role="user", content=persona_description_prompt)
        ]
        description_selection = call_ollama_chat(agent_state.llm_server_url, agent_state.llm_model, description_message_buffer, json_schema=PersonaDescriptionSchema.model_json_schema())
        description_selection = PersonaDescriptionSchema.model_validate_json(description_selection)
        description = description_selection.description
        
        new_persona_dbo = PersonaDBO(name=name, description=description)
        # add or update the persona
        self.persona_vector_storage.add(new_persona_dbo, metadata_fields=["id", "created_at"])
        self.current_persona = new_persona_dbo

        return f"Persona created: {name}\nDescription: {description}"

    def create_persona_from_random_demographic_seed(self, agent_state: AgentStateDBO):

        demographic_seed_manager = DemographicSeedManager()
        demographic_seed = demographic_seed_manager.get_random_demographic_seed()

        return self.create_persona(agent_state, demographic_seed.first_name + " " + demographic_seed.last_name, demographic_seed.get_formatted_description())

    def set_persona(self, agent_state: AgentStateDBO, persona_id: str):
        """
        {
            "toolset_id": "persona",
            "name": "set_persona",
            "description": "Set the persona",
        }
        """
        persona_dbo = self.persona_vector_storage.get_by_id(persona_id)
        if persona_dbo is None:
            return f"Persona not found: {persona_id}"
        self.current_persona = persona_dbo
        return f"Persona set: {persona_dbo.name}\nDescription: {persona_dbo.description}"

    def get_persona_string(self, agent_state: AgentStateDBO):
        """{
            "toolset_id": "persona",
            "name": "get_persona_string",
            "description": "Get the persona string",
            "is_long_running": false,
            "expose_to_agent": false,
            "arguments": []
        }"""
        return f"Your current persona: {self.current_persona.name}\n{self.current_persona.description}"


    ########### AgentInterface ###########


    def get_toolset_details(self) -> ToolsetDetails:
        return ToolsetDetails(
            toolset_id=self.toolset_name,
            name=self.toolset_name,
            description="Persona toolset"
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
    
   