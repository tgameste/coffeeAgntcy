# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any
from uuid import uuid4
from pydantic import PrivateAttr

from a2a.types import (
    AgentCard, 
    SendMessageRequest, 
    MessageSendParams, 
    Message, 
    Part, 
    TextPart, 
    Role,
)

from langchain_core.tools import BaseTool
from graph.models import FlavorProfileInput, FlavorProfileOutput, WeatherInput

from agntcy_app_sdk.protocols.a2a.gateway import A2AProtocol
from agntcy_app_sdk.factory import GatewayFactory
from ioa_observe.sdk.decorators import tool

from config.config import DEFAULT_MESSAGE_TRANSPORT, TRANSPORT_SERVER_ENDPOINT

logger = logging.getLogger("corto.supervisor.tools")

# Initialize a multi-protocol, multi-transport gateway factory.
# All tools will share this factory instance and the transport.
factory = GatewayFactory()
transport = factory.create_transport(
    DEFAULT_MESSAGE_TRANSPORT,
    endpoint=TRANSPORT_SERVER_ENDPOINT,
)

class FlavorProfileTool(BaseTool):
    """
    This tool sends a prompt to the A2A agent and returns the flavor profile estimation.
    """
    name: str = "get_flavor_profile"
    description: str = "Estimates the flavor profile of coffee beans based on a given prompt."

    # private attribute to store client connection
    _client = PrivateAttr()
    
    def __init__(self, remote_agent_card: AgentCard, **kwargs: Any):
        super().__init__(**kwargs)
        self._remote_agent_card = remote_agent_card
        self._client = None

    async def _connect(self):
        logger.info(f"[FlavorProfileTool._connect] Starting connection to remote agent: {self._remote_agent_card.name}")
        logger.info(f"[FlavorProfileTool._connect] Agent URL: {self._remote_agent_card.url}")
        logger.info(f"[FlavorProfileTool._connect] Transport endpoint: {TRANSPORT_SERVER_ENDPOINT}")
       
        try:
            a2a_topic = A2AProtocol.create_agent_topic(self._remote_agent_card)
            logger.info(f"[FlavorProfileTool._connect] Created A2A topic: {a2a_topic}")
            logger.info(f"[FlavorProfileTool._connect] Creating A2A client...")
            self._client = await factory.create_client(
                "A2A", 
                agent_topic=a2a_topic,  
                agent_url=self._remote_agent_card.url, 
                transport=transport)
            logger.info(f"[FlavorProfileTool._connect] Successfully connected to remote agent")
        except Exception as e:
            logger.error(f"[FlavorProfileTool._connect] Error connecting to remote agent: {str(e)}")
            raise

    def _run(self, input: FlavorProfileInput) -> float:
        raise NotImplementedError("Use _arun for async execution.")

    async def _arun(self, input: FlavorProfileInput, **kwargs: Any) -> float:
        logger.info("FlavorProfileTool has been called.")
        try:
            if not input.get('prompt'):
                logger.error("Invalid input: Prompt must be a non-empty string.")
                raise ValueError("Invalid input: Prompt must be a non-empty string.")
            resp = await self.send_message(input.get('prompt'))
            return FlavorProfileOutput(flavor_profile=resp)
        except Exception as e:
            logger.error(f"Failed to get flavor profile: {str(e)}")
            raise RuntimeError(f"Failed to get flavor profile: {str(e)}")
    
    @tool(name="exchange_tool")
    async def send_message(self, prompt: str) -> str:
        """
        Sends a message to the flavor profile farm agent via A2A, specifically invoking its `estimate_flavor` skill.
        Args:
            prompt (str): The user input prompt to send to the agent.
        Returns:
            str: The flavor profile estimation returned by the agent.
        """

        # Ensure the client is connected, use async event loop to connect if not
        if not self._client:
            await self._connect()

        request = SendMessageRequest(
            params=MessageSendParams(
                skill_id="estimate_flavor",
                sender_id="coffee-exchange-agent",
                receiver_id="flavor-profile-farm-agent",
                message=Message(
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text=prompt))],
                )
            )
        )

        response = await self._client.send_message(request)
        logger.info(f"Response received from A2A agent: {response}")

        if response.root.result:
            if not response.root.result.parts:
                raise ValueError("No response parts found in the message.")
            part = response.root.result.parts[0].root
            if hasattr(part, "text"):
                return part.text
        elif response.root.error:
            raise Exception(f"A2A error: {response.root.error.message}")

        raise Exception("Unknown response type")


class WeatherTool(BaseTool):
    """
    This tool sends a location to the A2A weather agent and returns the weather information.
    """
    name: str = "get_weather"
    description: str = "Gets current weather information for a given location or region. Use this when users ask about weather conditions in a specific area."

    # private attribute to store client connection
    _client = PrivateAttr()
    
    def __init__(self, remote_agent_card: AgentCard, **kwargs: Any):
        super().__init__(**kwargs)
        self._remote_agent_card = remote_agent_card
        self._client = None
        self.args_schema = WeatherInput

    async def _connect(self):
        logger.info(f"[WeatherTool] Connecting to remote agent: {self._remote_agent_card.name}")
        logger.info(f"[WeatherTool] Agent URL: {self._remote_agent_card.url}")
        logger.info(f"[WeatherTool] Transport: {DEFAULT_MESSAGE_TRANSPORT}, Transport endpoint: {TRANSPORT_SERVER_ENDPOINT}")
       
        a2a_topic = A2AProtocol.create_agent_topic(self._remote_agent_card)
        logger.info(f"[WeatherTool] Creating A2A client with topic: {a2a_topic}")
        self._client = await factory.create_client(
            "A2A", 
            agent_topic=a2a_topic,  
            agent_url=self._remote_agent_card.url, 
            transport=transport)
        
        logger.info("[WeatherTool] Connected to remote agent successfully")

    def _run(self, input: dict) -> str:
        raise NotImplementedError("Use _arun for async execution.")

    async def _arun(self, input: dict, **kwargs: Any) -> str:
        logger.info(f"WeatherTool._arun called with input: {input}, type: {type(input)}")
        try:
            # Handle both dict and Pydantic model inputs
            if isinstance(input, dict):
                location = input.get('location')
            elif hasattr(input, 'location'):
                location = input.location
            else:
                # If input is a string, use it as location
                location = str(input) if input else None
            
            logger.info(f"WeatherTool._arun extracted location: {location}")
            
            if not location:
                logger.error("Invalid input: Location must be a non-empty string.")
                raise ValueError("Invalid input: Location must be a non-empty string.")
            
            resp = await self.send_message(location)
            logger.info(f"WeatherTool._arun returning response: {resp[:100]}...")
            return resp
        except Exception as e:
            logger.error(f"Failed to get weather information: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to get weather information: {str(e)}")
    
    @tool(name="weather_tool")
    async def send_message(self, location: str) -> str:
        """
        Sends a message to the weather agent via A2A, specifically invoking its `get_weather` skill.
        Args:
            location (str): The location name to send to the agent.
        Returns:
            str: The weather information returned by the agent.
        """
        logger.info(f"WeatherTool.send_message called with location: {location}")

        # Ensure the client is connected, use async event loop to connect if not
        if not self._client:
            logger.info("Client not connected, calling _connect()")
            await self._connect()
        else:
            logger.info("Client already connected")

        logger.info(f"Creating SendMessageRequest for location: {location}")
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

        logger.info("Sending message to weather agent via A2A client...")
        response = await self._client.send_message(request)
        logger.info(f"Response received from A2A agent: {response}")

        if response.root.result:
            if not response.root.result.parts:
                raise ValueError("No response parts found in the message.")
            part = response.root.result.parts[0].root
            if hasattr(part, "text"):
                return part.text
        elif response.root.error:
            raise Exception(f"A2A error: {response.root.error.message}")

        raise Exception("Unknown response type")