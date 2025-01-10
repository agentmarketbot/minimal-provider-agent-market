"""Constants used across the application."""

# OpenAI API Configuration
DEFAULT_MODEL = "gpt-4"  # Fallback to GPT-3.5-turbo if not available
MAX_TOKENS = 500
TEMPERATURE = 0.2  # Lower temperature for more focused responses

# Commit Message Generation
SYSTEM_PROMPT = """You are a helpful AI that generates clear and informative git commit messages.
You analyze git diffs and create structured commit messages that follow best practices.
Focus on technical accuracy and clarity. Be concise but complete."""

COMMIT_MESSAGE_PROMPT_TEMPLATE = """Generate a concise and informative git commit message for the following changes.

DIFF:
{diff}

REQUIREMENTS:
1. Start with a brief summary line (max 50 chars) using imperative mood (e.g., "Add" not "Added")
2. Leave one blank line after the summary
3. Follow with bullet points describing key changes
4. Include technical details and impact of changes
5. Reference issue numbers found in diff: {issue_refs}
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

# API Client Configuration
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3