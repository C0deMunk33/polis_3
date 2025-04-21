import argparse
import json
from libs.agent import Agent
def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/standalone_agent_config.json")
    parsed_args = parser.parse_args()
    
    with open(parsed_args.config, "r") as f:
        config = json.load(f)
    return config

def main():
    # get config from command line
    config = get_config()
    print(config.get("base_system_prompt"))

    # create agent
    agent = Agent(
        id="liasion",
        llm_server_url=config.get("ollama_server"),
        llm_model=config.get("llm_model"),
        embedding_model=config.get("embedding_model"),
        initial_instruction=config.get("initial_instruction"),
        vision_model=config.get("vision_model"),
        base_system_prompt=config.get("base_system_prompt"),
        apps=[],
        pre_inference_tool_calls=config.get("pre_inference_tool_calls"),
        post_inference_tool_calls=config.get("post_inference_tool_calls"),
        app_keys={},
        init_keys=config
    )
    while True:
        agent.run_pass()
        agent.save_state()

if __name__ == "__main__":
    main()