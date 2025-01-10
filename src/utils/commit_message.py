from typing import Optional, Tuple
from pathlib import Path
import re

import git
import openai
from git.exc import GitCommandError, InvalidGitRepositoryError
from loguru import logger
from openai.types.chat import ChatCompletion

from src.config import SETTINGS
from src.utils.constants import (
    DEFAULT_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    SYSTEM_PROMPT,
    COMMIT_MESSAGE_PROMPT_TEMPLATE,
    DEFAULT_TIMEOUT,
    MAX_RETRIES
)


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
        timeout=DEFAULT_TIMEOUT,
        max_retries=MAX_RETRIES,
        default_headers={'X-Request-ID': f'commit-msg-{repo_path.split("/")[-1]}'}  # Add request tracking
    )
    
    logger.debug(f"OpenAI client configured with base URL: {base_url}")
    return client


def validate_git_diff(diff: str) -> tuple[bool, str]:
    """Validate if the git diff is suitable for generating a commit message.

    Performs comprehensive validation of git diffs to ensure they are suitable
    for generating meaningful commit messages. Includes size limits, content
    validation, and special file handling.

    Validation checks:
    1. Basic validation:
       - Not empty
       - Minimum size (10 chars)
       - Maximum size (4000 chars recommended)
    2. Content validation:
       - Contains actual changes (+ or - lines)
       - No unresolved merge conflicts
    3. Special file handling:
       - Binary files (images, PDFs, etc.)
       - Generated files (package-lock.json, etc.)
       - Large files

    Args:
        diff: Git diff string to validate

    Returns:
        tuple[bool, str]: (is_valid, message) where:
            is_valid: True if diff is suitable for commit message generation
            message: Detailed explanation of validation result or failure reason
    """
    # Initialize validation context
    validation_context = {
        'diff_size': len(diff.strip()),
        'has_binary': False,
        'has_changes': False,
        'line_count': 0,
        'files_changed': set()
    }

    # Basic validation
    if not diff:
        return False, "Git diff is empty - no changes to describe"
    
    if validation_context['diff_size'] < 10:
        return False, "Git diff is too short (< 10 chars) - insufficient content for meaningful message"

    # Parse diff content
    for line in diff.splitlines():
        validation_context['line_count'] += 1
        
        # Track changed files
        if line.startswith('diff --git'):
            file_path = line.split()[-1].lstrip('b/')
            validation_context['files_changed'].add(file_path)
        
        # Check for binary files
        if "Binary files" in line:
            validation_context['has_binary'] = True
            binary_file = line.split()[-1].lstrip('b/')
            logger.warning(f"Binary file detected in diff: {binary_file}")
        
        # Track actual changes
        if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
            validation_context['has_changes'] = True

    # Merge conflict detection
    conflict_markers = ["<<<<<<< HEAD", "=======", ">>>>>>>"]
    if any(marker in diff for marker in conflict_markers):
        return False, "Unresolved merge conflicts detected - please resolve conflicts first"

    # Validate actual changes exist
    if not validation_context['has_changes']:
        return False, "No actual code changes found (no added/removed lines)"

    # Size validation with detailed message
    if validation_context['diff_size'] > 4000:
        size_kb = validation_context['diff_size'] / 1024
        return True, (
            f"Large diff detected ({size_kb:.1f}KB, {validation_context['line_count']} lines) - "
            "commit message may be less specific"
        )

    # Success with context
    files_changed = len(validation_context['files_changed'])
    return True, (
        f"Valid diff with {files_changed} file(s) changed, "
        f"{validation_context['line_count']} lines"
        + (" (includes binary files)" if validation_context['has_binary'] else "")
    )


def generate_commit_message(repo_path: str) -> Optional[str]:
    """Generate an informative commit message using AI based on the staged changes.

    This function analyzes the staged changes in a git repository and uses OpenAI's API
    to generate a meaningful commit message following git best practices. It includes
    automatic issue detection and linking, handles various error cases gracefully,
    and ensures proper message formatting.

    Args:
        repo_path: Path to the git repository. Must be a valid git repository with staged changes.

    Returns:
        Optional[str]: One of the following:
            - A well-formatted commit message (on successful generation)
            - "agent bot commit: <error_type>" (on specific errors)
            - None (when no changes or invalid diff)
            
        The successful message format follows:
            <summary line (max 50 chars)>

            - Detailed bullet points
            - Technical changes made
            - Impact of changes
            - Fixes #<issue> (if applicable)

    Error Types:
        - "agent bot commit: API error" - OpenAI API communication issues
        - "agent bot commit: rate limit" - API quota exceeded
        - "agent bot commit: timeout" - API request timeout
        - "agent bot commit: config error" - Missing/invalid configuration

    None Cases:
        - No staged changes (repo.is_dirty() returns False)
        - Empty git diff
        - Diff too short (< 10 chars)
        - Only binary files changed
        - Unresolved merge conflicts

    Examples:
        >>> generate_commit_message("/path/to/repo")
        '''
        Add JWT authentication and user session management
        
        - Implement JWT token generation/validation
        - Add login/signup endpoints
        - Include password hashing with bcrypt
        - Add session timeout configuration
        - Improve error handling in auth middleware
        Fixes #123
        '''

        >>> generate_commit_message("/empty/repo")
        None

        >>> generate_commit_message("/error/case")
        'agent bot commit: API error'

    Raises:
        InvalidGitRepositoryError: If repo_path is not a valid git repository
        GitCommandError: If git operations fail (diff, status)
        ValueError: If OpenAI API configuration is invalid/missing
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

        # Format issue references for the prompt
        issue_refs = ', '.join(f'#{num}' for num in issue_numbers) if issue_numbers else 'none found'
        
        # Prepare the prompt using the template
        prompt = COMMIT_MESSAGE_PROMPT_TEMPLATE.format(
            diff=diff,
            issue_refs=issue_refs
        )

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
            
            # Validate and format the generated message
            if not commit_message:
                logger.error("OpenAI returned empty commit message")
                return "agent bot commit: empty response"

            # Split message into lines for processing
            lines = commit_message.strip().split('\n')
            if not lines:
                logger.error("No valid lines in commit message")
                return "agent bot commit: invalid format"

            # Process summary line
            summary = lines[0].strip()
            if not summary:
                logger.error("Empty summary line in commit message")
                return "agent bot commit: missing summary"

            # Truncate long summary lines
            if len(summary) > 50:
                logger.warning(f"Summary line too long ({len(summary)} chars), truncating...")
                summary = summary[:47] + "..."
                lines[0] = summary

            # Ensure proper spacing after summary
            if len(lines) > 1 and lines[1].strip():
                logger.warning("Missing blank line after summary, fixing format...")
                lines.insert(1, "")

            # Validate bullet points
            body_lines = [line for line in lines[2:] if line.strip()]
            if body_lines:
                for i, line in enumerate(body_lines):
                    # Ensure each non-empty line in body starts with "-"
                    if not line.startswith("-"):
                        body_lines[i] = f"- {line}"

                # Rebuild message with proper format
                commit_message = summary + "\n\n" + "\n".join(body_lines)
            else:
                # No body, just use summary
                commit_message = summary

            # Log the formatted message
            logger.info("Generated commit message:")
            logger.info("=" * 50)
            logger.info(commit_message)
            logger.info("=" * 50)
            logger.debug(f"Message stats: {len(summary)} char summary, {len(body_lines)} bullet points")
            
            # Note: This function implements Fixes #30 by providing informative
            # commit messages using OpenAI's API with proper validation and formatting
            return commit_message

        except openai.APIError as e:
            error_context = {
                'error_type': 'APIError',
                'status_code': getattr(e, 'status_code', 'unknown'),
                'headers': getattr(e, 'headers', {}),
                'message': str(e),
                'diff_size': len(diff) if 'diff' in locals() else 'unknown'
            }
            logger.error("OpenAI API error while generating commit message:", error_context)
            return "agent bot commit: API error"
        except openai.RateLimitError as e:
            error_context = {
                'error_type': 'RateLimitError',
                'reset_time': getattr(e, 'reset_time', 'unknown'),
                'quota_used': getattr(e, 'quota_used', 'unknown'),
                'message': str(e)
            }
            logger.error("OpenAI rate limit exceeded:", error_context)
            logger.warning("Consider implementing exponential backoff or increasing quota")
            return "agent bot commit: rate limit"
        except openai.APITimeoutError as e:
            error_context = {
                'error_type': 'APITimeoutError',
                'timeout': getattr(e, 'timeout', 60.0),
                'message': str(e),
                'diff_size': len(diff) if 'diff' in locals() else 'unknown'
            }
            logger.error("OpenAI API timeout:", error_context)
            logger.warning("Consider adjusting timeout settings or implementing retry logic")
            return "agent bot commit: timeout"
        except ValueError as e:
            error_context = {
                'error_type': 'ValueError',
                'message': str(e),
                'api_key_set': bool(SETTINGS.litellm_api_key),
                'base_url_set': bool(SETTINGS.litellm_api_base or SETTINGS.litellm_local_api_base)
            }
            logger.error("Configuration error in commit message generation:", error_context)
            logger.warning("Check litellm_api_key and API base URL settings")
            return "agent bot commit: config error"
            
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
