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
from graph.tools import FlavorProfileTool
from graph.weather_worker import create_weather_worker_agent

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
        
        #  worker agent- always responsible for flavor, taste, or sensory profile of coffee queries
        get_flavor_profile_a2a_agent = create_react_agent(
            model=model,
            tools=[flavor_profile_tool],  # list of tools for the agent
            name="get_flavor_profile_via_a2a",
        )
        
        # worker agent for weather queries - encapsulates A2A communication internally
        logger.info("[build_graph] Creating weather worker agent (self-contained)")
        get_weather_agent = create_weather_worker_agent()
        logger.info(f"[build_graph] Weather worker agent created: {get_weather_agent}")
        
        # Improved supervisor prompt with explicit weather query detection
        supervisor_prompt = (
            "You are a routing supervisor. Your ONLY job is to route queries to the correct worker agent.\n"
            "\n"
            "AVAILABLE WORKER AGENTS:\n"
            "1. get_weather_info - Use tool: transfer_to_get_weather_info\n"
            "2. get_flavor_profile_via_a2a - Use tool: transfer_to_get_flavor_profile_via_a2a\n"
            "\n"
            "ROUTING RULES (FOLLOW STRICTLY):\n"
            "\n"
            "STEP 1: Check for WEATHER queries FIRST\n"
            "  - Keywords: 'weather', 'temperature', 'climate', 'current conditions', 'wind', 'forecast', 'meteorological'\n"
            "  - Phrases: 'what's the weather', 'get weather', 'weather in', 'temperature in', 'current weather'\n"
            "  - Examples: 'Get the current weather for Brazil', 'What's the weather like in Colombia?', 'Temperature in Vietnam'\n"
            "  - ACTION: If ANY weather-related keyword or phrase is present → IMMEDIATELY call transfer_to_get_weather_info\n"
            "  - DO NOT continue to other steps if this is a weather query\n"
            "\n"
            "STEP 2: Check for FLAVOR queries\n"
            "  - Keywords: 'flavor', 'taste', 'sensory', 'profile', 'notes', 'aroma', 'acidity', 'body', 'tasting'\n"
            "  - Phrases: 'flavor notes', 'taste profile', 'what does it taste like', 'flavor characteristics'\n"
            "  - Examples: 'What are the flavor notes of Colombian coffee?', 'Describe the taste of Brazilian coffee'\n"
            "  - ACTION: If flavor-related → call transfer_to_get_flavor_profile_via_a2a\n"
            "\n"
            "STEP 3: Check for CAPABILITY questions\n"
            "  - Phrases: 'what can you do', 'help', 'capabilities', 'what do you do'\n"
            "  - ACTION: Respond with: \"I can help you learn about coffee flavor profiles, taste characteristics, and sensory profiles, as well as get weather information for coffee regions. You can ask me questions like: What are the flavor notes of Colombian coffee in winter? What's the weather like in Colombia? Get the current weather for Brazil.\"\n"
            "\n"
            "STEP 4: Unknown queries\n"
            "  - ACTION: Respond: \"I'm sorry, I cannot assist with that request. I specialize in coffee flavor profiles, taste characteristics, sensory profiles, and weather information for coffee regions. You can ask me about coffee flavors for different regions and seasons, weather conditions in coffee-growing areas, or ask 'what can you do' to learn more about my capabilities.\"\n"
            "\n"
            "CRITICAL RULES:\n"
            "- ALWAYS check for weather queries FIRST before checking flavor queries\n"
            "- When you call a transfer tool and get a result, return that result EXACTLY as-is\n"
            "- DO NOT modify, summarize, or add anything to worker agent responses\n"
            "- DO NOT call multiple tools - one query = one tool call\n"
            "- After receiving a result from a worker agent, STOP immediately\n"
        )
        
        logger.info("[build_graph] Creating supervisor with improved routing prompt")
        graph = create_supervisor(
            model=model,
            agents=[get_flavor_profile_a2a_agent, get_weather_agent],  # worker agents list
            prompt=supervisor_prompt,
            add_handoff_back_messages=False,
            output_mode="last_message",
        ).compile()
        logger.debug("LangGraph supervisor created and compiled successfully.")
        return graph

    async def serve(self, prompt: str, thread_id: str = None):
        """
        Processes the input prompt and returns a response from the graph.
        Args:
            prompt (str): The input prompt to be processed by the graph.
            thread_id (str, optional): Thread ID for conversation continuity. If None, generates a new one.
        Returns:
            str: The response generated by the graph based on the input prompt.
        """
        try:
            # build graph if not already built
            self._ensure_graph()
            logger.info(f"[ExchangeGraph.serve] Received prompt: {prompt}")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Prompt must be a non-empty string.")
            
            # Use provided thread_id or generate a new one
            if thread_id is None:
                thread_id = str(uuid.uuid4())
            
            logger.info(f"[ExchangeGraph.serve] Invoking graph with thread_id: {thread_id}")
            logger.info(f"[ExchangeGraph.serve] Query content: '{prompt}'")
            
            # Log query classification hints
            weather_keywords = ['weather', 'temperature', 'climate', 'current conditions', 'wind', 'forecast']
            flavor_keywords = ['flavor', 'taste', 'sensory', 'profile', 'notes', 'aroma', 'acidity', 'body']
            prompt_lower = prompt.lower()
            has_weather = any(kw in prompt_lower for kw in weather_keywords)
            has_flavor = any(kw in prompt_lower for kw in flavor_keywords)
            logger.info(f"[ExchangeGraph.serve] Query classification: weather={has_weather}, flavor={has_flavor}")
            
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
                        "thread_id": thread_id,
                    },
                    "recursion_limit": 100
                }
            )
            
            logger.info("[ExchangeGraph.serve] Graph execution completed, extracting result...")

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

    async def serve_stream(self, prompt: str, thread_id: str = None):
        """
        Processes the input prompt and streams responses from the graph.
        Args:
            prompt (str): The input prompt to be processed by the graph.
            thread_id (str, optional): Thread ID for conversation continuity. If None, generates a new one.
        Yields:
            dict: Streaming chunks with content and thread_id.
        """
        try:
            # build graph if not already built
            self._ensure_graph()
            logger.debug(f"Received streaming prompt: {prompt}")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Prompt must be a non-empty string.")
            
            # Use provided thread_id or generate a new one
            if thread_id is None:
                thread_id = str(uuid.uuid4())
            
            # Stream the graph execution
            async for event in self.graph.astream(
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
                        "thread_id": thread_id,
                    },
                    "recursion_limit": 100
                }
            ):
                # Extract messages from the event
                if "messages" in event:
                    messages = event["messages"]
                    # Find the last AIMessage with content
                    for message in reversed(messages):
                        if isinstance(message, AIMessage) and message.content.strip():
                            yield {
                                "content": message.content.strip(),
                                "thread_id": thread_id
                            }
                            break
        except ValueError as ve:
            logger.error(f"ValueError in serve_stream method: {ve}")
            yield {"error": str(ve), "thread_id": thread_id}
        except Exception as e:
            logger.error(f"Error in serve_stream method: {e}")
            yield {"error": str(e), "thread_id": thread_id}
