# SLIM Dataplane Architecture Diagram

## Visual Representation

```
┌─────────────────────────────────────────────────────────────────┐
│                    SLIM Dataplane (Message Broker)                │
│                      Port: 46357 (Pub/Sub)                       │
│                      Port: 46358 (Control)                       │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Topic Registry                          │  │
│  │  • Coffee_Farm_Flavor_Agent_1.0.0                        │  │
│  │  • Coffee_Weather_Agent_1.0.0                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Message Routing Engine                       │  │
│  │  Routes messages from publishers to subscribers          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ▲                    ▲
                            │                    │
                            │                    │
        ┌───────────────────┴────────┐          │
        │                              │          │
        │                              │          │
┌───────▼──────────────┐    ┌─────────▼──────────▼──────┐
│   Farm Agent Server   │    │   Weather Agent Server    │
│  (Subscriber)         │    │   (Subscriber)            │
│                       │    │                           │
│  Topic:               │    │  Topic:                   │
│  Coffee_Farm_...     │    │  Coffee_Weather_...       │
│                       │    │                           │
│  • Listens for       │    │  • Listens for            │
│    messages on topic │    │    messages on topic      │
│  • Processes         │    │  • Processes             │
│    flavor queries    │    │    weather queries        │
│  • Publishes         │    │  • Publishes             │
│    responses         │    │    responses              │
└───────────────────────┘    └───────────────────────────┘
        ▲                              ▲
        │                              │
        │                              │
        └──────────────┬───────────────┘
                       │
                       │
        ┌──────────────▼───────────────┐
        │   Exchange Server (Client)    │
        │   (Publisher)                 │
        │                               │
        │  • WeatherQueryTool          │
        │    - Publishes to:           │
        │      Coffee_Weather_...      │
        │                               │
        │  • FlavorProfileTool          │
        │    - Publishes to:           │
        │      Coffee_Farm_...         │
        │                               │
        │  • Receives responses         │
        └───────────────────────────────┘
```

## Message Flow Sequence

### Weather Query Example

```
1. User → Exchange Server
   "Get the current weather for Brazil"
   
2. Exchange Server → WeatherQueryTool
   Calls tool with location="Brazil"
   
3. WeatherQueryTool → SLIM Dataplane
   PUBLISH to topic: "Coffee_Weather_Agent_1.0.0"
   Message: {skill_id: "get_weather", location: "Brazil"}
   
4. SLIM Dataplane → Weather Agent Server
   ROUTE message to subscriber of "Coffee_Weather_Agent_1.0.0"
   
5. Weather Agent Server → Weather Agent
   Process query (geocode, fetch weather)
   
6. Weather Agent Server → SLIM Dataplane
   PUBLISH response to topic
   
7. SLIM Dataplane → WeatherQueryTool
   ROUTE response back to client
   
8. WeatherQueryTool → Exchange Server
   Return weather data
   
9. Exchange Server → User
   "Current weather for Brazil: 24.6°C..."
```

## Topic Structure

### Full Topic Format
```
{org}/{namespace}/{agent_name}_{version}
```

### Actual Topics in Corto
```
default/default/Coffee_Farm_Flavor_Agent_1.0.0
default/default/Coffee_Weather_Agent_1.0.0
```

**Components:**
- **org**: `default` (organization)
- **namespace**: `default` (namespace within org)
- **agent_name**: From Agent Card `name` field
- **version**: From Agent Card `version` field

## Connection Lifecycle

### Agent Server Startup (Subscriber)

```
1. Agent Server Starts
   ↓
2. Create GatewayFactory
   ↓
3. Create SLIM Transport
   transport = factory.create_transport("SLIM", "http://slim:46357")
   ↓
4. Create A2A Server
   server = A2AStarletteApplication(agent_card, handler)
   ↓
5. Create Bridge
   bridge = factory.create_bridge(server, transport=transport)
   ↓
6. Start Bridge
   await bridge.start(blocking=True)
   ↓
7. Bridge Subscribes to Topic
   Topic: "default/default/{Agent_Name}_{Version}"
   ↓
8. Agent is Now Listening
   Ready to receive messages
```

### Client Connection (Publisher)

```
1. Client Needs to Send Message
   ↓
2. Create GatewayFactory
   ↓
3. Create SLIM Transport
   transport = factory.create_transport("SLIM", "http://slim:46357")
   ↓
4. Generate Topic from Agent Card
   topic = A2AProtocol.create_agent_topic(agent_card)
   ↓
5. Create A2A Client
   client = await factory.create_client("A2A", agent_topic=topic, transport=transport)
   ↓
6. Send Message
   response = await client.send_message(request)
   ↓
7. Client Publishes to Topic
   SLIM routes to subscriber
   ↓
8. Receive Response
   Response routed back via SLIM
```

## SLIM Configuration Details

### Runtime Configuration
- **Thread Name**: `slim-data-plane`
- **Drain Timeout**: `10s` (time to wait for graceful shutdown)
- **Cores**: `0` (auto-detect)

### Server Endpoints
- **Pub/Sub Endpoint**: `0.0.0.0:46357`
  - Main message routing endpoint
  - HTTP/2 only
  - TLS: Insecure (development)
  
- **Controller Endpoint**: `0.0.0.0:46358`
  - Control plane operations
  - Management and monitoring

### Connection Parameters
- **Max Connection Idle**: 3600s (1 hour)
- **Max Connection Age**: 7200s (2 hours)
- **Keepalive Time**: 120s
- **Keepalive Timeout**: 20s

## Observability

### What SLIM Enables

1. **Centralized Message Logging**
   - All messages flow through SLIM
   - Can log all A2A communications

2. **Message Tracing**
   - Trace message flows across agents
   - Identify bottlenecks

3. **Connection Monitoring**
   - See which agents are connected
   - Monitor subscription status

4. **Topic Analytics**
   - Message volume per topic
   - Latency metrics
   - Error rates

### Integration with OpenTelemetry

SLIM can be instrumented with OpenTelemetry to provide:
- Distributed tracing
- Metrics collection
- Performance monitoring

---

## Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Topic** | Named channel for message routing (e.g., `Coffee_Weather_Agent_1.0.0`) |
| **Publisher** | Client that sends messages to a topic |
| **Subscriber** | Agent server that listens to a topic |
| **Bridge** | Connection between A2A server and SLIM transport |
| **Transport** | Abstraction layer for message delivery (SLIM, HTTP, etc.) |
| **Gateway** | SLIM gateway instance managing pub/sub operations |

---

## Benefits in Corto Stack

1. **Agent Independence**: Agents don't need direct network connections
2. **Scalability**: Multiple agent instances can subscribe to same topic
3. **Reliability**: SLIM can buffer messages if agent is temporarily down
4. **Observability**: All messages flow through centralized broker
5. **Flexibility**: Easy to add/remove agents without reconfiguration

