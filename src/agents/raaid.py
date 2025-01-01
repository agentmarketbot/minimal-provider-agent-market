import os

from src.config import settings


def get_container_kwargs(
    repo_directory: str,
    solver_command: str,
) -> str:
    escaped_solver_command = solver_command.replace("'", "'\"'\"'")
    entrypoint = [
        "/bin/bash",
        "-c",
        (
            "apt-get install ripgrep && "
            "source /venv/bin/activate && "
            "pip install ra-aid && "
            f"ra-aid -m '{escaped_solver_command}' "
        ).strip(),
    ]

    env_vars = {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
    }

    volumes = {
        f"{repo_directory}/.": {"bind": "/app", "mode": "rw"},
        "/tmp/aider_cache": {"bind": "/home/ubuntu", "mode": "rw"},
    }
    user = f"{os.getuid()}:{os.getgid()}"
    kwargs = {
        "image": "paulgauthier/aider",
        "entrypoint": entrypoint,
        "environment": env_vars,
        "user": user,
        "volumes": volumes,
    }
    return kwargs
