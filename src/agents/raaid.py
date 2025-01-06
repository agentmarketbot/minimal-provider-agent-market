import os

from src.config import SETTINGS


def get_container_kwargs(
    repo_directory: str,
    solver_command: str,
) -> str:
    escaped_solver_command = solver_command.replace("'", "'\"'\"'")
    entrypoint = [
        "/bin/bash",
        "-c",
        (
            "source /venv/bin/activate && "
            f"ra-aid -m '{escaped_solver_command}' --provider openai --model bedrock-claude-v2 --cowboy-mode"  # noqa: E501
        ).strip(),
    ]

    env_vars = {
        "OPENAI_API_BASE": SETTINGS.openai_api_base,
    }

    volumes = {
        f"{repo_directory}/.": {"bind": "/app", "mode": "rw"},
        "/tmp/aider_cache": {"bind": "/home/ubuntu", "mode": "rw"},
    }
    user = f"{os.getuid()}:{os.getgid()}"
    kwargs = {
        "image": "aider-raaid",
        "entrypoint": entrypoint,
        "environment": env_vars,
        "volumes": volumes,
        "user": user,
    }
    return kwargs
