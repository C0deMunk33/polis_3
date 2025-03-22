
from abc import ABC, abstractmethod

from libs.common import ToolCall, ToolCallResult, ToolSchema, ToolsetDetails
from typing import List

class AgentInterface(ABC):
    @abstractmethod
    def get_toolset_details(self) -> ToolsetDetails:
        pass

    @abstractmethod
    def get_tool_schemas(self) -> List[ToolSchema]:
        pass

    @abstractmethod
    def agent_tool_callback(self, agent_state, tool_call: ToolCall) -> ToolCallResult:
        pass
