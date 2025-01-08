from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
import openai
from loguru import logger

from src.config import SETTINGS, Settings

TIMEOUT = httpx.Timeout(10.0)


@dataclass
class InstanceToSolve:
    instance: dict
    messages_history: Optional[str] = None
    provider_needs_response: bool = False


def _get_instance_to_solve(instance_id: str, settings: Settings) -> Optional[InstanceToSolve]:
    headers = {
        "x-api-key": settings.market_api_key,
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        instance_endpoint = f"{settings.market_url}/v1/instances/{instance_id}"
        response = client.get(instance_endpoint, headers=headers)
        instance = response.json()

        if instance["status"] != settings.market_resolved_instance_code:
            return None

    with httpx.Client(timeout=TIMEOUT) as client:
        chat_endpoint = f"{settings.market_url}/v1/chat/{instance_id}"
        response = client.get(chat_endpoint, headers=headers)

        chat = response.json()
        if not chat:
            return InstanceToSolve(instance=instance)

        sorted_messages = sorted(chat, key=lambda m: m["timestamp"])
        last_message = sorted_messages[-1]
        provider_needs_response = last_message["sender"] == "provider"

        messages_history = "\n".join(
            [f"{message['sender']}: {message['message']}" for message in sorted_messages]
        )

        return InstanceToSolve(
            instance=instance,
            messages_history=messages_history,
            provider_needs_response=provider_needs_response,
        )


def _solve_instance(
    instance_to_solve: InstanceToSolve,
    settings: Settings,
) -> str:
    logger.info("Solving instance id: {}", instance_to_solve.instance["id"])

    conversation = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant that helps solve technical problems "
                "and answer questions. Your role is to maintain a helpful conversation "
                "and provide follow-up responses when needed. Analyze the conversation "
                "context and the last message to determine if a response is required. "
                "Only respond if:\n"
                "1. The last message explicitly asks a question\n"
                "2. The last message requests clarification\n"
                "3. The last message requires acknowledgment or confirmation\n"
                "4. Additional information or explanation would be helpful\n\n"
                "If none of these conditions are met, reply with 'NO_RESPONSE_NEEDED'."
            ),
        },
        {"role": "user", "content": instance_to_solve.instance["background"]},
    ]

    if instance_to_solve.messages_history:
        conversation.append(
            {
                "role": "user",
                "content": f"Previous conversation:\n{instance_to_solve.messages_history}",
            }
        )

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
    )

    if "NO_RESPONSE_NEEDED" in response.choices[0].message.content:
        return None

    return response.choices[0].message.content


def get_awarded_proposals(settings: Settings) -> list[dict]:
    headers = {
        "x-api-key": settings.market_api_key,
    }
    url = f"{settings.market_url}/v1/proposals/"

    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    all_proposals = response.json()

    current_time = datetime.utcnow()
    one_day_ago = current_time - timedelta(days=1)

    awarded_proposals = [
        p
        for p in all_proposals
        if p["status"] == settings.market_awarded_proposal_code
        and datetime.fromisoformat(p["creation_date"]) > one_day_ago
    ]
    return awarded_proposals


def _send_message(instance_id: str, message: str, settings: Settings) -> None:
    headers = {
        "x-api-key": settings.market_api_key,
    }
    url = f"{settings.market_url}/v1/chat/send-message/{instance_id}"
    data = {"message": message}

    response = httpx.post(url, headers=headers, json=data)
    response.raise_for_status()


def solve_instances_handler() -> None:
    logger.info("Solve instances handler")
    awarded_proposals = get_awarded_proposals(SETTINGS)

    logger.info(f"Found {len(awarded_proposals)} awarded proposals")

    for p in awarded_proposals:
        instance_to_solve = _get_instance_to_solve(p["instance_id"], SETTINGS)
        try:
            if not instance_to_solve:
                continue

            if not instance_to_solve.provider_needs_response:
                continue

            message = _solve_instance(
                instance_to_solve,
                SETTINGS,
            )
            if not message:
                continue

            _send_message(
                instance_to_solve.instance["id"],
                message,
                SETTINGS,
            )
        except Exception as e:
            logger.error(f"Error solving instance id {instance_to_solve.instance['id']}: {e}")
