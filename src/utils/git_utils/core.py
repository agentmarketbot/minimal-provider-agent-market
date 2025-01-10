import os
import shutil
from typing import Optional
import git
from loguru import logger

from ..commit_message import generate_commit_message

def clone_repository(repo_url: str, target_dir: str) -> None:
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    os.makedirs(target_dir)
    git.Repo.clone_from(repo_url, target_dir)
    logger.info(f"Cloned repository from {repo_url} to {target_dir}")

def add_and_commit(repo_path: str) -> None:
    try:
        repo = git.Repo(repo_path)
        logger.info(f"Repository initialized at {repo_path}")

        if repo.is_dirty(untracked_files=True):
            logger.info("Repository is dirty. Staging all changes.")
            repo.git.add(A=True)
            logger.info("All changes staged successfully.")

            commit_message = generate_commit_message(repo_path)
            if commit_message is None:
                commit_message = "agent bot commit"  # Fallback if generation fails

            repo.index.commit(commit_message)
            logger.info(f"Changes committed with message: '{commit_message}'")
        else:
            logger.info("No unstaged changes detected. Nothing to commit.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

def push_commits(repo_path: str, github_token: str) -> bool:
    try:
        repo = git.Repo(repo_path)

        if repo.head.is_detached:
            logger.error("The HEAD is detached. Cannot push commits.")
            return False

        current_branch = repo.active_branch.name

        remote_url = repo.remotes.origin.url.rstrip("/")
        if "github.com/" in remote_url:
            repo_part = remote_url.split("github.com/")[-1]
            remote_url = f"https://{github_token}@github.com/{repo_part}"
            repo.remotes.origin.set_url(remote_url)

        logger.info("Fetching remote changes")
        repo.remotes.origin.fetch()

        remote_branch = f"origin/{current_branch}"
        if remote_branch in repo.refs and repo.head.commit != repo.refs[remote_branch].commit:
            logger.info("There are commits ahead of the remote branch.")
        else:
            logger.info("No new commits to push.")
            return False

        repo.remotes.origin.push()
        logger.info("Changes pushed to remote.")
        return True
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        raise

def set_git_config(username: str, email: str, repo_dir: str):
    try:
        repo = git.Repo(repo_dir)
        with repo.config_writer() as git_config:
            git_config.set_value("user", "name", username)
            git_config.set_value("user", "email", email)
        logger.info(
            f"Git repo config set for user: {username}, email: {email} in directory: {repo_dir}"
        )
    except Exception as e:
        logger.info(f"Error setting git config: {e}")
        raise

def create_and_push_branch(repo_path: str, branch_name: str, github_token: str) -> None:
    """Create and push a new branch, ensuring the fork is synced with upstream first.

    Args:
        repo_path: Path to the local repository
        branch_name: Name of the branch to create
        github_token: GitHub personal access token
    """
    try:
        # First sync the fork with upstream
        from .github_api import sync_fork_with_upstream
        sync_fork_with_upstream(repo_path, github_token)

        repo = git.Repo(repo_path)
        repo.remotes.origin.fetch()
        logger.info(f"Repository initialized and fetched at {repo_path}")

        if repo.bare:
            logger.error("The repository is bare. Cannot perform operations.")
            raise Exception("The repository is bare. Cannot perform operations.")

        local_branches = [head.name for head in repo.heads]
        logger.info(f"Local heads are: {local_branches}")
        remote_branches = [ref.name.split("/")[-1] for ref in repo.remotes.origin.refs if "heads"]
        logger.info(f"Remote branches are: {remote_branches}")

        branch_in_remote = branch_name in remote_branches

        if branch_name in local_branches:
            logger.info(f"Branch '{branch_name}' already exists locally.")
        elif branch_in_remote:
            logger.info(f"Branch '{branch_name}' exists remotely. Checking it out locally.")
            repo.git.checkout(f"origin/{branch_name}", b=branch_name)
        else:
            logger.info(f"Branch '{branch_name}' does not exist. Creating locally.")
            repo.create_head(branch_name)

        repo.heads[branch_name].checkout()
        logger.info(f"Checked out to branch '{branch_name}'.")

        if branch_in_remote:
            logger.info(f"Pulling latest changes from origin/{branch_name}")
            repo.remotes.origin.pull(branch_name)
        else:
            logger.info(f"No remote branch '{branch_name}' to pull from.")

        origin = repo.remote(name="origin")
        remote_url = origin.url

        if remote_url.startswith("https://"):
            repo_path = remote_url.split("github.com/")[-1].removesuffix(".git")
        elif remote_url.startswith("git@"):
            repo_path = remote_url.split(":")[-1].removesuffix(".git")
        else:
            logger.error("Unrecognized remote URL format.")
            raise Exception("Invalid remote URL format.")

        if branch_name in remote_branches:
            logger.warning(f"Branch '{branch_name}' already exists on the remote.")
        else:
            origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
            logger.info(f"Branch '{branch_name}' pushed to remote and set upstream.")

    except Exception as e:
        logger.error(f"Error: {e}")