from dataclasses import dataclass


@dataclass
class PipelineInputs:
    """
    Holds all data about a PR, its diffs together with the sliced code, test file information and available imports.
    """

    pr_data: any
    pr_diff_ctx: any
    problem_statement: str
    filename_to_insert_test: str | None = None
    test_file_content: str | None = None
    test_file_content_sliced: str | None = None
    available_packages: str | None = None
    available_relative_imports: str | None = None
    code_sliced: list[str] | None = None

    def __post_init__(self):
        # ensure instance types
        from webhook_handler.models.pr_data import PullRequestData

        assert isinstance(self.pr_data, PullRequestData)
        from webhook_handler.services.pr_diff_context import PullRequestDiffContext

        assert isinstance(self.pr_diff_ctx, PullRequestDiffContext)
