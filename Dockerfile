FROM python:3.12-slim-buster

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DOCKER_CONTAINER=1

# Add build argument for agent selection
ARG AGENT_TYPE=aider
ENV AGENT_TYPE=${AGENT_TYPE}

RUN apt-get update -y && \
    apt-get install -y git curl && \
    apt-get clean

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies based on AGENT_TYPE
RUN if [ "$AGENT_TYPE" = "aider" ]; then \
        poetry install --no-root --only main,aider; \
    elif [ "$AGENT_TYPE" = "open-hands" ]; then \
        poetry install --no-root --only main,open-hands; \
    elif [ "$AGENT_TYPE" = "raaid" ]; then \
        poetry install --no-root --only main,raaid; \
    else \
        echo "Invalid AGENT_TYPE specified" && exit 1; \
    fi

# Copy application code
COPY . .

# Create a non-root user and log directory
RUN useradd -m appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app
USER appuser

# Run the application using poetry
CMD ["poetry", "run", "python", "-u", "main.py"]
