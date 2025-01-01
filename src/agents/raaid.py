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
            "apt-get update && "
            "apt-get install -y ripgrep && "
            "source /venv/bin/activate && "
            "pip install ra-aid && "
            f"ra-aid -m '{escaped_solver_command}' "
        ).strip(),
    ]

    env_vars = {
        "ANTHROPIC_API_KEY": SETTINGS.anthropic_api_key,
    }

    volumes = {
        f"{repo_directory}/.": {"bind": "/app", "mode": "rw"},
        "/tmp/aider_cache": {"bind": "/home/ubuntu", "mode": "rw"},
    }
    kwargs = {
        "image": "paulgauthier/aider",
        "entrypoint": entrypoint,
        "environment": env_vars,
        "volumes": volumes,
    }
    return kwargs
