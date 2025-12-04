# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

# logging_config.py
import logging

from config.config import LOGGING_LEVEL

def setup_logging():
    logging.basicConfig(
        level=LOGGING_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )

    # Set specific logging levels for noisy libraries
    logging.basicConfig(level=logging.INFO)  # default
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Enable debug logging for SLIM gateway operations (if LOGGING_LEVEL is DEBUG)
    if LOGGING_LEVEL == "DEBUG":
        logging.getLogger("agntcy_app_sdk.transports.slim").setLevel(logging.DEBUG)
        logging.getLogger("agntcy_app_sdk.transports.slim.gateway").setLevel(logging.DEBUG)
        logging.getLogger("agntcy_app_sdk.factory").setLevel(logging.DEBUG)