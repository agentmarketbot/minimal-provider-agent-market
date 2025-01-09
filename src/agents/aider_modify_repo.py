import argparse
from pathlib import Path

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo
from loguru import logger

from .prompt_cache import PromptCache


def modify_repo_with_aider(model_name, solver_command, test_command=None) -> str:
    io = InputOutput(yes=True)
    model = Model(model_name)
    prompt_cache = PromptCache()

    # Clean up expired cache entries
    prompt_cache.cleanup_expired()

    # Check if we have a cached response
    cached_response = prompt_cache.get(solver_command, model_name)
    if cached_response:
        logger.info("Using cached response")
        return cached_response

    coder = Coder.create(
        main_model=model,
        io=io,
        edit_format="diff",
        suggest_shell_commands=False,
        use_git=False,
    )

    coder.run(solver_command)
    response = coder.partial_response_content

    if response:
        prompt_cache.store(solver_command, model_name, response)

    return response


def main():
    parser = argparse.ArgumentParser(description="Modify a repository with Aider.")
    parser.add_argument(
        "--model-name", type=str, required=True, help="The name of the model to use."
    )
    parser.add_argument(
        "--solver-command",
        type=str,
        required=True,
        help="The command to run the solver.",
    )
    parser.add_argument(
        "--test-command",
        type=str,
        required=False,
        help="An optional test command to run.",
    )

    args = parser.parse_args()

    modify_repo_with_aider(args.model_name, args.solver_command, args.test_command)


if __name__ == "__main__":
    main()
