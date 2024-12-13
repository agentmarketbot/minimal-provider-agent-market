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

        current_branch = repo.active_branch.name
        logger.info(f"Pulling latest changes from origin/{current_branch}")

        repo.remotes.origin.pull(current_branch)

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


def get_last_pr_comments(pr_url: str, github_token: str) -> str | bool:
    g = github.Github(github_token)

    pr_path = pr_url.split("github.com/")[-1]
    owner_repo, pr_number = pr_path.split("/pull/")
    pr_number = int(pr_number)

    repo = g.get_repo(owner_repo)
    pr = repo.get_pull(pr_number)

    latest_comment_time = None

    issue_comments = list(pr.get_issue_comments())
    review_comments = list(pr.get_review_comments())

    if issue_comments:
        latest_issue_comment_time = issue_comments[-1].created_at
        if latest_comment_time is None or latest_issue_comment_time > latest_comment_time:
            latest_comment_time = latest_issue_comment_time

    if not latest_comment_time:
        return False

    if review_comments:
        latest_review_comment_time = review_comments[-1].created_at
        if latest_comment_time is None or latest_review_comment_time > latest_comment_time:
            latest_comment_time = latest_review_comment_time

    if not latest_comment_time:
        return False

    commits = list(pr.get_commits())
    if commits:
        latest_commit = commits[-1]
        if latest_commit.commit.author.date > latest_comment_time:
            return False

    diff_content = pr.get_files()
    diff_text = []
    for file in diff_content:
        diff_text.append(f"File: {file.filename}")
        diff_text.append(f"Status: {file.status}")
        diff_text.append(f"Changes: +{file.additions} -{file.deletions}")
        diff_text.append(f"Patch:\n{file.patch if file.patch else 'No patch available'}\n")

    comments = []

    issue_comments = pr.get_issue_comments()
    for comment in issue_comments:
        comments.append(f"Comment by {comment.user.login} at {comment.created_at}:")
        comments.append(comment.body)
        comments.append("---")

    review_comments = pr.get_review_comments()
    for comment in review_comments:
        comments.append(f"Review comment by {comment.user.login} at {comment.created_at}:")
        comments.append(f"File: {comment.path}, Line: {comment.line}")
        comments.append(comment.body)
        comments.append("---")

    result = "\n".join(
        [
            "DIFF",
            "\n".join(diff_text),
            "COMMENTS",
            "\n".join(comments),
        ]
    )

    return result


def add_pr_comments_to_background(background: str, pr_info: str) -> str:
    result = "\n".join(
        [
            "=== SYSTEM INSTRUCTIONS ===",
            "You are a helpful AI assistant that implements code changes based on pull request feedback.",
            "Your task is to analyze the issue description and specifically address the LAST comment in the pull request.",
            "Focus only on implementing changes requested in the most recent comment.",
            "",
            "=== CONTEXT ===",
            "ISSUE DESCRIPTION",
            background,
            "PULL REQUEST DETAILS",
            pr_info,
            "\n=== REQUIRED ACTIONS ===",
            "1. Review the issue description to understand the context",
            "2. Analyze the pull request diff and comments",
            "3. Implement the necessary code changes addressing the feedback in the last comment",
            "4. Ensure your changes maintain code quality and follow the project's standards",
        ]
    )
    return result


def add_aider_logs_as_pr_comments(pr_url: str, github_token: str, logs: str) -> None:
    g = github.Github(github_token)

    pr_path = pr_url.split("github.com/")[-1]
    owner_repo, pr_number = pr_path.split("/pull/")
    pr_number = int(pr_number)

    repo = g.get_repo(owner_repo)
    pr = repo.get_pull(pr_number)

    comment = f"## Aider:\n{logs}\n"

    pr.create_issue_comment(comment)
    logger.info("Successfully added aider logs as PR comment")


def get_pr_url(chat_text: str) -> str:
    pr_url_pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+"
    match = re.search(pr_url_pattern, chat_text)
    if match:
        return match.group(0)
    return None
