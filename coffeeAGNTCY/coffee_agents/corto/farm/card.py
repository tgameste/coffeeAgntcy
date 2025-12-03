# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill)
from config.config import FARM_AGENT_HOST, FARM_AGENT_PORT

AGENT_SKILL = AgentSkill(
    id="estimate_flavor",
    name="Estimate Flavor Profile",
    description="Analyzes a natural language prompt and returns the expected flavor profile for a coffee-growing region and/or season.",
    tags=["coffee", "flavor", "farm"],
    examples=[
        "What flavors can I expect from coffee in Huila during harvest?",
        "Describe the taste of beans grown in Sidamo in the dry season",
        "How does Yirgacheffe coffee taste?"
    ]
)

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
    name='Coffee Farm Flavor Agent',
    id='flavor-profile-farm-agent',
    description='An AI agent that estimates the flavor profile of coffee beans using growing conditions like season and altitude, and provides weather information for coffee-growing regions.',
    url=f'http://{FARM_AGENT_HOST}:{FARM_AGENT_PORT}/',
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[AGENT_SKILL, WEATHER_SKILL],
    supportsAuthenticatedExtendedCard=False,
)
