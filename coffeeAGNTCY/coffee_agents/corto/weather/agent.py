# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import TypedDict
import httpx

from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage

from common.llm import get_llm
from ioa_observe.sdk.decorators import agent, graph

logger = logging.getLogger("corto.weather_agent.graph")

class State(TypedDict):
    location: str
    error_type: str
    error_message: str
    weather_info: str

@agent(name="weather_agent")
class WeatherAgent:
    def __init__(self):
        self.WEATHER_NODE = "WeatherNode"
        self._agent = self.build_graph()
        
        # Base URLs for weather API
        self.NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
        self.OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
        
        self.HEADERS_NOMINATIM = {
            "User-Agent": "CoffeeAgntcy/1.0"
        }

    @graph(name="weather_graph")
    def build_graph(self) -> StateGraph:
        graph_builder = StateGraph(State)
        graph_builder.add_node(self.WEATHER_NODE, self.weather_node)
        graph_builder.add_edge(START, self.WEATHER_NODE)
        graph_builder.add_edge(self.WEATHER_NODE, END)
        return graph_builder.compile()

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

    async def weather_node(self, state: State):
        """
        Retrieves current weather information for a given location using geocoding and weather APIs.

        This method takes the current state (which includes a location),
        geocodes the location to get coordinates, fetches weather data from Open-Meteo API,
        and returns formatted weather information.

        Args:
            state (State): The LangGraph state object containing a 'location' key with user input.

        Returns:
            dict: A dictionary with either:
                - "weather_info" (str): Formatted weather information if valid location was found.
                - or an "error_type" and "error_message" if the input was insufficient or processing failed.
        """
        location = state.get("location")
        logger.debug(f"Received location: {location}")

        if not location or not location.strip():
            logger.warning("Empty or missing location in user input.")
            return {
                "error_type": "invalid_input",
                "error_message": "Location must be a non-empty string."
            }

        location = location.strip()
        
        # Geocode the location
        coords = await self._geocode_location(location)
        if not coords:
            error_msg = f"Could not determine coordinates for location: {location}"
            logger.warning(error_msg)
            return {
                "error_type": "geocoding_failed",
                "error_message": error_msg
            }
        
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
                    return {
                        "error_type": "no_weather_data",
                        "error_message": error_msg
                    }
                
                cw = data["current_weather"]
                weather_info = (
                    f"Current weather for {location}:\n"
                    f"Temperature: {cw['temperature']}°C\n"
                    f"Wind speed: {cw['windspeed']} m/s\n"
                    f"Wind direction: {cw['winddirection']}°"
                )
                
                logger.info(f"Weather data retrieved successfully for {location}")
                return {"weather_info": weather_info}
                
            except Exception as e:
                error_msg = f"Error fetching weather data for {location}: {str(e)}"
                logger.error(error_msg)
                return {
                    "error_type": "weather_fetch_failed",
                    "error_message": error_msg
                }

    async def ainvoke(self, input: str) -> dict:
        """
        Sends a location string to the agent asynchronously and returns the weather information.

        Args:
            input (str): A location name (e.g., "Brazil", "Colombia", "Ethiopia").

        Returns:
            dict: A response dictionary, typically containing either:
                - "weather_info" with the formatted weather data, or
                - An error message if geocoding or weather fetching failed.
        """
        # build graph if not already built
        if not hasattr(self, '_agent'):
            self._agent = self.build_graph()
        return await self._agent.ainvoke({"location": input})

