from libs.common import ToolSchema, ToolCall, ToolsetDetails, get_tool_schemas_from_class, ToolCallResult
from libs.agent_interface import AgentInterface
from typing import List
import traceback
class AppManager:
    def __init__(self):
        self.apps = {}
        self.schemas = {}
        self.loaded_app_ids = [] # these are the tools that are currently available to the agent, app manager is always loaded
        self.exposed_tools = get_tool_schemas_from_class(self)        

        self.add_app(self)
        self.load_app(None, "app_manager")

    def add_app(self, agent_tool: AgentInterface):
        
        toolset_details = agent_tool.get_toolset_details()
        tool_schemas = agent_tool.get_tool_schemas()
        print(f"Adding app {toolset_details.toolset_id}")
        print(f"Tool schemas: {tool_schemas}")
        self.apps[toolset_details.toolset_id] = agent_tool
        self.schemas[toolset_details.toolset_id] = tool_schemas
    def remove_app(self, app_id: str):
        self.apps.pop(app_id)
        self.schemas.pop(app_id)

    def list_apps(self):
        result = "Available apps:\n"
        # sort apps by loaded status
        loaded_apps = []
        unloaded_apps = []
        for toolset_id in self.apps:
            app = self.apps[toolset_id]
            toolset_details = app.get_toolset_details()
            # get count of tools where expose_to_agent is true
            tool_count = len([tool for tool in app.get_tool_schemas() if tool.expose_to_agent])
            if tool_count == 0:
                continue
            if toolset_id in self.loaded_app_ids:
                loaded_apps.append(toolset_details)
            else:
                unloaded_apps.append(toolset_details)
        loaded_apps.sort(key=lambda x: x.name)
        unloaded_apps.sort(key=lambda x: x.name)
        for app in loaded_apps:
            result += f"    [loaded] {app.toolset_id} - {app.name} - {app.description} - {tool_count} tools\n"
        for app in unloaded_apps:
            result += f"    [unloaded] {app.toolset_id} - {app.name} - {app.description} - {tool_count} tools\n"

        """
        result += "\nApp Manager Tools:\n"
        for tool_schema in self.exposed_tools:
            if tool_schema.expose_to_agent:
                result += f"  (toolset_id: {tool_schema.toolset_id}) {tool_schema.name}({",".join([arg['name'] for arg in tool_schema.arguments])}) - description: {tool_schema.description}\n"
        """

        return result
    
    def load_app(self, agent_state, toolset_id: str):
        """
        {
            "toolset_id": "app_manager",
            "name": "load_app",
            "description": "loads an app, this makes their tools available to you to call.",
            "is_long_running": false,
            "expose_to_agent": true,
            "arguments": [{
                "name": "toolset_id",
                "type": "string",
                "description": "the toolset_id of the app to load"
            }]
        }
        """
        print(f"Loading app {toolset_id}")
        if toolset_id not in self.apps:
            return f"App {toolset_id} not found"
        
        app = self.apps[toolset_id]
        details = app.get_toolset_details()
        if details.toolset_id not in self.loaded_app_ids:
            self.loaded_app_ids.append(details.toolset_id)
        result = f"Loaded app {details.toolset_id} - {details.name}\n{self.get_app_tool_list(details.toolset_id)}"
        return result

    def unload_app(self, agent_state, toolset_id: str):
        """
        {
            "toolset_id": "app_manager",
            "name": "unload_app",
            "description": "unloads an app. do this to free up memory and resources.",
            "is_long_running": false,
            "expose_to_agent": true,
            "arguments": [{
                "name": "toolset_id",
                "type": "string",
                "description": "the toolset_id of the app to unload"
            }]
        }
        """
        # cannot unload the app manager
        if toolset_id == "app_manager":
            return "Cannot unload the app manager"
        if toolset_id not in self.loaded_app_ids:
            return f"App {toolset_id} is not loaded"
        self.loaded_app_ids.remove(toolset_id)
        return f"Unloaded app {toolset_id}"

    def get_app_tool_list(self, toolset_id: str):
        result = "Available Tools:\n"
        # schemas where expose_to_agent is true
        for tool_schema in self.schemas[toolset_id]:
            if tool_schema.expose_to_agent:
                result += f"        toolset_id='{tool_schema.toolset_id}' name='{tool_schema.name}' description='{tool_schema.description}' arguments='{tool_schema.arguments}'\n"
        
        return result

    def get_available_tools(self):
        tool_schemas = []
        for app_id in self.loaded_app_ids:
            tool_schemas.extend(self.schemas[app_id])
        return tool_schemas

    def get_loaded_apps(self):
        result = "Available Tools:\n"
        result += "(note: these are the only tools available to you at this time)\n"
        for app_id in self.loaded_app_ids:
            result += f"    App (toolset_id={app_id}):\n"
            for tool_schema in self.schemas[app_id]:       
                if tool_schema.expose_to_agent:
                    result += f"        toolset_id='{tool_schema.toolset_id}' name='{tool_schema.name}' description='{tool_schema.description}' arguments='{tool_schema.arguments}'\n"
                
        #print(result)
        return result
    
    def run_tool(self, tool_call: ToolCall, agent_state):
        # run tool
        return self.apps[tool_call.toolset_id].agent_tool_callback(agent_state, tool_call)

    def get_all_tool_schemas(self):
        result = []

        for schema in self.schemas.values():
            result.extend(schema)

        return result

    
    ############### Agent Interface ###############
    def get_toolset_details(self):
        return ToolsetDetails(
            toolset_id="app_manager",
            name="App Manager",
            description="Manages apps. Tools available are from loaded apps. An app must be loaded to be used."
        )
    
    def get_tool_schemas(self):
        return self.exposed_tools
    
    def agent_tool_callback(self, agent_state, tool_call: ToolCall) -> ToolCallResult:
        # call the tool
        result = getattr(self, tool_call.name)(agent_state, **tool_call.arguments)
        return ToolCallResult(
            toolset_id="app_manager",
            tool_call=tool_call,
            result=result
        )
        