# Configuration Example
# Copy this file to config.py and fill in your actual API keys

# OpenRouter API Key (for OpenAI, Qwen, Llama models)
OPENROUTER_API_KEY = "your_openrouter_api_key_here"

# Google AI API Key (for Gemini models)
GOOGLE_API_KEY = "your_google_ai_api_key_here"

# OpenAI API Key (if using OpenAI directly)
OPENAI_API_KEY = "your_openai_api_key_here"

# AI Studio API Key (if using AI Studio)
AI_STUDIO_API_KEY = "your_aistudio_api_key_here"

# Model configurations
MODEL_CONFIGS = {
    "openai": {
        "model_name": "openai/gpt-4o-mini",
        "api_key": OPENROUTER_API_KEY,
        "base_url": "https://openrouter.ai/api/v1"
    },
    "qwen": {
        "model_name": "qwen/qwen2.5-vl-72b-instruct:free",
        "api_key": OPENROUTER_API_KEY,
        "base_url": "https://openrouter.ai/api/v1"
    },
    "llama": {
        "model_name": "meta-llama/llama-4-maverick",
        "api_key": OPENROUTER_API_KEY,
        "base_url": "https://openrouter.ai/api/v1"
    },
    "gemini": {
        "model_name": "google/gemini-2.5-flash-preview-05-20:thinking",
        "api_key": GOOGLE_API_KEY,
        "base_url": None
    },
    "gemini_pro": {
        "model_name": "google/gemini-2.5-pro",
        "api_key": GOOGLE_API_KEY,
        "base_url": None
    }
} 