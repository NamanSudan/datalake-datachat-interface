"""
Central configuration for vLLM deployment
"""
import os

# Model settings
DEFAULT_MODEL_NAME = "mistral/Mistral-7B-Instruct-v0.1"
MODEL_PATH = "/app/models/mistral-7b-instruct"

# Environment-based configuration
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
ENABLE_QUANTIZATION = os.getenv("ENABLE_QUANTIZATION", "false").lower() == "true"
QUANTIZATION_TYPE = os.getenv("QUANTIZATION_TYPE", "int8")

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Resource settings
MAX_MODEL_LEN = int(os.getenv("MAX_MODEL_LEN", "2048")) 