#!/usr/bin/env python3
"""
Simple Test: Direct A2A Communication to Weather Agent
Tests the A2A communication path without going through the supervisor
"""

import asyncio
import logging
from uuid import uuid4

from a2a.types import (
    AgentCard,
    SendMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
)

from agntcy_app_sdk.protocols.a2a.gateway import A2AProtocol
from agntcy_app_sdk.factory import GatewayFactory
from config.config import DEFAULT_MESSAGE_TRANSPORT, TRANSPORT_SERVER_ENDPOINT
from weather.card import AGENT_CARD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

async def test_direct_a2a_to_weather():
    """Test direct A2A communication to weather agent"""
    logger.info("=" * 80)
    logger.info("Direct A2A Communication Test to Weather Agent")
    logger.info("=" * 80)
    
    try:
        # Create transport and factory
        factory = GatewayFactory()
        transport = factory.create_transport(
            DEFAULT_MESSAGE_TRANSPORT,
            endpoint=TRANSPORT_SERVER_ENDPOINT,
        )
        
        # Create A2A topic
        a2a_topic = A2AProtocol.create_agent_topic(AGENT_CARD)
        logger.info(f"Agent Card: {AGENT_CARD.name}")
        logger.info(f"Agent URL: {AGENT_CARD.url}")
        logger.info(f"A2A Topic: {a2a_topic}")
        logger.info(f"Transport: {DEFAULT_MESSAGE_TRANSPORT}, Endpoint: {TRANSPORT_SERVER_ENDPOINT}")
        
        # Create A2A client
        logger.info("Creating A2A client...")
        client = await factory.create_client(
            "A2A",
            agent_topic=a2a_topic,
            agent_url=AGENT_CARD.url,
            transport=transport
        )
        logger.info("✅ A2A client created")
        
        # Send message
        logger.info("Sending message: 'Brazil'")
        request = SendMessageRequest(
            params=MessageSendParams(
                skill_id="get_weather",
                sender_id="test-client",
                receiver_id="weather-agent",
                message=Message(
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text="Brazil"))],
                )
            )
        )
        
        logger.info("Waiting for response...")
        response = await client.send_message(request)
        logger.info(f"✅ Response received: {response}")
        
        if response.root.result:
            if response.root.result.parts:
                part = response.root.result.parts[0].root
                if hasattr(part, "text"):
                    logger.info(f"✅ Weather data: {part.text}")
                    return True
        
        logger.error(f"❌ Unexpected response format: {response}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_a2a_to_weather())
    exit(0 if success else 1)

