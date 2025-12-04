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
from weather.card import AGENT_CARD as weather_agent_card

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
        
        # initialize the weather tool for getting weather information with the weather agent card
        weather_tool = WeatherTool(
            remote_agent_card=weather_agent_card,
        )
        
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
            "You are a routing supervisor. Your job is SIMPLE: route queries to worker agents and return their results.\n"
            "\n"
            "Worker agents:\n"
            "- get_weather_info: Weather queries (tool: transfer_to_get_weather_info)\n"
            "- get_flavor_profile_via_a2a: Flavor queries (tool: transfer_to_get_flavor_profile_via_a2a)\n"
            "\n"
            "DECISION TREE:\n"
            "\n"
            "1. Is this a weather query? (contains: weather, temperature, climate, current conditions)\n"
            "   → YES: Call transfer_to_get_weather_info → When you see the result, return it EXACTLY → END\n"
            "   → NO: Continue to step 2\n"
            "\n"
            "2. Is this a flavor query? (contains: flavor, taste, sensory, profile, notes, aroma, acidity, body)\n"
            "   → YES: Call transfer_to_get_flavor_profile_via_a2a → When you see the result, return it EXACTLY → END\n"
            "   → NO: Continue to step 3\n"
            "\n"
            "3. Is this a capability question? (what can you do, help, capabilities)\n"
            "   → YES: Respond: \"I can help you learn about coffee flavor profiles, taste characteristics, and sensory profiles, as well as get weather information for coffee regions. You can ask me questions like: What are the flavor notes of Colombian coffee in winter? What's the weather like in Colombia? Get the current weather for Brazil.\" → END\n"
            "   → NO: Continue to step 4\n"
            "\n"
            "4. Unknown query\n"
            "   → Respond: \"I'm sorry, I cannot assist with that request. I specialize in coffee flavor profiles, taste characteristics, sensory profiles, and weather information for coffee regions. You can ask me about coffee flavors for different regions and seasons, weather conditions in coffee-growing areas, or ask 'what can you do' to learn more about my capabilities.\" → END\n"
            "\n"
            "CRITICAL: When a worker agent returns a result:\n"
            "- The result is the FINAL ANSWER\n"
            "- Copy it EXACTLY - do not modify, summarize, or add anything\n"
            "- Return it immediately\n"
            "- DO NOT call any tools\n"
            "- DO NOT route again\n"
            "- The conversation is COMPLETE\n"
            "\n"
            "STOP CONDITIONS:\n"
            "- After calling a tool and receiving a result → STOP\n"
            "- After responding to capability question → STOP\n"
            "- After responding to unknown query → STOP\n"
            "- NEVER continue after any of these\n"
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
            result = await self.graph.ainvoke(
                {
                    "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                    ],
                },
                {
                    "configurable": {
                        "thread_id": str(uuid.uuid4()),
                    },
                    "recursion_limit": 100
                }
            )

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
