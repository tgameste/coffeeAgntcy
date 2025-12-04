# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    UnsupportedOperationError,
    JSONRPCResponse,
    ContentTypeNotSupportedError,
    InternalError,
    Task)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from agent import WeatherAgent

logger = logging.getLogger("corto.weather_agent.a2a_executor")

class WeatherAgentExecutor(AgentExecutor):
    """
    This class extends the base `AgentExecutor` and executes requests on behalf of the Weather 
    Agent in an Agent-to-Agent (A2A) architecture.

    This executor handles user prompts related to weather information and retrieves current weather
    data using geocoding and weather APIs. It validates incoming requests, interacts with the 
    WeatherAgent for weather retrieval, and publishes appropriate events (e.g., messages or tasks) 
    to the event queue.

    """
    def __init__(self):
        self.agent = WeatherAgent()

    def _validate_request(self, context: RequestContext) -> JSONRPCResponse | None:
        """
        Validates the incoming request context.

        Ensures that the context contains a valid message with content parts.
        If the request is invalid, returns an appropriate JSON-RPC error response.

        Args:
            context (RequestContext): The incoming request context to validate.

        Returns:
            JSONRPCResponse | None: An error response if validation fails, otherwise None.
        """
        if not context or not context.message or not context.message.parts:
            logger.error("Invalid request parameters: %s", context)
            return JSONRPCResponse(error=ContentTypeNotSupportedError())
        return None
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Processes a user prompt to retrieve weather information via the WeatherAgent.

        This method extracts the user prompt (location) from the request context, invokes the 
        WeatherAgent asynchronously to get weather information, and publishes the result as an event.
        If the location is invalid or processing fails, it returns an error message.

        If no current task is associated with the request, a new task is created and emitted.

        Args:
            context (RequestContext): The request context containing message and task metadata.
            event_queue (EventQueue): The queue used to emit events (messages, tasks, etc.).

        Raises:
            ServerError: If an unexpected error occurs during weather retrieval.
        """

        logger.info("Received message request: %s", context.message)

        validation_error = self._validate_request(context)
        if validation_error:
            event_queue.enqueue_event(validation_error)
            return
        
        location = context.get_user_input()
        if not location:
            logger.warning("Empty or missing location in user input.")
            event_queue.enqueue_event(
                new_agent_text_message("No valid location provided.")
            )
            return
        task = context.current_task
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)

        try:
            output = await self.agent.ainvoke(location)
            if output.get("error_message") is not None and output.get("error_message") != "":
                logger.error("Error in agent response: %s", output.get("error_message"))
                message = new_agent_text_message(
                    output.get("error_message", "Failed to retrieve weather information"),
                )
                event_queue.enqueue_event(message)
                return

            weather_info = output.get("weather_info", "No weather information returned")
            logger.info("Weather information retrieved: %s", weather_info)
            event_queue.enqueue_event(new_agent_text_message(weather_info))
        except Exception as e:
            logger.error(f'An error occurred while retrieving weather information: {e}')
            raise ServerError(error=InternalError()) from e
        
    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        """
        Cancel this agent's execution for the given request context.
        
        Args:
            request (RequestContext): The request to cancel.
            event_queue (EventQueue): The event queue to potentially emit cancellation events.

        Raises:
            ServerError: Always raised due to unsupported operation.
        """
        raise ServerError(error=UnsupportedOperationError())

