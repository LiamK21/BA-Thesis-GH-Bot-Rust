import json
import os
from datetime import datetime
from pathlib import Path

import tree_sitter_rust
from dotenv import load_dotenv
from tree_sitter import Language

from webhook_handler.models import LLM


class Config:
    """Configuration for the bot runner"""

    def __init__(self):
        load_dotenv()  # take environment variables from .env.
        self.github_webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")

        self.HEADER = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.github_token}",
        }

        self.execution_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.curr_attempt = 0
        self.root_dir = Path.cwd()
        self.generated_tests_dir = Path(self.root_dir, "generated_tests")
        self.is_server = Path("/home/runner").is_dir()

        self.parsing_language = Language(tree_sitter_rust.language())

        if self.is_server:
            self.webhook_raw_log_dir = Path("home", "ubuntu", "logs", "raw")
            self.bot_log_dir = Path("home", "ubuntu", "logs")
        else:
            self.webhook_raw_log_dir = Path(self.root_dir, "bot_logs", "raw")
            self.bot_log_dir = Path(self.root_dir, "bot_logs")
        self.gen_test_dir = Path(self.root_dir, "generated_tests")

        self.pr_log_dir = None
        self.output_dir = None
        self.cloned_repo_dir = None
        self.executed_tests = None

        Path(self.webhook_raw_log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.bot_log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.generated_tests_dir).mkdir(parents=True, exist_ok=True)

    def setup_pr_related_dirs(
        self, pr_id: str, owner: str, repo: str, payload: dict
    ) -> None:
        """
        Sets up all directories related to a specific PR.

        Parameters:
            pr_id (str): ID of the PR
        """

        self._setup_pr_log_dir(pr_id, owner, repo, payload)
        self._setup_log_paths()

    def _setup_pr_log_dir(
        self, pr_id: str, owner: str, repo: str, payload: dict
    ) -> None:
        """
        Sets up directory for logger output file (one directory per PR)

        Parameters:
            pr_id (str): ID of the PR
        """

        self.pr_log_dir = Path(
            self.bot_log_dir,
            f"{owner}_{repo}",
            pr_id + "_%s" % self.execution_timestamp,
        )
        self.cloned_repo_dir = f"tmp_repo_dir_{owner}_{repo}_{pr_id}"
        Path(self.pr_log_dir).mkdir(parents=True, exist_ok=True)
        with open(
            Path(
                self.pr_log_dir,
                f"payload_{owner}_{repo}_{pr_id}_{self.execution_timestamp}.json",
            ),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(payload, f, indent=4)

    def _setup_log_paths(self):
        self.executed_tests = Path(self.bot_log_dir, "executed_tests.txt")
        self.executed_tests.touch(exist_ok=True)
        if not Path(self.bot_log_dir, "results.csv").exists():
            Path(self.bot_log_dir, "results.csv").write_text(
                "{:<9},{:<30},{:<9},{:<45}\n".format(
                    "prNumber", "model", "iAttempt", "stop"
                ),
                encoding="utf-8",
            )

    def setup_output_dir(self, i_attempt: int, model: LLM) -> None:
        """
        Sets up directory for generated runner files (one directory per run)

        Parameters:
            i_attempt (int): Attempt number
            model (LLM): Model name
        """
        # Assert setup_pr_log_dir has been called
        assert (
            self.pr_log_dir is not None
        ), "PR log directory must be set before setting up output directory."
        self.output_dir = Path(self.pr_log_dir, "i%s" % (i_attempt + 1) + "_%s" % model)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir, "generation").mkdir(parents=True)
        self.curr_attempt += 1
