import logging
from typing import cast

from pr_file_diff import PullRequestFileDiff

from webhook_handler.gh_service import GitHubService

logger = logging.getLogger(__name__)


class PullRequestDiffContext:
    """
    Holds all the PullRequestFileDiffs for one PR and provides common operations.
    """

    def __init__(self, base_commit: str, head_commit: str, gh_service: GitHubService):
        self._gh_service = gh_service
        self._pr_file_diffs: list[PullRequestFileDiff] = []
        raw_files = gh_service.fetch_pr_files()
        for raw_file in raw_files:
            file_name = raw_file["filename"]
            before = gh_service.fetch_file_version(base_commit, file_name)
            after = gh_service.fetch_file_version(head_commit, file_name)
            if before != after:
                self._pr_file_diffs.append(
                    PullRequestFileDiff(file_name, cast(str, before), cast(str, after))
                )

    @property
    def source_code_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_source_code_file
        ]

    @property
    def non_source_code_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_non_source_code_file
        ]

    @property
    def test_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_test_file
        ]

    @property
    def has_at_least_one_source_code_file(self) -> bool:
        return len(self.source_code_file_diffs) > 0

    @property
    def has_at_least_one_test_file(self) -> bool:
        return len(self.test_file_diffs) > 0

    @property
    def fulfills_requirements(self) -> bool:
        return (
            self.has_at_least_one_source_code_file
            and not self.has_at_least_one_test_file
            and len(self.non_source_code_file_diffs) == 0
        )

    @property
    def golden_code_patch(self) -> str:
        return (
            "\n\n".join(
                pr_file_diff.unified_code_diff()
                for pr_file_diff in self.source_code_file_diffs
            )
            + "\n\n"
        )
