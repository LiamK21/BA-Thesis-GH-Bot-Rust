import logging
from pathlib import Path

############### Custom Logger Tags ##############
# Marker: used to mark a new section (i.e., new PR, new run)
MARKER_LEVEL_NUM = 21
logging.addLevelName(MARKER_LEVEL_NUM, "MARKER")


def marker(self, message, *args, **kws):
    if self.isEnabledFor(MARKER_LEVEL_NUM):
        self._log(MARKER_LEVEL_NUM, message, args, **kws)


logging.Logger.marker = marker

# Success: used to mark the successful completion of an action
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def success(self, message, *args, **kws):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)


logging.Logger.success = success

# Fail: used to mark the failure of an action
FAIL_LEVEL_NUM = 35
logging.addLevelName(FAIL_LEVEL_NUM, "FAIL")


def fail(self, message, *args, **kws):
    if self.isEnabledFor(FAIL_LEVEL_NUM):
        self._log(FAIL_LEVEL_NUM, message, args, **kws)


logging.Logger.fail = fail


class ColoredFormatter(logging.Formatter):
    """
    Reformats the console output and applied custom colors
    """

    RESET = "\x1b[0m"
    COLORS = {
        logging.DEBUG: "\x1b[90m",  # grey
        logging.INFO: "\x1b[94m",  # bright blue
        MARKER_LEVEL_NUM: "\x1b[96m",  # bright cyan
        SUCCESS_LEVEL_NUM: "\x1b[32m",  # green
        logging.WARNING: "\x1b[38;5;208m",  # bright orange
        FAIL_LEVEL_NUM: "\x1b[31m",  # red
        logging.ERROR: "\x1b[31;1m",  # bold red
        logging.CRITICAL: "\x1b[91;1m",  # bold bright red
    }

    def format(self, record) -> str:
        """
        Applies colors to console output.
        """

        color = self.COLORS.get(record.levelno, self.RESET)
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}"


############# Logger Initialization #############
def configure_logger(pr_log_dir: Path, execution_id: str) -> None:
    """
    Sets up the global logger for PR test generation

    Parameters:
        pr_log_dir (Path): Path to the PR log directory
        execution_id (str): ID of the PR test generation execution
    """

    logfile = Path(pr_log_dir, f"{execution_id}.log")

    # get root logger
    root = logging.getLogger()
    root.setLevel("INFO")

    # remove any existing handlers (so pytest reruns don't duplicate)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = "[%(asctime)s] %(levelname)-9s: %(message)s"

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel("INFO")
    ch.setFormatter(ColoredFormatter(fmt, datefmt="%H:%M:%S"))
    root.addHandler(ch)

    # file handler
    fh = logging.FileHandler(logfile, mode="w", encoding="utf-8")
    fh.setLevel("INFO")
    fh.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(fh)
