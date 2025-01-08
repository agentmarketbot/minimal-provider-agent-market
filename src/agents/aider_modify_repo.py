import argparse
from pathlib import Path

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo


def modify_repo_with_aider(model_name, solver_command, test_command=None) -> str:
    io = InputOutput(yes=True)
    model = Model(model_name)

    coder = Coder.create(
        main_model=model,
        io=io,
        edit_format="diff",
        suggest_shell_commands=False,
        use_git=False,
        cache_prompts=True,  # Enable prompt caching
    )

    # Add cache control headers to the message
    messages = [{"role": "system", "content": solver_command}]
    if coder.add_cache_headers:
        messages[0]["cache-control"] = "max-age=604800"  # Cache for 1 week

    # Initialize required attributes
    coder.cur_messages = []
    coder.multi_response_content = ""
    coder.partial_response_content = ""
    coder.partial_response_function_call = dict()
    coder.mdstream = None
    coder.stream = False  # Disable streaming to avoid mdstream issues

    # Send messages and get response
    list(coder.send(messages))

    if coder.partial_response_content:
        content = coder.partial_response_content
        if "NO_RESPONSE_NEEDED" in content:
            return None
        return content

    return None


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
