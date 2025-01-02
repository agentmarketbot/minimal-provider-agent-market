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
            "source /venv/bin/activate && " f"ra-aid -m '{escaped_solver_command}' --cowboy-mode"
        ).strip(),
    ]

    env_vars = {
        "ANTHROPIC_API_KEY": SETTINGS.anthropic_api_key,
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
