# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
from pydantic import BaseModel
import uvicorn
import uuid
import json
from dotenv import load_dotenv
from ioa_observe.sdk import Observe
from ioa_observe.sdk.tracing import session_start
from config.logging_config import setup_logging
from graph.graph import ExchangeGraph

setup_logging()
logger = logging.getLogger("corto.supervisor.main")
load_dotenv()
Observe.init("corto_exchange", api_endpoint=os.getenv("OTLP_HTTP_ENDPOINT"))

# Initialize SLIM instrumentation with error handling
# Skip if OpenTelemetry requests instrumentation is not available
try:
    import importlib
    import logging as std_logging
    # Check if opentelemetry.instrumentation.requests is available
    importlib.import_module('opentelemetry.instrumentation.requests')
    # Only import and use SLIMInstrumentor if the dependency is available
    from ioa_observe.sdk.instrumentations.slim import SLIMInstrumentor
    # Temporarily suppress ERROR level for root logger to avoid instrumentation errors
    root_logger = std_logging.getLogger('root')
    original_level = root_logger.level
    root_logger.setLevel(std_logging.WARNING)
    try:
        instrumentor = SLIMInstrumentor()
        instrumentor.instrument()
    finally:
        root_logger.setLevel(original_level)
except (ImportError, Exception):
    # Missing optional dependency or other error - skip instrumentation silently
    pass

app = FastAPI()
# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # Replace "*" with specific origins if needed
  allow_credentials=True,
  allow_methods=["*"],  # Allow all HTTP methods
  allow_headers=["*"],  # Allow all headers
)

exchange_graph = ExchangeGraph()

class PromptRequest(BaseModel):
  prompt: str
  thread_id: Optional[str] = None
  stream: bool = False

@app.post("/agent/prompt")
async def handle_prompt(request: PromptRequest):
  """
  Processes a user prompt by routing it through the ExchangeGraph.

  Args:
      request (PromptRequest): Contains the input prompt, optional thread_id, and stream flag.

  Returns:
      dict: A dictionary containing the agent's response and thread_id.
      Or StreamingResponse if stream=True.

  Raises:
      HTTPException: 400 for invalid input, 500 for server-side errors.
  """
  logger.info(f"[handle_prompt] Received request - prompt: {request.prompt[:50]}..., thread_id: {request.thread_id}, stream: {request.stream}")
  try:
    session_start() # Start a new tracing session
    
    # Generate or use provided thread_id
    thread_id = request.thread_id or str(uuid.uuid4())
    logger.info(f"[handle_prompt] Using thread_id: {thread_id}")
    
    if request.stream:
      # Streaming response
      async def generate():
        try:
          async for chunk in exchange_graph.serve_stream(request.prompt, thread_id):
            yield f"data: {json.dumps(chunk)}\n\n"
          yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"
        except Exception as e:
          error_chunk = {"error": str(e), "thread_id": thread_id}
          yield f"data: {json.dumps(error_chunk)}\n\n"
      
      return StreamingResponse(generate(), media_type="text/event-stream")
    else:
      # Non-streaming response
      logger.info(f"[handle_prompt] Calling exchange_graph.serve() for non-streaming request")
      result = await exchange_graph.serve(request.prompt, thread_id)
      logger.info(f"[handle_prompt] Final result from LangGraph: {result}")
      return {"response": result, "thread_id": thread_id}
  except ValueError as ve:
    logger.exception(f"ValueError occurred: {str(ve)}")
    raise HTTPException(status_code=400, detail=str(ve))
  except Exception as e:
    logger.exception(f"An error occurred: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Run the FastAPI server using uvicorn
if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
