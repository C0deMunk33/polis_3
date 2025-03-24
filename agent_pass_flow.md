# Agent Pass Flow Diagram

This diagram illustrates the detailed flow of a single agent pass in the system.

```mermaid
graph TD
    subgraph AgentPass["Agent Pass (run_pass)"]
        RP[run_pass] --> |calls| RPA[run_pass_async]
        
        subgraph Initialization
            RPA --> |first step| AT[Load Available Tools]
            AT --> |updates| AS[Agent State]
        end
        
        subgraph PreInferencePhase["Pre-Inference Phase"]
            AT --> PITC[Execute Pre-Inference Tool Calls]
            PITC --> |for each tool| PTC[Process Tool Call]
            PTC --> |run tool| PTR[Get Tool Result]
            PTR --> |store in| STCR[Standing Tool Call Results]
        end
        
        subgraph MessageBufferBuilding["Message Buffer Building"]
            PITC --> |after all tools| BMB[Build Message Buffer]
            BMB --> |add| SP[System Prompt]
            SP --> |add| ATB[Available Tools]
            ATB --> |add| STCRB[Standing Tool Call Results]
            STCRB --> |add| TCRB[Tool Call Results]
            TCRB --> |add| PTCB[Pending Tool Calls]
            PTCB --> |add| NI[Next Instruction]
            NI --> |format with| ARS[AgentRunSchema Format]
        end
        
        subgraph InferencePhase["Inference Phase"]
            ARS --> |send to| LLM[LLM Inference]
            LLM --> |parse| ARSR[AgentRunSchema Response]
            ARSR --> |extract| TH[Thoughts]
            ARSR --> |extract| TC[Tool Calls]
            ARSR --> |extract| FT[Follow-up Thoughts]
            ARSR --> |extract| DNI[Detailed Next Instruction]
            DNI --> |update| NIS[Next Instruction State]
        end
        
        subgraph ToolExecutionPhase["Tool Execution Phase"]
            TC --> |for each tool| TCE[Execute Tool Call]
            TCE --> |check if| LR[Long Running?]
            LR --> |yes| BG[Create Background Task]
            LR --> |no| ST[Execute Synchronously]
            ST --> |store| TCR[Tool Call Results]
            BG --> |add to| BGT[Background Tasks]
            
            ARSR --> PITCE[Execute Post-Inference Tool Calls]
            PITCE --> |for each tool| PTCE[Process Tool Call]
            PTCE --> |check if| PLR[Long Running?]
            PLR --> |yes| PBG[Create Background Task]
            PLR --> |no| PST[Execute Synchronously]
            PST --> |store in| PSTCR[Standing Tool Call Results]
            PBG --> |add to| BGT
        end
        
        subgraph Finalization
            BGT --> |await all| ABGT[Await Background Tasks]
            ABGT --> |complete| SS[Save State]
            TCR --> SS
            PSTCR --> SS
            NIS --> SS
        end
    end
    
    subgraph ToolCallExecution["Tool Call Execution Detail"]
        RBGT[run_background_tool] --> |check if| APC[Already Pending?]
        APC --> |no| APT[Add to Pending Tools]
        APT --> |execute| RTE[Run Tool Execution]
        RTE --> |get| RTR[Tool Result]
        RTR --> |add to| RTCR[Tool Call Results]
        RTR --> |remove from| RPT[Pending Tool Calls]
    end
    
    subgraph StateManagement["State Management"]
        AS --> |stores| AST[Available Tools]
        AS --> |stores| ASPT[Pending Tool Calls]
        AS --> |stores| ASTCR[Tool Call Results]
        AS --> |stores| ASSTCR[Standing Tool Call Results]
        AS --> |stores| ASNI[Next Instruction]
    end
```

## Explanation

This diagram illustrates the detailed flow of a single agent pass, from initialization through tool execution and state management, preparing for the next pass in the agent's lifecycle.
