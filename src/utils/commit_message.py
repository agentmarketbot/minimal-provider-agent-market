from typing import List
import git
from loguru import logger
import openai
from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

def generate_commit_message(repo_path: str) -> str:
    """Generate an informative commit message using AI based on the staged changes."""
    try:
        repo = git.Repo(repo_path)
        if not repo.is_dirty(untracked_files=True):
            return None

        # Get the diff of staged changes
        diff = repo.git.diff('--cached')
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

<detailed description>"""

        # Get the commit message using OpenAI
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        commit_message = response.choices[0].message.content.strip()
        logger.info(f"Generated commit message:\n{commit_message}")
        return commit_message

    except Exception as e:
        logger.error(f"Error generating commit message: {e}")
        return "agent bot commit"  # Fallback to default message