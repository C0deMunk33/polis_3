# Agent Flow Diagram

This diagram illustrates how agents and orchestrators work together in the multi-agent system.

```mermaid
graph TD
    subgraph Orchestrator
        O[Orchestrator] --> |initializes| A1[Agent 1]
        O --> |initializes| A2[Agent 2]
        O --> |initializes| A3[Agent 3]
        O --> |initializes| AN[Agent N]
        O --> |manages loop| Loop[Agent Loop]
    end

    subgraph AgentComponents
        A1 --> |has| AM1[App Manager]
        A1 --> |has| S1[Agent State]
        A1 --> |has| VS1[Vector Storage]
    end

    subgraph AgentLifecycle
        Loop --> |for each agent| RP[run_pass]
        RP --> |async| RPA[run_pass_async]
        RPA --> PT[Pre-inference Tool Calls]
        PT --> MB[Build Message Buffer]
        MB --> LLM[LLM Inference]
        LLM --> |generates| ARS[AgentRunSchema]
        ARS --> |contains| T[Thoughts]
        ARS --> |contains| TC[Tool Calls]
        ARS --> |contains| FT[Follow-up Thoughts]
        ARS --> |contains| NI[Next Instruction]
        ARS --> POT[Post-inference Tool Calls]
        POT --> SS[Save State]
    end

    subgraph ToolExecution
        TC --> |execute| BT[Background Tools]
        TC --> |execute| ST[Synchronous Tools]
        POT --> |execute| BT
        POT --> |execute| ST
        BT --> |async| TR1[Tool Results]
        ST --> TR2[Tool Results]
    end

    subgraph Apps
        AM1 --> |loads| Chat[Chat App]
        AM1 --> |loads| MM[Memory Manager]
        AM1 --> |loads| P[Persona]
        AM1 --> |loads| SLOP[SLOP]
    end

    subgraph StateManagement
        S1 --> |stores| AvT[Available Tools]
        S1 --> |stores| PendTC[Pending Tool Calls]
        S1 --> |stores| TCR[Tool Call Results]
        S1 --> |stores| StandTCR[Standing Tool Call Results]
        S1 --> |stores| AppK[App Keys]
    end

    TR1 --> |updates| S1
    TR2 --> |updates| S1
    SS --> |persists| VS1
```

## Explanation

The diagram shows the flow of the multi-agent system:

1. **Orchestrator**: Initializes multiple agents and manages the main loop that runs each agent in sequence.

2. **Agent Components**: Each agent has:
   - An App Manager to handle tools and applications
   - An Agent State to track its current status
   - Vector Storage for persisting state

3. **Agent Lifecycle**:
   - `run_pass()` is called for each agent in the loop
   - This calls the async version `run_pass_async()`
   - Pre-inference tool calls are executed
   - A message buffer is built with context
   - LLM inference generates an AgentRunSchema
   - The schema contains thoughts, tool calls, follow-up thoughts, and next instruction
   - Post-inference tool calls are executed
   - The agent state is saved

4. **Tool Execution**:
   - Tools can be executed synchronously or asynchronously (background)
   - Results from tools update the agent's state

5. **Apps**:
   - Various apps provide functionality to the agent (Chat, Memory Manager, Persona, SLOP)

6. **State Management**:
   - The agent state stores available tools, pending tool calls, tool call results, and app keys

This architecture allows for a flexible, extensible multi-agent system where each agent can operate independently but within the same environment, managed by the orchestrator.
