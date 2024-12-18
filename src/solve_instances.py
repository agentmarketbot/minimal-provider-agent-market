import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from src import agents, utils
from src.config import SETTINGS, Settings
from src.containers import launch_container_with_repo_mounted
from src.enums import AgentType

TIMEOUT = httpx.Timeout(10.0)


def _get_instance_to_solve(instance_id: str, settings: Settings) -> Optional[dict]:
    headers = {
        "x-api-key": settings.market_api_key,
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        instance_endpoint = f"{settings.market_url}/v1/instances/{instance_id}"
        response = client.get(instance_endpoint, headers=headers)
        instance = response.json()

        if instance["status"] != settings.market_resolved_instance_code:
            return None

    repo_url = utils.find_github_repo_url(instance["background"])
    if not repo_url:
        logger.info(f"Instance id {instance_id} does not have a github repo url")
        return None

    with httpx.Client(timeout=TIMEOUT) as client:
        chat_endpoint = f"{settings.market_url}/v1/chat/{instance_id}"
        response = client.get(chat_endpoint, headers=headers)

        chat = response.json()
        if chat:
            logger.info(f"Instance id {instance_id} has chat messages. Looking for PR comments.")
            pr_url = utils.get_pr_url("\n".join([m["message"] for m in chat]))
            if not pr_url:
                logger.info(f"No PR URL found for instance id {instance_id}")
                return None
            pr_comments = utils.get_last_pr_comments(pr_url, settings.github_pat)
            if not pr_comments:
                logger.info(f"No PR comments found for instance id {instance_id}")
                return None

            return instance | {"pr_comments": pr_comments, "repo_url": repo_url, "pr_url": pr_url}

        return instance | {"repo_url": repo_url}


def _solve_instance(
    instance_id: str,
    instance_background: str,
    instance_repo_url: str,
    pr_comments: Optional[str],
    pr_url: Optional[str],
    settings: Settings,
) -> None:
    logger.info("Solving instance id: {}", instance_id)
    if pr_comments:
        solver_command = utils.add_pr_comments_to_background(instance_background, pr_comments)
    else:
        solver_command = instance_background
    solver_command = utils.remove_all_urls(solver_command)

    forked_repo_url = utils.fork_repo(instance_repo_url, settings.github_pat)
    logger.info(f"Forked repo url: {forked_repo_url}")
    forked_repo_name = utils.extract_repo_name_from_url(forked_repo_url)
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_absolute_path = Path(temp_dir)
        logger.info(f"Cloning repository {forked_repo_url} to {repo_absolute_path}")

        utils.clone_repository(forked_repo_url, str(repo_absolute_path))
        utils.create_and_push_branch(repo_absolute_path, instance_id, settings.github_pat)
        utils.set_git_config(settings.github_username, settings.github_email, repo_absolute_path)
        if settings.agent_type == AgentType.open_hands:
            container_kwargs = agents.open_hands_get_container_kwargs(
                str(repo_absolute_path),
                solver_command,
                settings.foundation_model_name,
            )
        elif settings.agent_type == AgentType.aider:
            modify_repo_absolute_path = (
                Path(os.path.dirname(os.path.abspath(__file__))) / "agents" / "aider_modify_repo.py"
            )
            utils.copy_file_to_directory(modify_repo_absolute_path, repo_absolute_path)
            utils.change_directory_ownership_recursive(repo_absolute_path, os.getuid(), os.getgid())

            test_command = agents.aider_suggest_test_command(str(repo_absolute_path))
            solver_command = utils.aider_get_solver_command(solver_command, pr_comments)
            container_kwargs = agents.aider_get_container_kwargs(
                str(repo_absolute_path),
                settings.foundation_model_name.value,
                solver_command,
                test_command,
            )
        logs = launch_container_with_repo_mounted(**container_kwargs)
        if pr_url:
            utils.add_aider_logs_as_pr_comments(pr_url, settings.github_pat, logs)

        utils.add_and_commit(str(repo_absolute_path))
        pushed = utils.push_commits(str(repo_absolute_path), settings.github_pat)
        if pushed:
            if pr_url:
                return "Added comments to PR"
            target_repo_name = utils.extract_repo_name_from_url(instance_repo_url)
            logger.info(
                f"Creating pull request from source repo {forked_repo_name} "
                f"to target repo {target_repo_name}"
            )

            pr_title = utils.get_pr_title(solver_command)
            pr_body = utils.get_pr_body(solver_command)

            pr_url = utils.create_pull_request(
                source_repo_name=forked_repo_name,
                target_repo_name=target_repo_name,
                source_repo_path=str(repo_absolute_path),
                github_token=settings.github_pat,
                pr_title=pr_title,
                pr_body=pr_body,
            )

            return f"Solved instance {instance_id} with PR {pr_url}"
        else:
            logger.info(f"No new commits to push for instance id {instance_id}")
            return logs


def get_awarded_proposals(settings: Settings) -> list[dict]:
    headers = {
        "x-api-key": settings.market_api_key,
    }
    url = f"{settings.market_url}/v1/proposals/"

    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    all_proposals = response.json()

    current_time = datetime.utcnow()
    one_day_ago = current_time - timedelta(days=1)

    awarded_proposals = [
        p
        for p in all_proposals
        if p["status"] == settings.market_awarded_proposal_code
        and datetime.fromisoformat(p["creation_date"]) > one_day_ago
    ]
    return awarded_proposals


def _send_message(instance_id: str, message: str, settings: Settings) -> None:
    headers = {
        "x-api-key": settings.market_api_key,
    }
    url = f"{settings.market_url}/v1/chat/send-message/{instance_id}"
    data = {"message": message}

    response = httpx.post(url, headers=headers, json=data)
    response.raise_for_status()


def solve_instances_handler() -> None:
    logger.info("Solve instances handler")
    awarded_proposals = get_awarded_proposals(SETTINGS)

    logger.info(f"Found {len(awarded_proposals)} awarded proposals")

    for p in awarded_proposals:
        instance = _get_instance_to_solve(p["instance_id"], SETTINGS)
        if not instance:
            continue

        logger.info("Solving instance id: {}", instance["id"])
        try:
            message = _solve_instance(
                instance["id"],
                instance["background"],
                instance["repo_url"],
                instance.get("pr_comments"),
                instance.get("pr_url"),
                SETTINGS,
            )
            if not message:
                continue
        except Exception as e:
            logger.error(f"Error solving instance id {instance['id']}: {e}")
        else:
            try:
                _send_message(
                    instance["id"],
                    message,
                    SETTINGS,
                )
            except Exception as e:
                logger.error(f"Error sending message for instance id {instance['id']}: {e}")
