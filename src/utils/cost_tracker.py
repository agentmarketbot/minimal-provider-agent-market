from datetime import datetime
import logging
from typing import Dict

from src.enums import ModelName, ProviderType

# Cost per 1K tokens in USD
MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o": {
        "input": 0.01,
        "output": 0.03
    },
    "bedrock-claude-v2": {
        "input": 0.008,
        "output": 0.024
    },
    "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0": {
        "input": 0.008,
        "output": 0.024
    },
    "openrouter/deepseek/deepseek-r1": {
        "input": 0.0015,
        "output": 0.0015
    },
    "o3-mini": {
        "input": 0.0015,
        "output": 0.002
    }
}

class CostTracker:
    def __init__(self, model_name: ModelName, provider: ProviderType):
        self.model_name = model_name.value
        self.provider = provider
        self.logger = logging.getLogger("cost_tracker")
        self.logger.setLevel(logging.INFO)
        
        # Create a file handler
        handler = logging.FileHandler(f"api_costs_{datetime.now().strftime('%Y%m%d')}.log")
        handler.setLevel(logging.INFO)
        
        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        self.logger.addHandler(handler)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of an API interaction."""
        if self.model_name not in MODEL_COSTS:
            self.logger.warning(f"No cost information available for model {self.model_name}")
            return 0.0

        costs = MODEL_COSTS[self.model_name]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        total_cost = input_cost + output_cost
        
        return total_cost

    def log_interaction(self, input_tokens: int, output_tokens: int) -> None:
        """Log the cost of an API interaction."""
        cost = self.calculate_cost(input_tokens, output_tokens)
        self.logger.info(
            f"API Interaction - Model: {self.model_name}, Provider: {self.provider}, "
            f"Input Tokens: {input_tokens}, Output Tokens: {output_tokens}, "
            f"Cost: ${cost:.4f}"
        )