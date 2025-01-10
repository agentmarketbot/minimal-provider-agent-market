from typing import Optional, Tuple
from pathlib import Path
import re

import git
import openai
from git.exc import GitCommandError, InvalidGitRepositoryError
from loguru import logger
from openai.types.chat import ChatCompletion

from src.config import SETTINGS

# Constants for OpenAI API configuration
DEFAULT_MODEL = "gpt-4"  # Fallback to GPT-3.5-turbo if not available
MAX_TOKENS = 500
TEMPERATURE = 0.2  # Lower temperature for more focused responses
SYSTEM_PROMPT = """You are a helpful AI that generates clear and informative git commit messages.
You analyze git diffs and create structured commit messages that follow best practices.
Focus on technical accuracy and clarity. Be concise but complete."""


def setup_openai_client() -> openai.OpenAI:
    """Initialize and return an OpenAI client with configured settings.

    This function sets up the OpenAI client with proper configuration and validation.
    It supports different environments (local, docker, cloud) through different base URLs
    and handles timeouts and retries.

    Returns:
        openai.OpenAI: Configured OpenAI client instance with:
            - Proper API key and base URL
            - Timeout settings
            - Retry configuration
            - Organization ID (if configured)
    
    Raises:
        ValueError: If required API settings are missing or invalid:
            - Missing API key
            - Invalid base URL format
            - Missing required configuration
    """
    # Validate API key
    if not SETTINGS.litellm_api_key:
        raise ValueError("OpenAI API key not configured. Set litellm_api_key in config.")
    
    # Determine base URL based on environment
    base_url = SETTINGS.litellm_local_api_base
    if SETTINGS.litellm_docker_internal_api_base and SETTINGS.is_docker:
        base_url = SETTINGS.litellm_docker_internal_api_base
    elif SETTINGS.litellm_api_base:  # Cloud/production URL
        base_url = SETTINGS.litellm_api_base
    
    if not base_url:
        raise ValueError("No valid base URL found in configuration")
    
    # Validate base URL format
    if not base_url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid base URL format: {base_url}")
    
    # Configure client with timeouts and retries
    client = openai.OpenAI(
        api_key=SETTINGS.litellm_api_key,
        base_url=base_url,
        timeout=60.0,  # 60 second timeout
        max_retries=3,  # Retry failed requests 3 times
    )
    
    logger.debug(f"OpenAI client configured with base URL: {base_url}")
    return client


def validate_git_diff(diff: str) -> tuple[bool, str]:
    """Validate if the git diff is suitable for generating a commit message.

    Performs various checks on the git diff to ensure it's valid and suitable
    for generating a meaningful commit message:
    - Not empty or too short
    - Not too large (which may affect API response quality)
    - Contains actual code changes
    - Doesn't contain only binary files
    - Doesn't contain merge conflicts

    Args:
        diff: Git diff string to validate

    Returns:
        tuple[bool, str]: A tuple containing:
            - bool: True if diff is valid, False otherwise
            - str: Reason for validation failure or success message
    """
    # Check for empty or too short diff
    if not diff:
        return False, "Git diff is empty"
    
    if len(diff.strip()) < 10:
        return False, "Git diff is too short (< 10 chars)"
    
    # Check for binary files
    if "Binary files" in diff:
        logger.warning("Git diff contains binary files")
    
    # Check for merge conflicts
    if any(marker in diff for marker in ["<<<<<<< HEAD", "=======", ">>>>>>>"]):
        return False, "Git diff contains unresolved merge conflicts"
    
    # Check for actual code changes
    if not any(line.startswith(('+', '-')) for line in diff.splitlines()):
        return False, "Git diff contains no actual changes (no + or - lines)"
    
    # Check diff size
    diff_size = len(diff)
    if diff_size > 4000:
        logger.warning(f"Git diff is large ({diff_size} chars), may affect message quality")
        # Still return True but with a warning message
        return True, f"Git diff is valid but large ({diff_size} chars)"
    
    return True, "Git diff is valid"


def generate_commit_message(repo_path: str) -> Optional[str]:
    """Generate an informative commit message using AI based on the staged changes.

    This function analyzes the staged changes in a git repository and uses OpenAI's API
    to generate a meaningful commit message following git best practices.

    Args:
        repo_path: Path to the git repository. Must be a valid git repository with staged changes.

    Returns:
        str: A well-formatted commit message in the following cases:
            - Successfully generated message from OpenAI (most detailed)
            - "agent bot commit" as fallback in case of errors
        None: In the following cases:
            - No changes are staged (repo.is_dirty() returns False)
            - Git diff validation fails (empty or too short diff)

    Format:
        The generated message follows this structure:
        <summary line (max 50 chars)>

        - Detailed bullet points
        - Technical changes made
        - Impact of changes
        - Fixes #<issue> (if applicable)

    Examples:
        Successful case:
            Add user authentication with JWT
            
            - Implement JWT token generation and validation
            - Add login endpoint with email/password
            - Include bcrypt password hashing
            - Add user session management
            - Fixes #123

        Error case:
            "agent bot commit"

    Raises:
        InvalidGitRepositoryError: If repo_path is not a valid git repository
        GitCommandError: If git diff or other git operations fail
        ValueError: If OpenAI API configuration (api_key, base_url) is missing
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
        is_valid, validation_message = validate_git_diff(diff)
        if not is_valid:
            logger.warning(f"Git diff validation failed: {validation_message}")
            return None
        else:
            logger.debug(f"Git diff validation: {validation_message}")

        # Extract issue numbers from diff for context
        issue_numbers = []
        for line in diff.splitlines():
            if '#' in line:
                # Look for patterns like "Fix #123" or "Fixes #456" or just "#789"
                matches = re.findall(r'(?:Fix(?:es)?|Close(?:s)?|Resolve(?:s)?)?\s*#(\d+)', line)
                issue_numbers.extend(matches)

        # Prepare the prompt for the AI model
        prompt = f"""Generate a concise and informative git commit message for the following changes.

DIFF:
{diff}

REQUIREMENTS:
1. Start with a brief summary line (max 50 chars) using imperative mood (e.g., "Add" not "Added")
2. Leave one blank line after the summary
3. Follow with bullet points describing key changes
4. Include technical details and impact of changes
5. Reference issue numbers found in diff: {', '.join(f'#{num}' for num in issue_numbers) if issue_numbers else 'none found'}
6. End with "Fixes #<number>" if the change completely resolves an issue

GUIDELINES:
- Be specific and technical
- Focus on WHAT changed and WHY
- Mention any breaking changes
- Include performance impacts
- Note any configuration changes

Format:
<summary line>

- Change detail 1
- Change detail 2
- Technical impact
- Breaking changes (if any)
Fixes #<number> (if applicable)"""

        try:
            # Setup OpenAI client
            client = setup_openai_client()
            
            # Generate commit message
            logger.debug("Sending request to OpenAI API")
            # Use configured model or fallback to default
            model = str(SETTINGS.foundation_model_name or DEFAULT_MODEL)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                presence_penalty=0.1,  # Slightly encourage new information
                frequency_penalty=0.3,  # Reduce repetition
            )

            commit_message = response.choices[0].message.content.strip()
            
            # Validate the generated message
            first_line = commit_message.split('\n')[0]
            if not commit_message:
                logger.error("OpenAI returned empty commit message")
                return "agent bot commit"
            if len(first_line) > 50:
                logger.warning(f"First line too long ({len(first_line)} chars), truncating...")
                lines = commit_message.split('\n')
                lines[0] = lines[0][:47] + "..."
                commit_message = '\n'.join(lines)
                
            # Log the generated message with a clear separator for readability
            logger.info("Generated commit message:")
            logger.info("=" * 50)
            logger.info(commit_message)
            logger.info("=" * 50)
            
            # Note: This function implements Fixes #30 by providing informative
            # commit messages using OpenAI's API with proper validation and formatting
            return commit_message

        except openai.APIError as e:
            logger.error(f"OpenAI API error while generating commit message: {e}")
            logger.error(f"API Response Status: {getattr(e, 'status_code', 'unknown')}")
            logger.error(f"API Response Headers: {getattr(e, 'headers', {})}")
            return "agent bot commit"
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            logger.error("Consider implementing rate limiting or increasing quota")
            return "agent bot commit"
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            logger.error("Consider increasing timeout settings or retrying")
            return "agent bot commit"
        except ValueError as e:
            logger.error(f"Configuration error in commit message generation: {e}")
            logger.error("Check litellm_api_key and litellm_local_api_base settings")
            return "agent bot commit"
            
    except Exception as e:
        error_context = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'repo_path': repo_path,
            'has_changes': repo.is_dirty() if 'repo' in locals() else 'unknown',
            'diff_size': len(diff) if 'diff' in locals() else 'unknown'
        }
        logger.error("Unexpected error in commit message generation:")
        logger.error(error_context)
        return "agent bot commit"  # Fallback to default message
