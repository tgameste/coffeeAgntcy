# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any
from uuid import uuid4
from pydantic import PrivateAttr
import httpx

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
from graph.models import FlavorProfileInput, FlavorProfileOutput, WeatherInput, WeatherOutput

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
        logger.info(f"Connecting to remote agent: {self._remote_agent_card.name}")
       
        a2a_topic = A2AProtocol.create_agent_topic(self._remote_agent_card)
        self._client = await factory.create_client(
            "A2A", 
            agent_topic=a2a_topic,  
            agent_url=self._remote_agent_card.url, 
            transport=transport)
        
        logger.info("Connected to remote agent")

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
            raise Exception(f"A2A error: {response.error.message}")

        raise Exception("Unknown response type")


class WeatherTool(BaseTool):
    """
    This tool fetches current weather information for a given location/region.
    """
    name: str = "get_weather"
    description: str = "Gets current weather information for a given location or region. Use this when users ask about weather conditions in a specific area."
    args_schema = WeatherInput

    # Base URLs for weather API
    NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
    OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
    
    HEADERS_NOMINATIM = {
        "User-Agent": "CoffeeAgntcy/1.0"
    }

    async def _geocode_location(self, location: str) -> tuple[float, float] | None:
        """Convert location name to (lat, lon) using Nominatim."""
        params = {
            "q": location,
            "format": "json",
            "limit": "1"
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    self.NOMINATIM_BASE,
                    headers=self.HEADERS_NOMINATIM,
                    params=params,
                    timeout=30.0
                )
                resp.raise_for_status()
                data = resp.json()
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    return lat, lon
            except Exception as e:
                logger.error(f"Error geocoding location {location}: {e}")
        return None

    def _run(self, input: dict) -> str:
        raise NotImplementedError("Use _arun for async execution.")

    @tool(name="weather_tool")
    async def _arun(self, location: str, **kwargs: Any) -> str:
        """
        Fetches current weather information for a given location.
        Args:
            location: The name of the location or region to get weather for (e.g., "Brazil", "Colombia", "Ethiopia").
        Returns:
            str: The weather information as a formatted string.
        """
        try:
            if not location or not location.strip():
                logger.error("Invalid input: Location must be a non-empty string.")
                raise ValueError("Invalid input: Location must be a non-empty string.")
            
            location = location.strip()
            logger.info(f"WeatherTool has been called for location: {location}")
            
            # Geocode the location
            coords = await self._geocode_location(location)
            if not coords:
                error_msg = f"Could not determine coordinates for location: {location}"
                logger.warning(error_msg)
                return error_msg
            
            lat, lon = coords
            logger.info(f"Geocoded {location} to coordinates: ({lat}, {lon})")
            
            # Fetch weather data
            params = {
                "latitude": str(lat),
                "longitude": str(lon),
                "current_weather": "true"
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(
                        self.OPEN_METEO_BASE,
                        params=params,
                        timeout=30.0
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if not data or "current_weather" not in data:
                        error_msg = f"No weather data available for {location}."
                        logger.warning(error_msg)
                        return error_msg
                    
                    cw = data["current_weather"]
                    weather_info = (
                        f"Current weather for {location}:\n"
                        f"Temperature: {cw['temperature']}°C\n"
                        f"Wind speed: {cw['windspeed']} m/s\n"
                        f"Wind direction: {cw['winddirection']}°"
                    )
                    
                    logger.info(f"Weather data retrieved successfully for {location}")
                    return weather_info
                    
                except Exception as e:
                    error_msg = f"Error fetching weather data for {location}: {str(e)}"
                    logger.error(error_msg)
                    return error_msg
                    
        except Exception as e:
            logger.error(f"Failed to get weather information: {str(e)}")
            raise RuntimeError(f"Failed to get weather information: {str(e)}")