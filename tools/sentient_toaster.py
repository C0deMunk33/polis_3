from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime
from libs.common import call_ollama_chat, Message

class Interaction(BaseModel):
    name: str = Field(description="The name of the interaction")
    description: str = Field(description="A description of the interaction")
    required_state: List[str] = Field(description="The state that is required to perform the interaction")
    action_inputs: List[str] = Field(description="The inputs that the interaction requires")
    action_outputs: List[str] = Field(description="The outputs that the interaction produces")


class SentientToasterTemplateLLMSchema(BaseModel):
    name: str = Field(description="The name of the item")
    description: str = Field(description="A description of the item")
    state_parameters: List[str] = Field(description="The names of the state parameters that the item needs to function")
    interactions: List[Interaction] = Field(description="The interactions that a user of the item can perform with the item")
    core_prompt: str = Field(description="The core prompt of the item")


def generate_sentient_toaster_template(llm_server_url: str, llm_model: str, description: str):
    st_generator_system_prompt = """
    You are a helpful assistant that generates in-game item templates for items where the logic of how the item works is via an LLM.

    Each item has a name, a description, a list of statuses, a core prompt, and a list of actions that users of the item can perform.
    It can be any type of item or device that a player or npc can interact with.
    """
    st_generator_user_prompt = f"""
    Generate an item template for the following description:
    {description}

    Please respond with the template in the following JSON format:
    {SentientToasterTemplateLLMSchema.model_json_schema()}
    """
    
    messages = [
        Message(role="system", content=st_generator_system_prompt),
        Message(role="user", content=st_generator_user_prompt)
    ]

    response = call_ollama_chat(llm_server_url, llm_model, messages, json_schema=SentientToasterTemplateLLMSchema.model_json_schema())
    response = SentientToasterTemplateLLMSchema.model_validate_json(response)

    

    print(f"* Name: {response.name}")
    print(f"* Description: {response.description}")
    print(f"* State Parameters: {response.state_parameters}")
    print(f"* Core Prompt: {response.core_prompt}")
    print(f"* Interactions:")
    for interaction in response.interactions:
        print(f"  -- {interaction.name}: {interaction.description}")
        print(f"      - Required State: {interaction.required_state}")
        print(f"      - Inputs: {interaction.action_inputs}")
        print(f"      - Outputs: {interaction.action_outputs}")

    return response
    

class InitialStateSchema(BaseModel):
    initial_state: Dict[str, str] = Field(description="The initial state of the item")

class InteractionRequestSchema(BaseModel):
    interaction: Interaction = Field(description="The interaction to perform")
    inputs: Dict[str, str] = Field(description="The inputs to the interaction")
    intent: str = Field(description="The intent of the interaction")

class InteractionResponseSchema(BaseModel):
    interaction_request: InteractionRequestSchema = Field(description="The interaction request")
    updated_item_state: Dict[str, str] = Field(description="The updated state of the item after the interaction")
    outputs: Dict[str, str] = Field(description="The outputs of the interaction")
    description: str = Field(description="A description of the interaction")

class SentientToaster:
    def __init__(self, llm_server_url: str, llm_model: str, template: SentientToasterTemplateLLMSchema, creation_prompt: str):
        self.template = template
        self.state = {}
        self.creation_prompt = creation_prompt
        self.llm_server_url = llm_server_url
        self.llm_model = llm_model
       
        get_initial_state_prompt = f"""
        You are a helpful assistant that generates the initial state of an item.
        The item is described by the following template:
        {self.template.model_dump_json()}

        The item is described by the following creation prompt:
        {self.creation_prompt}

        Please respond with the initial state of the item in the following JSON format:
        {InitialStateSchema.model_json_schema()}
        """
        messages = [
            Message(role="user", content=get_initial_state_prompt)
        ]
        response = call_ollama_chat(self.llm_server_url, self.llm_model, messages, json_schema=InitialStateSchema.model_json_schema())
        response = InitialStateSchema.model_validate_json(response)
        self.state = response.initial_state
      
    def interact(self, interaction: InteractionRequestSchema) -> InteractionResponseSchema:
        # call the interaction
        interaction_request_prompt = f"""
        You are a helpful assistant that simulates the interaction of an item with a user.
        The item is described by the following template:
        {self.template.model_dump_json()}

        The current state of the item is:
        {self.state}

        The user has the following interaction request:
        {interaction.model_dump_json()}

        Please respond with the interaction request in the following JSON format:
        {InteractionResponseSchema.model_json_schema()}
        """
        messages = [
            Message(role="user", content=interaction_request_prompt)
        ]
        response = call_ollama_chat(self.llm_server_url, self.llm_model, messages, json_schema=InteractionResponseSchema.model_json_schema())
        response = InteractionResponseSchema.model_validate_json(response)

        # extend or update self.state with the updated_item_state
        self.state.update(response.updated_item_state)

        return response

    def get_state(self):
        return self.state
    

class InteractionGenerator:
    def __init__(self, llm_server_url: str, llm_model: str, template: SentientToasterTemplateLLMSchema):
        self.template = template
        self.llm_server_url = llm_server_url
        self.llm_model = llm_model

    def generate_interaction(self, current_state: Dict[str, str]) -> InteractionRequestSchema:
        generate_interaction_prompt = f"""
        You are a helpful assistant that generates an interaction for an item.
        The item is described by the following template:
        {self.template.model_dump_json()}

        The current state of the item is:
        {current_state}

        Please respond with the interaction in the following JSON format:
        {InteractionRequestSchema.model_json_schema()}
        """
        messages = [
            Message(role="user", content=generate_interaction_prompt)
        ]
        response = call_ollama_chat(self.llm_server_url, self.llm_model, messages, json_schema=InteractionRequestSchema.model_json_schema())
        response = InteractionRequestSchema.model_validate_json(response)
        return response


if __name__ == "__main__":


    prompts = [
        "a simple espesso machine",
        "a porche 911",
        "a robot butler",
        "a monet painting",
        "a simple desk lamp",
        "a simple desk lamp that can also be used as a speaker",
        "a toaster",
        "an orb of warding"
    ]
    for prompt in prompts:
        print("~" * 80)
        template = generate_sentient_toaster_template("http://localhost:5000", "llama3.1:8b", prompt)
        print("~" * 80)

        # run the interaction
        sentient_toaster = SentientToaster("http://localhost:5000", "llama3.1:8b", template, "create an instance of this item")
        print("~" * 80)
        print(sentient_toaster.get_state())
        print("~" * 80)
        interaction_generator = InteractionGenerator("http://localhost:5000", "llama3.1:8b", template)
        interaction = interaction_generator.generate_interaction(sentient_toaster.get_state())
        print(interaction)
        print("~" * 80)
        response = sentient_toaster.interact(interaction)
        print(response)
        print("~" * 80)
        print("State after interaction:")
        print(sentient_toaster.get_state())
        print("~" * 80)
        