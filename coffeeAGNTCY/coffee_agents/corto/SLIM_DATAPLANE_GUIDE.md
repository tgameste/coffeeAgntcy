# SLIM Dataplane - Deep Dive Guide

## What is SLIM?

**SLIM** (Service-Level Interconnect Manager) is a **message bus/gateway** that provides a **pub/sub (publish-subscribe) transport layer** for Agent-to-Agent (A2A) communication.

### Core Concept

SLIM acts as a **centralized message broker** that enables agents to communicate with each other without needing direct HTTP connections. Instead of agents calling each other directly via HTTP, they:

1. **Publish** messages to SLIM topics
2. **Subscribe** to SLIM topics to receive messages
3. SLIM routes messages between agents based on topics

---

## Architecture Overview

### Traditional Direct Communication (Without SLIM)
```
Exchange Agent → HTTP Request → Farm Agent
                (Direct connection)
```

### SLIM-Based Communication (Current Architecture)
```
Exchange Agent → Publish to SLIM Topic → SLIM Dataplane → Subscribe to Topic → Farm Agent
                (Indirect, topic-based routing)
```

---

## SLIM Configuration

### Docker Compose Setup

```yaml
slim:
  image: ghcr.io/agntcy/slim:0.3.15
  container_name: slim-dataplane
  ports:
    - "46357:46357"  # Pub/Sub endpoint
  environment:
    - PASSWORD=${SLIM_GATEWAY_PASSWORD:-dummy_password}
    - CONFIG_PATH=/config.yaml
  volumes:
    - ./config/docker/slim/server-config.yaml:/config.yaml
  command: ["/slim", "--config", "/config.yaml"]
```

### Configuration File (`server-config.yaml`)

```yaml
tracing:
  log_level: info
  display_thread_names: true
  display_thread_ids: true

runtime:
  n_cores: 0
  thread_name: "slim-data-plane"
  drain_timeout: 10s

services:
  slim/0:
    pubsub:
      servers:
        - endpoint: "0.0.0.0:46357"  # Main pub/sub endpoint
          tls:
            insecure: true
      clients: []
    controller:
      server:
        endpoint: "0.0.0.0:46358"  # Control plane endpoint
        tls:
          insecure: true
```

**Key Configuration Points:**
- **Port 46357**: Main pub/sub endpoint for message routing
- **Port 46358**: Control plane for management operations
- **TLS**: Currently configured as insecure (development mode)

---

## How SLIM Works in Corto Stack

### 1. Agent Registration (Server Side)

When an agent server starts (e.g., `farm-server`, `weather-server`):

```python
# From farm_server.py / weather_server.py
from agntcy_app_sdk.factory import GatewayFactory

factory = GatewayFactory()

# Create SLIM transport
transport = factory.create_transport(
    "SLIM",  # Transport type
    endpoint="http://slim:46357"  # SLIM endpoint
)

# Create bridge between A2A server and SLIM transport
bridge = factory.create_bridge(server, transport=transport)

# Start the bridge (agent subscribes to its topic)
await bridge.start(blocking=True)
```

**What Happens:**
1. Agent creates a **topic** based on its Agent Card (e.g., `Coffee Farm Flavor Agent_1.0.0`)
2. Agent **subscribes** to that topic via SLIM
3. Agent is now **listening** for messages on that topic

### 2. Message Publishing (Client Side)

When a client wants to send a message (e.g., from `exchange-server`):

```python
# From tools.py or weather_worker.py
from agntcy_app_sdk.factory import GatewayFactory
from agntcy_app_sdk.protocols.a2a.gateway import A2AProtocol

factory = GatewayFactory()

# Create SLIM transport
transport = factory.create_transport(
    "SLIM",
    endpoint="http://slim:46357"
)

# Create topic from agent card
a2a_topic = A2AProtocol.create_agent_topic(weather_agent_card)
# Result: "Coffee Weather Agent_1.0.0"

# Create A2A client
client = await factory.create_client(
    "A2A",
    agent_topic=a2a_topic,  # Topic to publish to
    agent_url=weather_agent_card.url,  # Fallback URL
    transport=transport
)

# Send message (publishes to SLIM topic)
response = await client.send_message(request)
```

**What Happens:**
1. Client creates a **topic** from the target agent's card
2. Client **publishes** message to that topic via SLIM
3. SLIM routes the message to the agent subscribed to that topic
4. Agent receives the message and processes it
5. Agent publishes response back to SLIM
6. Client receives the response

---

## Topic-Based Routing

### Topic Generation

Topics are generated from Agent Cards:

```python
# Agent Card
AGENT_CARD = AgentCard(
    name='Coffee Weather Agent',
    id='weather-agent',
    version='1.0.0',
    ...
)

# Topic Generation
topic = A2AProtocol.create_agent_topic(AGENT_CARD)
# Result: "Coffee Weather Agent_1.0.0"
```

**Topic Format:** `{Agent Name}_{Version}`

### Topic Examples in Corto Stack

- **Farm Agent Topic:** `Coffee Farm Flavor Agent_1.0.0`
- **Weather Agent Topic:** `Coffee Weather Agent_1.0.0`

---

## Message Flow Example

### Weather Query Flow with SLIM

```
1. User Query: "Get the current weather for Brazil"
   ↓
2. Exchange Supervisor routes to Weather Worker Agent
   ↓
3. WeatherQueryTool creates A2A client
   ↓
4. Client publishes message to SLIM topic: "Coffee Weather Agent_1.0.0"
   ↓
5. SLIM Dataplane receives message
   ↓
6. SLIM routes message to Weather Agent (subscribed to that topic)
   ↓
7. Weather Agent receives message via bridge
   ↓
8. Weather Agent processes query (geocodes location, fetches weather)
   ↓
9. Weather Agent publishes response to SLIM
   ↓
10. SLIM routes response back to client
   ↓
11. WeatherQueryTool receives response
   ↓
12. Response returned to supervisor → user
```

---

## Benefits of SLIM

### 1. **Decoupling**
- Agents don't need to know each other's network addresses
- Agents only need to know the SLIM endpoint and topic names

### 2. **Scalability**
- Multiple instances of an agent can subscribe to the same topic (load balancing)
- SLIM handles message distribution

### 3. **Reliability**
- SLIM can buffer messages if an agent is temporarily unavailable
- Message persistence (if configured)

### 4. **Observability**
- All messages flow through SLIM, enabling centralized logging/monitoring
- Can trace message flows across the system

### 5. **Flexibility**
- Easy to add/remove agents without reconfiguring others
- Agents can be moved to different hosts without breaking communication

---

## SLIM vs Direct HTTP

### Direct HTTP (Alternative)
```python
# Direct connection
response = await httpx.post(
    "http://weather-server:9998/agent/message",
    json=message
)
```

**Pros:**
- Simpler (no message broker needed)
- Lower latency (direct connection)

**Cons:**
- Tight coupling (agents must know each other's addresses)
- Harder to scale (load balancing requires additional infrastructure)
- No centralized observability

### SLIM Transport (Current)
```python
# Topic-based via SLIM
client = await factory.create_client("A2A", agent_topic=topic, transport=transport)
response = await client.send_message(request)
```

**Pros:**
- Loose coupling (topic-based routing)
- Built-in scalability (multiple subscribers per topic)
- Centralized observability
- Message buffering/reliability

**Cons:**
- Additional infrastructure (SLIM server)
- Slightly higher latency (extra hop)

---

## Environment Configuration

### Agent Servers (Farm/Weather)

```python
# config.py
DEFAULT_MESSAGE_TRANSPORT = "SLIM"  # or "A2A" for direct HTTP
TRANSPORT_SERVER_ENDPOINT = "http://slim:46357"
```

**When `DEFAULT_MESSAGE_TRANSPORT == "SLIM"`:**
- Agent uses SLIM bridge for communication
- Agent subscribes to its topic via SLIM

**When `DEFAULT_MESSAGE_TRANSPORT == "A2A"`:**
- Agent uses direct HTTP server
- No SLIM dependency

### Client Tools (Exchange)

```python
# Same configuration
DEFAULT_MESSAGE_TRANSPORT = "SLIM"
TRANSPORT_SERVER_ENDPOINT = "http://slim:46357"
```

Clients create transport and publish to topics via SLIM.

---

## SLIM Gateway Factory Pattern

The `GatewayFactory` provides a unified interface for creating transports:

```python
factory = GatewayFactory()

# Create transport (supports multiple types: SLIM, A2A, etc.)
transport = factory.create_transport(
    "SLIM",  # Transport type
    endpoint="http://slim:46357"
)

# For servers: Create bridge
bridge = factory.create_bridge(server, transport=transport)

# For clients: Create client
client = await factory.create_client(
    "A2A",  # Protocol
    agent_topic=topic,
    transport=transport
)
```

**Abstraction Benefits:**
- Code is transport-agnostic
- Can switch between SLIM and direct HTTP by changing config
- Easy to add new transport types

---

## Monitoring and Debugging

### SLIM Logs

```bash
docker compose logs slim --tail 50 -f
```

### Agent Connection Status

Check if agents are connected to SLIM:
- Farm server logs: `Subscribed to default/default/Coffee_Farm_Flavor_Agent_1.0.0`
- Weather server logs: `Subscribed to default/default/Coffee_Weather_Agent_1.0.0`

### Message Tracing

All A2A messages flow through SLIM, making it easy to:
- Trace message flows
- Debug routing issues
- Monitor message volumes
- Identify bottlenecks

---

## Key Takeaways

1. **SLIM is a message broker** - Routes messages between agents via topics
2. **Topic-based routing** - Agents subscribe to topics, clients publish to topics
3. **Decoupled architecture** - Agents don't need direct network connections
4. **Transport abstraction** - `GatewayFactory` provides unified interface
5. **Observability** - Centralized message flow for monitoring/debugging
6. **Scalability** - Multiple agents can subscribe to same topic (load balancing)

---

## References

- **AGNTCY App SDK**: https://github.com/agntcy/app-sdk
- **SLIM Image**: `ghcr.io/agntcy/slim:0.3.15`
- **Configuration**: `config/docker/slim/server-config.yaml`

