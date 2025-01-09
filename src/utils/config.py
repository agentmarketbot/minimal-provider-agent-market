import os

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "anything")  # Default to "anything" for local testing
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "bedrock-claude-v2")