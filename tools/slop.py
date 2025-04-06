import requests
from libs.agent_interface import AgentInterface
from libs.common import ToolsetDetails, ToolSchema, ToolCall, ToolCallResult
from libs.agent import AgentStateDBO
from typing import Optional, Dict, List

class SLOP(AgentInterface):
    def __init__(self, init_keys: Optional[Dict[str, str]] = None):
        
        # init key should contain the server url
        if "server_url" in init_keys:
            self.server_url = init_keys["server_url"]
        else:
            raise ValueError("server_url is required")
        
        # init key could contain expose
        if "expose" in init_keys:
            self.expose = init_keys["expose"]
        else:
            self.expose = []

        # init key should contain the server name, which will be used for the toolset id
        if "server_name" in init_keys:
            self.server_name = init_keys["server_name"]
        else:
            raise ValueError("server_name is required")
        
        # init key may contain description
        if "description" in init_keys:
            self.description = init_keys["description"]
        else:
            self.description = "A tool for slopping"
        
        # call server url/tools to get the toolset details
        response = requests.get(f"{self.server_url}/tools")
        
        print(response.json())

        # iterate over the tools and create a ToolSchema for each one
        self.tool_schemas = []
        for tool in response.json()["tools"]:
            if tool["id"] in self.expose:
                expose_to_agent = True
            else:
                expose_to_agent = False

            self.tool_schemas.append(ToolSchema(
                toolset_id=self.server_name,
                name=tool["id"], 
                description=tool["description"], 
                is_long_running=False, 
                expose_to_agent=expose_to_agent, 
                arguments=tool["arguments"]
            ))

    def get_toolset_details(self) -> ToolsetDetails:
        return ToolsetDetails(toolset_id=self.server_name, name=self.server_name, description=self.description)

    def get_tool_schemas(self) -> List[ToolSchema]:
        return self.tool_schemas

    def agent_tool_callback(self, agent_state: AgentStateDBO, tool_call: ToolCall) -> ToolCallResult:
        # call self.server_url/tools/{tool_call.name} with the tool_call.arguments as the body
        if tool_call.name in self.expose:
            response = requests.post(f"{self.server_url}/tools/{tool_call.name}", json=tool_call.arguments)
            response_json = response.json()

            print("~~~~~~~~~~~~~ tool call result")
            print(response_json)
            print("~~~~~~~~~~~~~")

            if "result" in response_json:
                    return ToolCallResult(toolset_id=self.server_name, tool_call=tool_call, result=str(response_json["result"]))
            elif "error" in response_json:
                return ToolCallResult(toolset_id=self.server_name, tool_call=tool_call, result=str(response_json["error"]))
            else:
                return ToolCallResult(toolset_id=self.server_name, tool_call=tool_call, result=str(response_json))
        else:
            return ToolCallResult(toolset_id=self.server_name, tool_call=tool_call, result="Tool not exposed")