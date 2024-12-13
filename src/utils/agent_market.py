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


def get_pr_body(background):
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
                    "Based on the following background, "
                    f"generate a pull request description: {background}"
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()


def remove_all_urls(text: str) -> str:
    text = text.replace("Repository URL:", "")
    text = text.replace("Issue URL:", "")
    return re.sub(r"https?:\/\/[^\s]+", "", text)


def get_solver_command(instance_background: str, pr_comments: Optional[str]) -> str:
    if not pr_comments:
        return instance_background
    return instance_background
