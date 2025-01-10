from typing import Optional

import git
import openai
from loguru import logger

from src.config import SETTINGS


def generate_commit_message(repo_path: str) -> Optional[str]:
    """Generate an informative commit message using AI based on the staged changes.

    Args:
        repo_path: Path to the git repository

    Returns:
        Optional[str]: Generated commit message or None if no changes are staged
    """
    try:
        repo = git.Repo(repo_path)
        if not repo.is_dirty(untracked_files=True):
            return None

        # Get the diff of staged changes
        diff = repo.git.diff("--cached")
        if not diff:
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

Format the message like this:
<summary line>

<detailed description>"""  # noqa: E501

        # Get the commit message using OpenAI
        client = openai.OpenAI(
            api_key=SETTINGS.litellm_api_key, base_url=SETTINGS.litellm_local_api_base
        )

        response = client.chat.completions.create(
            model=SETTINGS.foundation_model_name.value,
            messages=[{"role": "user", "content": prompt}],
        )

        commit_message = response.choices[0].message.content.strip()
        logger.info(f"Generated commit message:\n{commit_message}")
        return commit_message

    except Exception as e:
        logger.error(f"Error generating commit message: {e}")
        return "agent bot commit"  # Fallback to default message
