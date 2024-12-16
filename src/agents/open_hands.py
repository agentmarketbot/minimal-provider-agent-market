import os
from datetime import datetime

from dotenv import load_dotenv

from src.enums import ModelName

load_dotenv()


_MODEL_ALIAS_TO_MODEL: dict[ModelName, str] = {
    ModelName.gpt_4o: "openai/gpt-4o",
}

_MODEL_ALIAS_TO_API_KEY_ENV_VAR_NAME: dict[ModelName, str] = {
    ModelName.gpt_4o: "OPENAI_API_KEY",
}


def get_container_kwargs(
    repo_directory: str,
    solver_command: str,
    model_name: ModelName,
) -> str:
    docker_image = "docker.all-hands.dev/all-hands-ai/openhands:0.15"
    entrypoint = [
        "/bin/bash",
        "-c",
        "python",
        "-m",
        "openhands.core.main",
        "-t",
        "write a bash script that prints hi",
        # solver_command,
        "--no-auto-continue" "&&",
        "sleep 240",
    ]
    env_vars = {
        "SANDBOX_RUNTIME_CONTAINER_IMAGE": "docker.all-hands.dev/all-hands-ai/runtime:0.15-nikolaik",  # noqa E501
        "SANDBOX_USER_ID": str(os.getuid()),
        "WORKSPACE_MOUNT_PATH": os.getenv("WORKSPACE_BASE"),
        "LLM_API_KEY": os.getenv(_MODEL_ALIAS_TO_API_KEY_ENV_VAR_NAME[model_name]),
        "LLM_MODEL": _MODEL_ALIAS_TO_MODEL.get(model_name, model_name.value),
        "LOG_ALL_EVENTS": "true",
    }
    volumes = {
        repo_directory: {"bind": "/opt/workspace_base", "mode": "rw"},
        "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
    }
    container_name = f"openhands-app-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    kwargs = {
        "image": docker_image,
        "entrypoint": entrypoint,
        "environment": env_vars,
        "volumes": volumes,
        "container_name": container_name,
    }
    return kwargs
