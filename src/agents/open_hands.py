import os
from datetime import datetime

from dotenv import load_dotenv

from src.config import SETTINGS

load_dotenv()

_DOCKER_IMAGE = "docker.all-hands.dev/all-hands-ai/openhands:0.15"
_RUNTIME_IMAGE = "docker.all-hands.dev/all-hands-ai/runtime:0.15-nikolaik"
_DOCKER_NETWORK_HOST = ["host.docker.internal:host-gateway"]


def get_container_kwargs(
    repo_directory: str,
    solver_command: str,
) -> str:
    solver_command += (
        "\n\n=== SYSTEM REQUIREMENTS ===\n"
        "MAKE SURE YOU COMMIT TO THE REPOSITORY THE CHANGES PROPOSED. "
        "NEVER PUSH THE CHANGES. "
        "ALWAYS STAY IN THE SAME REPOSITORY BRANCH."
    )
    entrypoint = ["python", "-m", "openhands.core.main", "-t", solver_command, "--no-auto-continue"]
    env_vars = {
        "SANDBOX_RUNTIME_CONTAINER_IMAGE": _RUNTIME_IMAGE,
        "SANDBOX_USER_ID": str(os.getuid()),
        "GITHUB_TOKEN": SETTINGS.github_pat,
        "GITHUB_USERNAME": SETTINGS.github_username,
        "GITHUB_EMAIL": SETTINGS.github_email,
        "WORKSPACE_MOUNT_PATH": repo_directory,
        "LLM_API_KEY": SETTINGS.openai_api_key,
        "LLM_MODEL": "openai/gpt-4o",
        "LOG_ALL_EVENTS": "true",
        "GIT_ASKPASS": "echo",
        "GIT_TERMINAL_PROMPT": "0",
    }
    volumes = {
        repo_directory: {"bind": "/opt/workspace_base", "mode": "rw"},
        "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
    }
    container_name = f"openhands-app-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    kwargs = {
        "image": _DOCKER_IMAGE,
        "entrypoint": entrypoint,
        "environment": env_vars,
        "volumes": volumes,
        "name": container_name,
        "extra_hosts": _DOCKER_NETWORK_HOST,
    }
    return kwargs
