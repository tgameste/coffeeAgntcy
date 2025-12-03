# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
import uuid
from langchain_core.messages import AIMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from ioa_observe.sdk.decorators import agent, graph



from common.llm import get_llm
from graph.tools import FlavorProfileTool, WeatherTool

from farm.card import AGENT_CARD as farm_agent_card

logger = logging.getLogger("corto.supervisor.graph")


@agent(name="exchange_agent")
class ExchangeGraph:
    def __init__(self):
        self.graph = None  # Build graph lazily to ensure fresh build
    
    def _ensure_graph(self):
        """Ensure graph is built."""
        if self.graph is None:
            self.graph = self.build_graph()

    @graph(name="exchange_graph")
    def build_graph(self) -> CompiledStateGraph:
        """
        Constructs and compiles a LangGraph instance.

        This function initializes a `SupervisorAgent` to create the base graph structure
        and uses an `InMemorySaver` as the checkpointer for the compilation process.

        The resulting compiled graph can be used to execute Supervisor workflow in LangGraph Studio.

        Returns:
        CompiledGraph: A fully compiled LangGraph instance ready for execution.
        """
        model = get_llm()

        # initialize the flavor profile tool(used for coffee flavor, taste, or sensory profile estimation) with the farm agent card
        flavor_profile_tool = FlavorProfileTool(
            remote_agent_card=farm_agent_card,
        )
        
        # initialize the weather tool for getting weather information
        weather_tool = WeatherTool()
        
        #  worker agent- always responsible for flavor, taste, or sensory profile of coffee queries
        get_flavor_profile_a2a_agent = create_react_agent(
            model=model,
            tools=[flavor_profile_tool],  # list of tools for the agent
            name="get_flavor_profile_via_a2a",
        )
        
        # worker agent for weather queries
        get_weather_agent = create_react_agent(
            model=model,
            tools=[weather_tool],  # list of tools for the agent
            name="get_weather_info",
        )
        
        graph = create_supervisor(
            model=model,
            agents=[get_flavor_profile_a2a_agent, get_weather_agent],  # worker agents list
            prompt=(
            "You are a routing supervisor agent. You have access to tools that allow you to transfer queries to specialized worker agents.\n"
            "\n"
            "Available worker agents:\n"
            "- get_weather_info: Handles all weather-related queries (use tool: transfer_to_get_weather_info)\n"
            "- get_flavor_profile_via_a2a: Handles coffee flavor, taste, and sensory profile queries (use tool: transfer_to_get_flavor_profile_via_a2a)\n"
            "\n"
            "Your routing rules:\n"
            "1. If the user asks about your capabilities:\n"
            "   - Respond: \"I can help you learn about coffee flavor profiles, taste characteristics, and sensory profiles, as well as get weather information for coffee regions. "
            "   You can ask me questions like: What are the flavor notes of Colombian coffee in winter? What's the weather like in Colombia? Get the current weather for Brazil.\"\n"
            "\n"
            "2. If the user prompt mentions weather, temperature, climate, current conditions, or asks 'get weather', 'what's the weather', 'weather in', 'weather for':\n"
            "   - YOU MUST call the tool: transfer_to_get_weather_info\n"
            "   - Pass the location/region from the user's query\n"
            "   - Do NOT respond directly about weather\n"
            "\n"
            "3. If the user prompt mentions coffee flavor, taste, or sensory profile:\n"
            "   - Call the tool: transfer_to_get_flavor_profile_via_a2a\n"
            "   - Do NOT respond directly about flavor\n"
            "\n"
            "4. If the worker agent returns a result:\n"
            "   - Return that result to the user\n"
            "\n"
            "5. If the query doesn't match rules 1-3:\n"
            "   - Respond: \"I'm sorry, I cannot assist with that request. I specialize in coffee flavor profiles, taste characteristics, sensory profiles, and weather information for coffee regions. "
            "   You can ask me about coffee flavors for different regions and seasons, weather conditions in coffee-growing areas, or ask 'what can you do' to learn more about my capabilities.\"\n"
            "\n"
            "CRITICAL: For weather queries, you MUST use the transfer_to_get_weather_info tool. Do not try to answer weather questions yourself.\n"
            ),
            add_handoff_back_messages=False,
            output_mode="last_message",
        ).compile()
        logger.debug("LangGraph supervisor created and compiled successfully.")
        return graph

    async def serve(self, prompt: str):
        """
        Processes the input prompt and returns a response from the graph.
        Args:
            prompt (str): The input prompt to be processed by the graph.
        Returns:
            str: The response generated by the graph based on the input prompt.
        """
        try:
            # build graph if not already built
            self._ensure_graph()
            logger.debug(f"Received prompt: {prompt}")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Prompt must be a non-empty string.")
            # session_start()
            result = await self.graph.ainvoke({
                "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
                ],
            }, {"configurable": {"thread_id": uuid.uuid4()}})

            messages = result.get("messages", [])
            if not messages:
                raise RuntimeError("No messages found in the graph response.")

            # Find the last AIMessage with non-empty content
            for message in reversed(messages):
                if isinstance(message, AIMessage) and message.content.strip():
                    logger.debug(f"Valid AIMessage found: {message.content.strip()}")
                    return message.content.strip()

            raise RuntimeError("No valid AIMessage found in the graph response.")
        except ValueError as ve:
            logger.error(f"ValueError in serve method: {ve}")
            raise ValueError(str(ve))
        except Exception as e:
            logger.error(f"Error in serve method: {e}")
            raise Exception(str(e))
