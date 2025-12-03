# How the Flavor Agent Resolves Queries

This document explains the complete flow of how the Flavor Agent (Farm Agent) processes and resolves queries.

## Overview

The Flavor Agent uses a **LangGraph-based workflow** with an **LLM (Large Language Model)** to generate coffee flavor profiles. The agent extracts location and season information from natural language queries and generates descriptive flavor profiles.

---

## Complete Query Resolution Flow

### 1. **Request Reception** (`agent_executor.py`)

**Entry Point:** `FarmAgentExecutor.execute()`

```python
async def execute(self, context: RequestContext, event_queue: EventQueue):
    # Step 1: Validate the incoming A2A request
    validation_error = self._validate_request(context)
    if validation_error:
        event_queue.enqueue_event(validation_error)
        return
    
    # Step 2: Extract the user prompt from the A2A message
    prompt = context.get_user_input()
    
    # Step 3: Create a task if one doesn't exist
    task = context.current_task
    if not task:
        task = new_task(context.message)
        event_queue.enqueue_event(task)
```

**What happens:**
- Receives A2A protocol request via `RequestContext`
- Validates that the request has valid message parts
- Extracts the text prompt from the A2A message
- Creates a task to track the request

---

### 2. **Agent Invocation** (`agent_executor.py` → `agent.py`)

**Transition:** `FarmAgentExecutor` → `FarmAgent.ainvoke()`

```python
# In agent_executor.py
output = await self.agent.ainvoke(prompt)

# In agent.py
async def ainvoke(self, input: str) -> dict:
    return await self._agent.ainvoke({"prompt": input})
```

**What happens:**
- The executor calls `FarmAgent.ainvoke()` with the extracted prompt
- The agent wraps the prompt in a state dictionary: `{"prompt": input}`
- The LangGraph workflow is invoked with this state

---

### 3. **LangGraph Workflow** (`agent.py`)

**Graph Structure:**
```
START → FlavorNode → END
```

**Graph Definition:**
```python
def build_graph(self) -> StateGraph:
    graph_builder = StateGraph(State)
    graph_builder.add_node(self.FLAVOR_NODE, self.flavor_node)
    graph_builder.add_edge(START, self.FLAVOR_NODE)
    graph_builder.add_edge(self.FLAVOR_NODE, END)
    return graph_builder.compile()
```

**State Schema:**
```python
class State(TypedDict):
    prompt: str           # User input query
    error_type: str       # Error classification (if any)
    error_message: str    # Error description (if any)
    flavor_notes: str     # Generated flavor profile
```

**What happens:**
- LangGraph receives state with `{"prompt": "user query"}`
- Routes to `FlavorNode` (the only processing node)
- Executes `flavor_node()` method

---

### 4. **Flavor Node Processing** (`agent.py` - `flavor_node()`)

**Core Resolution Logic:**

```python
async def flavor_node(self, state: State):
    # Step 1: Extract prompt from state
    user_prompt = state.get("prompt")
    
    # Step 2: Define system prompt for LLM
    system_prompt = (
        "You are a coffee farming expert and flavor profile connoisseur.\n"
        "The user will describe a question or scenario related to a coffee farm. "
        "Your job is to:\n"
        "1. Extract the `location` and `season` from the input if possible.\n"
        "2. Based on those, describe the expected **flavor profile** of the coffee grown there.\n"
        "3. Respond with only a brief, expressive flavor profile (1–3 sentences). "
        "Use tasting terminology like acidity, body, aroma, and finish.\n"
        "Respond with an empty response if no valid location or season is found. "
        "Do not include quotes or any placeholder."
    )
    
    # Step 3: Construct messages for LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Step 4: Invoke LLM
    response = get_llm().invoke(messages)
    flavor_notes = response.content
    
    # Step 5: Validate response
    if not flavor_notes.strip():
        return {
            "error_type": "invalid_input",
            "error_message": "Could not confidently extract coffee farm context from user prompt."
        }
    
    # Step 6: Return flavor profile
    return {"flavor_notes": flavor_notes}
```

**Key Steps:**

1. **Prompt Extraction:** Gets the user's query from the state
2. **System Prompt:** Defines the LLM's role and instructions:
   - Extract location and season
   - Generate flavor profile using tasting terminology
   - Return empty if context is insufficient
3. **LLM Invocation:** Sends system + user messages to the LLM
4. **Response Validation:** Checks if LLM returned valid content
5. **Error Handling:** Returns error if no valid flavor profile generated
6. **Success Response:** Returns flavor notes in state

---

### 5. **LLM Provider** (`common/llm.py`)

**LLM Factory:**
```python
def get_llm():
    factory = LLMFactory(provider=LLM_PROVIDER)
    return factory.get_llm()
```

**What happens:**
- Uses Cisco Outshift's `LLMFactory` to get the configured LLM
- LLM provider is determined by `LLM_PROVIDER` environment variable
- Supports multiple providers (OpenAI, Azure OpenAI, etc.)
- The LLM processes the system + user messages and generates the flavor profile

---

### 6. **Response Handling** (`agent_executor.py`)

**After Agent Returns:**

```python
output = await self.agent.ainvoke(prompt)

# Check for errors
if output.get("error_message") is not None and output.get("error_message") != "":
    message = new_agent_text_message(
        output.get("error_message", "Failed to generate flavor profile"),
    )
    event_queue.enqueue_event(message)
    return

# Success case
flavor = output.get("flavor_notes", "No flavor profile returned")
event_queue.enqueue_event(new_agent_text_message(flavor))
```

**What happens:**
- Executor receives the agent's output dictionary
- Checks for error messages
- If error: sends error message via event queue
- If success: extracts `flavor_notes` and sends via event queue
- Event queue publishes the response back through A2A protocol

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. A2A Request Received                                     │
│    (RequestContext with message containing user query)       │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. FarmAgentExecutor.execute()                             │
│    - Validates request                                      │
│    - Extracts prompt: context.get_user_input()             │
│    - Creates task                                           │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. FarmAgent.ainvoke(prompt)                               │
│    - Wraps prompt in state: {"prompt": input}              │
│    - Invokes LangGraph workflow                            │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LangGraph Workflow                                      │
│    START → FlavorNode → END                                │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. flavor_node(state)                                      │
│    - Extracts user_prompt from state                       │
│    - Constructs system prompt (instructions for LLM)       │
│    - Creates messages: [SystemMessage, HumanMessage]       │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. LLM Invocation                                           │
│    get_llm().invoke(messages)                               │
│    - LLMFactory.get_llm() (based on LLM_PROVIDER)          │
│    - LLM processes: extract location/season → generate     │
│      flavor profile                                         │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Response Processing                                     │
│    - If empty response → return error                      │
│    - If valid response → return {"flavor_notes": ...}     │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Executor Handles Output                                 │
│    - Checks for errors                                      │
│    - Extracts flavor_notes                                  │
│    - Publishes via event_queue                              │
└────────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. A2A Response Sent                                       │
│    (Flavor profile returned to requesting agent)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Components

### **1. System Prompt Strategy**

The agent uses a **specialized system prompt** that instructs the LLM to:
- **Extract** location and season from natural language
- **Generate** flavor profiles using coffee tasting terminology
- **Validate** that sufficient context exists
- **Format** response as 1-3 sentences

**Example System Prompt:**
```
"You are a coffee farming expert and flavor profile connoisseur.
The user will describe a question or scenario related to a coffee farm.
Your job is to:
1. Extract the `location` and `season` from the input if possible.
2. Based on those, describe the expected **flavor profile** of the coffee grown there.
3. Respond with only a brief, expressive flavor profile (1–3 sentences).
Use tasting terminology like acidity, body, aroma, and finish.
Respond with an empty response if no valid location or season is found."
```

### **2. Error Handling**

The agent has two levels of error handling:

**Level 1: LLM Validation**
- If LLM returns empty response → indicates insufficient context
- Returns error state: `{"error_type": "invalid_input", "error_message": "..."}`

**Level 2: Executor Validation**
- Checks for error_message in output
- Publishes error message via event queue if found

### **3. State Management**

Uses LangGraph's state management:
- **Input State:** `{"prompt": "user query"}`
- **Output State:** Either:
  - Success: `{"flavor_notes": "generated profile"}`
  - Error: `{"error_type": "...", "error_message": "..."}`

---

## Example Query Resolution

### **Input Query:**
```
"What are the flavor notes of Colombian coffee in winter?"
```

### **Processing Steps:**

1. **A2A Request** → Extracted prompt: `"What are the flavor notes of Colombian coffee in winter?"`

2. **LangGraph State:** `{"prompt": "What are the flavor notes of Colombian coffee in winter?"}`

3. **System Prompt + User Prompt** sent to LLM:
   ```
   System: "You are a coffee farming expert... Extract location and season..."
   User: "What are the flavor notes of Colombian coffee in winter?"
   ```

4. **LLM Processing:**
   - Extracts: location="Colombian" (or "Colombia"), season="winter"
   - Generates flavor profile based on coffee knowledge
   - Returns: `"Colombian coffee in winter typically exhibits bright acidity with notes of citrus and apple, a medium body, and a clean finish with hints of caramel."`

5. **State Update:** `{"flavor_notes": "Colombian coffee in winter typically exhibits..."}`

6. **Response:** Flavor notes published via A2A event queue

---

## Key Design Decisions

1. **Single-Node Graph:** Simple linear flow (START → FlavorNode → END)
   - No complex routing needed
   - All processing happens in one node

2. **LLM-Based Resolution:** Uses LLM for both extraction and generation
   - No structured parsing required
   - Handles natural language variations
   - Leverages LLM's coffee knowledge

3. **System Prompt Engineering:** Detailed instructions guide LLM behavior
   - Specifies extraction requirements
   - Defines output format
   - Handles edge cases (empty responses)

4. **Error Handling:** Graceful degradation
   - Returns helpful error messages
   - Validates LLM output
   - Prevents empty or invalid responses

---

## Configuration

The agent's behavior is controlled by:

- **LLM_PROVIDER:** Determines which LLM to use (OpenAI, Azure, etc.)
- **System Prompt:** Defines the LLM's role and instructions
- **State Schema:** Defines the data structure for the workflow

---

## Summary

The Flavor Agent resolves queries through a **LangGraph workflow** that:
1. Receives A2A requests via `FarmAgentExecutor`
2. Routes to a single `FlavorNode` in the graph
3. Uses an **LLM with a specialized system prompt** to:
   - Extract location and season from natural language
   - Generate coffee flavor profiles
4. Validates and returns results through the A2A event queue

The agent is **stateless** (no memory between requests) and **deterministic** (same input → same processing flow, though LLM output may vary).

