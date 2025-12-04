# SLIM Dataplane Debugging Guide

## Enabling Debug Logging

### 1. SLIM Server Configuration

**File:** `config/docker/slim/server-config.yaml`

Change log level to `debug`:

```yaml
tracing:
  log_level: debug  # Options: trace, debug, info, warn, error
  display_thread_names: true
  display_thread_ids: true
```

**After changing, restart SLIM:**
```bash
docker compose restart slim
```

### 2. View SLIM Debug Logs

```bash
# Follow SLIM logs in real-time
docker compose logs slim -f

# View last 100 lines
docker compose logs slim --tail 100

# Filter for specific events
docker compose logs slim | grep -E "(publish|subscribe|message|topic)"
```

### 3. Agent SDK Logging

Enable debug logging for SLIM gateway operations in agent code:

**Environment Variable:**
```bash
export LOGGING_LEVEL=DEBUG
```

Or in `docker-compose.yaml`, add to agent services:
```yaml
environment:
  - LOGGING_LEVEL=DEBUG
```

---

## Monitoring SLIM Communications

### Method 1: Docker Logs

**View all SLIM activity:**
```bash
docker compose logs slim -f
```

**View agent connections:**
```bash
docker compose logs farm-server weather-server exchange-server | grep -E "(SLIMGateway|Subscribed|connected|publish|message)"
```

### Method 2: Controller Endpoint (Port 46358)

The SLIM controller endpoint provides management and monitoring capabilities:

```bash
# Check if controller is accessible
curl http://localhost:46358/health  # (if health endpoint exists)

# Or check via docker exec
docker compose exec slim /slim --help
```

### Method 3: Network Inspection

**Monitor network traffic to SLIM:**
```bash
# Using tcpdump (if available in container)
docker compose exec slim tcpdump -i any -n port 46357

# Or use docker network inspection
docker network inspect corto_default | grep -A 10 slim
```

---

## Debugging Message Flow

### Step 1: Enable Verbose Logging

1. **SLIM Configuration** - Set `log_level: debug`
2. **Agent Logging** - Set `LOGGING_LEVEL=DEBUG`
3. **Restart services:**
   ```bash
   docker compose restart slim farm-server weather-server exchange-server
   ```

### Step 2: Monitor Message Flow

**Terminal 1 - SLIM Logs:**
```bash
docker compose logs slim -f | grep -E "(message|publish|subscribe|topic|route)"
```

**Terminal 2 - Agent Logs:**
```bash
docker compose logs exchange-server -f | grep -E "(WeatherTool|FlavorProfileTool|A2A|SLIM)"
```

**Terminal 3 - Weather Agent Logs:**
```bash
docker compose logs weather-server -f | grep -E "(Received|execute|message)"
```

### Step 3: Send Test Message

```bash
curl -X POST http://localhost:8000/agent/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Get the current weather for Brazil"}'
```

**Watch for:**
- Message published to SLIM topic
- Message received by weather agent
- Response published back
- Response received by exchange

---

## Debugging Tools

### 1. Check Active Subscriptions

**View agent subscription logs:**
```bash
docker compose logs farm-server weather-server | grep "Subscribed to"
```

**Expected output:**
```
farm-server: Subscribed to default/default/Coffee_Farm_Flavor_Agent_1.0.0
weather-server: Subscribed to default/default/Coffee_Weather_Agent_1.0.0
```

### 2. Check Topic Names

**Verify topic generation:**
```bash
docker compose logs exchange-server | grep -E "(A2A topic|agent_topic|Creating A2A client)"
```

**Expected output:**
```
[WeatherTool] Creating A2A client with topic: Coffee Weather Agent_1.0.0
[FlavorProfileTool] Created A2A topic: Coffee Farm Flavor Agent_1.0.0
```

### 3. Monitor Message Publishing

**Check for publish operations:**
```bash
docker compose logs exchange-server | grep -E "(Sending|publish|send_message)"
```

### 4. Monitor Message Receiving

**Check for receive operations:**
```bash
docker compose logs weather-server farm-server | grep -E "(Received message|execute|message request)"
```

---

## Common Debugging Scenarios

### Scenario 1: Message Not Reaching Agent

**Symptoms:**
- Client publishes message
- No log in agent server

**Debug Steps:**
1. Check topic name matches:
   ```bash
   # Client topic
   docker compose logs exchange-server | grep "A2A topic"
   
   # Agent subscription
   docker compose logs weather-server | grep "Subscribed to"
   ```

2. Check SLIM routing:
   ```bash
   docker compose logs slim -f
   # Look for routing errors or topic mismatches
   ```

3. Verify agent is connected:
   ```bash
   docker compose logs weather-server | grep "connected to gateway"
   ```

### Scenario 2: Response Not Returning

**Symptoms:**
- Agent receives message
- Client never gets response

**Debug Steps:**
1. Check agent publishes response:
   ```bash
   docker compose logs weather-server | grep -E "(Weather information retrieved|publish|response)"
   ```

2. Check SLIM receives response:
   ```bash
   docker compose logs slim -f | grep -E "(response|publish)"
   ```

3. Check client receives response:
   ```bash
   docker compose logs exchange-server | grep -E "(Response received|A2A agent)"
   ```

### Scenario 3: Connection Issues

**Symptoms:**
- Agents can't connect to SLIM
- Connection timeouts

**Debug Steps:**
1. Check SLIM is running:
   ```bash
   docker compose ps slim
   docker compose logs slim --tail 20
   ```

2. Check network connectivity:
   ```bash
   docker compose exec exchange-server ping slim
   docker compose exec weather-server ping slim
   ```

3. Check endpoint configuration:
   ```bash
   docker compose exec exchange-server env | grep TRANSPORT_SERVER_ENDPOINT
   # Should be: http://slim:46357
   ```

---

## Advanced Debugging

### Enable HTTP/2 Frame Logging

If SLIM supports it, you can enable frame-level logging by modifying the configuration or using environment variables.

### Message Payload Inspection

To see actual message contents, add logging in agent code:

**In `weather_worker.py` or `tools.py`:**
```python
logger.debug(f"[SLIM Debug] Publishing message: {request}")
logger.debug(f"[SLIM Debug] Message topic: {a2a_topic}")
logger.debug(f"[SLIM Debug] Message payload: {request.params.message.parts[0].root.text}")
```

### Network Packet Capture

For deep debugging, capture network packets:

```bash
# Install tcpdump in container (if needed)
docker compose exec slim apt-get update && apt-get install -y tcpdump

# Capture SLIM traffic
docker compose exec slim tcpdump -i any -n -A 'port 46357' -w /tmp/slim-capture.pcap
```

---

## Logging Levels Reference

| Level | Description | Use Case |
|-------|-------------|----------|
| `trace` | Most verbose, all operations | Deep debugging |
| `debug` | Detailed operations, message flows | Debugging message routing |
| `info` | General operations, connections | Normal monitoring |
| `warn` | Warnings only | Production monitoring |
| `error` | Errors only | Error tracking |

---

## Quick Debug Checklist

- [ ] SLIM log level set to `debug`
- [ ] Agent logging level set to `DEBUG`
- [ ] All services restarted
- [ ] SLIM container is running
- [ ] Agents show "connected to gateway" in logs
- [ ] Agents show "Subscribed to" in logs
- [ ] Topics match between client and server
- [ ] Network connectivity verified

---

## Example Debug Session

```bash
# Terminal 1: SLIM logs
docker compose logs slim -f

# Terminal 2: Exchange server (client)
docker compose logs exchange-server -f | grep -E "(WeatherTool|A2A|SLIM)"

# Terminal 3: Weather server (agent)
docker compose logs weather-server -f | grep -E "(Received|execute|message)"

# Terminal 4: Send test message
curl -X POST http://localhost:8000/agent/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Get the current weather for Brazil"}'

# Watch all terminals for message flow:
# 1. Exchange publishes to topic
# 2. SLIM routes message
# 3. Weather agent receives
# 4. Weather agent processes
# 5. Weather agent publishes response
# 6. SLIM routes response
# 7. Exchange receives response
```

---

## Troubleshooting Commands

```bash
# Check SLIM status
docker compose ps slim

# Check SLIM logs
docker compose logs slim --tail 50

# Check agent connections
docker compose logs farm-server weather-server | grep "Subscribed"

# Check topic names
docker compose logs exchange-server | grep "A2A topic"

# Test network connectivity
docker compose exec exchange-server ping -c 3 slim

# Check SLIM port accessibility
docker compose exec exchange-server curl -v http://slim:46357

# View all SLIM-related logs
docker compose logs | grep -i slim
```

