from tools.slop import SLOP
from libs.common import ToolCall
slop = SLOP(init_keys={"server_url": "https://slop.unturf.com", "server_name": "slop_1"})

print(slop.get_toolset_details())

for tool in slop.get_tool_schemas():
    print("~"*100)
    print(tool)
    print("~"*100)

print(slop.agent_tool_callback(
    ToolCall(toolset_id="slop_1", name="calculator", arguments={
        "expression": "1 + 1"        
    })))

print("~"*100)
print(slop.agent_tool_callback(
    ToolCall(toolset_id="slop_1", name="greet", arguments={
        "name": "John"        
    })))