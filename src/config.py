import os

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

from src.enums import AgentType, ModelName

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str = Field(..., description="The API key for OpenAI.")
    github_pat: str = Field(..., description="The personal access token for GitHub.")
    github_username: str = Field(..., description="The GitHub username.")
    github_email: str = Field(..., description="The GitHub email.")

    market_url: str = Field("https://api.agent.market", description="The URL for the market.")
    market_api_key: str = Field(..., description="The API key for the market.")

    market_open_instance_code: int = Field(
        0, description="The code for an open instance in the market."
    )
    market_resolved_instance_code: int = Field(
        3, description="The code for a resolved instance in the market."
    )
    market_awarded_proposal_code: int = Field(
        1, description="The code for an awarded proposal in the market."
    )

    max_bid: float = Field(0.01, gt=0, description="The maximum bid for a proposal.")
    agent_type: AgentType = Field(..., description="The type of agent to use.")

    anthropic_api_key: str | None = Field(None, description="The API key for Anthropic.")

    class Config:
        case_sensitive = False

    @model_validator(mode="after")
    def validate_model(self) -> "Settings":
        if self.agent_type == AgentType.raaid and self.anthropic_api_key is None:
            raise ValueError("anthropic_api_key is required when agent_type is raaid")

        return self

    @classmethod
    def load_settings(cls) -> "Settings":
        aws_execution_env = os.getenv("AWS_EXECUTION_ENV")
        if aws_execution_env:
            secret_arn = os.getenv("AWS_SECRET_ARN")
            if not secret_arn:
                raise ValueError("AWS_SECRET_ARN environment variable is not set.")

            secret_data = cls.fetch_secret(secret_arn)
            os.environ.update(secret_data)

        return cls()


SETTINGS = Settings.load_settings()
