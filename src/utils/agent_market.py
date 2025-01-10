import re
from typing import Optional

import openai

from src.config import SETTINGS

openai.api_key = SETTINGS.openai_api_key
WEAK_MODEL = "gpt-4o-mini"


def get_pr_title(background: str) -> str:
    response = openai.chat.completions.create(
        model=WEAK_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that helps generate concise, "
                    "professional pull request titles."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Based on the following background, "
                    f"generate a pull request title: {background}"
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()


def get_pr_body(background: str, logs: str) -> str:
    match = re.search(r"Issue Number: (\d+)", background)
    issue_number = match.group(1) if match else None

    response = openai.chat.completions.create(
        model=WEAK_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that helps generate detailed, "
                    "clear, and professional pull request descriptions."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Based on the following background and git logs, "
                    f"generate a pull request description.\n\n"
                    f"Background:\n{background}\n\n"
                    f"Git Logs:\n{logs}"
                ),
            },
        ],
    )
    body = response.choices[0].message.content.strip()

    if issue_number is not None and f"fixes #{issue_number}" not in body.lower():
        body = f"{body}\n\nFixes #{issue_number}"

    return body


def remove_all_urls(text: str) -> str:
    text = text.replace("Repository URL:", "")
    text = text.replace("Issue URL:", "")
    return re.sub(r"https?:\/\/[^\s]+", "", text)


def format_messages(messages: list[dict]) -> str:
    """Format a list of message dictionaries into a single string.

    Args:
        messages: List of dicts containing message data

    Returns:
        String with all messages joined by newlines
    """
    return "\n".join([m["message"] for m in messages])
