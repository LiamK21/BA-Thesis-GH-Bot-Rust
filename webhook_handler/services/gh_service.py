import re
import subprocess
import time

import requests

from webhook_handler.models import PullRequestData
from webhook_handler.services import Config

GH_API_URL = "https://api.github.com/repos"
GH_RAW_URL = "https://raw.githubusercontent.com"


class GitHubService:
    def __init__(self, config: Config, pr_data: PullRequestData) -> None:
        self._config = config
        self._pr_data = pr_data

    def fetch_pr_files(self) -> dict:
        """
        Fetches all files of a pull request.

        Returns:
            dict: All raw files
        """

        url = f"{GH_API_URL}/{self._pr_data.owner}/{self._pr_data.repo}/pulls/{self._pr_data.number}/files"
        response = requests.get(url, headers=self._config.HEADER)
        if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_time = reset_time - int(time.time()) + 1
            # logger.warning(f"Rate limit exceeded. Waiting for {wait_time} seconds...")
            time.sleep(max(wait_time, 1))
            return self.fetch_pr_files()

        response.raise_for_status()
        return response.json()

    def get_linked_data(self) -> str | None:
        """
        Checks and fetches a linked issue.

        Returns:
            str: The linked issue title and description
            str: The candidate PDF filename
        """
        owner = self._pr_data.owner
        repo = self._pr_data.repo
        pr_description = self._pr_data.description
        pr_title = self._pr_data.title
        # The regex patterns look for phrases like "Closes #123", "Fixes #123", "Resolves #123" in the PR title and description.
        # It will actually only capture the issue/bug number.
        issue_pattern = r"\b(?:Closes|Fixes|Resolves)\s+#(\d+)\b"
        url_pattern = rf"\bhttps://github\.com/{re.escape(owner)}/{re.escape(repo)}/issues/(\d+)\b"

        issue_description: str = f"{pr_title} {pr_description}"
        issue_matches: list[str] = re.findall(
            issue_pattern, issue_description, re.IGNORECASE
        )
        url_matches: list[str] = re.findall(
            url_pattern, issue_description, re.IGNORECASE
        )
        all_matches = issue_matches + url_matches
        for match in all_matches:
            issue_nr = int(match)
            if not issue_nr:
                continue

            linked_issue_description = self._get_github_issue(issue_nr)
            if linked_issue_description:
                return linked_issue_description
        return None

    def fetch_file_version(self, commit: str, file_name: str) -> str:
        """
        Fetches the version of a file at a specific commit.

        Parameters:
            commit (str): Commit hash
            file_name (str): File name
            get_bytes (bool, optional): Get bytes instead of text

        Returns:
            str | bytes: File contents
        """

        url = f"{GH_RAW_URL}/{self._pr_data.owner}/{self._pr_data.repo}/{commit}/{file_name}"
        response = requests.get(url, headers=self._config.HEADER)
        if response.status_code == 200:
            return response.text  # File exists
        return ""  # File most likely does not exist (anymore)

    def clone_repo(self, update: bool = False) -> None:
        """
        Clones a GitHub repository.
        """
        if update:
            self._config.cloned_repo_dir = f"tmp_repo_dir_{self._pr_data.owner}_{self._pr_data.repo}_{self._pr_data.id}"
        assert self._config.cloned_repo_dir, "Cloned repo dir not set in config"
        # logger.info(f"Cloning repository https://github.com/{self._pr_data.owner}/{self._pr_data.repo}.git")
        _ = subprocess.run(
            [
                "git",
                "clone",
                f"https://github.com/{self._pr_data.owner}/{self._pr_data.repo}.git",
                self._config.cloned_repo_dir,
            ],
            capture_output=True,
            check=True,
        )
        # logger.success(f"Cloning successful")

    def _get_github_issue(self, number: int) -> str | None:
        """
        Fetches a GitHub issue.

        Parameters:
            number (int): The number of the issue

        Returns:
            str | None: The GitHub issue title and description
        """
        url = f"{GH_API_URL}/{self._pr_data.owner}/{self._pr_data.repo}/issues/{number}"
        response = requests.get(url, headers=self._config.HEADER)
        if response.status_code == 200:
            issue_data: dict = response.json()

            if "pull_request" in issue_data:
                # logger.warning(f"Linked issue #{number} is a pull request, not an issue")
                return None

            # Check that it is a bug issue (label contains 'bug')
            issue_is_bug = False
            issue_type: str | None = issue_data.get("type", "")
            if issue_type != None and issue_type.lower() == "bug":
                issue_is_bug = True

            issue_labels: list[dict[str, str]] = issue_data.get("labels", [])
            if any(label.get("name", "").__contains__("bug") for label in issue_labels):
                issue_is_bug = True
            if issue_is_bug:
                return "\n".join(
                    value
                    for value in (issue_data["title"], issue_data["body"])
                    if value
                )

            return None

        # logger.warning("No GitHub issue found")
        return None
