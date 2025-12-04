# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

"""
Weather Worker Agent - Encapsulates A2A communication to weather agent
This worker agent handles weather queries by directly communicating with the weather agent via A2A.
"""

import logging
from typing import Any
from uuid import uuid4

from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

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
from weather.card import AGENT_CARD as weather_agent_card
from graph.models import WeatherInput
from common.llm import get_llm

logger = logging.getLogger("corto.supervisor.weather_worker")

# Initialize A2A factory and transport (shared instance)
_factory = GatewayFactory()
_transport = _factory.create_transport(
    DEFAULT_MESSAGE_TRANSPORT,
    endpoint=TRANSPORT_SERVER_ENDPOINT,
)
_a2a_client = None  # Lazy initialization


class WeatherQueryTool(BaseTool):
    """
    Tool that encapsulates A2A communication to the weather agent.
    This tool is self-contained and doesn't require external instantiation.
    """
    name: str = "get_weather"
    description: str = "Gets current weather information for a given location or region. Use this when users ask about weather conditions in a specific area."

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._client = None
        self._agent_card = weather_agent_card
        self.args_schema = WeatherInput

    async def _connect(self):
        """Establish A2A connection to weather agent"""
        if self._client:
            return
        
        logger.info(f"[WeatherQueryTool] Connecting to weather agent: {self._agent_card.name}")
        a2a_topic = A2AProtocol.create_agent_topic(self._agent_card)
        self._client = await _factory.create_client(
            "A2A",
            agent_topic=a2a_topic,
            agent_url=self._agent_card.url,
            transport=_transport
        )
        logger.info("[WeatherQueryTool] Connected to weather agent successfully")

    def _run(self, input: dict) -> str:
        raise NotImplementedError("Use _arun for async execution.")

    async def _arun(self, input: dict, **kwargs: Any) -> str:
        """Execute weather query via A2A"""
        logger.info(f"[WeatherQueryTool._arun] Processing weather query: {input}")
        
        # Extract location from input
        location = input.get('location') if isinstance(input, dict) else str(input)
        if not location:
            raise ValueError("Location must be provided")
        
        # Ensure connection
        await self._connect()
        
        # Send A2A message
        request = SendMessageRequest(
            params=MessageSendParams(
                skill_id="get_weather",
                sender_id="coffee-exchange-agent",
                receiver_id="weather-agent",
                message=Message(
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text=location))],
                )
            )
        )
        
        logger.info(f"[WeatherQueryTool] Sending weather query for location: {location}")
        response = await self._client.send_message(request)
        logger.info(f"[WeatherQueryTool] Received response from weather agent")
        
        # Extract response text
        if response.root.result and response.root.result.parts:
            part = response.root.result.parts[0].root
            if hasattr(part, "text"):
                return part.text
        elif response.root.error:
            raise Exception(f"Weather agent error: {response.root.error.message}")
        
        raise Exception("Unknown response type from weather agent")


def create_weather_worker_agent():
    """
    Creates a weather worker agent that encapsulates A2A communication.
    This agent is self-contained and doesn't require external tool instantiation.
    """
    logger.info("[create_weather_worker_agent] Creating self-contained weather worker agent")
    
    # Create the tool (encapsulated within the worker)
    weather_tool = WeatherQueryTool()
    
    # Create react agent with the tool
    model = get_llm()
    agent = create_react_agent(
        model=model,
        tools=[weather_tool],
        name="get_weather_info",
    )
    
    logger.info("[create_weather_worker_agent] Weather worker agent created successfully")
    return agent

