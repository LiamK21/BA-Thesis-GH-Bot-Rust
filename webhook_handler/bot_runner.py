import json
from pathlib import Path

from webhook_handler.models import LLM, PipelineInputs, PullRequestData
from webhook_handler.services import (Config, CSTBuilder, DockerService,
                                      GitHubService, LLMHandler,
                                      PullRequestDiffContext, TestGenerator)


class BotRunner:
    """Handles running the bot"""

    def __init__(
        self, payload: dict, config: Config, post_comment: bool = False
    ) -> None:
        self._pr_data = PullRequestData.from_payload(payload)
        self._execution_id = f"{self._pr_data.repo}_{self._pr_data.number}"
        self._config = config
        self._post_comment = post_comment
        self._generation_completed = False
        self._environment_prepared = False

        self._gh_service = GitHubService(config, self._pr_data)
        self._issue_statement = None
        self._pr_diff_ctx = None
        self._pipeline_inputs = None
        self._llm_handler = None
        self._docker_service = None
        self._cst_builder = None

    def is_valid_pr(self) -> tuple[str, bool]:
        """
        PR must have linked issue and source code changes.

        Returns:
            str: Message to deliver to client
            bool: True if PR is valid, False otherwise
        """

        # self._logger.marker(f"=============== Running Payload #{self._pr_data.number} ===============")
        # self._logger.marker("================ Preparing Environment ===============")
        self._issue_statement = self._gh_service.get_linked_data()
        if not self._issue_statement:
            # helpers.remove_dir(self._config.pr_log_dir)
            self._gh_api = None
            self._issue_statement = None
            self._pdf_candidate = None
            return "No linked issue found", False

        self._pr_diff_ctx = PullRequestDiffContext(
            self._pr_data.base_commit, self._pr_data.head_commit, self._gh_service
        )
        if not self._pr_diff_ctx.fulfills_requirements:
            # helpers.remove_dir(self._config.pr_log_dir)
            self._gh_api = None
            self._issue_statement = None
            self._pdf_candidate = None
            self._pr_diff_ctx = None
            return "Must modify source code files only", False

        return "Payload is being processed...", True

    def execute_runner(self, curr_attempt: int, model: LLM) -> bool:
        """
        Execute whole pipeline with 5 attempts per model (optional o4-mini execution).

        Parameters:
            execute_mini (bool, optional): If True, executes additional attempt with mini model

        Returns:
            bool: True if the generation was successful, False otherwise
        """
        # Prepare environment
        self.prepare_environment(curr_attempt, model)

        assert self._pipeline_inputs is not None
        assert self._llm_handler is not None
        assert self._cst_builder is not None
        assert self._docker_service is not None
        assert self._gh_service is not None

        generator = TestGenerator(
            self._config,
            self._pipeline_inputs,
            # self._mock_response,
            self._post_comment,
            self._gh_service,
            self._cst_builder,
            self._docker_service,
            self._llm_handler,
            i_attempt=curr_attempt,
            model=model,
        )

        try:
            result = generator.generate()
            assert self._config.output_dir is not None
            gen_test = Path(
                self._config.output_dir, "generation", "generated_test.txt"
            ).read_text(encoding="utf-8")
            new_filename = f"{self._execution_id}_{self._config.output_dir.name}.txt"
            Path(self._config.gen_test_dir, new_filename).write_text(
                gen_test, encoding="utf-8"
            )
            return result

        except Exception as e:
            print(f"Failed with unexpected error:\n{e}")
            return False

    def prepare_environment(self, curr_attempt: int, model: LLM) -> None:
        """
        Prepares all services and data used in each attempt. Only has to execute once to cut down on API calls.
        """

        # Check if PR has a linked issue and verify that it is a bug
        self._issue_statement = self._gh_service.get_linked_data()
        if self._issue_statement:
            print("Linked issue found")
            # logger.info("Linked issue found")
        else:
            print("No linked issue found, raising exception")
            # logger.info("No Linked issue found, raising exception")
            raise Exception("No linked issue found")

        # Prepare directories
        assert (
            self._config.pr_log_dir is not None
        ), "PR log directory must be set before preparing environment."

        # Create a directory for the current attempt with the current model
        attempt_instance_dir = Path(
            self._config.pr_log_dir, f"i{curr_attempt + 1}_{model}"
        )
        attempt_instance_dir.mkdir(parents=True, exist_ok=True)

        # Create a generation subdirectory within the attempt directory
        Path(attempt_instance_dir, "generation").mkdir(parents=True, exist_ok=True)

        # Get the file contents
        if self._pr_diff_ctx is None:
            self._pr_diff_ctx = PullRequestDiffContext(
                self._pr_data.base_commit, self._pr_data.head_commit, self._gh_service
            )
        if len(self._pr_diff_ctx.source_code_file_diffs) == 0:
            raise Exception("No source code changes found in PR")

        # Clone repository and checkout to the PR branch
        assert (
            self._config.cloned_repo_dir is not None
        ), "Cloned repo dir name must be set"

        # If repository has not been cloned yet, clone it
        # if not Path(self._config.cloned_repo_dir).exists():
        #     self._gh_service.clone_repo()

        # # If it is a different repository, clone the new one
        # if self._config.cloned_repo_dir.find(self._pr_data.repo) == -1:
        #     self._gh_service.clone_repo(update=True)

        # Get the PR diff and stuff like that

        self._cst_builder = CSTBuilder(self._config.parsing_language, self._pr_diff_ctx)
        # Check if this line is necessary
        # code_sliced = self._cst_builder.get_sliced_code_files()

        # Build docker image if not exists
        self._docker_service = DockerService(self._config.root_dir, self._pr_data)

        owner = self._pr_data.owner
        dockerfile_path = Path(
            self._config.root_dir, "dockerfiles", f"Dockerfile_{owner}"
        )
        self._docker_service.build_image(dockerfile_path)

        # Gather Pipeline data
        self._pipeline_inputs = PipelineInputs(
            pr_data=self._pr_data,
            pr_diff_ctx=self._pr_diff_ctx,
            # code_sliced,
            problem_statement=self._issue_statement,
        )

        # Setup LLM handler
        self._llm_handler = LLMHandler(self._config, self._pipeline_inputs)

    def _record_result(
        self, number: str, model: LLM, i_attempt: int, stop: bool | str
    ) -> None:
        """
        Writes result to csv.

        Parameters:
            number (str): The number of the PR
            model (LLM): The model
            i_attempt (int): The attempt number
            stop (bool | str): The stop flag or an error string
        """

        with open(Path(self._config.bot_log_dir, "results.csv"), "a") as f:
            f.write(
                "{:<9},{:<30},{:<9},{:<45}\n".format(number, model, i_attempt, stop)
            )
