#!/usr/bin/env python3
"""
Test Harness for Weather Agent Debugging

This script tests the weather agent communication flow:
1. Direct weather agent invocation
2. WeatherTool A2A communication
3. Supervisor routing to weather agent
4. End-to-end flow

Agent Responsibilities:
- Exchange (Supervisor): Routes queries to appropriate worker agents (farm/weather)
- Farm Agent: Handles coffee flavor profile queries independently
- Weather Agent: Handles weather queries independently via A2A/SLIM
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path - ensure we're in the right directory
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))
# Also add /app for container execution
if os.path.exists('/app'):
    sys.path.insert(0, '/app')
    os.chdir('/app')

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("test_weather")

async def test_weather_agent_direct():
    """Test 1: Direct weather agent invocation (bypassing A2A)"""
    logger.info("=" * 80)
    logger.info("TEST 1: Direct Weather Agent Invocation")
    logger.info("=" * 80)
    
    try:
        from weather.agent import WeatherAgent
        
        agent = WeatherAgent()
        result = await agent.ainvoke("Brazil")
        
        logger.info(f"✅ Weather Agent Direct Test: SUCCESS")
        logger.info(f"Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ Weather Agent Direct Test: FAILED - {e}", exc_info=True)
        return False

async def test_weather_tool_a2a():
    """Test 2: WeatherTool A2A communication"""
    logger.info("=" * 80)
    logger.info("TEST 2: WeatherTool A2A Communication")
    logger.info("=" * 80)
    
    try:
        import sys
        sys.path.insert(0, '/app')
        from exchange.graph.tools import WeatherTool
        from weather.card import AGENT_CARD
        
        tool = WeatherTool(remote_agent_card=AGENT_CARD)
        
        # Test connection
        logger.info("Testing A2A connection...")
        await tool._connect()
        logger.info("✅ A2A connection established")
        
        # Test message sending
        logger.info("Testing message sending...")
        result = await tool.send_message("Brazil")
        
        logger.info(f"✅ WeatherTool A2A Test: SUCCESS")
        logger.info(f"Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ WeatherTool A2A Test: FAILED - {e}", exc_info=True)
        return False

async def test_weather_tool_arun():
    """Test 3: WeatherTool._arun method"""
    logger.info("=" * 80)
    logger.info("TEST 3: WeatherTool._arun Method")
    logger.info("=" * 80)
    
    try:
        import sys
        sys.path.insert(0, '/app')
        from exchange.graph.tools import WeatherTool
        from weather.card import AGENT_CARD
        
        tool = WeatherTool(remote_agent_card=AGENT_CARD)
        
        # Test with dict input
        logger.info("Testing with dict input: {'location': 'Brazil'}")
        result = await tool._arun({"location": "Brazil"})
        
        logger.info(f"✅ WeatherTool._arun Test: SUCCESS")
        logger.info(f"Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ WeatherTool._arun Test: FAILED - {e}", exc_info=True)
        return False

async def test_weather_worker_agent():
    """Test 4: Weather worker agent (react agent with WeatherTool)"""
    logger.info("=" * 80)
    logger.info("TEST 4: Weather Worker Agent (React Agent)")
    logger.info("=" * 80)
    
    try:
        import sys
        sys.path.insert(0, '/app')
        from exchange.graph.tools import WeatherTool
        from weather.card import AGENT_CARD
        from common.llm import get_llm
        from langgraph.prebuilt import create_react_agent
        
        tool = WeatherTool(remote_agent_card=AGENT_CARD)
        model = get_llm()
        
        weather_agent = create_react_agent(
            model=model,
            tools=[tool],
            name="get_weather_info",
        )
        
        logger.info("Invoking weather worker agent with: 'Get the current weather for Brazil'")
        result = await weather_agent.ainvoke({
            "messages": [{"role": "user", "content": "Get the current weather for Brazil"}]
        })
        
        logger.info(f"✅ Weather Worker Agent Test: SUCCESS")
        logger.info(f"Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ Weather Worker Agent Test: FAILED - {e}", exc_info=True)
        return False

async def test_supervisor_routing():
    """Test 5: Supervisor routing to weather agent"""
    logger.info("=" * 80)
    logger.info("TEST 5: Supervisor Routing to Weather Agent")
    logger.info("=" * 80)
    
    try:
        import sys
        sys.path.insert(0, '/app')
        from exchange.graph.graph import ExchangeGraph
        
        graph = ExchangeGraph()
        
        logger.info("Invoking supervisor with: 'Get the current weather for Brazil'")
        result = await graph.serve("Get the current weather for Brazil", "test-thread-123")
        
        logger.info(f"✅ Supervisor Routing Test: SUCCESS")
        logger.info(f"Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ Supervisor Routing Test: FAILED - {e}", exc_info=True)
        return False

async def test_a2a_topic_creation():
    """Test 6: A2A topic creation and agent card verification"""
    logger.info("=" * 80)
    logger.info("TEST 6: A2A Topic Creation")
    logger.info("=" * 80)
    
    try:
        import sys
        sys.path.insert(0, '/app')
        from weather.card import AGENT_CARD
        from farm.card import AGENT_CARD as FARM_CARD
        from agntcy_app_sdk.protocols.a2a.gateway import A2AProtocol
        
        weather_topic = A2AProtocol.create_agent_topic(AGENT_CARD)
        farm_topic = A2AProtocol.create_agent_topic(FARM_CARD)
        
        logger.info(f"Weather Agent Card:")
        logger.info(f"  Name: {AGENT_CARD.name}")
        # AgentCard uses different attribute names - check what's available
        if hasattr(AGENT_CARD, 'id'):
            logger.info(f"  ID: {AGENT_CARD.id}")
        elif hasattr(AGENT_CARD, 'agent_id'):
            logger.info(f"  Agent ID: {AGENT_CARD.agent_id}")
        logger.info(f"  URL: {AGENT_CARD.url}")
        logger.info(f"  A2A Topic: {weather_topic}")
        
        logger.info(f"\nFarm Agent Card:")
        logger.info(f"  Name: {FARM_CARD.name}")
        if hasattr(FARM_CARD, 'id'):
            logger.info(f"  ID: {FARM_CARD.id}")
        elif hasattr(FARM_CARD, 'agent_id'):
            logger.info(f"  Agent ID: {FARM_CARD.agent_id}")
        logger.info(f"  URL: {FARM_CARD.url}")
        logger.info(f"  A2A Topic: {farm_topic}")
        
        logger.info(f"✅ A2A Topic Creation Test: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ A2A Topic Creation Test: FAILED - {e}", exc_info=True)
        return False

async def main():
    """Run all tests"""
    logger.info("Starting Weather Agent Test Harness")
    logger.info("=" * 80)
    
    results = {}
    
    # Run tests in sequence
    results['direct_agent'] = await test_weather_agent_direct()
    results['a2a_topic'] = await test_a2a_topic_creation()
    results['tool_arun'] = await test_weather_tool_arun()
    results['tool_a2a'] = await test_weather_tool_a2a()
    results['worker_agent'] = await test_weather_worker_agent()
    results['supervisor'] = await test_supervisor_routing()
    
    # Summary
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

