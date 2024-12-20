"""
Script to set up and verify vLLM installation on ARM
"""
import os
import sys
import logging
from pathlib import Path
import torch
from vllm import LLM, SamplingParams
from huggingface_hub import login
from config import (
    DEFAULT_MODEL_NAME, MODEL_PATH, HUGGING_FACE_TOKEN,
    ENABLE_QUANTIZATION, QUANTIZATION_TYPE, MAX_MODEL_LEN
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_huggingface_auth():
    """Setup Hugging Face authentication if token is provided"""
    if HUGGING_FACE_TOKEN:
        logger.info("Setting up Hugging Face authentication...")
        login(token=HUGGING_FACE_TOKEN, write_permission=False)
        logger.info("Hugging Face authentication completed")

def verify_system_requirements():
    """Verify system meets minimum requirements for vLLM"""
    logger.info("Verifying system requirements...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        raise RuntimeError("Python 3.8 or higher is required")
    
    # Check CPU architecture
    import platform
    if platform.machine() not in ('arm64', 'aarch64'):
        raise RuntimeError("ARM64 architecture is required")
    
    logger.info("System requirements verified successfully")

def setup_model_directory():
    """Create and setup model directory"""
    model_dir = Path("/app/models")
    model_dir.mkdir(exist_ok=True, parents=True)
    
    # Also create data directory
    data_dir = Path("/app/data")
    data_dir.mkdir(exist_ok=True, parents=True)
    
    # Set appropriate permissions
    os.chmod(model_dir, 0o755)
    os.chmod(data_dir, 0o755)
    
    return model_dir

def initialize_vllm():
    """Initialize vLLM and verify it's working"""
    logger.info("Initializing vLLM...")
    
    try:
        # Create a simple LLM instance
        sampling_params = SamplingParams(temperature=0.8, top_p=0.95)
        
        # Configure model settings
        model_kwargs = {
            "model": DEFAULT_MODEL_NAME,
            "download_dir": "/app/models",
            "max_model_len": MAX_MODEL_LEN,
        }
        
        # Add quantization if enabled
        if ENABLE_QUANTIZATION:
            model_kwargs["quantization"] = QUANTIZATION_TYPE
            logger.info(f"Enabling {QUANTIZATION_TYPE} quantization")
        
        llm = LLM(**model_kwargs)
        
        # Test with a simple prompt
        prompt = "Hello, how are you?"
        outputs = llm.generate([prompt], sampling_params)
        
        if outputs:
            logger.info("vLLM initialization successful")
            return True
            
    except Exception as e:
        logger.error(f"Error initializing vLLM: {str(e)}")
        raise
    
    return False

def main():
    """Main function to setup vLLM"""
    try:
        verify_system_requirements()
        setup_huggingface_auth()
        model_dir = setup_model_directory()
        if initialize_vllm():
            logger.info("vLLM setup completed successfully")
        else:
            logger.error("Failed to initialize vLLM")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 