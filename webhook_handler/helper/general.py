import os
import shutil
import stat
import time
from pathlib import Path


def remove_dir(
    path: Path, max_retries: int = 3, delay: float = 0.1, log_success: bool = False
) -> None:
    """
    Helper method to remove a directory.

    Parameters:
        path (Path): The path to the directory to remove
        max_retries (int, optional): The maximum number of times to retry the command
        delay (float, optional): The delay between retries
        log_success (bool, optional): Whether to log the success message
    """

    if not path.exists():
        return

    def on_error(func, path, _) -> None:
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, onerror=on_error)
            # if log_success: logger.success(f"Directory {path} removed successfully")
            return
        except Exception as e:
            if attempt < max_retries:
                #   logger.warning(f"Failed attempt {attempt} removing {path}: {e}, retrying in {delay}s")
                time.sleep(delay)
            else:
                pass
                #  logger.error(f"Final attempt failed removing {path}, must be removed manually: {e}")
