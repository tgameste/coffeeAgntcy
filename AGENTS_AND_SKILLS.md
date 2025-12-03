# Agents and Skills in Coffee AGNTCY

This document identifies all agents in the codebase and explains how their skills are expressed.

## Overview

The codebase uses the **A2A (Agent-to-Agent) protocol** to define agents and their skills. Agents are defined using `AgentCard` objects that contain `AgentSkill` definitions. Skills are invoked via skill IDs in A2A message requests.

---

## Corto Demo Agents

### 1. **Farm Agent** (Coffee Farm Flavor Agent)

**Location:** `coffeeAGNTCY/coffee_agents/corto/farm/`

**Agent Card Definition:**
- **File:** `farm/card.py`
- **Agent ID:** `flavor-profile-farm-agent`
- **Agent Name:** `Coffee Farm Flavor Agent`
- **Description:** An AI agent that estimates the flavor profile of coffee beans using growing conditions like season and altitude.

**Skill Definition:**
```python
AGENT_SKILL = AgentSkill(
    id="estimate_flavor",
    name="Estimate Flavor Profile",
    description="Analyzes a natural language prompt and returns the expected flavor profile for a coffee-growing region and/or season.",
    tags=["coffee", "flavor", "farm"],
    examples=[
        "What flavors can I expect from coffee in Huila during harvest?",
        "Describe the taste of beans grown in Sidamo in the dry season",
        "How does Yirgacheffe coffee taste?"
    ]
)
```

**How the Skill is Expressed:**
1. **Skill ID:** `"estimate_flavor"` - This is the unique identifier used when invoking the skill via A2A
2. **Skill Metadata:** Name, description, tags, and examples provide context about what the skill does
3. **Implementation:** The skill is implemented in `farm/agent.py` via the `FarmAgent` class:
   - Uses a LangGraph workflow with a single `FlavorNode`
   - Takes a user prompt and extracts location/season information
   - Generates flavor profiles using an LLM with a specialized system prompt
4. **Execution:** The `FarmAgentExecutor` (in `farm/agent_executor.py`) handles A2A requests:
   - Validates incoming requests
   - Invokes the `FarmAgent.ainvoke()` method
   - Returns flavor notes or error messages via the event queue

**Skill Invocation:**
When invoked via A2A, the skill ID `"estimate_flavor"` is specified in the `SendMessageRequest`:
```python
request = SendMessageRequest(
    params=MessageSendParams(
        skill_id="estimate_flavor",  # <-- Skill ID used here
        sender_id="coffee-exchange-agent",
        receiver_id="flavor-profile-farm-agent",
        message=Message(...)
    )
)
```

---

### 2. **Exchange Agent** (Supervisor)

**Location:** `coffeeAGNTCY/coffee_agents/corto/exchange/`

**Agent Definition:**
- **File:** `exchange/graph/graph.py`
- **Agent Name:** `exchange_agent` (decorated with `@agent(name="exchange_agent")`)
- **Type:** Supervisor agent that routes queries to worker agents

**Structure:**
The Exchange Agent is a **supervisor agent** that:
1. Routes coffee flavor queries to the `get_flavor_profile_via_a2a` worker agent
2. Handles capability questions directly
3. Uses LangGraph's `create_supervisor` to manage worker agents

**Worker Agent:**
- **Name:** `get_flavor_profile_via_a2a`
- **Type:** React agent created with `create_react_agent`
- **Tool:** Uses `FlavorProfileTool` which wraps A2A communication to the Farm Agent

**How Skills are Expressed:**
The Exchange Agent doesn't define its own A2A skills. Instead:
1. It uses **tools** (specifically `FlavorProfileTool`) to communicate with the Farm Agent
2. The tool internally invokes the Farm Agent's `estimate_flavor` skill via A2A
3. The supervisor routes queries based on prompt content, not skill IDs

**Tool Implementation:**
- **File:** `exchange/graph/tools.py`
- **Class:** `FlavorProfileTool` (extends `BaseTool`)
- **Method:** `send_message()` - Creates A2A requests with `skill_id="estimate_flavor"`

---

## Lungo Demo Agents

The Lungo demo has multiple farm agents with different skills:

### 3. **Brazil Farm Agent**

**Location:** `coffeeAGNTCY/coffee_agents/lungo/farms/brazil/`

**Agent Card:**
- **Agent ID:** `brazil-farm-agent`
- **Agent Name:** `Brazil Coffee Farm`

**Skill:**
```python
AGENT_SKILL = AgentSkill(
    id="get_yield",
    name="Get Coffee Yield",
    description="Returns the coffee farm's yield in lb.",
    tags=["coffee", "farm"],
    examples=[
        "What is the yield of the Brazil coffee farm?",
        "How much coffee does the Brazil farm produce?",
        ...
    ]
)
```

### 4. **Colombia Farm Agent**

**Location:** `coffeeAGNTCY/coffee_agents/lungo/farms/colombia/`

**Agent Card:**
- **Agent ID:** `colombia-farm-agent`
- **Agent Name:** `Colombia Coffee Farm`
- **Skill ID:** `get_yield` (similar to Brazil)

### 5. **Vietnam Farm Agent**

**Location:** `coffeeAGNTCY/coffee_agents/lungo/farms/vietnam/`

**Agent Card:**
- **Agent ID:** `vietnam-farm-agent`
- **Agent Name:** `Vietnam Coffee Farm`
- **Skill ID:** `get_yield` (similar to Brazil)

---

## How Skills Are Expressed: Summary

### 1. **AgentCard Structure**
Each agent defines an `AgentCard` containing:
- Agent metadata (name, ID, description, URL)
- **Skills array** - List of `AgentSkill` objects
- Capabilities (streaming, input/output modes)

### 2. **AgentSkill Structure**
Each skill defines:
- **`id`** - Unique skill identifier (e.g., `"estimate_flavor"`, `"get_yield"`)
- **`name`** - Human-readable skill name
- **`description`** - What the skill does
- **`tags`** - Categorization tags
- **`examples`** - Example queries that trigger the skill

### 3. **Skill Invocation**
Skills are invoked via A2A protocol:
- **Client side:** Creates `SendMessageRequest` with `skill_id` parameter
- **Server side:** `AgentExecutor` receives the request and routes to the appropriate agent method
- The skill ID maps to the agent's internal implementation

### 4. **Implementation Pattern**
```
AgentCard (defines skill metadata)
    ↓
AgentExecutor (handles A2A requests, validates, routes)
    ↓
Agent Class (implements the actual skill logic)
    ↓
Returns result via event queue
```

### 5. **Key Files**
- **Agent Card:** `*/card.py` - Defines `AGENT_CARD` and `AGENT_SKILL`
- **Agent Logic:** `*/agent.py` - Implements the skill behavior
- **A2A Executor:** `*/agent_executor.py` - Handles A2A protocol requests
- **Server:** `*/farm_server.py` or `*/main.py` - Starts the A2A server

---

## Example: Complete Skill Flow

**1. Skill Definition (card.py):**
```python
AGENT_SKILL = AgentSkill(
    id="estimate_flavor",  # <-- This ID is used for invocation
    name="Estimate Flavor Profile",
    description="...",
    examples=["..."]
)
```

**2. Skill Invocation (tools.py):**
```python
request = SendMessageRequest(
    params=MessageSendParams(
        skill_id="estimate_flavor",  # <-- Matches the skill ID
        ...
    )
)
```

**3. Skill Execution (agent_executor.py):**
```python
# Receives request with skill_id="estimate_flavor"
# Routes to agent.ainvoke(prompt)
```

**4. Skill Implementation (agent.py):**
```python
# FarmAgent.flavor_node() processes the prompt
# Returns flavor profile
```

---

## Key Concepts

1. **Skill ID is the Bridge:** The skill ID connects the A2A protocol request to the agent's implementation
2. **AgentCard is the Contract:** Defines what skills an agent exposes and how to invoke them
3. **AgentExecutor is the Handler:** Translates A2A protocol messages into agent method calls
4. **Tools Wrap A2A:** In supervisor patterns, tools encapsulate A2A communication to remote agents


