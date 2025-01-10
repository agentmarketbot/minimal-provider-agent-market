import os
import shlex
from loguru import logger


def get_container_kwargs(
    repo_directory: str,
    model_name: str,
    solver_command: str,
    test_command: str,
) -> str:
    escaped_solver_command = solver_command.replace("'", "'\"'\"'")
    escaped_test_command = shlex.quote(test_command) if test_command else ""

    test_args_and_command = f" --test-command {escaped_test_command}" if test_command else ""
    entrypoint = [
        "/bin/bash",
        "-c",
        (
            "source /venv/bin/activate && "
            f"python modify_repo.py --model-name {shlex.quote(model_name)} "
            f"--solver-command '{escaped_solver_command}' "
            f"{test_args_and_command}"
        ).strip(),
    ]
    env_vars = {key: os.getenv(key) for key in os.environ.keys()}
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
