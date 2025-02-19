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
    pip install ra-aid==0.11.3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/venv/bin:$PATH"
ENV AIDER_FLAGS="architect=true,model=openrouter/deepseek/deepseek-r1,editor-model=bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"
ENV OPENAI_API_BASE="https://openrouter.ai/api/v1"
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""

