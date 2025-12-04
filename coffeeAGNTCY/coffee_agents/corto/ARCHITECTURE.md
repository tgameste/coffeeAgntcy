# Corto Stack Architecture

## Agent Responsibilities

### 1. Exchange Agent (Supervisor)

**Location:** `exchange/graph/graph.py`

**Role:** Central routing supervisor that orchestrates queries to specialized worker agents.

**Responsibilities:**
- **Query Classification:** Analyzes user queries to determine intent (weather, flavor, capability, unknown)
- **Agent Routing:** Routes queries to appropriate worker agents:
  - Weather queries → `get_weather_info` worker agent
  - Flavor queries → `get_flavor_profile_via_a2a` worker agent
- **Response Aggregation:** Collects and returns results from worker agents
- **Error Handling:** Handles routing failures and unknown queries

**Architecture:**
- Uses LangGraph's `create_supervisor` pattern
- Creates worker agents using `create_react_agent`
- Each worker agent has access to specialized tools (WeatherTool, FlavorProfileTool)
- Tools communicate with remote agents via A2A protocol over SLIM transport

**Independence:** 
- Does NOT process queries directly
- Does NOT contain domain logic (weather/flavor)
- Only responsible for routing and coordination

---

### 2. Farm Agent (Flavor Profile Specialist)

**Location:** `farm/agent.py`, `farm/agent_executor.py`

**Role:** Independent agent specializing in coffee flavor profile estimation.

**Responsibilities:**
- **Flavor Analysis:** Generates coffee flavor profiles based on location and season
- **LLM Processing:** Uses specialized prompts to extract location/season and generate tasting notes
- **A2A Communication:** Receives requests via A2A protocol and returns structured responses

**Architecture:**
- Standalone LangGraph workflow: `START → FlavorNode → END`
- Exposes skill: `estimate_flavor`
- Communicates via A2A/SLIM transport
- Independent of Exchange and Weather agents

**Independence:**
- Can operate standalone (direct A2A requests)
- No dependencies on Exchange or Weather agents
- Self-contained flavor profile logic

---

### 3. Weather Agent (Weather Information Specialist)

**Location:** `weather/agent.py`, `weather/agent_executor.py`

**Role:** Independent agent specializing in weather information retrieval.

**Responsibilities:**
- **Weather Retrieval:** Fetches current weather data for given locations
- **Geocoding:** Converts location names to coordinates using Nominatim API
- **Weather API Integration:** Retrieves weather data from Open-Meteo API
- **A2A Communication:** Receives requests via A2A protocol and returns formatted weather information

**Architecture:**
- Standalone LangGraph workflow: `START → WeatherNode → END`
- Exposes skill: `get_weather`
- Communicates via A2A/SLIM transport
- Independent of Exchange and Farm agents

**Independence:**
- Can operate standalone (direct A2A requests)
- No dependencies on Exchange or Farm agents
- Self-contained weather retrieval logic

---

## Communication Flow

### Weather Query Flow (Expected)
```
User Query: "Get the current weather for Brazil"
    ↓
Exchange Supervisor (graph.py)
    ↓ (routes to get_weather_info worker)
Weather Worker Agent (create_react_agent with WeatherTool)
    ↓ (calls WeatherTool._arun)
WeatherTool (tools.py)
    ↓ (A2A client sends message)
SLIM Transport Gateway
    ↓ (routes via A2A topic)
Weather Agent Server (weather_server.py)
    ↓ (receives A2A message)
Weather Agent Executor (agent_executor.py)
    ↓ (invokes WeatherAgent.ainvoke)
Weather Agent (agent.py)
    ↓ (geocodes location, fetches weather)
Weather API (Open-Meteo)
    ↓ (returns weather data)
Response flows back through the chain
```

### Current Issue
The flow breaks at the supervisor routing step - WeatherTool is never invoked, suggesting:
1. Supervisor not recognizing weather queries correctly
2. Weather worker agent not being called
3. Tool registration issue

---

## Agent Independence

All three agents are **architecturally independent**:

1. **Exchange Agent:**
   - Depends on: Farm and Weather agents (for routing)
   - Independent: Can be replaced/modified without affecting worker agents

2. **Farm Agent:**
   - Depends on: None (standalone)
   - Independent: Can receive direct A2A requests, doesn't need Exchange

3. **Weather Agent:**
   - Depends on: None (standalone)
   - Independent: Can receive direct A2A requests, doesn't need Exchange

**Communication Protocol:**
- All inter-agent communication uses A2A protocol
- Transport layer: SLIM (Service-Level Interconnect Manager)
- Agents discover each other via Agent Cards (name, id, url, skills)

