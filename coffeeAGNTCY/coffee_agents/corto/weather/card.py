# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill)
from config.config import WEATHER_AGENT_HOST, WEATHER_AGENT_PORT

WEATHER_SKILL = AgentSkill(
    id="get_weather",
    name="Get Weather Information",
    description="Retrieves current weather information for a given location or region, including temperature, wind speed, and wind direction.",
    tags=["weather", "climate", "temperature", "coffee"],
    examples=[
        "What's the weather like in Brazil?",
        "Get the current weather for Colombia",
        "What are the weather conditions in Ethiopia?",
        "Temperature in Vietnam"
    ]
)

AGENT_CARD = AgentCard(
    name='Coffee Weather Agent',
    id='weather-agent',
    description='An AI agent that retrieves current weather information for coffee-growing regions and other locations.',
    url=f'http://{WEATHER_AGENT_HOST}:{WEATHER_AGENT_PORT}/',
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[WEATHER_SKILL],
    supportsAuthenticatedExtendedCard=False,
)

