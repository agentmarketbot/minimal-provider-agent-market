import os
import re
import shutil
import time
from typing import Optional

import git
import github
from loguru import logger


def find_github_repo_url(text: str) -> Optional[str]:
    pattern = r"https://github.com/[^\s]+"
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None


def clone_repository(repo_url: str, target_dir: str) -> None:
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    os.makedirs(target_dir)
    git.Repo.clone_from(repo_url, target_dir)
    logger.info(f"Cloned repository from {repo_url} to {target_dir}")


def fork_repo(github_url: str, github_token: str) -> str:
    g = github.Github(github_token)
    repo_path = github_url.replace("https://github.com/", "").removesuffix(".git")
    repo = g.get_repo(repo_path)
    user = g.get_user()
    forked_repo = user.create_fork(repo)
    logger.info("Forked repo: {}", forked_repo.clone_url)
    return forked_repo.clone_url


def push_commits(repo_path: str, github_token: str) -> bool:
    try:
        repo = git.Repo(repo_path)

        if repo.head.is_detached:
            logger.error("The HEAD is detached. Cannot push commits.")
            return False

        if "main" not in repo.heads:
            main_branch = "master"
        else:
            main_branch = "main"

        if repo.head.commit != repo.remotes.origin.refs[main_branch].commit:
            logger.info("There are commits ahead of the remote branch.")
        else:
            logger.info("No new commits to push.")
            return False

        remote_url = repo.remotes.origin.url
        if remote_url.startswith("https://github.com/"):
            remote_url = remote_url.replace(
                "https://github.com/", f"https://{github_token}@github.com/"
            )
            repo.remotes.origin.set_url(remote_url)

        current_branch = repo.active_branch.name
        repo.remotes.origin.push(refspec=f"{current_branch}:{current_branch}", set_upstream=True)
        logger.info("Changes pushed to remote.")
        return True
    except Exception as e:
        logger.error("Error pushing changes: {}", e)
        raise


def create_pull_request(
    source_repo_name: str,
    target_repo_name: str,
    source_repo_path: str,
    github_token: str,
    pr_title: str = None,
    pr_body: str = None,
    base_branch: str = "main",
) -> str:
    try:
        repo = git.Repo(source_repo_path)
        g = github.Github(github_token)

        source_repo_name = source_repo_name.removesuffix(".git")
        target_repo_name = target_repo_name.removesuffix(".git")

        logger.info(f"Attempting to create PR from {source_repo_name} to {target_repo_name}")

        try:
            target_repo = g.get_repo(target_repo_name)
        except github.UnknownObjectException:
            logger.error(f"Target repository not found: {target_repo_name}")
            raise ValueError(f"Target repository not found: {target_repo_name}")

        try:
            source_repo = g.get_repo(source_repo_name)
        except github.UnknownObjectException:
            logger.error(f"Source repository not found: {source_repo_name}")
            raise ValueError(f"Source repository not found: {source_repo_name}")

        try:
            target_repo.get_branch(base_branch)
        except github.GithubException:
            logger.warning(f"Base branch '{base_branch}' not found, trying 'master'")
            try:
                target_repo.get_branch("master")
                base_branch = "master"
            except github.GithubException:
                logger.error("Neither 'main' nor 'master' branch found in target repo")
                raise ValueError("Could not find a valid base branch")

        current_branch = repo.active_branch.name
        repo.remotes.origin.fetch()

        try:
            comparison = target_repo.compare(
                base=f"{target_repo.owner.login}:{base_branch}",
                head=f"{source_repo.owner.login}:{current_branch}",
            )

            if comparison.total_commits == 0:
                logger.warning("No changes detected between source and target branches")
                return "No changes needed"
        except github.GithubException as e:
            logger.error(f"Error comparing branches: {e.data}")
            raise

        if not pr_title:
            pr_title = (
                "Automated changes from fork at "
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}"
            )

        if not pr_body:
            pr_body = (
                "This pull request contains automated changes pushed to the forked repository."
            )

        head = f"{source_repo.owner.login}:{current_branch}"
        logger.info(f"Creating PR with head={head} and base={base_branch}")

        try:
            pr = target_repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=head,
                base=base_branch,
            )
            logger.info(f"Pull request created: {pr.html_url}")
            return pr.html_url
        except github.GithubException as e:
            logger.error(f"Error creating pull request: {e.data}")
            logger.error(f"PR creation failed with head={head}, base={base_branch}")
            raise

    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        raise


def extract_repo_name_from_url(repo_url: str) -> str:
    """Extract the repository name from a GitHub URL.

    Args:
        repo_url: The GitHub repository URL

    Returns:
        The repository name in the format "owner/repo"
    """
    # Remove trailing slashes and .git suffix
    repo_url = repo_url.rstrip("/")
    repo_url = repo_url.removesuffix(".git")

    # Handle both HTTPS and SSH URLs
    if repo_url.startswith("git@github.com:"):
        repo_name = repo_url.split("git@github.com:")[-1]
    else:
        repo_name = repo_url.split("github.com/")[-1]

    # Validate the repository name format
    if not repo_name or "/" not in repo_name:
        raise ValueError(f"Invalid repository URL format: {repo_url}")

    owner, repo = repo_name.split("/", 1)
    if not owner or not repo:
        raise ValueError(f"Invalid repository name format: {repo_name}")

    logger.info(f"Extracted repository name: {owner}/{repo}")
    return f"{owner}/{repo}"


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


def create_and_push_branch(repo_path, branch_name, github_token):
    try:
        repo = git.Repo(repo_path)
        logger.info(f"Repository initialized at {repo_path}.")

        if repo.bare:
            logger.error("The repository is bare. Cannot perform operations.")
            raise Exception("The repository is bare. Cannot perform operations.")

        if branch_name in repo.heads:
            logger.info(f"Branch '{branch_name}' already exists locally.")
        else:
            repo.create_head(branch_name)
            logger.info(f"Branch '{branch_name}' created locally.")

        repo.heads[branch_name].checkout()
        logger.info(f"Checked out to branch '{branch_name}'.")

        g = github.Github(github_token)
        logger.info("Authenticated with GitHub using the provided token.")

        origin = repo.remote(name="origin")
        remote_url = origin.url
        logger.info(f"Remote URL: {remote_url}")

        if remote_url.startswith("https://"):
            repo_path = remote_url.split("github.com/")[-1].removesuffix(".git")
        elif remote_url.startswith("git@"):
            repo_path = remote_url.split(":")[-1].removesuffix(".git")
        else:
            logger.error("Unrecognized remote URL format.")
            raise Exception("Invalid remote URL format.")

        github_repo = g.get_repo(repo_path)
        logger.info(f"Connected to GitHub repository: {github_repo.full_name}")

        remote_branches = [ref.ref.replace("refs/heads/", "") for ref in github_repo.get_git_refs()]
        logger.info(f"Remote branches fetched: {remote_branches}")

        if branch_name in remote_branches:
            logger.warning(f"Branch '{branch_name}' already exists on the remote.")
        else:
            origin.set_url(f"https://{github_token}@{remote_url.split('://')[-1]}")
            origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
            logger.info(f"Branch '{branch_name}' pushed to remote and set upstream.")

    except Exception as e:
        logger.error(f"Error: {e}")
