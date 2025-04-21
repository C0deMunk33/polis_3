from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import List, Dict, Any, Literal
import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import Column, JSON
from libs.common import call_ollama_chat, Message, get_tool_schemas_from_class
import hashlib
import json
import os
from sqlalchemy.orm import attributes

class InteractionIOType(str, Enum):
    ITEM = "item"
    SOUND = "sound"
    SMELL = "smell"
    STATUS = "status"
    FEELING = "feeling"
    TEXT = "text"
    FORCE = "force"

class InteractionIOSchema(BaseModel):
    name_and_amount: str = Field(description="The name and amount of the input or output")
    type: InteractionIOType = Field(description="The type of the input or output, types available are: item, sound, smell, status, feeling, text, force")

class Interaction(BaseModel):
    name: str = Field(description="The name of the interaction")
    description: str = Field(description="A description of the interaction")
    required_state: List[str] = Field(description="The state that is required to perform the interaction")
    action_inputs: List[InteractionIOSchema] = Field(description="The inputs that the interaction requires")
    action_outputs: List[InteractionIOSchema] = Field(description="The outputs that the interaction produces")


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
    For each action, there is a list of inputs and outputs.
    The inputs and outputs can be any of the following types: item, sound, smell, status, feeling, text, force
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
    inputs: Dict[str, str] = Field(description="The inputs to the interaction. name => amount/details mapping")
    intent: str = Field(description="The intent of the interaction")

class InteractionResponseSchema(BaseModel):
    interaction_request: InteractionRequestSchema = Field(description="The interaction request")
    updated_item_state: Dict[str, str] = Field(description="The updated state of the item after the interaction")
    outputs: List[InteractionIOSchema] = Field(description="The outputs of the interaction")
    description: str = Field(description="A description of the interaction")

class SentientToasterTemplateDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(description="The name of the item")
    description: str = Field(description="A description of the item")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(description="The user that created the item")
    template: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    @property
    def template_obj(self) -> SentientToasterTemplateLLMSchema:
        """Return the template as a SentientToasterTemplateLLMSchema object"""
        return SentientToasterTemplateLLMSchema.model_validate(self.template)

class SentientToasterDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(description="The user that created the item")
    template_id: str = Field(description="The id of the template that the item is based on")
    state: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )

    interaction_history: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )

    
    
class SentientToasterInteractionDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(description="The name of the interaction")
    final_state: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    outputs: List[InteractionIOSchema] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    actor_id: str = Field(description="The id of the actor that performed the interaction")
    instance_id: str = Field(description="The id of the instance that the interaction belongs to")
    interaction: InteractionRequestSchema = Field(
        default_factory=InteractionRequestSchema,
        sa_column=Column(JSON)
    )
    result: InteractionResponseSchema = Field(
        default_factory=InteractionResponseSchema,
        sa_column=Column(JSON)
    )

    @property
    def interaction_obj(self) -> InteractionRequestSchema:
        """Return the interaction as an InteractionRequestSchema object"""
        return InteractionRequestSchema.model_validate(self.interaction)
    

class SentientToasterManager:
    def __init__(self, llm_server_url: str, llm_model: str, db_path: str):
        self.db_path = db_path
        self.llm_server_url = llm_server_url
        self.llm_model = llm_model
        self.engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def generate_template(self, description: str, sender_id: str):
        new_template = generate_sentient_toaster_template(self.llm_server_url, self.llm_model, description)
        dbo = SentientToasterTemplateDBO(
            name=new_template.name,
            description=new_template.description,
            template=new_template.model_dump(),
            created_by=sender_id
        )
        self.db.add(dbo)
        self.db.commit()
        return dbo

    def generate_instance(self, template_id: str, creation_prompt: str, sender_id: str):
        template_dbo = self.db.exec(select(SentientToasterTemplateDBO).where(SentientToasterTemplateDBO.id == template_id)).first()
        if not template_dbo:
            raise ValueError(f"Template with id {template_id} not found")
       
        get_initial_state_prompt = f"""
        You are a helpful assistant that generates the initial state of an item.
        The item is described by the following template:
        {template_dbo.template_obj.model_dump_json()}

        The item is described by the following creation prompt:
        {creation_prompt}

        Please respond with the initial state of the item in the following JSON format:
        {InitialStateSchema.model_json_schema()}
        """
        messages = [
            Message(role="user", content=get_initial_state_prompt)
        ]
        response = call_ollama_chat(self.llm_server_url, self.llm_model, messages, json_schema=InitialStateSchema.model_json_schema())
        response = InitialStateSchema.model_validate_json(response)

        result_dbo = SentientToasterDBO(
            template_id=template_id,
            state=response.initial_state,
            created_by=sender_id
        )
        self.db.add(result_dbo)
        self.db.commit()
        return result_dbo
      
    def interact(self, instance_id: str, interaction: InteractionRequestSchema, sender_id: str) -> InteractionResponseSchema:
        instance_dbo = self.db.exec(select(SentientToasterDBO).where(SentientToasterDBO.id == instance_id)).first()
        template_dbo = self.db.exec(select(SentientToasterTemplateDBO).where(SentientToasterTemplateDBO.id == instance_dbo.template_id)).first()
        if not instance_dbo:
            raise ValueError(f"Instance with id {instance_id} not found")

        # call the interaction
        interaction_request_prompt = f"""
        You are a helpful assistant that simulates the interaction of an item with a user.
        The item is described by the following template:
        {template_dbo.template_obj.model_dump_json()}

        The current state of the item is:
        {instance_dbo.state}

        The user has the following interaction request:
        {interaction.model_dump_json()}

        If new keys need to be added to the state, add them to the state.
        If a key is removed from the state, remove it from the state, think about how the state will look after the interaction.
        If you notice a mistake, in the state, silently correct it. Do not place notes to the state, just fix it.

        Please respond with the interaction request in the following JSON format:
        {InteractionResponseSchema.model_json_schema()}
        """
        messages = [
            # add the interaction history to the system prompt, limit to most recent interactions
            Message(role="system", content=f"The interaction history is: {instance_dbo.interaction_history[30:]}"),
            Message(role="user", content=interaction_request_prompt)
        ]
        response = call_ollama_chat(self.llm_server_url, self.llm_model, messages, json_schema=InteractionResponseSchema.model_json_schema())
        response = InteractionResponseSchema.model_validate_json(response)


        # merge the updated_item_state into the instance_dbo.state
        instance_dbo.state.update(response.updated_item_state)
        instance_dbo.updated_at = datetime.now()  # Update the timestamp
        attributes.flag_modified(instance_dbo, "state")
        attributes.flag_modified(instance_dbo, "updated_at")
        instance_dbo.interaction_history.append(f"user:{sender_id}")
        instance_dbo.interaction_history.append(f"interaction: {interaction.interaction.description}")
        instance_dbo.interaction_history.append(f"result: {response.description}")
        attributes.flag_modified(instance_dbo, "interaction_history")
        self.db.commit()
        self.db.refresh(instance_dbo)

        interaction_dbo = SentientToasterInteractionDBO(
            name=interaction.interaction.name,
            outputs=[output.model_dump() for output in response.outputs],
            final_state=instance_dbo.state,
            instance_id=instance_id,    
            interaction=interaction.model_dump(),
            result=response.model_dump(),
            actor_id=sender_id
        )
        self.db.add(interaction_dbo)
        self.db.commit()
        return response

    

class InteractionGenerator:
    def __init__(self, llm_server_url: str, llm_model: str, template: SentientToasterTemplateLLMSchema):
        self.template = template
        self.llm_server_url = llm_server_url
        self.llm_model = llm_model

    def generate_interaction(self, current_state: Dict[str, str], interaction_history: List[str]) -> InteractionRequestSchema:
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
            Message(role="system", content=f"The interaction history is: {interaction_history}"),
            Message(role="user", content=generate_interaction_prompt)
        ]
        response = call_ollama_chat(self.llm_server_url, self.llm_model, messages, json_schema=InteractionRequestSchema.model_json_schema())
        response = InteractionRequestSchema.model_validate_json(response)
        return response


if __name__ == "__main__":

    db_path = "toaster_db.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    
    output_dir = "toaster_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # delete all files in the output directory
    for file in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, file))

    prompts = [
        "a simple espesso machine",
        "a porche 911",
        "a robot butler",
        "a monet painting",
        "a simple desk lamp",
        "a simple desk lamp that can also be used as a speaker",
        "a toaster",
        "an orb of warding",
        
        # Kitchen appliances
        "a retro blender",
        "a smart refrigerator",
        "a copper kettle",
        "a pasta maker",
        "a waffle iron shaped like a dinosaur",
        "a sous vide machine",
        "a rice cooker with 20 settings",
        "a bread box that keeps bread fresh for weeks",
        "a molecular gastronomy kit",
        "an instant pot with AI capabilities",
        
        # Technology
        "a holographic smartphone",
        "a laptop that never needs charging",
        "a drone that follows you",
        "a virtual reality headset",
        "a smart watch that monitors all vital signs",
        "a tablet that can fold like paper",
        "a wireless charging station shaped like a bonsai tree",
        "a pair of noise-cancelling earbuds",
        "a smart thermostat",
        "a rollable TV screen",
        
        # Furniture
        "a bookshelf that rotates to reveal a secret room",
        "a coffee table with built-in garden",
        "a recliner that massages and heats",
        "a bed that gently rocks you to sleep",
        "a chair that adjusts to your posture",
        "a desk with integrated computer",
        "a modular sofa that can form any shape",
        "a hammock that doesn't flip over",
        "a self-cleaning litter box disguised as an end table",
        "a dining table that expands for guests",
        
        # Transportation
        "a flying car",
        "a hoverboard that actually hovers",
        "a bicycle with electric assist",
        "a teleportation pod",
        "a personal submarine",
        "a jetpack with safety features",
        "a self-driving motorcycle",
        "a solar-powered yacht",
        "a pair of rocket boots",
        "a skateboard with AI balance assist",
        
        # Art and decor
        "a sculpture that changes with temperature",
        "a framed digital art display",
        "a vase that keeps flowers alive for months",
        "a constellation projector",
        "a stained glass window that generates power",
        "a rug that cleans itself",
        "an indoor waterfall",
        "a levitating plant pot",
        "a wall clock that shows different time zones",
        "a terrarium with its own ecosystem",
        
        # Magical/fantasy items
        "a crystal ball that answers yes or no questions",
        "a wand that translates languages",
        "a cloak of invisibility",
        "a potion brewing station",
        "a magic mirror that gives compliments",
        "a book that writes your dreams",
        "a bag of holding",
        "a door to another dimension",
        "a phoenix feather quill",
        "a cauldron that stirs itself",
        
        # Gaming items
        "a gaming PC with liquid cooling",
        "a console that plays every game ever made",
        "a deck of cards that never repeats the same hand",
        "a chess set with pieces that move on voice command",
        "a board game that creates new rules each time",
        "a pinball machine with holographic elements",
        "a D&D dice set that always rolls critical hits",
        "a gaming chair with haptic feedback",
        "a virtual tabletop system",
        "an arcade cabinet with 1000 classic games",
        
        # Gadgets with multiple functions
        "a pen that records and transcribes audio",
        "a flashlight that doubles as a phone charger",
        "a wallet with fingerprint security and GPS tracking",
        "a water bottle that purifies and adds flavors",
        "a mirror that also functions as a computer",
        "a belt with built-in tools",
        "a backpack with solar panels and massage features",
        "an umbrella that predicts the weather",
        "a knife that measures food nutrition",
        "a pair of glasses that translate text in real-time",
        
        # Robots and AI
        "a houseplant-tending robot",
        "a robotic pet that never needs feeding",
        "an AI writing assistant",
        "a robotic chef that knows 10,000 recipes",
        "a personal drone bodyguard",
        "a robot therapist",
        "an AI art mentor",
        "a swimming pool cleaning robot",
        "a robotic bartender",
        "an AI dungeon master",
        
        # Vehicles and transport
        "a steampunk airship",
        "a submarine car",
        "an amphibious RV",
        "a hot air balloon with luxury cabin",
        "a bicycle that transforms into a boat",
        "a solar-powered glider",
        "a walking house on mechanical legs",
        "a sled that works on any surface",
        "a miniature train that runs through your house",
        "a personal rapid transit pod",
        
        # Unusual combinations
        "a bookshelf that's also an aquarium",
        "a guitar that can also brew coffee",
        "a pillow with built-in speakers and cooling system",
        "a plant pot that's also a bluetooth speaker",
        "a shower head that plays music and light shows",
        "a doorbell that also orders pizza",
        "a trash can that composts and grows herbs",
        "a ceiling fan with integrated air purifier",
        "a couch that transforms into exercise equipment",
        "a window that generates electricity and grows food",
        
        # Sci-fi concepts
        "a matter replicator",
        "a time machine disguised as a grandfather clock",
        "a personal force field generator",
        "a gravity manipulation device",
        "a neural interface headband",
        "a consciousness transfer machine",
        "a portable wormhole generator",
        "a universal translator microphone",
        "a memory recording device",
        "a holodeck room installation",
        
        # Home improvement
        "a paint that changes color with mood",
        "a window that tints automatically",
        "a self-mowing lawn maintenance system",
        "a door that recognizes family members",
        "a shower that recycles water",
        "a roof that collects rainwater for household use",
        "a floor that generates electricity from footsteps",
        "a closet that organizes clothes automatically",
        "a garage that charges electric vehicles wirelessly",
        "a smart mailbox that scans and digitizes mail",
        
        # Wearable tech
        "a jacket with 50 pockets and climate control",
        "a hat that translates thoughts to text",
        "shoes that adjust their grip to any surface",
        "a scarf that filters air pollution",
        "gloves that teach piano by guiding fingers",
        "a tie with hidden video camera",
        "a belt that monitors nutrition and digestion",
        "earrings that function as emergency beacons",
        "a ring that controls smart home devices",
        "a necklace that projects holographic displays",
        
        # Health and wellness
        "a meditation pod with stress-reducing technology",
        "a sleep optimization system",
        "a personal air quality bubble",
        "a hydration reminder water bottle",
        "a posture-correcting chair insert",
        "a light therapy mask for skin and mood",
        "a portable sauna suit",
        "a mindfulness training headband",
        "a biorhythm-synchronizing alarm clock",
        "a full-body diagnostic scanner",
        
        # Musical instruments
        "a piano that teaches as you play",
        "a guitar with auto-tuning strings",
        "a drumset that fits in a pocket",
        "a synthesizer that reads brainwaves",
        "a violin made of light",
        "a flute that can sound like any instrument",
        "a harp that plays with the wind",
        "a theremin with visual effects",
        "a musical instrument for plants",
        "a voice-activated orchestra conductor baton",
        
        # Bizarre and unique
        "a cloud in a bottle",
        "a device that translates animal sounds",
        "a machine that makes everything taste like chocolate",
        "a sphere that is always at the exact center of the room",
        "a lamp powered by dreams",
        "a doorway to yesterday",
        "a box that contains a smaller version of itself",
        "a device that makes plants grow in patterns",
        "a bubble maker that produces bubbles that never pop",
        "a kaleidoscope that shows possible futures"
    ]
    
    manager = SentientToasterManager("http://localhost:5000", "llama3.1:8b", db_path)
    

    for prompt in prompts:

        # generate template and instance
        print(f"Generating template for {prompt}")
        template = manager.generate_template(prompt, "test_user")
        print(f"Generated template: {template.name}")
        print(f"Generating instance for {prompt}")
        instance = manager.generate_instance(template.id, "create an instance of this item", "test_user")
        print(f"Generated instance: {instance.id}")

        print("~"*100)
        print(f"Generating interactions for {prompt}")
        for i in range(5):
            
            
            interaction_generator = InteractionGenerator(manager.llm_server_url, manager.llm_model, template.template_obj)
            interaction_request = interaction_generator.generate_interaction(instance.state, instance.interaction_history)

            # interact with the instance
            print(f"-- {interaction_request.interaction.name}")
            print(f"    Current state: {instance.state}")
            print(f"    Inputs: {interaction_request.inputs}")
            interaction = manager.interact(instance.id, interaction_request, "test_user")
            print(f"    Interaction result: {interaction.description}")
            for output in interaction.outputs:
                # parse into InteractionIOSchema
                parsed_output = InteractionIOSchema.model_validate_json(output.model_dump_json())
                print(f"    Output: {parsed_output.name_and_amount} ({parsed_output.type})")
            print(f"    Updated state: {instance.state}")
        print("~"*100)
