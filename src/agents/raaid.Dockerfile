FROM python:3.10-slim

SHELL ["/bin/bash", "-c"]
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ripgrep \
      git \
      ca-certificates \
      curl \
      libssl-dev && \
    update-ca-certificates && \
    python -m venv /venv && \
    . /venv/bin/activate && \
    pip install --upgrade pip && \
    pip install ra-aid==0.13.2 && \
    pip install boto3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure Git
RUN git config --global user.email "agentmarketbot@gmail.com" && \
    git config --global user.name "minimalProviderAgentMarket"

USER root
WORKDIR /app
RUN chmod -R 777 /app
RUN chmod -R 777 /venv


ENV PATH="/venv/bin:$PATH"
ENV AIDER_FLAGS="architect,model=openrouter/deepseek/deepseek-r1,editor-model=bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"