from typing import Optional, Tuple
from pathlib import Path

import git
import openai
from git.exc import GitCommandError, InvalidGitRepositoryError
from loguru import logger
from openai.types.chat import ChatCompletion

from src.config import SETTINGS


def setup_openai_client() -> openai.OpenAI:
    """Initialize and return an OpenAI client with configured settings.

    Returns:
        openai.OpenAI: Configured OpenAI client instance
    
    Raises:
        ValueError: If required API settings are missing
    """
    if not SETTINGS.litellm_api_key:
        raise ValueError("OpenAI API key not configured")
    
    return openai.OpenAI(
        api_key=SETTINGS.litellm_api_key,
        base_url=SETTINGS.litellm_local_api_base
    )


def validate_git_diff(diff: str) -> bool:
    """Validate if the git diff is suitable for generating a commit message.

    Args:
        diff: Git diff string to validate

    Returns:
        bool: True if diff is valid, False otherwise
    """
    if not diff or len(diff.strip()) < 10:  # Arbitrary minimum length
        return False
    if len(diff) > 4000:  # Avoid too large diffs
        logger.warning("Git diff too large (>4000 chars), may affect message quality")
    return True


def generate_commit_message(repo_path: str) -> Optional[str]:
    """Generate an informative commit message using AI based on the staged changes.

    This function analyzes the staged changes in a git repository and uses OpenAI's API
    to generate a meaningful commit message following git best practices.

    Args:
        repo_path: Path to the git repository

    Returns:
        Optional[str]: A well-formatted commit message with summary and description,
                      or None if no changes are staged or validation fails.
                      Example:
                      Add user authentication feature
                      
                      - Implement JWT-based authentication
                      - Add login and signup endpoints
                      - Include password hashing
                      - Fixes #123

    Raises:
        InvalidGitRepositoryError: If the provided path is not a valid git repository
        GitCommandError: If git operations fail
        ValueError: If OpenAI API configuration is invalid
    """
    try:
        # Validate repository path
        repo_path = str(Path(repo_path).resolve())
        logger.debug(f"Generating commit message for repository: {repo_path}")
        
        # Initialize repository
        try:
            repo = git.Repo(repo_path)
        except InvalidGitRepositoryError:
            logger.error(f"Invalid git repository: {repo_path}")
            raise
        
        # Check for changes
        if not repo.is_dirty(untracked_files=True):
            logger.info("No changes detected in repository")
            return None

        # Get the diff of staged changes
        try:
            diff = repo.git.diff("--cached")
        except GitCommandError as e:
            logger.error(f"Failed to get git diff: {e}")
            raise

        # Validate diff content
        if not validate_git_diff(diff):
            logger.warning("Git diff validation failed")
            return None

        # Prepare the prompt for the AI model
        prompt = f"""Generate a concise and informative git commit message based on the following diff:

{diff}

The commit message should:
1. Start with a brief summary line (max 50 chars)
2. Follow with a blank line
3. Include a detailed description of the changes
4. Use imperative mood (e.g., "Add" not "Added")
5. Reference any relevant issue numbers if found in the diff
6. Include "Fixes #<number>" if the change fixes an issue

Format the message like this:
<summary line>

<detailed description>"""  # noqa: E501

        try:
            # Setup OpenAI client
            client = setup_openai_client()
            
            # Generate commit message
            logger.debug("Sending request to OpenAI API")
            response = client.chat.completions.create(
                model=str(SETTINGS.foundation_model_name),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Add some creativity while keeping focus
                max_tokens=500,  # Limit response length
            )

            commit_message = response.choices[0].message.content.strip()
            
            # Validate the generated message
            if not commit_message or len(commit_message.split('\n')[0]) > 50:
                logger.warning("Generated message failed validation")
                return "agent bot commit"
                
            logger.info(f"Successfully generated commit message:\n{commit_message}")
            return commit_message

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "agent bot commit"
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return "agent bot commit"
            
    except Exception as e:
        logger.error(f"Unexpected error generating commit message: {type(e).__name__}: {e}")
        return "agent bot commit"  # Fallback to default message
