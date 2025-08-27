from pathlib import Path

from config import Config
from gh_service import GitHubService

from webhook_handler.models import LLM, PullRequestData, PullRequestDiffContext

USED_MODELS = [LLM.GPT4o, LLM.LLAMA, LLM.DEEPSEEK]

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
        self.prepare_environment()
        try:
                self._generation_completed = self._execute_attempt(model, i_attempt=curr_attempt)
                # self._logger.success(success_msg)
                # self._record_result(self._pr_data.number, curr_model, curr_i_attempt + 1, self._generation_completed)
            # except ExecutionError as e:
                # self._record_result(self._pr_data.number, curr_model, curr_i_attempt + 1, str(e))
        except Exception as e:
                print(f"Failed with unexpected error:\n{e}")
                # self._logger.critical("Failed with unexpected error:\n%s" % e)
                # self._record_result(self._pr_data.number, curr_model, curr_i_attempt + 1, "unexpected error")

        def _save_generated_test() -> None:
            gen_test = Path(self._config.output_dir, "generation", "generated_test.txt").read_text(encoding="utf-8")
            new_filename = f"{self._execution_id}_{self._config.output_dir.name}.txt"
            Path(self._config.gen_test_dir, new_filename).write_text(gen_test, encoding="utf-8")
            #self._logger.success(f"Test file copied to {self._config.gen_test_dir.name}/{new_filename}")

        
        
        return self._generation_completed

    def _execute_attempt(
            self,
            model: LLM,
            i_attempt: int
    ) -> bool:
        """
        Executes a single attempt.

        Parameters:
            model (LLM): Model to use
            i_attempt (int): Number of current attempt

        Returns:
            bool: True if generation was successful, False otherwise
        """

        if self._environment_prepared:
            print("Environment ready – preparation skipped")
            #self._logger.info("Environment ready – preparation skipped")
        else:
            self._prepare_environment()
            self._environment_prepared = True


        assert self._pipeline_inputs is not None, "Pipeline inputs must be prepared before executing an attempt."
        assert self._llm_handler is not None, "LLM handler must be prepared before executing an attempt."
        assert self._cst_builder is not None, "CST builder must be prepared before executing an attempt."
        assert self._docker_service is not None, "Docker service must be prepared before executing an attempt."
        assert self._gh_api is not None, "GitHub API must be prepared before executing an attempt."
        
        generator = TestGenerator(
            self._config,
            self._pipeline_inputs,
            self._mock_response,
            self._post_comment,
            templates.COMMENT_TEMPLATE,
            self._gh_api,
            self._cst_builder,
            self._docker_service,
            self._llm_handler,
            i_attempt,
            model,
        )

        return generator.generate()
    
    
    def prepare_environment(self) -> None:
        """
        Prepares all services and data used in each attempt. Only has to execute once to cut down on API calls.
        """
        
        # Check if PR has a linked issue and verify that it is a bug
        linked_issue_description = self._gh_service.get_linked_data()
        if linked_issue_description:
            print("Linked issue found")
            #logger.info("Linked issue found")
        else:
            print("No linked issue found, raising exception")
            #logger.info("No Linked issue found, raising exception")
            raise Exception("No linked issue found")
        
        # Prepare directories
        
        # Clone repository and checkout to the PR branch
        # Get the PR diff and stuff like that
        # Build docker image if not exists
        # return and execute
        