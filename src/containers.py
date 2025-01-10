import re
import time

from docker import from_env as docker_from_env
from loguru import logger


def _clean_logs(logs: str) -> str:
    anti_escape_logs = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    return anti_escape_logs.sub("", logs).split("Tokens:")[0]


def launch_container_with_repo_mounted(
    timeout: int = 300,
    **kwargs,
) -> str:
    docker_client = docker_from_env()
    logger.info("Launching container")
    container = docker_client.containers.run(
        **kwargs,
        tty=True,
        stdin_open=True,
        detach=True,
    )
    logger.info("Container launched")

    try:
        time.sleep(timeout)
        logger.info("Timeout reached. Examining logs.")
        raw_logs = container.logs(stream=False).decode("utf-8")
        logger.info(f"Raw logs: {raw_logs}")
        logs = _clean_logs(raw_logs)
        logger.info(f"Clean logs: {logs}")

        logger.info("Removing all containers")
        for container in docker_client.containers.list(all=True):
            container.stop()
            container.remove()
        logger.info("Containers removed")

    except Exception as e:
        logger.error(f"Failed to wait for container: {e}")
        for container in docker_client.containers.list(all=True):
            container.stop()
            container.remove()
        raise

    return logs
