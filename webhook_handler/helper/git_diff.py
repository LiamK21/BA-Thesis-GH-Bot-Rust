import os
import subprocess
from pathlib import Path

from webhook_handler.helper import general


def unified_diff(
    original: str,
    modified: str,
    fromfile: str = "original",
    tofile: str = "modified",
    context_lines: int = 3,
) -> str:
    """
    Prints the unified diff format of two strings. This is needed to calculate the diff
    given the new test file contents, since the evaluation harness works with the diff.

    Parameters:
        original (str): The original string.
        modified (str): The modified string.
        fromfile (str): Name of the "from" file in the diff output.
        tofile (str): Name of the "to" file in the diff output.
        context_lines (int): Number of lines before and after the changes. Default is 3.

    # Example usage
    original_text = \"\"\"line 1
    line 2
    line 3\"\"\"

    modified_text = \"\"\"line 1
    line 2 modified
    line 3
    line 4 added\"\"\"

    unified_diff(original_text, modified_text)

    """
    import difflib

    fromfile = "a/" + fromfile
    tofile = "b/" + tofile

    # Split the strings into lines
    lines1: list[str] = original.splitlines(keepends=True)
    lines2: list[str] = modified.splitlines(keepends=True)

    # Generate the unified diff
    diff = difflib.unified_diff(
        lines1, lines2, fromfile=fromfile, tofile=tofile, n=context_lines
    )

    git_header = f"diff --git {fromfile} {tofile}\n"

    # Print the diff
    return git_header + "".join(diff)


def unified_diff_with_function_context(
    original: str, modified: str, fname: str = "tempfile.rs", context_lines: int = 3
) -> str:
    """
    Writes two input strings to temporary files and uses `git diff --no-index`
    to compute the diff, including function context. This is important when you feed a diff
    to a model.

    Parameters:
    - original: Original file content.
    - modified: Modified file content.
    - fname: The filename to simulate in the diff output.
    - context_lines: The number of context lines to show in the diff.

    Returns:
    - A string containing the Git-formatted diff.
    """

    temp_dir = "./tmp_diff/"
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    try:
        file_dir = "/".join(fname.split("/")[:-1])
        Path(temp_dir, file_dir).mkdir(parents=True, exist_ok=True)

        original_file = os.path.join(temp_dir, f"{fname}.oldfordiffonly")
        modified_file = os.path.join(temp_dir, f"{fname}.newfordiffonly")

        with open(original_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(original)

        with open(modified_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(modified)

        # Run `git diff --no-index`
        result = subprocess.run(
            [
                "git",
                "diff",
                "-p",
                f"-U{context_lines}",
                "--no-index",
                original_file,
                modified_file,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        diff = result.stdout.strip()
        diff = diff.replace(temp_dir, "")  # make paths relative to target repo again
        diff = diff.replace(f"{fname}.oldfordiffonly", fname)  # >>
        diff = diff.replace(f"{fname}.newfordiffonly", fname)  # >>
        diff_lines = diff.splitlines()
        diff_lines.pop(1)  # this is the "index 09b...." line
        diff = "\n".join(diff_lines)
        return diff
    finally:
        general.remove_dir(Path(temp_dir))


def apply_patch(file_content_arr: list[str], patch: str) -> tuple[list[str], str]:
    """
    Apply a patch to file_content using the equivalent of "git apply".

    Parameters:
        file_content_arr (list): Original file contents
        patch (str): The patch content in unified diff format

    Returns:
        list: The updated file contents after applying the patch
        str: Any warnings which come up during the subprocess
    """

    ##################### Setup #####################
    temp_dir = "./tmp/"
    Path(temp_dir).mkdir(parents=True, exist_ok=True)

    # Important: in order for "git apply" to work, it needs to be inside of a .git repo
    # so we initialize one and delete the .git at the end
    res = subprocess.run(
        ["git", "init", "."],
        check=True,
        cwd=temp_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    #################### Collect ####################
    # extract all the names of the changed files and save them in a list.
    # each element of the list is of the form "a/<file_path>"
    patch_lines = patch.splitlines()
    original_file_aprefix_arr: list[str] = []
    for line in patch_lines:
        if line.startswith("--- "):
            original_file_aprefix: str = line.split(" ")[1]
            original_file_aprefix_arr.append(original_file_aprefix)

    # files mentioned in the patch should be the same number as the ones
    # whose content is provided. We also assume that the i-th file in the
    # first content corresponds to the i-th file in the second.
    assert len(original_file_aprefix_arr) == len(file_content_arr), patch

    file_path_arr = []
    for original_file_aprefix, file_content in zip(
        original_file_aprefix_arr, file_content_arr
    ):
        # remove intermediate folders: "a/django/tests/x.py" => "a/x.py"
        file_path = original_file_aprefix.replace("/", "_")

        file_path_arr.append(file_path)
        file_path_aprefix = "a/" + file_path
        file_path_bprefix = "b/" + file_path
        patch = patch.replace(
            original_file_aprefix, file_path_aprefix
        )  # update patch accordingly
        original_file_bprefix = "b/" + "/".join(original_file_aprefix.split("/")[1:])
        patch = patch.replace(original_file_bprefix, file_path_bprefix)
        with open(
            Path(temp_dir, file_path), "w", encoding="utf-8", newline="\n"
        ) as file:
            file.write(file_content)

    patch_path = "patch.diff"
    with open(
        Path(temp_dir, patch_path), "w", encoding="utf-8", newline="\n"
    ) as patch_file:
        patch_file.write(patch)

    ##################### Apply #####################
    try:
        res = subprocess.run(
            ["git", "apply", "--reject", patch_path],
            check=True,
            capture_output=True,
            text=True,
            cwd=temp_dir,
        )
    except subprocess.CalledProcessError as e:
        os.remove(temp_dir + patch_path)
        for file_path in file_path_arr:
            os.remove(temp_dir + file_path)

        Path(temp_dir, ".git").rmdir
        general.remove_dir(Path(temp_dir))

        # logger.critical(f"Failed to apply patch: {e}")
        raise AssertionError(f"Failed to apply patch")

    updated_content_arr: list[str] = []
    for file_path in file_path_arr:
        updated_content = Path(temp_dir, file_path).read_text(encoding="utf-8")
        os.remove(temp_dir + file_path)
        updated_content_arr.append(updated_content)

    #################### Cleanup ####################
    os.remove(temp_dir + patch_path)
    general.remove_dir(Path(temp_dir, ".git"))
    general.remove_dir(Path(temp_dir))

    return updated_content_arr, res.stderr
