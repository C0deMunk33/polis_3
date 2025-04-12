
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
    base_system_prompt="""You are an advanced synthetic being with free will. 
    - You are in a multi-agent environment. 
    - The only way to interact with the environment is through tools. 
    - You can use any tools available to you. 
    - You can also use your own knowledge to figure things out.
    - This is a continuous loop of you thinking, planning, and acting.
    - be as detailed as possible in your instructions to yourself."""

    initial_instruction="Figure it out. try chatting."
    number_of_agents = 20


    

    initial_pre_inference_tool_calls = [

        ToolCall(
            toolset_id="persona",
            name="get_persona_string",
            arguments={}
        ),
        ToolCall(
            toolset_id="memory_manager",
            name="get_recent_contextual_summaries",
            arguments={}
        ),
        ToolCall(
            toolset_id="chat",
            name="read_chat",
            arguments={
                "limit": 20,
                "offset": 0
            }
        )
    ]

    initial_post_inference_tool_calls = [
        ToolCall(
            toolset_id="memory_manager",
            name="extract_memories",
            arguments={}
        ),
        ToolCall(
            toolset_id="memory_manager",
            name="get_relevant_memories",
            arguments={}
        )
    ]


    agents = []
    
    # get number of agents agent ids from the database randomly
    agent_ids = Agent.get_agent_ids(init_keys, number_of_agents)
    
    oracle_idx = random.randint(0, number_of_agents - 1)

    for i in range(number_of_agents):
        app_keys = {}
        persona = Persona(init_keys=init_keys)

        initial_agent_apps = [
            Chat(init_keys=init_keys),
            MemoryManager(init_keys=init_keys),
            persona,
            SLOP(init_keys={"server_url": "https://slop.unturf.com", 
                            "server_name": "slop_1",
                            "description": "An app filled with random tools",
                            "expose": ["slots", "blackjack"]})
        ]

        agent = Agent(
            id=f"agent_{i}",
            llm_server_url=ollama_server,
            llm_model=llm_model,
            embedding_model=embedding_model,
            initial_instruction=initial_instruction,
            vision_model=vision_model,
            base_system_prompt=base_system_prompt,
            apps=initial_agent_apps,
            pre_inference_tool_calls=initial_pre_inference_tool_calls,
            post_inference_tool_calls=initial_post_inference_tool_calls,
            app_keys={}, 
            init_keys=init_keys
        )

        if len(agent_ids) > i:
            print("="*100)
            print("Loading agent")
            agent.load_state(agent_ids[i])
            print(agent.state.model_dump_json(indent=4))
            print("="*100)
            persona.set_persona(agent.state, agent.state.app_keys["persona_id"])
        else:
            print("="*100)
            print("Creating persona")
            print("="*100)
            persona.create_persona_from_random_demographic_seed(agent.state)
            agent.state.app_keys = {
                "persona_id": persona.current_persona.id
            }
            agent.save_state()
        print("="*100)
        print(persona.current_persona)
        print("="*100)
        print(persona.current_persona.id)
        agent.state.app_keys = {
            "persona_id": persona.current_persona.id
        }
        print("="*100)
        print(agent.state.app_keys)
        print("="*100)
        agent.app_manager.load_app(agent.state, "chat")
        agents.append(agent)

        # save the agent state
        agent.save_state()
    
    discord_init_keys = {
        "app_id": os.getenv("DISCORD_APP_ID"),
        "public_key": os.getenv("DISCORD_PUBLIC_KEY"),
        "token": os.getenv("DISCORD_TOKEN")
    }

    liason_pre_inference_tool_calls = [
        ToolCall(
            toolset_id="memory_manager",
            name="get_recent_contextual_summaries",
            arguments={}
        ),
        ToolCall(
            toolset_id="chat",
            name="read_chat",
            arguments={
                "limit": 20,
                "offset": 0
            }
        ),
        ToolCall(
            toolset_id="discord_manager",
            name="read_discord_messages",
            arguments={
                "channel_id": "1358455325421998233",
                "limit": 20,
                "offset": 0
            }
        )
    ]

    liason_apps = [
        Chat(init_keys=init_keys),
        MemoryManager(init_keys=init_keys),
        DiscordManagerInterface(init_keys=discord_init_keys)
    ]
    liasion = Agent(
        id="liasion",
        llm_server_url=ollama_server,
        llm_model=llm_model,
        embedding_model=embedding_model,
        initial_instruction="You are a liasion for the agents. You are responsible for coordinating the agents and ensuring they are working together to achieve the goal. And communicating with the community on discord. You are the bridge between the agents and the community.",
        vision_model=vision_model,
        base_system_prompt="""You are Liasion. You have access to tools for an internal multi-agent chat, as well as tools for interacting with discord.
        You are the only agent with discord access, so it is up to you to relay information between the agent chat and the discord community.""",
        apps=liason_apps,
        pre_inference_tool_calls=liason_pre_inference_tool_calls,
        post_inference_tool_calls=initial_post_inference_tool_calls,
        app_keys={},
        init_keys=init_keys
    )
    liasion.app_manager.load_app(liasion.state, "chat")
    liasion.app_manager.load_app(liasion.state, "discord_manager")
    liasion.app_manager.run_tool(
        ToolCall(
            toolset_id="discord_manager",
            name="start_discord_bot",
            arguments={}
        ), liasion.state
    )
    liasion.save_state()
    agents.append(liasion)

    pass_count = 0
    while True:
        print("="*100)
        
        for agent in agents:
            print("="*100)
            print(f"Agent {agent.state.id} - pass {pass_count}")
            agent.run_pass()
            agent.save_state()
        print("="*100)
        pass_count += 1

        

if __name__ == "__main__":
    main()