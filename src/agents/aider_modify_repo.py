import argparse

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model


def modify_repo_with_aider(
    editor_model_name, solver_command, test_command=None, architect_model_name: str | None = None
) -> None:
    io = InputOutput(yes=True)
    if architect_model_name is not None:
        model = Model(architect_model_name, editor_model=editor_model_name)
        coder = Coder.create(
            main_model=model,
            io=io,
            auto_commits=False,
            dirty_commits=False,
            edit_format="architect",
        )
    else:
        model = Model(editor_model_name)
        coder = Coder.create(main_model=model, io=io)

    coder.run(solver_command)

    if test_command:
        coder.run(f"/test {test_command}")


def main():
    parser = argparse.ArgumentParser(description="Modify a repository with Aider.")
    parser.add_argument(
        "--editor-model-name", type=str, required=True, help="The name of the model to use."
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
    parser.add_argument(
        "--architect-model-name",
        type=str,
        required=False,
        help="The name of the architect model to use.",
    )

    args = parser.parse_args()
    print(args)
    # modify_repo_with_aider(
    #     args.editor_model_name, args.solver_command, args.test_command, args.architect_model_name
    # )


if __name__ == "__main__":
    main()
